# 📖 Benutzerhandbuch (Bedienungsanleitung)

Dieses Handbuch beschreibt Schritt für Schritt, wie Sie den **Telegram Chat & Forex Extractor** installieren, bedienen und die Ergebnisse optimal nutzen.

---

## 💻 1. Systemvoraussetzungen & Start

### Voraussetzungen
*   **Betriebssystem**: Windows (10 oder 11 empfohlen).
*   **Python**: Installierte Python-Version 3.8 oder neuer.
*   *Tipp*: Stellen Sie sicher, dass bei der Python-Installation die Option **"Add Python to PATH"** aktiviert wurde.

### Programm starten
1.  Öffnen Sie den Projektordner `TelegramScraper` im Windows-Explorer.
2.  Doppelklicken Sie auf die Datei **`start.bat`**.
3.  Es öffnet sich ein schwarzes Konsolenfenster (das eventuelle Systemmeldungen anzeigt) und kurz darauf das Hauptfenster der grafischen Benutzeroberfläche (GUI).

---

## 📁 2. Methode A: Offline JSON-Export Parser

Nutzen Sie diese Methode, wenn Sie bereits einen Chatverlauf manuell aus Telegram Desktop exportiert haben oder keine Verbindung zum Internet/Telegram-API herstellen möchten.

### Schritt 1: Chat-Export aus Telegram erzeugen
1.  Öffnen Sie die Anwendung **Telegram Desktop** auf Ihrem PC.
2.  Gehen Sie in den Chat, die Gruppe oder den Kanal, den Sie sichern möchten.
3.  Klicken Sie oben rechts auf das Drei-Punkte-Menü **⋮** und wählen Sie **Chatverlauf exportieren**.
4.  **Sehr wichtig**: Stellen Sie das Export-Format von **HTML** auf **JSON** um. (HTML-Dateien können von diesem Programm nicht gelesen werden).
5.  Aktivieren Sie das Kontrollkästchen bei **Dateien** (unter "Medien-Export-Einstellungen").
6.  Schieben Sie den Regler **Größenlimit** ganz nach rechts (z. B. auf 2000 MB oder unbegrenzt), damit alle Forex-Dateien mit heruntergeladen werden.
7.  Klicken Sie auf **Exportieren** und warten Sie, bis der Vorgang abgeschlossen ist. Telegram erstellt einen Ordner (z. B. `Telegram Desktop/ChatExport_2026-06-04/`).

### Schritt 2: Extraktion in der GUI durchführen
1.  Öffnen Sie das Programm über `start.bat`.
2.  Wählen Sie den Reiter **Methode A: JSON-Export Parser (Offline)**.
3.  Klicken Sie auf **Suchen...** neben dem Feld "Pfad zur result.json" und wählen Sie die Datei `result.json` aus dem eben exportierten Telegram-Ordner aus.
4.  Geben Sie unter "Ausgabeordner" an, wo die extrahierten Daten abgelegt werden sollen (Standard: `extracted_data`).
5.  Klicken Sie auf **Extraktion starten**. Sie können den Fortschritt live in der Konsole am unteren Fensterrand mitverfolgen.

---

## ⚡ 3. Methode B: Direkt-Download über die Telegram-API

Nutzen Sie diese Methode, wenn Sie Chats vollautomatisch und direkt aus dem Internet von den Telegram-Servern herunterladen möchten.

### Schritt 1: Vorbereitung & Bibliothek prüfen
1.  Öffnen Sie das Programm und wählen Sie den Reiter **Methode B: Direkt-Download (API Online)**.
2.  Das Programm prüft im Hintergrund, ob die Python-Bibliothek `telethon` installiert ist.
3.  *Falls die Bibliothek fehlt*: Zeigt das Programm ein rotes Warnfeld an. Klicken Sie einfach auf den Button **"Telethon jetzt via Pip installieren"**. Das Programm installiert die Bibliothek im Hintergrund. Nach erfolgreicher Installation wird das Feld grün.

### Schritt 2: Anmeldung bei Telegram
1.  Geben Sie Ihre Telefonnummer im internationalen Format (z. B. `+491701234567`) in das Feld ein.
2.  *(Hinweis: Ihre API ID und Ihr API Hash sind für dieses Projekt bereits fest hinterlegt, Sie müssen diese nicht ändern).*
3.  Klicken Sie auf den Button **1. Anmelden & Chats laden**.
4.  **Bestätigungscode eingeben**: Telegram sendet Ihnen einen Anmeldecode (entweder als SMS oder als Direktnachricht in Telegram auf einem anderen Gerät). Geben Sie diesen Code in das geöffnete Abfragefenster ein und klicken Sie auf **OK**.
5.  **Zweistufige Verifizierung (Optional)**: Falls Sie ein zusätzliches Passwort für Ihr Telegram-Konto eingerichtet haben, öffnet sich ein zweites Fenster. Geben Sie dort Ihr Passwort ein.
6.  Nach erfolgreichem Login wird die Liste "Verfügbare Chats" mit Ihren letzten 100 Konversationen gefüllt.

### Schritt 3: Download & Extraktion starten
1.  Wählen Sie den gewünschten Chat aus der Dropdown-Liste aus.
2.  Passen Sie bei Bedarf die Einstellungen wie die "Chunk-Größe" (Standard: 500) oder die zu filternden Dateiendungen an.
3.  Klicken Sie auf den Button **2. Download & Extraktion starten**.
4.  Der Downloader lädt nun chronologisch (von alt nach neu) alle Nachrichten und lädt passende Forex-Dateien automatisch im Hintergrund herunter.

---

## 📂 4. Ausgabedaten & Verwendung mit einer KI

Nach Abschluss der Extraktion öffnet sich im unteren Bereich der GUI ein Aktionsfeld. Sie können dort direkt den Ausgabeordner im Explorer öffnen oder den generierten Bericht anzeigen lassen.

### Die erzeugten Dateien im Überblick:
*   **`extracted_data/forex_files/`**: Hier liegen alle Kopien der gefundenen Forex-Robots (`.ex4`, `.ex5`, `.mq4`, `.mq5`) sowie Einstellungsdateien (`.set`).
*   **`extracted_data/chat_chunks/`**: Diese Ordnerstruktur enthält Textdateien (z. B. `chat_chunk_001.txt`). Jede Datei enthält exakt 500 fortlaufende Nachrichten.
*   **`extracted_data/forex_report.md`**: Ein übersichtlicher Markdown-Bericht, der jede gefundene Datei auflistet, inklusive des Datums, des Absenders und der genauen Nachricht, in der die Datei gepostet wurde.
*   **`extracted_data/forex_report.csv`**: Die tabellarische Variante für den Import in Excel.

### Wie Sie die Chunks in einer KI (z. B. Claude oder ChatGPT) analysieren:
1.  Öffnen Sie einen der Text-Chunks (z. B. `chat_chunk_001.txt`) in einem Texteditor.
2.  Kopieren Sie den gesamten Inhalt (Strg + A, danach Strg + C).
3.  Fügen Sie den Text in das Chatfenster Ihrer KI ein.
4.  **Der Vorteil**: Da am Anfang jedes Chunks bereits ein optimierter System-Prompt eingebettet ist, weiß die KI sofort, was zu tun ist: Sie liest den Chatverlauf, filtert Empfehlungen heraus und listet Stärken und Risiken der genannten Roboter auf.
