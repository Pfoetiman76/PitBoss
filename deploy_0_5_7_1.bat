@echo off
setlocal
cd /d "%~dp0"
echo == Deploy PitBoss 0.5.7.1 ==
where git >nul 2>nul || (echo [FEHLER] git fehlt: https://git-scm.com/download/win ^& pause ^& exit /b 1)
if not exist ".git" git init
git config user.name  >nul 2>nul || git config user.name  "Pfoetiman76"
git config user.email >nul 2>nul || git config user.email "Pfoetiman76@users.noreply.github.com"
git add -A
git commit -m "Release 0.5.7.1" 2>nul
git branch -M main
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/Pfoetiman76/lmu-consistency-coach.git
git push -f origin main
if errorlevel 1 goto PUSHFAIL
git tag v0.5.7.1 2>nul
git push origin v0.5.7.1
echo. & echo Fertig. Build: https://github.com/Pfoetiman76/lmu-consistency-coach/actions
goto END
:PUSHFAIL
echo [FEHLER] Push fehlgeschlagen. Eingeloggt? Sonst: gh auth login
:END
pause
