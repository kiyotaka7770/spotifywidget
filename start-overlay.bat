@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo [!] Python ne nayden.
  echo     Ustanovi Python 3 s python.org i postav galku "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)
echo Zapusk servera na http://127.0.0.1:8888
echo [Esli stranica ne otkrylas - obnovi ee klavishey F5]
echo.
start "" "http://127.0.0.1:8888"
python server.py
pause
