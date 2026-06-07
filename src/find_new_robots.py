import os
import re
from pathlib import Path
from collections import defaultdict

# Pfade definieren
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
FOREX_FILES_DIR = WORKSPACE_DIR / "extracted_data" / "forex_files"
CHUNKS_DIR = WORKSPACE_DIR / "extracted_data" / "chat_chunks"

def clean_name(filename):
    # Entferne Dateiendung
    name, ext = os.path.splitext(filename)
    if ext.lower() not in ['.ex4', '.ex5', '.mq4', '.mq5', '.set']:
        return None
        
    # Entferne Telegram-Nachrichtenanhänge (z.B. _msg123456)
    name = re.sub(r'_msg\d+', '', name, flags=re.IGNORECASE)
    # Entferne typische Modifikationen/Labels
    name = re.sub(r'\b(?:fix|nodll|no_dll|unlocked|trial|free|demo|updated|version|final|pro|v?\d+(?:\.\d+)*)\b', '', name, flags=re.IGNORECASE)
    # Ersetze Klammern und Sonderzeichen mit Leerzeichen
    name = re.sub(r'[\(\)\[\]\{\}\-\+\~]', ' ', name)
    # Entferne mehrfache Leerzeichen
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Ignoriere sehr kurze Namen oder reine Zahlen
    if len(name) < 3 or name.isdigit():
        return None
        
    # Ignoriere generische Begriffe
    generics = {'ea', 'indicator', 'bot', 'robot', 'scalper', 'grid', 'martingale', 'set', 'preset', 'file', 'setup'}
    words = name.split()
    clean_words = [w for w in words if w.lower() not in generics]
    if not clean_words:
        return None
        
    return " ".join(clean_words)

def scan_for_candidates():
    print("[*] Starte Scan nach potenziellen neuen Forex-Robotern...")
    
    if not FOREX_FILES_DIR.exists():
        print(f"[!] Verzeichnis '{FOREX_FILES_DIR}' nicht gefunden. Bitte lasse zuerst die Extraktion laufen.")
        return
        
    # 1. Dateien nach Bereinigung clustern
    robot_files = defaultdict(list)
    for f in os.listdir(FOREX_FILES_DIR):
        c_name = clean_name(f)
        if c_name:
            key = c_name.lower()
            robot_files[key].append(f)
            
    print(f"  [+] {len(os.listdir(FOREX_FILES_DIR))} Dateien in {len(robot_files)} einzigartige Roboter-Kandidaten geclustert.")
    
    # 2. Chat-Nachrichten auf Vorhandensein dieser Namen scannen
    chunk_files = list(CHUNKS_DIR.glob("chat_chunk_*.txt"))
    if not chunk_files:
        print("[!] Keine Chat-Chunks in 'chat_chunks/' gefunden. Kann keine Erwähnungen zählen.")
        return
        
    print(f"  [*] Scanne {len(chunk_files)} Chat-Chunk-Dateien nach Erwähnungen...")
    
    # Lese alle Chunks in den Speicher für schnellen Zugriff
    all_chunks_text = []
    for chunk_file in chunk_files:
        try:
            all_chunks_text.append(chunk_file.read_text(encoding="utf-8").lower())
        except Exception:
            pass
            
    unified_text = "\n".join(all_chunks_text)
    
    # 3. Ergebnisse berechnen und sortieren
    candidates = []
    for key, files in robot_files.items():
        # Zähle wie oft der Name im Chat vorkommt
        count = unified_text.count(key)
        rep_name = clean_name(files[0])
        
        candidates.append({
            'name': rep_name,
            'key': key,
            'file_count': len(files),
            'chat_mentions': count,
            'files': files
        })
        
    # Sortieren nach Chat-Erwähnungen und Anzahl der Dateien
    candidates.sort(key=lambda x: (x['chat_mentions'], x['file_count']), reverse=True)
    
    print("\n" + "="*60)
    print("           POTENZIELLE NEUE Forex-Roboter (Top 30)")
    print("="*60)
    print(f"{'Name':<30} | {'Erwähnungen':<12} | {'Dateien':<8}")
    print("-"*60)
    
    for r in candidates[:30]:
        print(f"{r['name']:<30} | {r['chat_mentions']:<12} | {r['file_count']:<8}")
        
    print("="*60)
    print("\nTipp: Wenn du einen dieser Roboter im Dashboard registrieren möchtest,")
    print("füge ihn einfach der Liste 'ROBOTS_REGISTRY' in 'src/generate_dashboard.py' hinzu.")

if __name__ == "__main__":
    scan_for_candidates()
