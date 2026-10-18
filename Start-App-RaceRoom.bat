@echo off
cd /d "%~dp0"
set QT_LOGGING_RULES=*.warning=false
rem RaceRoom Racing Experience als Datenquelle ($R3E). Auto-Erkennung LMU/RaceRoom: --sim auto
python main.py --sim raceroom 2>nul
pause
