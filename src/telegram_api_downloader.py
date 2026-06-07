#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram API Downloader (Methode B)
==================================
Verwendet die Bibliothek 'telethon', um sich direkt mit der Telegram-API zu verbinden,
Chats aufzulisten, die Historie herunterzuladen und Forex-Dateien zu extrahieren.

Die API-Zugangsdaten (API ID & Hash) werden aus config.local.json,
Umgebungsvariablen oder der GUI-Eingabe geladen.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Versuche Telethon zu importieren
try:
    from telethon import TelegramClient, errors
    from telethon.tl.types import Channel, Chat, User
except ImportError:
    print("[-] Telethon ist nicht installiert. Bitte führen Sie 'pip install telethon' aus.")
    sys.exit(1)

# Importiere Hilfsfunktionen aus dem Hauptskript
try:
    from telegram_extractor import write_forex_reports, write_chat_chunks, format_size
except ImportError:
    # Fallback-Funktionen falls nicht auffindbar
    def format_size(b): return f"{b} B"
    def write_forex_reports(f, o): pass
    def write_chat_chunks(m, c, o, s): pass

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_FILE = PROJECT_ROOT / "config.local.json"


def load_api_credentials():
    """Load Telegram API credentials without storing real defaults in source code."""
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            api_id = api_id or config.get("api_id")
            api_hash = api_hash or config.get("api_hash")
        except Exception as e:
            print(f"[-] Warnung: config.local.json konnte nicht gelesen werden: {e}")

    if api_id is not None:
        api_id = int(api_id)

    return api_id, api_hash

def write_single_chunk(chunk_msgs, chat_name, output_dir, chunk_num, chunk_size, total_messages):
    chunk_filename = output_dir / f"chat_chunk_{chunk_num:03d}.txt"
    start_date = chunk_msgs[0]["date"]
    end_date = chunk_msgs[-1]["date"]
    
    num_chunks = (total_messages + chunk_size - 1) // chunk_size if total_messages > 0 else chunk_num
    
    with open(chunk_filename, "w", encoding="utf-8") as f:
        f.write("========================================================================\n")
        f.write(f"TELEGRAM CHAT EXPORT - CHUNK {chunk_num} VON {num_chunks} (Chronologisch)\n")
        f.write(f"Chat-Name: {chat_name}\n")
        f.write(f"Zeitraum: {start_date} bis {end_date}\n")
        f.write(f"Nachrichten in diesem Teil: {len(chunk_msgs)}\n")
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

class TelegramAPIDownloader:
    def __init__(self, api_id=None, api_hash=None, session_name="session_telegram_extractor"):
        if api_id is None or api_hash is None:
            loaded_api_id, loaded_api_hash = load_api_credentials()
            api_id = api_id or loaded_api_id
            api_hash = api_hash or loaded_api_hash

        if not api_id or not api_hash:
            raise ValueError("Telegram API ID und API Hash fehlen. Bitte in der GUI eingeben, config.local.json setzen oder TELEGRAM_API_ID/TELEGRAM_API_HASH verwenden.")

        self.api_id = api_id
        self.api_hash = api_hash
        self.session_path = PROJECT_ROOT / session_name
        self.client = None
        self.loop = None

    def initialize_client(self, loop=None):
        """Erstellt den Telethon-Client im angegebenen Event-Loop."""
        self.loop = loop or asyncio.get_event_loop()
        self.client = TelegramClient(str(self.session_path), self.api_id, self.api_hash, loop=self.loop)

    async def connect(self):
        """Verbindet mit den Telegram-Servern."""
        if not self.client:
            self.initialize_client()
        await self.client.connect()

    async def is_authorized(self):
        """Prüft, ob die Sitzung bereits angemeldet ist."""
        if not self.client:
            await self.connect()
        return await self.client.is_user_authorized()

    async def send_code(self, phone):
        """Sendet den Anmeldecode an das Telefon des Benutzers."""
        if not self.client:
            await self.connect()
        # Telethon send_code_request gibt ein SentCode-Objekt zurück
        return await self.client.send_code_request(phone)

    async def sign_in(self, phone, code, password=None, phone_code_hash=None):
        """Führt die Anmeldung durch. Kann bei 2FA ein Passwort erfordern."""
        if not self.client:
            await self.connect()
        try:
            if password:
                await self.client.sign_in(password=password)
            else:
                await self.client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            return True
        except errors.SessionPasswordNeededError:
            # 2FA Passwort wird benötigt
            raise
        except Exception as e:
            print(f"[-] Fehler bei Anmeldung: {e}")
            raise

    async def get_chat_list(self):
        """Ruft die letzten 100 Chats des Benutzers ab."""
        if not await self.is_authorized():
            raise PermissionError("Nicht angemeldet.")
            
        print("[*] Rufe Chat-Liste ab...")
        dialogs = await self.client.get_dialogs(limit=100)
        
        chat_list = []
        for d in dialogs:
            entity = d.entity
            chat_type = "Group"
            username = getattr(entity, 'username', None)
            
            if isinstance(entity, Channel):
                chat_type = "Channel" if entity.broadcast else "Supergroup"
            elif isinstance(entity, Chat):
                chat_type = "Group"
            elif isinstance(entity, User):
                chat_type = "Direct Message"
                
            chat_list.append({
                "id": d.id,
                "name": d.name,
                "type": chat_type,
                "username": username
            })
        return chat_list

    def get_sender_name(self, sender):
        """Generiert einen lesbaren Absendernamen aus einem Telethon-Objekt."""
        if not sender:
            return "System/Unbekannt"
        if isinstance(sender, User):
            first = sender.first_name or ""
            last = sender.last_name or ""
            name = f"{first} {last}".strip()
            if not name:
                name = sender.username or f"User_{sender.id}"
            return name
        elif hasattr(sender, 'title'):
            return sender.title
        return str(sender.id)

    async def download_history(self, chat_id, output_dir, chunk_size, target_extensions, progress_callback=None):
        """Lädt die Historie und Medien eines Chats herunter und verarbeitet diese."""
        if not await self.is_authorized():
            raise PermissionError("Nicht angemeldet.")

        out_path = Path(output_dir).resolve()
        files_out_dir = out_path / "forex_files"
        chunks_out_dir = out_path / "chat_chunks"

        os.makedirs(files_out_dir, exist_ok=True)
        os.makedirs(chunks_out_dir, exist_ok=True)

        # Hole Gruppen/Kanal Informationen
        entity = await self.client.get_entity(chat_id)
        chat_name = getattr(entity, 'title', 'DirectChat')
        if not chat_name and hasattr(entity, 'first_name'):
            chat_name = f"{entity.first_name} {entity.last_name or ''}".strip()

        print(f"[*] Starte Download für Chat: '{chat_name}'")
        
        # Um den Gesamtfortschritt anzuzeigen, holen wir die Gesamtanzahl der Nachrichten
        if progress_callback:
            progress_callback("Hole Nachrichten-Anzahl...", 0, 0)
            
        try:
            res = await self.client.get_messages(entity, limit=0)
            total_messages = res.total
        except Exception as e:
            print(f"[-] Warnung beim Abrufen der Nachrichtenanzahl: {e}")
            total_messages = 0
            
        print(f"[+] Insgesamt {total_messages} Nachrichten im Chat gefunden.")

        processed_messages = []
        extracted_files_info = []
        count = 0
        chunk_count = 0
        chunk_buffer = []

        # reverse=True liefert die Nachrichten von alt nach neu. Dadurch sind Chunks global chronologisch.
        async for message in self.client.iter_messages(entity, reverse=True):
            count += 1
            msg_id = message.id
            date_str = message.date.strftime("%Y-%m-%dT%H:%M:%S")
            sender = self.get_sender_name(await message.get_sender())
            text = message.text or ""

            attached_file_info = None

            # Prüfe, ob die Nachricht eine Datei enthält
            if message.document:
                # Hole Dateinamen
                filename = message.file.name
                if filename:
                    file_ext = Path(filename).suffix.lower()
                    if file_ext in target_extensions:
                        dest_filename = filename
                        dest_file_path = files_out_dir / dest_filename

                        # Kollisionsprüfung
                        if dest_file_path.exists():
                            stem = Path(filename).stem
                            dest_filename = f"{stem}_msg{msg_id}{file_ext}"
                            dest_file_path = files_out_dir / dest_filename

                        if progress_callback:
                            progress_callback(f"Lade Datei herunter: {filename}...", count, total_messages)
                        else:
                            print(f"[*] Lade Datei herunter: {filename}...")

                        # Datei herunterladen
                        file_copied = False
                        file_size = None
                        try:
                            await self.client.download_media(message, file=str(dest_file_path))
                            file_copied = True
                            file_size = dest_file_path.stat().st_size
                        except Exception as e:
                            print(f"[-] Fehler beim Herunterladen von {filename}: {e}")

                        info = {
                            "msg_id": msg_id,
                            "date": date_str,
                            "sender": sender,
                            "original_name": filename,
                            "saved_name": dest_filename,
                            "file_type": file_ext[1:].upper() if len(file_ext) > 1 else "UNBEKANNT",
                            "file_size": file_size,
                            "copied": file_copied,
                            "context": text
                        }
                        extracted_files_info.append(info)
                        attached_file_info = dest_filename

            # Nachricht vorbereiten
            msg_entry = {
                "id": msg_id,
                "date": date_str,
                "sender": sender,
                "text": text,
                "attached_file": attached_file_info
            }
            processed_messages.append(msg_entry)
            chunk_buffer.append(msg_entry)

            # Wenn ein Chunk voll ist, sofort schreiben!
            if len(chunk_buffer) == chunk_size:
                chunk_count += 1
                write_single_chunk(chunk_buffer, chat_name, chunks_out_dir, chunk_count, chunk_size, total_messages)
                chunk_buffer = []

            # Fortschritt alle 50 Nachrichten oder bei Updates melden
            if progress_callback and (count % 50 == 0 or count == total_messages):
                progress_callback(f"Lade Nachricht {count}/{total_messages} herunter...", count, total_messages)

        # Letzten unvollständigen Chunk schreiben, falls vorhanden
        if chunk_buffer:
            chunk_count += 1
            write_single_chunk(chunk_buffer, chat_name, chunks_out_dir, chunk_count, chunk_size, total_messages)

        # 1. Berichte schreiben
        if progress_callback:
            progress_callback("Schreibe Berichte...", total_messages, total_messages)
        write_forex_reports(extracted_files_info, out_path)

        print("[+] API-Download und Extraktion erfolgreich abgeschlossen!")
        return len(extracted_files_info), len(processed_messages)
