import os
import sys
from pathlib import Path

def should_rebuild():
    workspace = Path(__file__).parent.parent.resolve()
    db_path = workspace / "data" / "telegram_scraper.db"
    stats_path = workspace / "extracted_data" / "stats.json"
    
    # If outputs are missing, we must rebuild
    if not db_path.exists() or not stats_path.exists():
        return True
        
    db_mtime = db_path.stat().st_mtime
    
    # 1. Check if generate_dashboard.py has been modified since the DB was created
    script_path = workspace / "src" / "generate_dashboard.py"
    if script_path.exists() and script_path.stat().st_mtime > db_mtime:
        return True
        
    # 2. Check if ea_insights.json is newer
    insights_path = workspace / "extracted_data" / "ea_insights.json"
    if insights_path.exists() and insights_path.stat().st_mtime > db_mtime:
        return True
        
    # 3. Check if any chat chunk file is newer
    chunks_dir = workspace / "extracted_data" / "chat_chunks"
    if chunks_dir.exists():
        for f in chunks_dir.glob("chat_chunk_*.txt"):
            if f.stat().st_mtime > db_mtime:
                return True
                
    # 4. Check if any forex file is newer
    forex_dir = workspace / "extracted_data" / "forex_files"
    if forex_dir.exists():
        for f in forex_dir.iterdir():
            if f.is_file() and f.stat().st_mtime > db_mtime:
                return True
                
    return False

if __name__ == "__main__":
    if should_rebuild():
        sys.exit(0) # Rebuild is needed
    else:
        sys.exit(1) # Rebuild is NOT needed
