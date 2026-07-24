LMU Consistency Coach 0.4.9.4 Beta

Neu gegenueber 0.4.8.2:
- Standard-Rundenzeit-Referenz mit Skill-Level: Auswahl Klasse (LMGT3/LMH/LMP3/
  LMP2 ELMS/LMP2 WEC/GTE), Strecke und Level (Alien/Competitive/Good/Midpack/
  Tail-Ender/Offline). Die Ziel-Rundenzeit wird angezeigt; die Auswahl bleibt
  gespeichert (exports/standard_reference.json).
- Datengrundlage: Snapshot der ALIEN-Basiszeiten aus 'Ohne Speed's - LMU laptimes'
  (Stand 2026-07-21). Die Level werden als Prozentaufschlag berechnet (101/102/104/
  106/107 %), exakt wie in der Tabelle. Voll offline, kein Cloud-Zugriff.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.8.2 Beta

Neu gegenueber 0.4.8.1:
- Light-Theme ueberarbeitet: Logo bleibt sichtbar (dunkler Chip), Titel nimmt die
  Theme-Textfarbe, 'Overlays'/'Mehr'/'Profil'-Dropdowns passen sich jetzt Hell/Dunkel an.
- Die vier Profil-Buttons (neu/laden/speichern/loeschen) sind zu einem 'Profil'-Dropdown
  zusammengefasst.
- Ansicht-Dropdown aufgeraeumt: flache Liste ohne die Gruppen-Ueberschriften
  'ANALYSE' und 'COACHING' (und ohne Einrueckungen).

Offen (braucht deine Tabellenstruktur): Standard-Rundenzeiten als Referenz mit
Skill-Level-Auswahl (Alien/Competitive/Good/Midpack/Tail-Ender/Offline).

----------------------------------------------------------------------

LMU Consistency Coach 0.4.8.1 Beta

Neu gegenueber 0.4.8.0 (UI-Feinschliff):
- Recording als EIN Toggle-Button (Start/Stop statt zwei Buttons).
- Beim Recording-Start wird der Snapshot automatisch gelesen (kein extra Knopf;
  'Snapshot lesen (manuell)' liegt jetzt im 'Mehr'-Menue).
- Die Overlays (Reifen/Pedal/Monitor) sind in EIN 'Overlays'-Dropdown gewandert.
- Dark-/Light-Umschalter unter 'Mehr' -> 'Design: Hell/Dunkel' (bleibt gespeichert).
- Aufgeraeumt: Hilfetext und die Hardware-/Settings-Kontext-Vorschau entfernt;
  System-Log/Debug standardmaessig ausgeblendet ('Mehr' -> 'System-Log ein/aus').

----------------------------------------------------------------------

LMU Consistency Coach 0.4.8.0 Beta

Neu gegenueber 0.4.7.5:
- Piper (natuerliche Offline-Stimme) ist im Installer ENTHALTEN und wird
  automatisch erkannt: kein manuelles Einrichten mehr noetig. Beim Bauen laedt
  die CI eine MIT-lizenzierte Piper-Binary + die deutsche Thorsten-Stimme und
  bundelt sie. Die App findet 'piper/piper.exe' + '*.onnx' beim Start selbst.
  (Manuelles Setzen ueber 'Natuerliche Stimme (Piper)...' bleibt als Option.)
- Moderne UI: neues Theme mit Pill-Tabs (Akzent-Fill), groesseren Radien,
  Akzent-Primaerbutton, dezenteren Tabellen sowie modernen Menues/Scrollbars.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.7.5 Beta

Neu gegenueber 0.4.7.4:
- Update-Pruefung: 'Mehr' -> 'Nach Updates suchen...'. Vergleicht die installierte
  Version mit dem neuesten GitHub-Release und fuehrt bei Bedarf zur Download-Seite.
  Einmalig 'GITHUB_REPO' in updater.py auf dein 'benutzer/repo' setzen.
- Projekt ist GitHub-fertig: README.md, LICENSE (MIT), .gitignore (schliesst
  exports/ mit dem API-Key aus!), Release-Anleitung (RELEASING.md).
- Windows-Installer-Pipeline: installer/lmu_coach.spec (PyInstaller) +
  installer/setup.iss (Inno Setup) + .github/workflows/release.yml. Ein Tag 'vX.Y.Z'
  baut per GitHub Actions automatisch den Setup-Installer und haengt ihn ans Release.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.7.4 Beta

Neu gegenueber 0.4.7.3:
- Automatisches Vorlesen der KI-Analyse WIEDER aktiv und standardmaessig AN.
  Nach 'Report analysieren' wird das Ergebnis automatisch gesprochen (Piper,
  sonst SAPI). Steuerung ueber die Checkbox 'Analyse automatisch vorlesen';
  Einstellung bleibt erhalten (exports/tts_config.json). 'Stop' bricht ab.
  Hinweis zur Vorgeschichte: analyze() laeuft synchron im GUI-Thread, der
  Sprach-Aufruf war also nie ein Thread-Problem - vorher war die Option nur
  standardmaessig aus bzw. es kam noch kein Ton. Jetzt: Default an + geprueft.
  Es wird die komplette Analyse vorgelesen; auf Wunsch kuerzbar auf die 3
  Kernsaetze.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.7.3 Beta

Neu gegenueber 0.4.7.2:
- KEIN automatisches Vorlesen mehr. Sprachausgabe startet nur manuell ueber
  'Analyse vorlesen' bzw. 'Testtext'. Die Checkbox 'automatisch vorlesen' entfaellt.
- Natuerliche, OFFLINE Stimme via Piper (optionales Backend, kein Cloud):
  Button 'Natuerliche Stimme (Piper)...' im KI-Fenster -> piper-Programm und ein
  Stimm-Modell (.onnx) waehlen. Ist beides gesetzt, nutzt die App automatisch
  Piper (Anzeige beim Testtext: 'backend: piper (natuerlich)'). Sonst weiter SAPI.
  Backend-Prioritaet: Piper -> SAPI5 (pywin32) -> PowerShell System.Speech.

  Einrichtung Piper (einmalig, ~40 MB, komplett offline):
   1) Piper holen: 'pip install piper-tts' (erzeugt piper.exe im Scripts-Ordner)
      ODER die Standalone-Binary vom aktuellen Repo OHF-Voice/piper1-gpl
      (GitHub Releases) herunterladen und entpacken.
   2) Deutsche Stimme 'de_DE-thorsten' (high oder medium) laden - zwei Dateien:
      de_DE-thorsten-high.onnx  UND  de_DE-thorsten-high.onnx.json
      (rhasspy/piper-voices bzw. Thorsten-Voice/Piper auf HuggingFace).
      WICHTIG: beide Dateien in DENSELBEN Ordner legen - Piper laedt die .json
      automatisch neben der .onnx.
   3) In der App auf 'Natuerliche Stimme (Piper)...' klicken, piper-Programm und
      die .onnx-Datei waehlen. Fertig; Auswahl bleibt in exports/tts_config.json.
  Hinweis: Piper synthetisiert lokal auf der CPU (schneller als Echtzeit) und
  spielt per Windows-Audio ab. Rate/Tempo-Regler wirken nur auf SAPI, nicht Piper.
- Sofort-Tipp ohne Piper: in 'Stimme' eine DEUTSCHE Systemstimme waehlen - eine
  englische Stimme, die deutschen Text liest, ist die haeufigste Ursache fuer
  'klingt unnatuerlich'.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.7.2 Beta

Neu gegenueber 0.4.7.1:
- Offline-Sprachausgabe im KI-Analyse-Fenster (keine Cloud):
  * Backend SAPI5 via pywin32 (asynchron, niedrige Latenz); Fallback PowerShell
    System.Speech (immer auf Windows vorhanden). Auf Nicht-Windows sauber
    deaktiviert, ohne Absturz.
  * Stimmenauswahl, Tempo (-10..10). Einstellungen bleiben erhalten
    (exports/tts_config.json).
  * Ablauf wie geplant: zuerst 'Testtext' (Backend pruefen), dann ans Coaching
    gekoppelt - Button 'Analyse vorlesen' bzw. Checkbox 'Analyse automatisch
    vorlesen'. 'Stop' bricht die Ausgabe ab.
  * Markdown/Aufzaehlungszeichen werden vor dem Sprechen entfernt.

----------------------------------------------------------------------

LMU Consistency Coach 0.4.7.1 Beta

Neu gegenueber 0.4.7.0:
- KI-Kontingent-Uebersicht im KI-Analyse-Fenster (Gemini): Requests/Tokens pro Tag.
  Wichtig: Die Gemini-API liefert KEIN Rest-Kontingent zurueck (kein Endpoint dafuer),
  daher lokal gezaehlt (exports/ai_quota_usage.json). Tagesbudget im UI einstellbar
  (Default 1500 Requests). Reset an Mitternacht Pacific Time (passend zu Googles RPD;
  ohne das Paket 'tzdata' Fallback auf lokale Tagesgrenze).
- Warnhinweise bei 80 %, 90 % und 95 % des Tagesbudgets (je einmal pro Tag),
  plus getrennte Meldung bei HTTP 429 (hartes Limit: RPD -> Reset Mitternacht PT,
  RPM/TPM -> kurzer Backoff).
- Pedal-/Lenk-Trace-Overlay (scrollender History-Graph) als Desktop-Overlay,
  verschiebbar, Always-on-top, bewusst KEIN SteamVR (laeuft im VDXR-Mirror mit).
  Zeigt die ROH-Fahrereingabe ueber die Zeit: Gas gruen (mit Flaeche), Bremse rot,
  Lenkung cyan um die Mittellinie. Keine Kupplung. Quelle: mUnfilteredThrottle/
  Brake/Steering. Umschalten ueber Button 'Pedal-Overlay' bzw. 'Mehr'-Menue
  (kein Hotkey belegt, da F6-F10 vergeben).

----------------------------------------------------------------------

LMU Consistency Coach 0.4.5.4 Beta

Neu gegenüber 0.4.5.3:
- PB-Referenz laden
- kann die veröffentlichte Google-Tabelle "Ohne Speed's - LMU laptimes spreadsheet" als CSV laden
- alternativ lokale CSV-Datei importieren
- Dashboard-Kachel "PB-Bereich"
- Report-Block "Persönlicher Bestzeiten-Referenzbereich"
- Einordnung der persönlichen Bestzeit nach Strecke/Fahrzeugklasse/Fahrzeug, soweit die CSV-Spalten vorhanden sind
- zeigt ungefähres Feld: Top 10%, Top 25%, vordere Hälfte, Mittelfeld oder hinteres Feld/Einsteigerbereich

Hinweis:
Wenn Online-Laden auf deinem System nicht funktioniert, öffne die Tabelle im Browser, lade sie als CSV herunter und nutze "PB-Referenz laden" -> lokale CSV.


0.4.5.5 Beta:
- Flatspot-Event-Log aus 0.4.5.3 wieder additiv aufgesetzt (war in 0.4.5.4b nicht enthalten).
  Report-Abschnitt "Flatspot-Event-Log 0.4.5.5": Runde, Streckenmeter, Speed,
  Bremsdruck, Lenkwinkel, betroffener Reifen, Ereignistyp.
  "Flatspot" = echter LMU-mFlat-Status (steigende Flanke, einmal pro Ereignis).
  "Lockup"/"ABS-Lock" = starker Schlupf unter Bremse (grip_fract >= 0.35), zu Bursts
  gruppiert, Peak-Sample als Ursachen-Kandidat.
- Vereint jetzt alle drei Features: PB-Bereich (aus 0.4.5.4b), Hardwareprofil-Import
  (aus 0.4.5.4b) und Flatspot-Event-Log.
- Rein additiv gegenueber 0.4.5.4b: eine neue Methode + ein Report-Hook. Keine Aenderung
  an PB-/Hardware-Features, GUI-Struktur, Qt oder PySide.


0.4.5.6 Beta:
- Flatspot-Ursprung jetzt klassenabhaengig und nur bei bestaetigtem mFlat ausgeloest.
  GT3/ABS -> Dreher/Slide (groesstes Lenk-Reversal im Vorlauf, da ABS Geradeaus-Blockaden
  verhindert). Nicht-ABS (Hypercar/LMP/GTE) -> haerteste Bremsung mit staerkster Verzoegerung.
- grip_fract-basierte Lockup-Erkennung entfernt (Feld ist in echten LMU-Aufnahmen leer).
- Report nennt pro bestaetigtem Flatspot Runde+Meter des wahrscheinlichen Ursprungs samt
  Kontext (Bremse, Speed-Fenster, Invalidierung). An echter Session validiert:
  HR-Flatspot Lap 27 -> Ursprung Dreher Lap 27 ~741 m.
- Rein additiv/isoliert in flatspot_event_log_lines. Keine Aenderung an PB, Hardware-Import,
  GUI, Qt oder PySide.


0.4.6.0 Beta:
- Neues, kohaerentes UI-Theme mit LMU-Orange-Akzent (#ff5a1f): aktiver Tab mit Akzent-
  Unterstrich, Fokus-/Auswahlrahmen, GroupBox-Titel, Tabellen-Header und -Auswahl,
  gestylte Scrollbars, einheitliche Buttons/Inputs.
- Rein praesentativ: nur das zentrale Stylesheet ersetzt. Kein Layout-, Logik-, Qt- oder
  PySide-Eingriff. Alle Funktionen (Flatspot-Ursprung, PB, Hardware-Import) unveraendert.
- Naechster Optik-Schritt (separat): Entschlacken der 13-Button-Leiste und der 12 Tabs.


0.4.6.1 Beta:
- Reifen-Overlay VR-tauglich ueberarbeitet (2x2 beibehalten):
  * NEU pro Reifen: Carcass-Temp (Carc) und Verschleiss-Trend im Stint (Pfeil an Rest

0.4.6.1 Beta:
- Reifen-Overlay VR-tauglich ueberarbeitet (2x2 beibehalten):
  * NEU pro Reifen: Carcass-Temp (Carc) und Verschleiss-Trend im Stint (Pfeil an Rest-Prozent).
  * Flat/Lock-Warnung nur bei Nicht-GT3 (GT3-Flatspots kommen vom Dreher, nicht vom Lockup).
  * Skalierung (Mausrad oder Rechtsklick-Menue 75-200 Prozent) und Deckkraft (Rechtsklick 40-100 Prozent)
    fuer bessere Lesbarkeit im VD-Stream; Default-Skalierung 130 Prozent.
  * Kein Druck-Delta (bewusst weggelassen).
- Bedienung im VR: Overlay per Virtual-Desktop-Overlay in den Raum pinnen.
- Rein am Overlay geaendert (TireMiniWidget/TireOverlayWindow). Report, PB, Hardware,
  Theme, Qt/PySide unveraendert.


0.4.6.2 Beta:
- Reifen-Overlay oeffnet sich automatisch, sobald der Fahrer auf der Strecke ist
  (Fahrsample erkannt), einmal pro Sitzung. Kein Button/Hotkey noetig. Nach manuellem
  Schliessen poppt es nicht erneut auf. Schalter: self.tire_overlay_autostart.
- Hinweis VR-Sichtbarkeit: Ohne SteamVR kann die App das Fenster nicht selbst in die
  VR-Ansicht kompositieren. Bei flachem VD-Bildschirm erscheint es automatisch; bei
  echtem VR-Titel muss es einmalig ueber das Virtual-Desktop-Overlay gepinnt werden.
- Rein additiv (eine Methode + ein live_tick-Hook). Overlay-Optik, Report, PB, Hardware
  unveraendert.


0.4.6.3 Beta (Declutter):
- Navigation aufgeraeumt: breite 12er-Tab-Leiste ausgeblendet, stattdessen ein gruppiertes
  "Ansicht"-Dropdown: Dashboard | Live | Reifen | Analyse (Analyse/Runden/Vergleich/Heatmap/
  Setup-Coach) | Coaching (Coach/Limit-Coach/Input-Coach) | Fahrer & Hardware.
- Aktionsleiste kompakt: sichtbar nur Snapshot, Recording starten/stoppen, Report, Reifen-Overlay;
  der Rest (CSV, Referenz ex/import, PB-Referenz, Auto-Bestlap, Monitor-Overlay, Export-Ordner,
  Loeschen) sitzt im "Mehr"-Menue. Alle Buttons bleiben funktional, nur versteckt + ueber Menue.
- Rein an Navigation/Anordnung geaendert. Alle Seiteninhalte, Logik, Signale, Report, PB,
  Hardware, Overlay unveraendert. Tab-Seiten selbst wurden NICHT angefasst.


0.4.7.0 Beta (Gemini-Basis, Stage 1 von Live-Coach):
- KI-Analyse (Gemini) im Tab "Fahrer & Hardware": API-Key-Feld (verdeckt) + Modellfeld
  (Default gemini-2.5-flash), "Key speichern" (lokal in exports/gemini_config.json, NIE im Code),
  "KI-Analyse (Report)" schickt den erzeugten Report an Gemini und zeigt priorisiertes Coaching.
- Direkter REST-Call ueber urllib (kein SDK). Endpoint generativelanguage.googleapis.com
  v1beta generateContent, Auth per x-goog-api-key-Header.
- Fehlerbehandlung: HTTP-/Netzwerkfehler werden im Status angezeigt, App bleibt stabil.
- Rein additiv. Naechste Stufen: 0.4.7.1 Sprachausgabe (TTS/SAPI), 0.4.7.2 Live-Coach.

0.4.7.0 Beta (Korrektur):
- Default-Modell auf gemini-3.5-flash geaendert (gemini-2.5-flash ist fuer neue Keys nicht
  mehr freigegeben -> HTTP 404 NOT_FOUND).
- NEU "Modelle laden": fragt via ListModels die fuer DEINEN Key verfuegbaren generateContent-
  Modelle ab und setzt automatisch ein Flash-Modell. Robust gegen kuenftige Umbenennungen.

0.4.7.0 Beta (Ueberarbeitung KI-Analyse):
- Modell FEST auf gemini-3.5-flash verankert (GEMINI_MODEL). "Modelle laden" entfernt,
  da es fuer den Key gemini-2.5-flash zog (nicht mehr freigegeben).
- KI-Analyse laeuft jetzt in EIGENEM Fenster (GeminiWindow): API-Key + Key speichern +
  Report analysieren + Ausgabe. Ueber Button "KI-Analyse" neben dem Setup-Feld zu oeffnen.
- Neuer Button "Fahrer & Hardware" neben dem Setup-Feld wechselt direkt in diese Ansicht.
- Gemini-UI aus dem Tab "Fahrer & Hardware" entfernt; Key wird in exports/gemini_config.json
  gespeichert und beim Start in self.gemini_api_key geladen.
