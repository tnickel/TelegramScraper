# 💻 Entwickler-Handbuch (Developer Guide)

Dieses Dokument richtet sich an Software-Entwickler und KI-Assistenten, die das Projekt warten, erweitern oder anpassen möchten.

---

## 🛠️ Code-Richtlinien & Konventionen

### 1. Skriptrelative Pfadauflösung (Sehr wichtig!)
In der Vergangenheit traten Fehler auf, weil Pfade über `Path.cwd()` (aktuelles Arbeitsverzeichnis) aufgelöst wurden. Startet ein Nutzer das Skript aus einem anderen Ordner heraus, schlagen Dateioperationen fehl oder Logs landen im falschen Verzeichnis.

*   **Richtlinie**: Definieren Sie Pfade im Projektordner **immer** relativ zum Speicherort des Skripts selbst.
*   **Beispiel**:
    ```python
    from pathlib import Path
    
    # Ermittelt das Wurzelverzeichnis des Projekts (eine Ebene über 'src/')
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    
    # Verzeichnisse definieren
    LOG_DIR = PROJECT_ROOT / "log"
    EXTRACTED_DIR = PROJECT_ROOT / "extracted_data"
    ```

### 2. Thread-Sicherheit in der GUI
Modifizieren Sie Tkinter-Widgets (wie Textboxen, Labels oder Status-Bars) **niemals** direkt aus einem asynchronen Hintergrundthread (`telethon` oder `threading.Thread`). Dies führt unter Windows unweigerlich zu unvorhersehbaren Abstürzen.

*   Nutzen Sie die `self.log_queue` (eine `queue.Queue`), um Log-Nachrichten aus Threads zu senden.
*   Die Methode `poll_logs()` im Hauptthread holt diese Nachrichten ab und schreibt sie sicher in die GUI.

---

## 🧪 Ausführen der automatisierten Tests

Bevor Sie Änderungen committen oder neue Features hinzufügen, müssen Sie die Testsuite ausführen.

### Ausführung über die Konsole:
```bash
python src/test_extractor.py
```

### Was der Test macht:
1.  Erstellt ein temporäres Verzeichnis `test_env/`.
2.  Erzeugt simulierte EA-Dateien (`robot1.ex4`, `robot2.ex5`, `logic.mq5`, etc.) und eine Textdatei, die ignoriert werden soll.
3.  Erstellt eine künstliche `result.json` mit verschiedenen Nachrichtentypen (Service-Nachrichten, Text-Nachrichten, Medien-Anhänge).
4.  Führt die Kern-Extraktionsmethode aus.
5.  Prüft, ob die richtigen Dateien extrahiert wurden, ob Chunks korrekt aufgeteilt sind (inklusive Prompt-Vorspann) und ob die Berichte (`.md` und `.csv`) vollständig generiert wurden.
6.  Löscht das Testverzeichnis `test_env/` rückstandslos.

Achten Sie darauf, dass der Test mit der Zeile `=== VERIFIZIERUNG ERFOLGREICH ===` abschließt.

---

## ⚙️ Die Subroutine zur EA-Katalogisierung (`analyze_organize.py`)

Dieses Skript dient dazu, die unstrukturierten extrahierten Dateien automatisch nach den Erkenntnissen aus den Chats zu sortieren.

### Aufbau der Konfiguration (`ROBOTS_CONFIG`)
Im Skript [src/analyze_organize.py](file:///d:/AntiGravitySoftware/GitWorkspace/TelegramScraper/src/analyze_organize.py) befindet sich ein Dictionary namens `ROBOTS_CONFIG`. Wenn Sie einen neuen Roboter hinzufügen möchten, ergänzen Sie diesen dort wie folgt:

```python
    "Name_des_Roboters": {
        "files": [
            "Exakter_Dateiname_1.ex5",
            "Exakter_Dateiname_2.ex4"
        ],
        "settings": [
            "Optionale_Einstellungsdatei.set"
        ],
        "description": """# Handbuch Name des Roboters
        
## 📝 Beschreibung
Zusammenfassung der Funktion aus dem Chat...

## ⚙️ Einstellungen
* Währungspaar: XAUUSD
* Timeframe: M15

## ⚠️ Risikomanagement
* Risiko-Rating: 🔴 Hoch
"""
    }
```

### Ausführung
Starten Sie das Skript nach der Konfiguration über die Konsole:
```bash
python src/analyze_organize.py
```
Das Skript bereinigt und erstellt daraufhin im Ordner `report/robots/` für jeden Eintrag ein eigenes Verzeichnis, kopiert die angegebenen Dateien hinein und generiert die Datei `beschreibung.md`.

---

## 📝 Logging & Fehlerprotokollierung

*   **Log-Pfad**: `log/telegram_scraper.log` (relativ zur Projektwurzel).
*   Das Logfile enthält wichtige Ausgaben der GUI, der Telethon-API-Aktionen und Fehlermeldungen bei Abstürzen.
*   Bei Problemen mit dem Verbindungsaufbau oder dem OTP-Code (Einmalpasswort) prüfen Sie zuerst diese Datei.
