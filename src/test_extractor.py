#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test-Skript für telegram_extractor.py
=====================================
Dieses Skript erstellt Testdaten (eine Schein-result.json und simulierte Forex-Dateien),
führt den Extractor aus und überprüft das Ergebnis auf Korrektheit.
"""

import os
import json
import shutil
from pathlib import Path

def setup_test_environment():
    test_dir = Path("test_env")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Erstelle Unterordner für Telegram-Dateien
    files_dir = test_dir / "files"
    os.makedirs(files_dir)
    
    # Erstelle Dummy-Forex-Dateien im Quellordner
    dummy_files = {
        "robot1.ex4": b"DUMMY_EX4_DATA",
        "robot2.ex5": b"DUMMY_EX5_DATA",
        "indicator.mq4": b"DUMMY_MQ4_DATA",
        "logic.mq5": b"DUMMY_MQ5_DATA",
        "params.set": b"DUMMY_SET_DATA",
        "regular_doc.txt": b"SHOULD_NOT_BE_COPIED"  # Sollte ignoriert werden
    }
    
    for filename, content in dummy_files.items():
        with open(files_dir / filename, "wb") as f:
            f.write(content)
            
    # Erstelle eine Mock-result.json
    mock_json = {
        "name": "Forex Traders Group",
        "type": "public_supergroup",
        "id": 987654321,
        "messages": [
            {
                "id": 1,
                "type": "service",
                "date": "2026-06-01T10:00:00",
                "actor": "Admin",
                "action": "migrate_from_group"
            },
            {
                "id": 2,
                "type": "message",
                "date": "2026-06-01T10:05:00",
                "from": "John Doe",
                "from_id": "user_111",
                "text": "Hello everyone! Welcome to the group. Check out this new robot.",
                "file": "files/robot1.ex4",
                "media_type": "document"
            },
            {
                "id": 3,
                "type": "message",
                "date": "2026-06-01T10:15:00",
                "from": "Alice Smith",
                "from_id": "user_222",
                "text": [
                    "Here is the EX5 version: ",
                    {"type": "bold", "text": "robot2.ex5"},
                    "\nAnd the configuration file is attached below."
                ],
                "file": "files/robot2.ex5",
                "media_type": "document"
            },
            {
                "id": 4,
                "type": "message",
                "date": "2026-06-01T10:16:00",
                "from": "Alice Smith",
                "from_id": "user_222",
                "text": "This is the config file.",
                "file": "files/params.set",
                "media_type": "document"
            },
            {
                "id": 5,
                "type": "message",
                "date": "2026-06-01T10:20:00",
                "from": "Bob Johnson",
                "from_id": "user_333",
                "text": "Can someone share the source code?"
            },
            {
                "id": 6,
                "type": "message",
                "date": "2026-06-01T10:25:00",
                "from": "John Doe",
                "from_id": "user_111",
                "text": "Here is the source code for the indicator and robot logic.",
                "file": "files/indicator.mq4",
                "media_type": "document"
            },
            {
                "id": 7,
                "type": "message",
                "date": "2026-06-01T10:26:00",
                "from": "John Doe",
                "from_id": "user_111",
                "text": "And the mq5 logic.",
                "file": "files/logic.mq5",
                "media_type": "document"
            },
            {
                "id": 8,
                "type": "message",
                "date": "2026-06-01T10:30:00",
                "from": "Alice Smith",
                "from_id": "user_222",
                "text": "Here is a general description txt file.",
                "file": "files/regular_doc.txt",
                "media_type": "document"
            },
            {
                "id": 9,
                "type": "message",
                "date": "2026-06-01T10:35:00",
                "from": "Bob Johnson",
                "from_id": "user_333",
                "text": "This text message has no file."
            }
        ]
    }
    
    with open(test_dir / "result.json", "w", encoding="utf-8") as f:
        json.dump(mock_json, f, indent=4, ensure_ascii=False)
        
    return test_dir

def run_verification(test_dir):
    print("[*] Führe telegram_extractor.py auf Testdaten aus...")
    
    # Importiere die Hauptfunktion direkt aus telegram_extractor
    from telegram_extractor import parse_telegram_json, DEFAULT_EXTENSIONS
    
    output_dir = test_dir / "extracted_data"
    success = parse_telegram_json(
        json_path=test_dir / "result.json",
        output_dir=output_dir,
        chunk_size=3,  # Kleine Chunk-Größe zum Testen
        target_extensions=DEFAULT_EXTENSIONS
    )
    
    if not success:
        print("[-] Extraktor schlug fehl.")
        return False
        
    print("[*] Verifiziere Ausgabedateien...")
    
    # 1. Prüfe, ob die Forex-Dateien korrekt kopiert wurden
    copied_files_dir = output_dir / "forex_files"
    expected_copies = {"robot1.ex4", "robot2.ex5", "indicator.mq4", "logic.mq5", "params.set"}
    actual_copies = set(os.listdir(copied_files_dir))
    
    if expected_copies != actual_copies:
        print(f"[-] Fehler: Erwartete kopierte Dateien: {expected_copies}, erhalten: {actual_copies}")
        return False
    print("[+] Dateiverzeichnis-Prüfung erfolgreich.")
    
    # 2. Prüfe, ob die ignorierten Dateien ignoriert wurden
    if "regular_doc.txt" in actual_copies:
        print("[-] Fehler: regular_doc.txt wurde kopiert, sollte aber ignoriert werden.")
        return False
    print("[+] Ausschluss-Filter erfolgreich.")
    
    # 3. Prüfe Chunks (insgesamt 8 Nachrichten vom Typ 'message', chunk_size=3 -> 3 Chunks erwartet)
    chunks_dir = output_dir / "chat_chunks"
    expected_chunks = {"chat_chunk_001.txt", "chat_chunk_002.txt", "chat_chunk_003.txt"}
    actual_chunks = set(os.listdir(chunks_dir))
    
    if expected_chunks != actual_chunks:
        print(f"[-] Fehler: Erwartete Chunks: {expected_chunks}, erhalten: {actual_chunks}")
        return False
    print("[+] Chunks-Prüfung erfolgreich.")
    
    # Inhaltsprüfung eines Chunks (z.B. Alice Smith in Chunk 1)
    with open(chunks_dir / "chat_chunk_001.txt", "r", encoding="utf-8") as f:
        content = f.read()
        if "John Doe" not in content or "robot1.ex4" not in content:
            print("[-] Fehler: Chunk-Inhalt ist fehlerhaft.")
            return False
            
    # 4. Prüfe Berichte
    if not (output_dir / "forex_report.md").exists():
        print("[-] Fehler: forex_report.md fehlt.")
        return False
    if not (output_dir / "forex_report.csv").exists():
        print("[-] Fehler: forex_report.csv fehlt.")
        return False
    print("[+] Berichte-Prüfung erfolgreich.")
    
    print("[+] Alle Verifizierungstests ERFOLGREICH abgeschlossen!")
    
    # Bereinigung
    shutil.rmtree(test_dir)
    print("[*] Testumgebung bereinigt.")
    return True

if __name__ == "__main__":
    test_dir = setup_test_environment()
    success = run_verification(test_dir)
    if success:
        print("\n=== VERIFIZIERUNG ERFOLGREICH ===")
    else:
        print("\n=== VERIFIZIERUNG FEHLGESCHLAGEN ===")
        exit(1)

