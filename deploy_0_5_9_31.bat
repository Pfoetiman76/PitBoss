@echo off
setlocal
cd /d "%~dp0"
echo == Deploy PitBoss 0.5.9.31 ==
where git >nul 2>nul || (echo [FEHLER] git fehlt: https://git-scm.com/download/win ^& pause ^& exit /b 1)
findstr /L /C:"0.5.9.31 Beta" main.py >nul || (echo [FEHLER] main.py traegt nicht die Version 0.5.9.31 ^& pause ^& exit /b 1)
if not exist "raceroom_sm.py" (echo [FEHLER] raceroom_sm.py fehlt im Paket ^& pause ^& exit /b 1)
if not exist "assets\r3e_names.json" (echo [FEHLER] assets\r3e_names.json fehlt im Paket ^& pause ^& exit /b 1)
if not exist ".github\workflows\release.yml" (echo [FEHLER] .github\workflows\release.yml fehlt - Force-Push wuerde die CI loeschen ^& pause ^& exit /b 1)
if not exist ".git" git init
git config user.name  >nul 2>nul || git config user.name  "Pfoetiman76"
git config user.email >nul 2>nul || git config user.email "Pfoetiman76@users.noreply.github.com"
git add -A
git commit -m "Release 0.5.9.31 - RaceRoom (R3E) Shared-Memory-Quelle" 2>nul
git branch -M main
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/Pfoetiman76/pitboss.git
git push -f origin main
if errorlevel 1 goto PUSHFAIL
echo - Tag v0.5.9.31 sauber neu setzen (verhindert No-Op / haengende CI)...
git tag -d v0.5.9.31 2>nul
git push origin :refs/tags/v0.5.9.31 2>nul
git tag v0.5.9.31
git push origin v0.5.9.31
if errorlevel 1 goto TAGFAIL
echo.
echo Fertig. Build laeuft in ~1-2 Min:
echo   https://github.com/Pfoetiman76/pitboss/actions
goto END
:PUSHFAIL
echo [FEHLER] main-Push fehlgeschlagen. Eingeloggt? Sonst: gh auth login
goto END
:TAGFAIL
echo [FEHLER] Tag-Push fehlgeschlagen. Eingeloggt? Sonst: gh auth login
:END
pause
