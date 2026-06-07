import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime

from backtest_data import get_backtester_root

# Paths
TELEGRAM_SCRAPER_ROOT = Path(__file__).parent.parent.resolve()
BACKTESTER_ROOT = get_backtester_root(TELEGRAM_SCRAPER_ROOT)
REPORTS_DIR = BACKTESTER_ROOT / "backtest_reports"
OUTPUT_HTML = TELEGRAM_SCRAPER_ROOT / "report" / "backtest_results.html"

def parse_summary_txt(summary_path):
    if not summary_path.exists():
        return None
    try:
        content = summary_path.read_text(encoding="utf-8")
    except Exception:
        try:
            content = summary_path.read_text(encoding="cp1252")
        except Exception:
            return None
            
    data = {}
    lines = content.splitlines()
    if lines:
        first_line = lines[0].strip()
        if "MT5" in first_line:
            data["_platform_detected"] = "MT5"
        elif "MT4" in first_line or "MetaTrader" in first_line:
            data["_platform_detected"] = "MT4"
            
    if "check MT4 logs" in content:
        data["_platform_detected"] = "MT4"
    elif "check MT5 logs" in content:
        data["_platform_detected"] = "MT5"

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            data[key] = val
            
    return data

def main():
    print("[*] Scanne Backtest-Berichte...")
    if not REPORTS_DIR.exists():
        print(f"[!] Berichtsordner nicht gefunden: {REPORTS_DIR}")
        return
        
    runs = []
    
    # Iterate through subdirectories
    for folder in REPORTS_DIR.iterdir():
        if not folder.is_dir():
            continue
        if folder.name == "batch_runs":
            continue
            
        summary_path = folder / "summary.txt"
        if not summary_path.exists():
            continue
            
        summary_data = parse_summary_txt(summary_path)
        if not summary_data:
            continue
            
        # Extract timestamp from folder name: e.g. "Arthur EA_M15_EURUSD_20250101_20260604_193721"
        folder_name = folder.name
        match = re.search(r"_(\d{8})_(\d{6})$", folder_name)
        timestamp_str = ""
        if match:
            date_part = match.group(1)
            time_part = match.group(2)
            timestamp_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
        else:
            # Fallback to file creation time
            stat = summary_path.stat()
            timestamp_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
        # Check for BacktestReport.png or report.png (equity curve)
        report_png_path = folder / "BacktestReport.png"
        if not report_png_path.exists():
            report_png_path = folder / "report.png"
            
        has_equity_curve = report_png_path.exists()
        image_name = report_png_path.name if has_equity_curve else ""
        
        relative_image_path = report_png_path.resolve().as_uri() if has_equity_curve else ""
        
        # Parse metrics safely
        profit = 0.0
        try:
            profit = float(summary_data.get("total_profit", "0").replace("USD", "").strip())
        except ValueError:
            pass
            
        drawdown = 0.0
        try:
            drawdown = float(summary_data.get("max_drawdown", "0").replace("%", "").strip())
        except ValueError:
            pass
            
        trades = 0
        try:
            trades = int(summary_data.get("total_trades", "0"))
        except ValueError:
            pass
            
        win_rate = 0.0
        try:
            win_rate = float(summary_data.get("win_rate", "0").replace("%", "").strip())
        except ValueError:
            pass
            
        profit_factor = 0.0
        try:
            profit_factor = float(summary_data.get("profit_factor", "0"))
        except ValueError:
            pass
            
        sharpe_ratio = 0.0
        try:
            sharpe_ratio = float(summary_data.get("sharpe_ratio", "0"))
        except ValueError:
            pass
            
        # Clean Expert Name
        expert_raw = summary_data.get("expert", "Unknown")
        platform = summary_data.get("_platform_detected", "UNKNOWN")
        if platform == "UNKNOWN":
            if ".ex5" in expert_raw.lower() or ".mq5" in expert_raw.lower():
                platform = "MT5"
            elif ".ex4" in expert_raw.lower() or ".mq4" in expert_raw.lower():
                platform = "MT4"
            elif "mt5" in folder_name.lower():
                platform = "MT5"
            elif "mt4" in folder_name.lower():
                platform = "MT4"

        expert = expert_raw
        if "ScraperTemp\\" in expert:
            expert = expert.replace("ScraperTemp\\", "")
        if ".ex5" in expert:
            expert = expert.replace(".ex5", "")
        if ".ex4" in expert:
            expert = expert.replace(".ex4", "")
        if ".mq5" in expert:
            expert = expert.replace(".mq5", "")
        if ".mq4" in expert:
            expert = expert.replace(".mq4", "")
            
        runs.append({
            "folder_name": folder_name,
            "expert": expert,
            "platform": platform,
            "symbol": summary_data.get("symbol", "EURUSD"),
            "period": summary_data.get("period", "M15"),
            "from_date": summary_data.get("from", ""),
            "to_date": summary_data.get("to", ""),
            "model": summary_data.get("model", ""),
            "deposit": summary_data.get("deposit", ""),
            "leverage": summary_data.get("leverage", ""),
            "status": summary_data.get("status", "FAILED").split("-")[0].strip(),
            "status_full": summary_data.get("status", "FAILED"),
            "profit": profit,
            "drawdown": drawdown,
            "trades": trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "timestamp": timestamp_str,
            "has_curve": has_equity_curve,
            "image_path": relative_image_path if has_equity_curve else ""
        })
        
    # Sort runs by timestamp descending
    runs.sort(key=lambda x: x["timestamp"], reverse=True)
    print(f"[+] {len(runs)} Backtests erfolgreich geladen.")
    
    # Calculate stats
    total_runs = len(runs)
    success_runs = sum(1 for r in runs if r["status"] == "SUCCESS")
    failed_runs = total_runs - success_runs
    avg_profit = sum(r["profit"] for r in runs if r["status"] == "SUCCESS") / max(1, success_runs)
    max_profit = max((r["profit"] for r in runs), default=0.0)
    
    # Find best EA by total success profit
    ea_profits = {}
    for r in runs:
        if r["status"] == "SUCCESS":
            ea_profits[r["expert"]] = ea_profits.get(r["expert"], 0.0) + r["profit"]
    best_ea = max(ea_profits, key=ea_profits.get, default="N/A")
    
    # HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MetaTrader Backtest Ergebnisse</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0b0b14;
            --bg-secondary: #121225;
            --bg-glass: rgba(255, 255, 255, 0.02);
            --border-glass: rgba(255, 255, 255, 0.05);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-primary); color: var(--text-primary); min-height: 100vh; padding: 2rem; }}
        h1, h2, h3, h4 {{ font-family: 'Outfit', sans-serif; }}
        
        header {{ margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; }}
        .header-title h1 {{ font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, var(--text-secondary) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.3rem; }}
        .header-title p {{ color: var(--text-secondary); font-size: 0.95rem; }}
        .btn-back {{ background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary); padding: 0.6rem 1.2rem; border-radius: 8px; text-decoration: none; font-size: 0.9rem; font-weight: 600; transition: all 0.3s ease; }}
        .btn-back:hover {{ background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.2); }}

        /* Stats Grid */
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem; }}
        .stat-card {{ background: var(--bg-secondary); border: 1px solid var(--border-glass); border-radius: 12px; padding: 1.5rem; position: relative; overflow: hidden; }}
        .stat-card::before {{ content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--accent-blue); }}
        .stat-card.success::before {{ background: var(--accent-green); }}
        .stat-card.profit::before {{ background: var(--accent-green); }}
        .stat-card.ea::before {{ background: var(--accent-purple); }}
        .stat-label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); margin-bottom: 0.5rem; }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; color: #fff; }}

        /* Filters */
        .filters-card {{ background: var(--bg-secondary); border: 1px solid var(--border-glass); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem; display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: flex-end; }}
        .filter-group {{ display: flex; flex-direction: column; gap: 0.5rem; flex: 1; min-width: 180px; }}
        .filter-group label {{ font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }}
        .filter-group input, .filter-group select {{ background: var(--bg-primary); border: 1px solid var(--border-glass); color: #fff; padding: 0.7rem 1rem; border-radius: 8px; font-family: inherit; font-size: 0.9rem; outline: none; transition: border-color 0.3s; width: 100%; }}
        .toggle-group {{ display: flex; background: var(--bg-primary); border: 1px solid var(--border-glass); padding: 0.3rem; border-radius: 8px; height: 42px; align-items: center; }}
        .toggle-btn {{ background: transparent; border: none; color: var(--text-secondary); padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: all 0.3s; }}
        .toggle-btn.active {{ background: var(--bg-glass); color: #fff; border: 1px solid var(--border-glass); }}

        /* Badges */
        .badge-status {{ padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-status.success {{ background: rgba(16, 185, 129, 0.1); color: var(--accent-green); }}
        .badge-status.failed {{ background: rgba(239, 68, 68, 0.1); color: var(--accent-red); }}
        
        .badge-platform {{ padding: 0.15rem 0.55rem; border-radius: 20px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge-platform.mt4 {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-platform.mt5 {{ background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }}
        .badge-platform.unknown {{ background: rgba(156, 163, 175, 0.1); color: var(--text-secondary); border: 1px solid rgba(156, 163, 175, 0.2); }}

        /* Results Grid */
        .results-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 2rem; }}
        .run-card {{ background: var(--bg-secondary); border: 1px solid var(--border-glass); border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.3s ease; }}
        .run-card-header {{ padding: 1.2rem; border-bottom: 1px solid var(--border-glass); display: flex; justify-content: space-between; align-items: flex-start; }}
        .ea-name {{ font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 0.2rem; }}
        .ea-meta {{ font-size: 0.8rem; color: var(--text-secondary); display: flex; gap: 0.8rem; }}
        .run-card-body {{ padding: 1.2rem; flex: 1; }}
        .run-metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.2rem; }}
        .metric-item {{ text-align: center; background: var(--bg-glass); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border-glass); }}
        .metric-title {{ font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.3rem; }}
        .metric-value {{ font-size: 1rem; font-weight: 700; }}
        .metric-value.positive {{ color: var(--accent-green); }}
        .metric-value.negative {{ color: var(--accent-red); }}
        .equity-curve-container {{ width: 100%; height: 150px; background: #000; border-radius: 8px; overflow: hidden; display: flex; justify-content: center; align-items: center; cursor: pointer; position: relative; }}
        .equity-curve-container img {{ width: 100%; height: 100%; object-fit: contain; transition: transform 0.3s; }}
        .run-card-footer {{ padding: 1rem 1.2rem; background: rgba(255,255,255,0.01); border-top: 1px solid var(--border-glass); font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between; }}

        /* Table */
        .table-container {{ background: var(--bg-secondary); border: 1px solid var(--border-glass); border-radius: 16px; overflow-x: auto; display: none; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }}
        th, td {{ padding: 1rem 1.2rem; border-bottom: 1px solid var(--border-glass); }}
        th {{ color: var(--text-secondary); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; background: rgba(0,0,0,0.1); }}
        .tr-expandable {{ cursor: pointer; transition: background 0.3s; }}
        .tr-expandable:hover {{ background: rgba(255,255,255,0.02); }}
        .expanded-row {{ background: rgba(0, 0, 0, 0.2); display: none; }}
        .expanded-content {{ display: flex; gap: 2rem; padding: 1.5rem; align-items: center; }}
        .expanded-details {{ flex: 1; display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }}
        .detail-p {{ font-size: 0.85rem; color: var(--text-secondary); }}
        .detail-p span {{ color: #fff; font-weight: 600; }}
        .expanded-image {{ width: 320px; height: 160px; background: #000; border-radius: 8px; overflow: hidden; display: flex; justify-content: center; align-items: center; cursor: pointer; }}
        
        .modal {{ display: none; position: fixed; z-index: 1000; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); justify-content: center; align-items: center; }}
        .modal-content {{ max-width: 90%; max-height: 85%; border-radius: 12px; overflow: hidden; border: 1px solid var(--border-glass); background: #000; display: flex; justify-content: center; align-items: center; }}
        .modal-content img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .close-btn {{ position: absolute; top: 2rem; right: 2rem; font-size: 2.5rem; color: #fff; cursor: pointer; }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>📊 MetaTrader Backtest Ergebnisse</h1>
            <p>Übersicht aller ausgeführten Strategietests auf dem lokalen System</p>
        </div>
        <a href="dashboard.html" class="btn-back"><span>←</span> Roboter-Dashboard</a>
    </header>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Gesamte Tests</div>
            <div class="stat-value">{total_runs}</div>
        </div>
        <div class="stat-card success">
            <div class="stat-label">Erfolgreich</div>
            <div class="stat-value">{success_runs}</div>
        </div>
        <div class="stat-card profit">
            <div class="stat-label">⌀ Gewinn (Erfolg)</div>
            <div class="stat-value" style="color: var(--accent-green);">{avg_profit:+.2f} USD</div>
        </div>
        <div class="stat-card ea">
            <div class="stat-label">Bester Roboter (Summe)</div>
            <div class="stat-value" style="font-size: 1.4rem; padding-top: 0.3rem;">{best_ea}</div>
        </div>
    </div>

    <div class="filters-card">
        <div class="filter-group">
            <label for="search-ea">Roboter Name:</label>
            <input type="text" id="search-ea" placeholder="Suchen..." onkeyup="filterDataAndResetPage()">
        </div>
        <div class="filter-group" style="flex:0 0 auto; min-width:auto;">
            <label>Plattform:</label>
            <div class="toggle-group">
                <button class="toggle-btn active" id="btn-plat-all" onclick="setPlatform('ALL')">Alle</button>
                <button class="toggle-btn" id="btn-plat-mt4" onclick="setPlatform('MT4')">MT4</button>
                <button class="toggle-btn" id="btn-plat-mt5" onclick="setPlatform('MT5')">MT5</button>
            </div>
        </div>
        <div class="filter-group">
            <label for="filter-symbol">Symbol:</label>
            <select id="filter-symbol" onchange="filterDataAndResetPage()">
                <option value="ALL">Alle Symbole</option>
                <option value="EURUSD">EURUSD</option>
                <option value="XAUUSD">XAUUSD</option>
                <option value="GBPUSD">GBPUSD</option>
                <option value="USDJPY">USDJPY</option>
                <option value="AUDCAD">AUDCAD</option>
                <option value="AUDNZD">AUDNZD</option>
                <option value="NZDCAD">NZDCAD</option>
            </select>
        </div>
        <div class="filter-group">
            <label for="filter-period">Timeframe:</label>
            <select id="filter-period" onchange="filterDataAndResetPage()">
                <option value="ALL">Alle Timeframes</option>
                <option value="M1">M1</option>
                <option value="M5">M5</option>
                <option value="M15">M15</option>
                <option value="M30">M30</option>
                <option value="H1">H1</option>
                <option value="H4">H4</option>
                <option value="D1">D1</option>
            </select>
        </div>
        <div class="filter-group">
            <label for="sort-by">Sortieren nach:</label>
            <select id="sort-by" onchange="filterDataAndResetPage()">
                <option value="timestamp-desc">Datum (Neueste zuerst)</option>
                <option value="profit-desc">Gewinn (Höchster zuerst)</option>
                <option value="drawdown-asc">Drawdown (Geringster zuerst)</option>
                <option value="profitfactor-desc">Profit Factor (Höchster zuerst)</option>
                <option value="trades-desc">Trades (Meiste zuerst)</option>
            </select>
        </div>
        <div class="toggle-group">
            <button class="toggle-btn active" id="btn-grid" onclick="setView('grid')">Kacheln</button>
            <button class="toggle-btn" id="btn-table" onclick="setView('table')">Tabelle</button>
        </div>
    </div>

    <div id="results-grid-view" class="results-grid"></div>
    <div id="pagination-grid"></div>
    
    <div id="results-table-view" class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Roboter</th>
                    <th>Plattform</th>
                    <th>Symbol</th>
                    <th>Period</th>
                    <th>Gewinn</th>
                    <th>Drawdown</th>
                    <th>PF</th>
                    <th>Trades</th>
                    <th>Status</th>
                    <th>Datum</th>
                </tr>
            </thead>
            <tbody id="table-body"></tbody>
        </table>
    </div>
    <div id="pagination-table"></div>

    <div id="image-modal" class="modal" onclick="closeModal()">
        <span class="close-btn">&times;</span>
        <div class="modal-content" onclick="event.stopPropagation()">
            <img id="modal-img" src="" alt="Equity Curve Large">
        </div>
    </div>

    <script>
        const backtestData = {json.dumps(runs, indent=2)};
        let currentView = 'grid';
        let currentPlatform = 'ALL';
        let currentPage = 1;
        const PAGE_SIZE_GRID = 24;
        const PAGE_SIZE_TABLE = 30;

        function getPlatform(item) {{
            if (item && item.platform) return item.platform;
            if (!item || !item.expert) return 'UNKNOWN';
            const lower = item.expert.toLowerCase();
            if (lower.includes('.ex5') || lower.includes('mt5')) return 'MT5';
            if (lower.includes('.ex4') || lower.includes('mt4')) return 'MT4';
            return 'UNKNOWN';
        }}

        function setPlatform(platform) {{
            currentPlatform = platform;
            currentPage = 1;
            document.getElementById('btn-plat-all').classList.toggle('active', platform === 'ALL');
            document.getElementById('btn-plat-mt4').classList.toggle('active', platform === 'MT4');
            document.getElementById('btn-plat-mt5').classList.toggle('active', platform === 'MT5');
            render();
        }}

        function setView(view) {{
            currentView = view;
            currentPage = 1;
            document.getElementById('btn-grid').classList.toggle('active', view === 'grid');
            document.getElementById('btn-table').classList.toggle('active', view === 'table');
            
            document.getElementById('results-grid-view').style.display = view === 'grid' ? 'grid' : 'none';
            document.getElementById('results-table-view').style.display = view === 'table' ? 'block' : 'none';
            
            render();
        }}

        function filterData() {{
            const search = document.getElementById('search-ea').value.toLowerCase();
            const symbol = document.getElementById('filter-symbol').value;
            const period = document.getElementById('filter-period').value;
            const sortBy = document.getElementById('sort-by').value;

            let filtered = backtestData.filter(item => {{
                const matchesSearch = item.expert.toLowerCase().includes(search);
                const matchesSymbol = symbol === 'ALL' || item.symbol === symbol;
                const matchesPeriod = period === 'ALL' || item.period === period;
                const platform = getPlatform(item);
                const matchesPlatform = currentPlatform === 'ALL' || platform === currentPlatform;
                return matchesSearch && matchesSymbol && matchesPeriod && matchesPlatform;
            }});

            filtered.sort((a, b) => {{
                if (sortBy === 'timestamp-desc') {{
                    return new Date(b.timestamp) - new Date(a.timestamp);
                }} else if (sortBy === 'profit-desc') {{
                    return b.profit - a.profit;
                }} else if (sortBy === 'drawdown-asc') {{
                    return a.drawdown - b.drawdown;
                }} else if (sortBy === 'profitfactor-desc') {{
                    return b.profit_factor - a.profit_factor;
                }} else if (sortBy === 'trades-desc') {{
                    return b.trades - a.trades;
                }}
                return 0;
            }});
            return filtered;
        }}

        function filterDataAndResetPage() {{
            currentPage = 1;
            render();
        }}

        function renderPaginationBar(total, pageSize, containerId) {{
            const totalPages = Math.ceil(total / pageSize);
            const bar = document.getElementById(containerId);
            if (!bar) return;
            const start = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
            const end = Math.min(currentPage * pageSize, total);
            bar.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:1.25rem 1.5rem; background:rgba(0,0,0,0.15); border-top:1px solid var(--border-glass); border-radius:0 0 16px 16px; margin-top:1.5rem;">
                    <span style="color:var(--text-secondary); font-size:0.9rem;">Zeige <strong style="color:#fff">${{start}}–${{end}}</strong> von <strong style="color:#fff">${{total}}</strong> Ergebnissen</span>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        <button onclick="changePage(${{currentPage - 1}})" ${{currentPage <= 1 ? 'disabled' : ''}}
                            style="background:rgba(255,255,255,0.05); border:1px solid var(--border-glass); color:${{currentPage <= 1 ? 'var(--text-secondary)' : '#fff'}}; padding:0.4rem 0.9rem; border-radius:8px; cursor:${{currentPage <= 1 ? 'default' : 'pointer'}}; font-size:0.85rem; opacity:${{currentPage <= 1 ? '0.4' : '1'}};">← Zurück</button>
                        <span style="color:#fff; font-weight:600; font-size:0.9rem; min-width:100px; text-align:center;">Seite ${{currentPage}} / ${{Math.max(1, totalPages)}}</span>
                        <button onclick="changePage(${{currentPage + 1}})" ${{currentPage >= totalPages ? 'disabled' : ''}}
                            style="background:rgba(255,255,255,0.05); border:1px solid var(--border-glass); color:${{currentPage >= totalPages ? 'var(--text-secondary)' : '#fff'}}; padding:0.4rem 0.9rem; border-radius:8px; cursor:${{currentPage >= totalPages ? 'default' : 'pointer'}}; font-size:0.85rem; opacity:${{currentPage >= totalPages ? '0.4' : '1'}};">Weiter →</button>
                    </div>
                </div>`;
        }}

        function changePage(page) {{
            const data = filterData();
            const pageSize = currentView === 'grid' ? PAGE_SIZE_GRID : PAGE_SIZE_TABLE;
            const totalPages = Math.ceil(data.length / pageSize);
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            render();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function openModal(imgSrc) {{
            const modal = document.getElementById('image-modal');
            const img = document.getElementById('modal-img');
            img.src = imgSrc;
            modal.style.display = 'flex';
        }}

        function closeModal() {{ document.getElementById('image-modal').style.display = 'none'; }}

        function toggleRow(id) {{
            const detailRow = document.getElementById('detail-' + id);
            if (detailRow.style.display === 'table-row') {{
                detailRow.style.display = 'none';
            }} else {{
                document.querySelectorAll('.expanded-row').forEach(row => row.style.display = 'none');
                detailRow.style.display = 'table-row';
            }}
        }}

        function render() {{
            const allData = filterData();
            const pageSize = currentView === 'grid' ? PAGE_SIZE_GRID : PAGE_SIZE_TABLE;
            const totalPages = Math.ceil(allData.length / pageSize);
            if (currentPage > totalPages && totalPages > 0) currentPage = totalPages;
            const start = (currentPage - 1) * pageSize;
            const data = allData.slice(start, start + pageSize);
            
            if (currentView === 'grid') {{
                const container = document.getElementById('results-grid-view');
                const frag = document.createDocumentFragment();
                container.innerHTML = '';
                document.getElementById('pagination-table').innerHTML = '';
                
                if (allData.length === 0) {{
                    container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-secondary);">Keine Ergebnisse gefunden.</div>';
                    document.getElementById('pagination-grid').innerHTML = '';
                    return;
                }}
                
                data.forEach(item => {{
                    const profitClass = item.profit > 0 ? 'positive' : (item.profit < 0 ? 'negative' : '');
                    const profitSign = item.profit > 0 ? '+' : '';
                    const curveHtml = item.has_curve 
                        ? `<div class="equity-curve-container" onclick="openModal('${{item.image_path}}')"><img loading="lazy" src="${{item.image_path}}" alt="Equity Curve"></div>`
                        : `<div class="equity-curve-container"><div class="no-image">Kein Chart verfügbar</div></div>`;
                    const platform = getPlatform(item);
                    const platformLabel = platform === 'UNKNOWN' ? '?' : platform;
                    const platformClass = platform.toLowerCase();
                    const div = document.createElement('div');
                    div.className = 'run-card';
                    div.innerHTML = `
                        <div class="run-card-header">
                            <div>
                                <div class="ea-name">${{item.expert}}</div>
                                <div class="ea-meta">
                                    <span>${{item.symbol}}</span>
                                    <span>${{item.period}}</span>
                                </div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:0.35rem;">
                                <span class="badge-platform ${{platformClass}}">${{platformLabel}}</span>
                                <span class="badge-status ${{item.status.toLowerCase()}}">${{item.status}}</span>
                            </div>
                        </div>
                        <div class="run-card-body">
                            <div class="run-metrics">
                                <div class="metric-item">
                                    <div class="metric-title">Gewinn</div>
                                    <div class="metric-value ${{profitClass}}">${{profitSign}}${{item.profit.toFixed(2)}}</div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-title">Drawdown</div>
                                    <div class="metric-value" style="color: ${{item.drawdown > 15 ? 'var(--accent-red)' : 'var(--text-primary)'}}">${{item.drawdown.toFixed(1)}}%</div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-title">Profit Factor</div>
                                    <div class="metric-value" style="color: ${{item.profit_factor >= 1.5 ? 'var(--accent-green)' : 'var(--text-primary)'}}">${{item.profit_factor.toFixed(2)}}</div>
                                </div>
                            </div>
                            ${{curveHtml}}
                        </div>
                        <div class="run-card-footer">
                            <span>Trades: ${{item.trades}} (Win: ${{item.win_rate.toFixed(1)}}%)</span>
                            <span>${{item.timestamp}}</span>
                        </div>
                    `;
                    frag.appendChild(div);
                }});
                container.appendChild(frag);
                renderPaginationBar(allData.length, pageSize, 'pagination-grid');
            }} else {{
                const tbody = document.getElementById('table-body');
                tbody.innerHTML = '';
                document.getElementById('pagination-grid').innerHTML = '';
                
                if (allData.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 3rem; color: var(--text-secondary);">Keine Ergebnisse gefunden.</td></tr>';
                    document.getElementById('pagination-table').innerHTML = '';
                    return;
                }}
                
                const frag = document.createDocumentFragment();
                data.forEach((item, idx) => {{
                    const globalIdx = start + idx;
                    const profitClass = item.profit > 0 ? 'positive' : (item.profit < 0 ? 'negative' : '');
                    const profitSign = item.profit > 0 ? '+' : '';
                    const plat = getPlatform(item);
                    const platCls = plat.toLowerCase();
                    const tr = document.createElement('tr');
                    tr.className = 'tr-expandable';
                    tr.onclick = () => toggleRow(globalIdx);
                    tr.innerHTML = `
                        <td style="font-weight: 600; color: #fff;">${{item.expert}}</td>
                        <td><span class="badge-platform ${{platCls}}">${{plat === 'UNKNOWN' ? '?' : plat}}</span></td>
                        <td>${{item.symbol}}</td>
                        <td>${{item.period}}</td>
                        <td class="${{profitClass}}" style="font-weight: 700;">${{profitSign}}${{item.profit.toFixed(2)}}</td>
                        <td>${{item.drawdown.toFixed(1)}}%</td>
                        <td>${{item.profit_factor.toFixed(2)}}</td>
                        <td>${{item.trades}}</td>
                        <td><span class="badge-status ${{item.status.toLowerCase()}}" style="padding: 0.1rem 0.4rem; font-size: 0.7rem;">${{item.status}}</span></td>
                        <td style="font-size: 0.8rem; color: var(--text-secondary);">${{item.timestamp}}</td>
                    `;
                    frag.appendChild(tr);
                    const tr2 = document.createElement('tr');
                    tr2.className = 'expanded-row';
                    tr2.id = 'detail-' + globalIdx;
                    tr2.innerHTML = `
                        <td colspan="10">
                            <div class="expanded-content">
                                <div class="expanded-details">
                                    <div class="detail-p">Zeitraum: <span>${{item.from_date}} bis ${{item.to_date}}</span></div>
                                    <div class="detail-p">Hebel / Startkapital: <span>${{item.leverage}} / ${{item.deposit}}</span></div>
                                    <div class="detail-p">Modell: <span>${{item.model}}</span></div>
                                    <div class="detail-p">Sharpe Ratio: <span>${{item.sharpe_ratio.toFixed(2)}}</span></div>
                                    <div class="detail-p">Win Rate: <span>${{item.win_rate.toFixed(1)}}%</span></div>
                                    <div class="detail-p">Status Details: <span>${{item.status_full}}</span></div>
                                </div>
                                ${{item.has_curve ? `
                                <div class="expanded-image" onclick="openModal('${{item.image_path}}')">
                                    <img src="${{item.image_path}}" alt="Equity Curve">
                                </div>` : '<div style="color: var(--text-secondary);">Kein Chart verfügbar</div>'}}
                            </div>
                        </td>
                    `;
                    frag.appendChild(tr2);
                }});
                tbody.appendChild(frag);
                renderPaginationBar(allData.length, pageSize, 'pagination-table');
            }}
        }}
        render();
    </script>
</body>
</html>
"""
    
    # Write output HTML
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"[+] Backtest Dashboard erfolgreich generiert unter: {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
