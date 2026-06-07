@echo off
title Telegram Extractor GUI Starter
echo Starte Telegram Chat ^& Forex Extractor...

:: Führe das GUI-Skript aus
python src/telegram_extractor_gui.py

:: Falls ein Fehler auftritt (z.B. Python nicht installiert/nicht im Pfad)
if %errorlevel% neq 0 (
    echo.
    echo ------------------------------------------------------------
    echo ERROR: Das Programm konnte nicht gestartet werden.
    echo Bitte stellen Sie sicher, dass Python installiert und im
    echo systemweiten Pfad (PATH) eingetragen ist.
    echo ------------------------------------------------------------
    echo.
    pause
)
