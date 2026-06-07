#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Chat Extractor & Forex File Parser
==========================================
Dieses Skript analysiert einen Telegram-Chat-Export im JSON-Format.
Es führt folgende Aktionen aus:
1. Extrahiert Forex-Dateien (.mq4, .mq5, .ex4, .ex5, .set) und organisiert sie.
2. Erstellt einen detaillierten Bericht (CSV & Markdown) über alle gefundenen Forex-Dateien mit Kontext.
3. Teilt den Chatverlauf in mundgerechte Portionen (Chunks) auf, die ideal für KI-Analysen (LLMs) geeignet sind.

Verwendung:
    python telegram_extractor.py [Pfad_zu_result.json] [Optionen]
"""

import os
import json
import csv
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Standard-Ziel-Dateiendungen für Forex-Robots und Einstellungen
DEFAULT_EXTENSIONS = {".mq4", ".mq5", ".ex4", ".ex5", ".set"}

def clean_text(text_field):
    """
    Konvertiert das 'text'-Feld aus dem Telegram-JSON (das entweder ein String
    oder eine Liste von Objekten/Strings sein kann) in einen sauberen Plain-Text String.
    """
    if not text_field:
        return ""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts = []
        for part in text_field:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(text_field)

def format_size(bytes_size):
    """Formatiert Dateigrößen in lesbare Einheiten."""
    if bytes_size is None:
        return "Unbekannt"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def get_message_sender(msg):
    """Extrahiert den Absendernamen einer Nachricht."""
    sender = msg.get("from")
    if not sender:
        # Check for channel post or service messages
        sender = msg.get("actor", "System/Unbekannt")
    return sender

def parse_telegram_json(json_path, output_dir, chunk_size, target_extensions):
    json_path = Path(json_path).resolve()
    if not json_path.exists():
        print(f"[-] Fehler: Die Datei '{json_path}' existiert nicht.")
        return False

    print(f"[*] Lese Telegram-Export-Datei: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[-] Fehler beim Laden der JSON-Datei: {e}")
        return False

    chat_name = data.get("name", "Telegram Chat")
    messages = data.get("messages", [])
    print(f"[+] Erfolgreich geladen. Chat-Name: '{chat_name}' | Insgesamt {len(messages)} Einträge gefunden.")

    # Zielverzeichnisse erstellen
    out_path = Path(output_dir).resolve()
    files_out_dir = out_path / "forex_files"
    chunks_out_dir = out_path / "chat_chunks"

    os.makedirs(files_out_dir, exist_ok=True)
    os.makedirs(chunks_out_dir, exist_ok=True)

    print(f"[*] Zielverzeichnisse erstellt unter: {out_path}")

    # Listen für Berichte und Dateiverarbeitung
    extracted_files_info = []
    processed_messages = []

    # Iteriere über alle Nachrichten
    for msg in messages:
        if msg.get("type") != "message":
            # Überspringe Service-Nachrichten wie Pinning, Gruppenbild-Änderungen etc.
            continue

        msg_id = msg.get("id")
        date_str = msg.get("date", "")
        sender = get_message_sender(msg)
        text = clean_text(msg.get("text", ""))

        file_field = msg.get("file")
        attached_file_info = None

        if file_field and isinstance(file_field, str):
            # Pfad der Datei relativ zum JSON-Export-Ordner
            src_file_path = json_path.parent / file_field
            file_ext = src_file_path.suffix.lower()

            if file_ext in target_extensions:
                original_filename = src_file_path.name
                dest_filename = original_filename

                # Kollisionsprüfung: Wenn Datei bereits existiert, Nachricht-ID anhängen
                dest_file_path = files_out_dir / dest_filename
                if dest_file_path.exists():
                    stem = src_file_path.stem
                    dest_filename = f"{stem}_msg{msg_id}{file_ext}"
                    dest_file_path = files_out_dir / dest_filename

                file_copied = False
                file_size = None
                
                # Kopiere Datei, falls sie existiert
                if src_file_path.exists():
                    try:
                        shutil.copy2(src_file_path, dest_file_path)
                        file_copied = True
                        file_size = dest_file_path.stat().st_size
                    except Exception as e:
                        print(f"[-] Warnung: Fehler beim Kopieren von {original_filename}: {e}")
                else:
                    print(f"[-] Warnung: Datei '{file_field}' wurde im Export-Ordner nicht gefunden.")

                # Speichere Infos über die extrahierte Datei
                info = {
                    "msg_id": msg_id,
                    "date": date_str,
                    "sender": sender,
                    "original_name": original_filename,
                    "saved_name": dest_filename,
                    "file_type": file_ext[1:].upper() if len(file_ext) > 1 else "UNBEKANNT",
                    "file_size": file_size,
                    "copied": file_copied,
                    "context": text
                }
                extracted_files_info.append(info)
                attached_file_info = dest_filename

        # Speichere die verarbeitete Nachricht für das Chunking
        processed_messages.append({
            "id": msg_id,
            "date": date_str,
            "sender": sender,
            "text": text,
            "attached_file": attached_file_info
        })

    # 1. Schreibe Forex-Berichte
    write_forex_reports(extracted_files_info, out_path)

    # 2. Schreibe Chat-Chunks
    write_chat_chunks(processed_messages, chat_name, chunks_out_dir, chunk_size)

    print(f"\n[+] Extraktion abgeschlossen!")
    print(f"  - Extrahierte Forex-Dateien: {len([x for x in extracted_files_info if x['copied']])} Stück in 'forex_files/'")
    print(f"  - Generierte Chat-Portionen (Chunks): {len(os.listdir(chunks_out_dir))} Dateien in 'chat_chunks/'")
    print(f"  - Detaillierter Bericht: '{out_path / 'forex_report.md'}' und '.csv'")
    return True

def write_forex_reports(files_info, output_dir):
    """Generiert Markdown- und CSV-Berichte für die extrahierten Forex-Dateien."""
    if not files_info:
        print("[-] Keine Forex-Dateien (.mq4, .mq5, .ex4, .ex5, .set) im Chat gefunden.")
        # Erstelle leere Berichte mit Hinweis
        with open(output_dir / "forex_report.md", "w", encoding="utf-8") as f:
            f.write("# Forex-Dateien Bericht\n\nEs wurden keine Forex-Dateien im Chat-Export gefunden.\n")
        return

    # 1. Markdown Report
    md_path = output_dir / "forex_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Telegram Forex-Dateien Bericht\n")
        f.write(f"Generiert am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Insgesamt wurden **{len(files_info)}** Forex-Dateien identifiziert.\n\n")
        
        f.write("| ID | Datum/Zeit | Absender | Dateiname (Gespeichert) | Typ | Größe | Status | Kontext / Nachricht |\n")
        f.write("|---:|:---|:---|:---|:---|:---|:---|:---|\n")
        
        for idx, info in enumerate(files_info, 1):
            status = "✅ Kopiert" if info["copied"] else "❌ Nicht gefunden im Export"
            size_formatted = format_size(info["file_size"])
            context_clean = info["context"].replace("\n", " ").replace("|", "\\|")
            if len(context_clean) > 150:
                context_clean = context_clean[:147] + "..."
            
            f.write(f"| {info['msg_id']} | {info['date']} | {info['sender']} | `{info['saved_name']}` | {info['file_type']} | {size_formatted} | {status} | {context_clean} |\n")

    # 2. CSV Report
    csv_path = output_dir / "forex_report.csv"
    try:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            # Header
            writer.writerow(["Nachricht_ID", "Datum_Uhrzeit", "Absender", "Original_Dateiname", "Gespeicherter_Dateiname", "Dateityp", "Groesse_Bytes", "Status", "Nachrichtentext"])
            for info in files_info:
                status_str = "Kopiert" if info["copied"] else "Nicht im Export-Ordner gefunden"
                writer.writerow([
                    info["msg_id"],
                    info["date"],
                    info["sender"],
                    info["original_name"],
                    info["saved_name"],
                    info["file_type"],
                    info["file_size"] if info["file_size"] is not None else "",
                    status_str,
                    info["context"]
                ])
    except Exception as e:
        print(f"[-] Fehler beim Schreiben des CSV-Berichts: {e}")

def write_chat_chunks(messages, chat_name, output_dir, chunk_size):
    """Teilt die Nachrichten in Portionen auf und schreibt sie in TXT-Dateien."""
    if not messages:
        return

    total_messages = len(messages)
    num_chunks = (total_messages + chunk_size - 1) // chunk_size

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, total_messages)
        chunk_msgs = messages[start_idx:end_idx]

        chunk_filename = output_dir / f"chat_chunk_{i+1:03d}.txt"
        
        start_date = chunk_msgs[0]["date"]
        end_date = chunk_msgs[-1]["date"]

        with open(chunk_filename, "w", encoding="utf-8") as f:
            # Einleitender KI-System-Prompt für den Benutzer zum Kopieren
            f.write("========================================================================\n")
            f.write(f"TELEGRAM CHAT EXPORT - CHUNK {i+1} VON {num_chunks}\n")
            f.write(f"Chat-Name: {chat_name}\n")
            f.write(f"Zeitraum: {start_date} bis {end_date}\n")
            f.write(f"Nachrichten in diesem Teil: {len(chunk_msgs)} (Nachricht #{start_idx+1} bis #{end_idx})\n")
            f.write("========================================================================\n")
            f.write("HINWEIS FÜR DIE KI-ANALYSE:\n")
            f.write("Analysiere diesen Chat-Auszug. Beachte besonders Diskussionen über Forex-Roboter (EAs),\n")
            f.write("Strategien, .set-Einstellungsdateien, Backtest-Ergebnisse oder Fragen der Nutzer.\n")
            f.write("Jede Nachricht ist wie folgt formatiert: [ID] | [Datum] | [Absender]: Text\n")
            f.write("========================================================================\n\n")

            for m in chunk_msgs:
                f.write(f"[{m['id']}] | [{m['date']}] | {m['sender']}:\n")
                if m['text']:
                    f.write(f"{m['text']}\n")
                if m['attached_file']:
                    f.write(f"[Angehängte Forex-Datei: {m['attached_file']}]\n")
                f.write("-" * 40 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Chat-Export JSON Parser & Forex Extractor")
    parser.add_argument("json_path", nargs="?", default="result.json", help="Pfad zur exportierten result.json (Standard: result.json)")
    parser.add_argument("--out-dir", "-o", default="extracted_data", help="Ausgabeverzeichnis für Chunks und extrahierte Dateien (Standard: extracted_data)")
    parser.add_argument("--chunk-size", "-c", type=int, default=500, help="Anzahl der Nachrichten pro Textportion/Chunk für die KI (Standard: 500)")
    parser.add_argument("--exts", "-e", default=".mq4,.mq5,.ex4,.ex5,.set", help="Kommagetrennte Liste der zu extrahierenden Dateiendungen (Standard: .mq4,.mq5,.ex4,.ex5,.set)")

    args = parser.parse_args()

    # Bereite Ziel-Endungen vor
    extensions = {ext.strip().lower() for ext in args.exts.split(",")}
    # Sicherstellen, dass sie mit einem Punkt beginnen
    extensions = {ext if ext.startswith(".") else f".{ext}" for ext in extensions}

    success = parse_telegram_json(args.json_path, args.out_dir, args.chunk_size, extensions)
    if not success:
        # Falls standardmäßig nach result.json gesucht wurde, aber diese fehlt, weise den Nutzer darauf hin
        if args.json_path == "result.json" and not os.path.exists("result.json"):
            print("\n[!] Hinweis: Es wurde keine 'result.json' im aktuellen Ordner gefunden.")
            print("    Bitte exportieren Sie einen Chat aus Telegram Desktop (als JSON) und legen Sie die Datei hier ab,")
            print("    oder übergeben Sie den Pfad zur JSON-Datei als Argument:")
            print("    python telegram_extractor.py C:\\Pfad\\zu\\Ihrem\\Export\\result.json")
