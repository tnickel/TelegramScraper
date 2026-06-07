# KI-Anweisung: Subroutine zur dynamischen Chat-Analyse & Roboter-Organisation

Diese Datei dient als Arbeitsanweisung für KI-Assistenten (wie Antigravity/Gemini/Claude), die in diesem Projekt arbeiten. Wenn der Benutzer diese Subroutine anfordert, muss folgendes Vorgehen eingehalten werden:

---

## 📋 Ablaufbeschreibung für die KI

### 1. Analyse der neuen Chatverläufe
Lese alle neuen Textdateien im Verzeichnis `extracted_data/chat_chunks/` durch und suche nach Erwähnungen von Forex-Robotern (EAs). Analysiere:
* Welche Roboter werden von den Mitgliedern der Community positiv bewertet? (z. B. "läuft seit Monaten stabil", "gute Profits", "doubled account").
* Welche Risiken werden genannt? (z. B. "martingale", "blown account", "drawdown").
* Welche Einstellungen (.set-Parameter, Timeframes, Währungspaare) werden für diese EAs empfohlen?

### 2. Abgleich mit dem Dateibestand
Überprüfe das Verzeichnis `extracted_data/forex_files/` und schaue, ob für die positiv bewerteten EAs entsprechende Dateien (z. B. `.ex5`, `.ex4`, `.mq5`, `.mq4`, `.set`) vorhanden sind.
* **Bedingung:** Ein Roboter wird nur dann als "empfohlen und vorhanden" eingestuft, wenn wir sowohl positive User-Bewertungen im Chat als auch die ausführbare Datei im Dateibestand haben.

### 3. Aktualisierung der Subroutine (`src/analyze_organize.py`)
Passe die Konfiguration `ROBOTS_CONFIG` im Skript `src/analyze_organize.py` an. Füge neue Roboter hinzu oder aktualisiere die bestehenden Einträge mit:
* Den genauen Dateinamen, die kopiert werden sollen.
* Eventuell neu gefundenen `.set`-Dateien.
* Einer aktualisierten Markdown-Beschreibung (`beschreibung.md`), die die neuen Erkenntnisse aus dem Chat zusammenfasst.

### 4. Ausführung der Subroutine
Führe das Skript aus:
```bash
python src/analyze_organize.py
```
Dadurch werden die Ordner unter `report/robots/` bereinigt, neu strukturiert und alle Dateien kopiert.

### 5. Bericht an den Benutzer
Präsentiere dem Benutzer eine Zusammenfassung der neuen Erkenntnisse und verweise auf die aktualisierten Verzeichnisse.
