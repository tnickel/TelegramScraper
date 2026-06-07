@echo off
title Forex EA Dashboard Server

echo [*] Pruefe auf alte Dashboard-Server Instanzen auf Port 8000...
powershell -Command "$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; if ($p) { Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue }"

set REBUILD=0
if "%~1"=="--force" set REBUILD=1
if "%~1"=="-f" set REBUILD=1
if "%REBUILD%"=="1" goto GENERATE

python src/check_rebuild.py
if %errorlevel% equ 0 goto GENERATE
goto SERVE_DIRECTLY

:GENERATE
echo [*] Generiere Dashboard-Dateien (Datenumwandlung)...
python src/generate_dashboard.py
if %errorlevel% neq 0 goto ERROR
goto START_SERVER

:SERVE_DIRECTLY
echo [+] telegram_scraper.db und stats.json vorhanden. Ueberspringe Datenumwandlung.
echo [i] Info: Zum Erzwingen der Umwandlung starte mit: start_dashboard.bat --force
echo [i] Info: Alternativ kann die Umwandlung ueber das Web-UI (Workflow) gestartet werden.
goto START_SERVER

:START_SERVER
echo [*] Starte lokalen Dashboard-Server...
python src/dashboard_server.py
goto END

:ERROR
echo [!] Fehler beim Vorbereiten des Dashboards.
pause
exit /b %errorlevel%

:END
