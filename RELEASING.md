# Release-Anleitung

## Schnellster Weg (einmaliges Setup + erstes Release)

`GITHUB_REPO` in `updater.py` ist bereits auf `Pfoetiman76/lmu-consistency-coach` gesetzt.

Voraussetzungen: **git** (https://git-scm.com) und **GitHub CLI** (https://cli.github.com).

Dann im Projektordner einfach ausfuehren:

- Windows: Doppelklick auf **`github_setup.bat`**
- Git Bash / WSL / Linux: **`./github_setup.sh`**

Das Skript meldet dich per Browser bei GitHub an (kein Passwort im Klartext),
legt das oeffentliche Repo an, pusht den Code und setzt den Tag `v0.4.7.5`.
GitHub Actions baut daraufhin automatisch den Windows-Installer und haengt ihn
ans Release. Fortschritt: `…/actions`, Ergebnis: `…/releases`.

----------------------------------------------------------------------

Voraussetzung einmalig: in `updater.py` `GITHUB_REPO = "dein-user/dein-repo"` setzen.

## Neues Release veröffentlichen

1. Version erhöhen: in `main.py` `APP_VERSION` anpassen (z. B. `0.4.7.6 Beta`).
2. Committen:
   ```bash
   git add -A
   git commit -m "Release 0.4.7.6"
   ```
3. Passenden Tag setzen und pushen (Tag **muss** zur Version passen, mit führendem `v`):
   ```bash
   git tag v0.4.7.6
   git push origin main --tags
   ```
4. GitHub Actions (`.github/workflows/release.yml`) baut auf `windows-latest`
   automatisch den Installer und hängt `LMU-Consistency-Coach-Setup-0.4.7.6.exe`
   ans erzeugte Release.
5. Nutzer sehen den Update-Hinweis über **„Mehr" → „Nach Updates suchen…"**.

## Erstmalige Einrichtung des Repos

```bash
git init
git add -A
git commit -m "Initial commit: LMU Consistency Coach 0.4.7.5"
git branch -M main
# Repo bei GitHub anlegen (Web) ODER mit GitHub CLI:
gh repo create lmu-consistency-coach --public --source=. --remote=origin --push
# ohne gh: erst leeres Repo auf github.com anlegen, dann:
git remote add origin https://github.com/DEIN-USER/lmu-consistency-coach.git
git push -u origin main
```

## Lokal testen (ohne CI)

```bash
pip install PySide6 pywin32 pyinstaller
pyinstaller installer/lmu_coach.spec --noconfirm
# Inno Setup installieren, dann:
iscc installer\setup.iss
# Ergebnis: installer\Output\LMU-Consistency-Coach-Setup-<version>.exe
```
