# -*- coding: utf-8 -*-
import sys
import json
import subprocess
import argparse
from pathlib import Path

from backtest_data import (
    get_backtester_root,
)

def parse_args():
    parser = argparse.ArgumentParser(description="Einzelläufer-Backtester für TelegramScraper EAs")
    parser.add_argument("--expert", type=str, required=True, help="Name des Expert Advisors")
    parser.add_argument("--platform", type=str, default="MT5", choices=["MT4", "MT5"], help="MetaTrader Platform (MT4 oder MT5)")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Währungspaar")
    parser.add_argument("--period", type=str, default="M15", help="Zeiteinheit")
    parser.add_argument("--from-date", type=str, default="2025-01-01", help="Startdatum (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, default="2026-06-01", help="Enddatum (YYYY-MM-DD)")
    parser.add_argument("--model", type=str, default="1", help="Tick-Modell (0=Every tick, 1=1m OHLC, 2=Open price, 4=Real ticks)")
    parser.add_argument("--deposit", type=str, default="10000", help="Startkapital")
    parser.add_argument("--leverage", type=str, default="1:100", help="Hebel")
    parser.add_argument("--keep-open", action="store_true", help="MetaTrader nach dem Test offen lassen und sichtbar ausführen")
    return parser.parse_args()

def find_ea_and_set_files(project_root, expert_name, platform):
    clean_name = expert_name
    if clean_name.startswith("ScraperTemp\\"):
        clean_name = clean_name.replace("ScraperTemp\\", "")
    for ext in [".ex5", ".ex4", ".mq5", ".mq4"]:
        if clean_name.lower().endswith(ext):
            clean_name = clean_name[:-len(ext)]
    
    suffix = ".ex5" if platform == "MT5" else ".ex4"
    
    search_dirs = [
        project_root / "extracted_data" / "forex_files",
        project_root / "report" / "robots"
    ]
    
    ea_path = None
    set_path = None
    
    # Try exact match first (case insensitive)
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob(f"*{suffix}"):
            if path.name.lower() == f"{clean_name.lower()}{suffix}":
                ea_path = path.resolve()
                break
        if ea_path:
            break
            
    # If not found, try fuzzy match (contains)
    if not ea_path:
        for directory in search_dirs:
            if not directory.exists():
                continue
            for path in directory.rglob(f"*{suffix}"):
                if clean_name.lower() in path.name.lower():
                    ea_path = path.resolve()
                    break
            if ea_path:
                break
                
    # Search for a .set file
    if ea_path:
        # Check in the same directory first
        parent_dir = ea_path.parent
        set_files = list(parent_dir.glob("*.set"))
        if set_files:
            set_path = set_files[0].resolve()
        else:
            # Check for a set file matching the clean name
            for directory in search_dirs:
                if not directory.exists():
                    continue
                for path in directory.rglob("*.set"):
                    if clean_name.lower() in path.name.lower():
                        set_path = path.resolve()
                        break
                if set_path:
                    break
                    
    return ea_path, set_path

def map_model_to_int(model_str):
    model_str = str(model_str).strip().lower()
    
    # String mapping based on MetaTrader descriptions
    if "every tick" in model_str or "everytick" in model_str or model_str == "0":
        return 0
    elif "1 minute" in model_str or "1m" in model_str or "ohlc" in model_str or model_str == "1":
        return 1
    elif "open price" in model_str or "open_price" in model_str or model_str == "2":
        return 2
    elif "real tick" in model_str or "real_tick" in model_str or "realtick" in model_str or model_str == "4":
        return 4
        
    try:
        val = int(model_str)
        if val in [0, 1, 2, 3, 4]:
            return val
    except ValueError:
        pass
        
    return 1 # Default to 1m OHLC

def main():
    args = parse_args()
    
    src_dir = Path(__file__).parent.resolve()
    project_root = src_dir.parent
    
    backtester_root = get_backtester_root(project_root)
    backtester_target = backtester_root / "target"
    
    print(f"[*] Suche Dateien für Expert Advisor '{args.expert}' ({args.platform})...")
    ea_path, set_path = find_ea_and_set_files(project_root, args.expert, args.platform)
    
    if not ea_path:
        print(f"[!] Fehler: Ausführbare Datei (.ex5/.ex4) für '{args.expert}' wurde nicht gefunden.")
        sys.exit(1)
        
    print(f"  [+] EA-Pfad gefunden: {ea_path}")
    if set_path:
        print(f"  [+] Parameterdatei (.set) gefunden: {set_path}")
    else:
        print("  [i] Keine spezifische Parameterdatei (.set) gefunden. Verwende Default-Einstellungen.")
        
    # Format dates to YYYY-MM-DD
    from_date = args.from_date.replace(".", "-")
    to_date = args.to_date.replace(".", "-")
    
    model_int = map_model_to_int(args.model)
    
    # Qualify run
    run_info = {
        "expert_name": f"{args.expert}_{args.symbol}_{args.period}",
        "expert_path": str(ea_path),
        "symbol": args.symbol,
        "period": args.period,
        "set_file_path": str(set_path) if set_path else ""
    }
    
    # Clean deposit and leverage
    deposit_clean = "".join(c for c in str(args.deposit) if c.isdigit())
    deposit_int = int(deposit_clean) if deposit_clean else 10000
    
    leverage_clean = args.leverage.replace("\\", "")

    # Construct config
    single_config = {
        "output_directory": str((backtester_root / "backtest_reports" / "batch_runs").resolve()),
        "settings": {
            "from_date": from_date,
            "to_date": to_date,
            "deposit": deposit_int,
            "currency": "USD",
            "leverage": leverage_clean,
            "model": model_int,
            "use_virtual_desktop": not args.keep_open,
            "auto_kill_mt5": not args.keep_open
        },
        "runs": [run_info]
    }
    
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_out_path = data_dir / "single_backtest_config.json"
    config_out_path.write_text(json.dumps(single_config, indent=2), encoding="utf-8")
    print(f"[+] Konfigurationsdatei geschrieben nach: {config_out_path}")
    
    # Locate Backtester JAR
    if not backtester_target.exists():
        print(f"[!] Target-Verzeichnis des Backtesters existiert nicht: {backtester_target}")
        sys.exit(1)
        
    jars = list(backtester_target.glob("mt5-backtester-*.jar"))
    if not jars:
        print(f"[!] Kein compiled JAR im Verzeichnis {backtester_target} gefunden.")
        sys.exit(1)
        
    jar_path = jars[0].resolve()
    print(f"[*] Gefundene Backtester-Anwendung: {jar_path}")
    
    # Exec backtester CLI
    print(f"[*] Starte Backtester in CLI-Modus...")
    cmd = ["java", "-jar", str(jar_path), "--cli", str(config_out_path)]
    print(f"  [>] Command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   text=True, encoding="utf-8", errors="replace", bufsize=1, cwd=str(backtester_root))
        
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            
        process.wait()
        
        if process.returncode == 0:
            print("\n[+] Backtest erfolgreich abgeschlossen!")
        else:
            print(f"\n[!] Backtester wurde mit Fehlercode {process.returncode} beendet.")
            sys.exit(process.returncode)
            
    except KeyboardInterrupt:
        print("\n[!] Backtest abgebrochen durch den Benutzer.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[!] Fehler beim Starten des Backtesters: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
