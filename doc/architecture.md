# 🏗️ Systemarchitektur & Datenfluss-Dokumentation

Dieses Dokument beschreibt die innere Struktur, das Threading-Modell und den Datenfluss des **Telegram Chat & Forex Extractor**-Projekts.

---

## 🧩 Übersicht der Software-Komponenten

Das System besteht aus fünf Kernmodulen im Ordner `src/`, die klar nach dem Prinzip der Trennung von Zuständigkeiten (*Separation of Concerns*) entkoppelt sind:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        telegram_extractor_gui.py                       │
│  (Tkinter UI, Threading, Log-Queue, Pip-Installer, Benutzereingaben)   │
└────────────────────────────────────────────────┬───────────────────────┘
                                                 │
                        ┌────────────────────────┴──────────────────────┐
                        ▼                                               ▼
          ┌──────────────────────────┐                    ┌──────────────────────────┐
          │   telegram_extractor.py  │                    │telegram_api_downloader.py│
          │  (Offline-JSON-Parser)   │                    │ (Online-Telethon-Client) │
          └─────────────┬────────────┘                    └─────────────┬────────────┘
                        │                                               │
                        └────────────────────────┬──────────────────────┘
                                                 ▼
                                  ┌──────────────────────────┐
                                  │   analyze_organize.py    │
                                  │ (Subroutine/Katalog-Bot) │
                                  └──────────────────────────┘
```

1.  **GUI (`telegram_extractor_gui.py`)**: Der Orchestrator. Bietet die Steuerung, liest Benutzereingaben und visualisiert Ergebnisse.
2.  **JSON Parser (`telegram_extractor.py`)**: Das offline Analyse-Modul. Verarbeitet rohe JSON-Dateien ohne Netzwerkabhängigkeit.
3.  **API Downloader (`telegram_api_downloader.py`)**: Das online Download-Modul. Kommuniziert asynchron über das Telegram-Protokoll (MTProto) unter Verwendung von Telethon.
4.  **Katalog-Subroutine (`analyze_organize.py`)**: Das nachgelagerte Analysemodul, das empfohlene Handelsroboter klassifiziert und ordnet.
5.  **Verifizierung (`test_extractor.py`)**: Ein isolierter Integrationstest, der Mock-Chats erzeugt, um die Integrität des Parsers bei Änderungen zu gewährleisten.

---

## 🧵 Threading-Modell und Asynchronität in der GUI

Eine der größten Herausforderungen bei Desktop-Anwendungen mit Netzwerkzugriff (wie Downloads von Telegram) ist das **Einfrieren der Benutzeroberfläche** (GUI-Hänger). Um dies zu verhindern, nutzt das Programm eine robuste Multithreading-Architektur:

### 1. Der GUI-Thread (Main Thread)
*   Verantwortlich für das Zeichnen der Tkinter-Fenster und das Reagieren auf Benutzerklicks.
*   Fragt alle 100 Millisekunden über die Methode `poll_logs()` eine thread-sichere `queue.Queue` ab, um Logmeldungen aus den Hintergrund-Threads in der Textbox anzuzeigen.

### 2. Der asynchrone Event-Loop-Thread (`AsyncLoopThread`)
*   Da die Telegram-Bibliothek `telethon` auf Pythons `asyncio` aufbaut, benötigt sie einen aktiven Event-Loop.
*   Die GUI startet beim Laden einen eigenen Hintergrund-Thread, der ausschließlich diesen Event-Loop am Leben erhält. Alle Telethon-Aufrufe (Verbindungsaufbau, Login, Kanäle laden) werden per `asyncio.run_coroutine_threadsafe` in diesen Thread delegiert.

### 3. Der Extraktions-Hintergrundthread
*   Für die Offline-Extraktion (Methode A) wird ein Standard-Python-`threading.Thread` gestartet. Dieser parst die potenziell gigantischen `result.json`-Dateien (oft mehrere Gigabyte groß) im Hintergrund.

### 4. Thread-Sichere Benutzerinteraktion (2FA & Code-Eingabe)
Da der Telethon-Client im Hintergrund-Thread läuft, kann er nicht direkt Tkinter-Dialoge öffnen. Das System löst dies wie folgt:
1.  Telethon stellt fest, dass ein Login-Code benötigt wird.
2.  Es blockiert im Hintergrund-Thread und signalisiert dem Haupt-Thread über eine Thread-sichere Variable den Bedarf.
3.  Die GUI öffnet im Haupt-Thread ein modales Eingabefenster und blockiert die Interaktion des Benutzers mit dem Hauptfenster.
4.  Nach Eingabe des Codes wird dieser an den blockierten Telethon-Hintergrund-Thread zurückgegeben, welcher die Anmeldung fortsetzt.

---

## 📈 Datenfluss-Pipeline

### Daten-Strukturierung (JSON & API)
Unabhängig davon, ob die Daten über Methode A (JSON) oder Methode B (API) geladen werden, transformieren die Parser die Chat-Einträge in eine einheitliche interne Datenstruktur:

```json
{
  "id": 1452,
  "date": "2026-06-04T16:45:00",
  "sender": "Max Mustermann",
  "text": "Hier ist die neue Version des Gold-EAs!",
  "attached_file": "Gold_Pure_V1.ex5"
}
```

### Der Chunking-Prozess
Der gesamte bereinigte Chatverlauf wird in Text-Dateien (`chat_chunk_XXX.txt`) im Ordner `extracted_data/chat_chunks/` aufgeteilt.
*   **Chunk-Größe**: Standardmäßig **500 Nachrichten**.
*   **Reihenfolge**: Chronologisch (älteste Nachricht oben, neueste unten).
*   **Vorspann (Systemprompt)**: Jeder Chunk enthält am Anfang standardisierte Anweisungen für KI-Modelle. Dadurch muss ein Analyst den Text nur kopieren und kann ihn ohne weitere Erklärungen einer KI (wie ChatGPT oder Gemini) übergeben.

### Dateinamens-Kollisionsschutz
Um zu verhindern, dass verschiedene Dateien gleichen Namens (z. B. wenn Nutzer mehrmals eine Datei namens `config.set` senden) sich gegenseitig überschreiben, prüft der Parser vor dem Kopieren das Zielverzeichnis:
*   Existiert `extracted_data/forex_files/config.set` bereits?
*   Falls ja, wird die Datei in `config_msg<NachrichtenID>.set` umbenannt (z. B. `config_msg1452.set`).
*   Dies stellt sicher, dass alle historischen Versionen der EAs verlustfrei erhalten bleiben.
