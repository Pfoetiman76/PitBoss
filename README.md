# PitBoss

Telemetrie-Coach für **Le Mans Ultimate** (auf Basis des offiziellen LMU Shared Memory),
ab 0.5.9.31 optional auch für **RaceRoom** (siehe unten).
Reifen-/Flatspot-Analyse, KI-Coaching (Gemini), Pedal-/Lenk-Trace-Overlay und
offline-Sprachausgabe.

> Beta-Software. Läuft unter Windows (LMU-Voraussetzung).

## Installation (Endnutzer)

1. Unter **[Releases](../../releases/latest)** die aktuelle
   `LMU-Consistency-Coach-Setup-x.y.z.exe` herunterladen und ausführen.
2. Starten über das Startmenü. Fertig.

Die App prüft auf Wunsch selbst auf neue Versionen: **„Mehr" → „Nach Updates suchen…"**.
Ist eine neuere Version verfügbar, führt der Button direkt zur Download-Seite.

## Aus dem Quellcode starten (Entwicklung)

```bash
pip install -r requirements.txt      # PySide6 (+ optional pywin32, tzdata)
python main.py
```

## Funktionen

- **Flatspot-Event-Log** mit Ursprung (Runde, Meter, Speed, Bremse, Lenkwinkel);
  klassenabhängig (GT3/ABS → Dreher, Nicht-GT3 → Brems-Lockup).
- **Reifen-Overlay** (Carcass-Temp, Verschleiß-Trend) und **Pedal-/Lenk-Trace-Overlay**
  (Gas/Bremse/Lenkung über die Zeit) als Desktop-Overlays.
- **KI-Analyse** (Gemini) mit priorisiertem Coaching, **KI-Kontingent-Anzeige**
  (lokal gezählt) inkl. Warnungen bei 80/90/95 %.
- **Offline-Sprachausgabe**: natürliche Stimme via **Piper** (kein Cloud),
  Fallback SAPI5/PowerShell. Optionales Auto-Vorlesen der Analyse.

## Sprachausgabe: natürliche Stimme (Piper) — im Installer enthalten

Vollständig offline. **Ab 0.4.8.0 ist Piper im Windows-Installer gebündelt** und wird
beim Start automatisch erkannt — kein manuelles Einrichten nötig.

Gebündelt werden (von der CI zur Build-Zeit geladen): die **MIT-lizenzierte
rhasspy/piper-Standalone-Binary** (per Subprozess aufgerufen, arm's-length) und die
deutsche Stimme **de_DE-thorsten (medium)**. Beim Start sucht die App
`piper/piper.exe` + `*.onnx` neben der Anwendung und nutzt sie automatisch.

Manuell überschreiben geht weiterhin über **„Natürliche Stimme (Piper)…"** im
KI-Fenster (eigene Piper-Binary/Stimme wählen).

## RaceRoom Racing Experience (ab 0.5.9.31)

PitBoss kann zusätzlich zu LMU die Telemetrie von **RaceRoom** (Shared Memory `$R3E`) lesen.
Overlays, Recording, Rundenanalyse, Reifen-/Pedal-/Pit-Overlays und Spotter-Daten laufen
dabei unverändert weiter. **Ohne Auswahl startet PitBoss wie bisher mit LMU.**

| Start | Wirkung |
|---|---|
| `Start-App-RaceRoom.bat` bzw. `python main.py --sim raceroom` | RaceRoom als Quelle |
| `python main.py --sim auto` | nimmt automatisch, was gerade läuft (LMU zuerst) |
| Umgebungsvariable `PITBOSS_SIM=raceroom` | dasselbe ohne Argument (z. B. für die installierte `PitBoss.exe`; alternativ eine Verknüpfung mit dem Zusatz ` --sim raceroom`) |

Die Quelle steht im Fenstertitel (`… · RaceRoom`). Diagnose/Kalibrierung:
`python raceroom_sm.py --probe` (Rohwerte), `--watch` (Live-Zeile), `--selftest`.

**Nicht verfügbar in RaceRoom** (die Felder bleiben 0, nichts wird erfunden): Karkassentemperatur,
Wetter/Strecken-/Lufttemperatur, Schadens-Dellen, Reifen-Schlupf, Abstand zum Führenden,
LMU-REST-Funktionen (Port 6397), LMU-Setup-Dateien und die LMU-PB-Referenzzeiten.

**Beim ersten Einsatz prüfen** (R3E dokumentiert das nicht eindeutig; PitBoss erkennt es selbst
und lässt sich überschreiben): Reifenverschleiß `1.0 = neu` oder `0.0 = neu`
(`PITBOSS_R3E_WEAR=new1|new0`) und Sektorzeiten kumulativ oder einzeln
(`PITBOSS_R3E_SECTORS=cumulative|single`). `--probe` zeigt beide Rohwerte.

Struktur nach Sector3-Header `r3e.h` v3.5; Auto-/Klassennamen aus Sector3s
`r3e-data.json` (Public Domain / Unlicense), reduziert in `assets/r3e_names.json`.

## Konfiguration für das eigene Repo

Vor dem ersten Release **`updater.py`** öffnen und `GITHUB_REPO` auf `dein-user/dein-repo`
setzen — sonst kann die App nicht nach Updates suchen.

## Release bauen (Maintainer)

Siehe **[RELEASING.md](RELEASING.md)**. Kurz: Tag `vX.Y.Z` pushen → GitHub Actions
baut den Windows-Installer (PyInstaller + Inno Setup) und hängt ihn ans Release.

## Lizenz

MIT (siehe [LICENSE](LICENSE)). Bündelt `pyLMUSharedMemory` (MIT, © 2021 Tony Whitley,
© 2025 Xiang).

## Hinweis

Kein API-Key gehört ins Repo. `exports/` (mit `gemini_config.json`) ist per
`.gitignore` ausgeschlossen.
