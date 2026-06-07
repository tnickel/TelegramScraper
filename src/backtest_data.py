# -*- coding: utf-8 -*-
"""Shared data access helpers for TelegramScraper backtest selection."""

import json
import os
import sqlite3
from pathlib import Path


SUPPORTED_SYMBOLS = [
    "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "EURAUD", "EURCHF", "EURGBP",
    "EURJPY", "EURUSD", "GBPCHF", "GBPJPY", "GBPUSD",
    "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "XAGUSD", "XAUUSD", "XTIUSD",
]


def load_backtest_robots_from_db(project_root):
    """Load dashboard robot rows from the current SQLite database."""
    db_path = Path(project_root) / "data" / "telegram_scraper.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Dashboard-Datenbank nicht gefunden: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        robots = []
        rows = conn.execute(
            """
            SELECT id, name, strategy, risk, timeframe, pairs, description, mentions, score
            FROM robots
            ORDER BY mentions DESC
            """
        ).fetchall()

        for row in rows:
            files = [
                r["filename"]
                for r in conn.execute(
                    "SELECT filename FROM robot_files WHERE robot_id = ?",
                    (row["id"],),
                ).fetchall()
            ]
            robots.append({
                "id": row["id"],
                "name": row["name"],
                "strategy": row["strategy"],
                "risk": row["risk"],
                "timeframe": row["timeframe"],
                "pairs": row["pairs"],
                "description": row["description"],
                "mentions": row["mentions"],
                "score": row["score"],
                "files": files,
            })
        return robots
    finally:
        conn.close()


def load_local_config(project_root):
    config_path = Path(project_root) / "config.local.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def get_backtester_root(project_root):
    configured = os.environ.get("BACKTESTER_ROOT")
    if not configured:
        try:
            configured = load_local_config(project_root).get("backtester_root")
        except Exception:
            configured = None

    if configured:
        return Path(configured).expanduser().resolve()

    return (Path(project_root).parent / "Backtester").resolve()


def resolve_backtest_assets(project_root, robot):
    """Find executable EA and optional set file for a robot."""
    if "files" not in robot:
        raise KeyError(f"robot-Dict für '{robot.get('name', '?')}' enthält keinen 'files'-Key. "
                       "Wurde load_backtest_robots_from_db() verwendet?")
    project_root = Path(project_root)
    robot_folder = project_root / "report" / "robots" / robot["id"]
    forex_files_dir = project_root / "extracted_data" / "forex_files"

    search_dirs = []
    if robot_folder.exists():
        search_dirs.append(robot_folder)
    if forex_files_dir.exists():
        search_dirs.append(forex_files_dir)

    def first_existing_from_db(exts):
        for filename in robot.get("files", []):
            if Path(filename).suffix.lower() not in exts:
                continue
            for directory in search_dirs:
                candidate = directory / filename
                if candidate.exists():
                    return candidate.resolve()
        return None

    def first_existing_glob(exts):
        for ext in exts:
            for directory in search_dirs:
                matches = sorted(directory.glob(f"*{ext}"))
                if matches:
                    return matches[0].resolve()
        return None

    executable = first_existing_from_db({".ex5"}) or first_existing_from_db({".ex4"})
    if not executable and robot_folder.exists():
        executable = first_existing_glob([".ex5", ".ex4"])

    set_file = first_existing_from_db({".set"})
    if not set_file and robot_folder.exists():
        set_file = first_existing_glob([".set"])

    return executable, set_file


def determine_symbols_list(pairs_str):
    if not pairs_str:
        return ["EURUSD"]

    pairs_upper = pairs_str.upper()
    if any(k in pairs_upper for k in ["HAUPTWÄHRUNG", "FOREX", "MAJOR", "HAUPTPAARE", "FX"]):
        return ["EURUSD", "GBPUSD", "USDJPY"]

    matched = [sym for sym in SUPPORTED_SYMBOLS if sym in pairs_upper]
    if not matched:
        if "GOLD" in pairs_upper:
            return ["XAUUSD"]
        return ["EURUSD"]

    return matched


def determine_periods_list(timeframe_str):
    if not timeframe_str:
        return ["M15"]

    timeframe_upper = timeframe_str.upper()
    matched = [tf for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1"] if tf in timeframe_upper]
    if not matched:
        return ["M15"]

    return matched
