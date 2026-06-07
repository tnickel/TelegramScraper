import sys
import json
import subprocess
import argparse
from pathlib import Path

from backtest_data import (
    determine_periods_list,
    determine_symbols_list,
    get_backtester_root,
    load_backtest_robots_from_db,
    resolve_backtest_assets,
)

def parse_args():
    parser = argparse.ArgumentParser(description="Automatisierter Batch-Backtester für TelegramScraper EAs")
    parser.add_argument("--min-score", type=int, default=50, help="Mindest-Score im Dashboard (Default: 50)")
    parser.add_argument("--symbol", type=str, default=None, help="Erzwinge ein bestimmtes Währungspaar für alle Tests")
    parser.add_argument("--period", type=str, default=None, help="Erzwinge eine bestimmte Zeiteinheit (z.B. M15, H1) für alle Tests")
    parser.add_argument("--from-date", type=str, default="2025-01-01", help="Startdatum im Format YYYY-MM-DD")
    parser.add_argument("--to-date", type=str, default="2026-06-01", help="Enddatum im Format YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="Maximale Anzahl der zu testenden Roboter (für Testläufe)")
    parser.add_argument("--dry-run", action="store_true", help="Erstellt nur die JSON-Konfiguration, startet aber keinen Backtest")
    parser.add_argument("--model", type=int, default=1, choices=[0, 1, 2, 3, 4], 
                        help="Tick-Modell: 0=Every tick, 1=1m OHLC (Default), 2=Open price, 4=Real ticks")
    parser.add_argument("--keep-open", action="store_true", help="MetaTrader nach dem Testen offen lassen und sichtbar ausführen")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Pfade auflösen
    src_dir = Path(__file__).parent.resolve()
    project_root = src_dir.parent
    
    # Backtester-Pfad
    backtester_root = get_backtester_root(project_root)
    backtester_target = backtester_root / "target"
    
    # 1. Daten einlesen
    print("[*] Lese Roboter-Daten aus data/telegram_scraper.db...")
    try:
        robots_data = load_backtest_robots_from_db(project_root)
    except Exception as e:
        print(f"[!] Fehler beim Laden der Dashboard-Datenbank: {e}")
        sys.exit(1)

    if not robots_data:
        print("[!] Keine Daten zum Verarbeiten. Beende.")
        sys.exit(1)
    print(f"  [+] {len(robots_data)} Roboter erfolgreich geladen.")
        
    # 2. Roboter filtern und für Backtest vorbereiten
    runs = []
    for r in robots_data:
        # Filter 1: Score & Risikowarnungen
        if r.get("score", 0) < args.min_score:
            continue
        if "scam" in r.get("risk", "").lower():
            continue

        # Filter 2: Suche nach ausführbaren MT4/MT5 Dateien (.ex5, .ex4)
        exec_path, set_path = resolve_backtest_assets(project_root, r)
        if not exec_path:
            continue
        
        # Bestimme Symbole und Periods
        run_symbols = [args.symbol] if args.symbol else determine_symbols_list(r.get("pairs"))
        run_periods = [args.period] if args.period else determine_periods_list(r.get("timeframe"))
        
        for sym in run_symbols:
            for prd in run_periods:
                runs.append({
                    "expert_name": f"{r['name']}_{sym}_{prd}",
                    "expert_path": str(exec_path),
                    "symbol": sym,
                    "period": prd,
                    "set_file_path": str(set_path) if set_path else ""
                })

    # Limitierung anwenden falls gesetzt
    if args.limit:
        runs = runs[:args.limit]
        
    print(f"[*] Filterung abgeschlossen. {len(runs)} Backtest-Runs qualifiziert.")
    if not runs:
        print("[!] Keine Roboter für die Kriterien gefunden. Beende.")
        sys.exit(1)
        
    # 3. JSON Konfiguration erstellen
    batch_config = {
        "output_directory": str((backtester_root / "backtest_reports" / "batch_runs").resolve()),
        "settings": {
            "from_date": args.from_date,
            "to_date": args.to_date,
            "deposit": 10000,
            "currency": "USD",
            "leverage": "1:100",
            "model": args.model,
            "use_virtual_desktop": not args.keep_open,
            "auto_kill_mt5": not args.keep_open
        },
        "runs": runs
    }
    
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_out_path = data_dir / "batch_config.json"
    config_out_path.write_text(json.dumps(batch_config, indent=2), encoding="utf-8")
    print(f"[+] Konfigurationsdatei geschrieben nach: {config_out_path}")
    
    if args.dry_run:
        print("[*] Dry-run aktiv. Backtester wird nicht gestartet.")
        return
        
    # 4. Suche shaded Backtester JAR
    if not backtester_target.exists():
        print(f"[!] Target-Verzeichnis des Backtesters existiert nicht: {backtester_target}")
        print("[!] Bitte baue zuerst das Backtester-Projekt mit Maven.")
        sys.exit(1)
        
    jars = list(backtester_target.glob("mt5-backtester-*.jar"))
    if not jars:
        print(f"[!] Kein compiled JAR im Verzeichnis {backtester_target} gefunden.")
        sys.exit(1)
        
    # Wähle das shaded JAR (das Maven-Shade Plugin ersetzt das Original, daher ist es das Standard-JAR)
    jar_path = jars[0].resolve()
    print(f"[*] Gefundene Backtester-Anwendung: {jar_path}")
    
    # 5. Starte Backtester CLI
    print(f"[*] Starte Backtester in CLI-Modus...")
    cmd = ["java", "-jar", str(jar_path), "--cli", str(config_out_path)]
    print(f"  [>] Command: {' '.join(cmd)}")
    
    try:
        # Führe Befehl aus und zeige den Output live an
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   text=True, encoding="utf-8", errors="replace", bufsize=1, cwd=str(backtester_root))
        
        for line in process.stdout:
            try:
                print(line, end="")
            except UnicodeEncodeError:
                try:
                    clean_line = line.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
                    print(clean_line, end="")
                except Exception:
                    pass
            
        process.wait()
        
        if process.returncode == 0:
            print("\n[+] Batch-Backtest erfolgreich abgeschlossen!")
            print(f"[+] Die Ergebnisse wurden unter {batch_config['output_directory']} gespeichert.")
        else:
            print(f"\n[!] Backtester wurde mit Fehlercode {process.returncode} beendet.")
            sys.exit(process.returncode)
            
    except KeyboardInterrupt:
        print("\n[!] Batch-Lauf abgebrochen durch den Benutzer.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[!] Fehler beim Starten des Backtesters: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
