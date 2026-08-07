"""
PitBoss — MoTeC-CSV-Import fuer die KI-Analyse (additiv)
==================================================================

Zweck
-----
Liest einen "Generic CSV"-Export aus MoTeC i2 (File > Data Export) und baut
daraus einen Text-Report im selben Stil wie MainWindow.build_report(), damit
er ueber dieselbe Gemini-Analyse (GeminiWindow.analyze) ausgewertet werden
kann wie ein normaler PitBoss-Report.

An einer echten i2-Standard-Export-Datei verifiziertes Format:
- Zeilen 1-12: Metadaten als Key/Value-Paare (teils zwei Paare pro Zeile,
  durch leere Felder getrennt), z.B. "Venue","Silverstone...",,,"Worksheet",""
- danach zwei Leerzeilen
- Kanalnamen-Zeile (quoted, kommasepariert)
- Einheiten-Zeile
- zwei Leerzeilen
- Datenzeilen, eine pro Sample (bei Standard-Export ueblich: 100 Hz)

Wichtiger Fallstrick (an echten Daten geprueft): "G Force Long" ist bei
LMU/i2-Export POSITIV waehrend des Bremsens (Geschwindigkeit sinkt), nicht
beim Beschleunigen - umgekehrt zur intuitiven Erwartung. Alle Auswertungen
hier halten sich an dieses verifizierte Vorzeichen.

Nicht jeder MoTeC-Export hat exakt dieselben Kanalnamen (haengt vom
Fahrzeug/Plugin ab) - alle Auswertungen pruefen deshalb, ob ein Kanal
ueberhaupt vorhanden ist, bevor sie ihn nutzen, statt hart vorauszusetzen.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _parse_meta(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in lines[:14]:
        if not line.strip():
            continue
        try:
            parts = next(csv.reader([line]))
        except Exception:
            continue
        if len(parts) >= 2 and parts[0]:
            meta[parts[0]] = parts[1]
        if len(parts) >= 6 and parts[4]:
            meta[parts[4]] = parts[5]
    return meta


def parse_motec_csv(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()

    meta = _parse_meta(lines)

    header_idx = next((i for i, l in enumerate(lines) if l.startswith('"Time","Distance"')), None)
    if header_idx is None:
        raise ValueError(
            f"{path.name}: keine MoTeC-Kanalzeile gefunden (erwarte eine Zeile beginnend mit "
            f'"Time","Distance" - ist das wirklich ein MoTeC "Generic CSV"-Export?)'
        )

    header = next(csv.reader([lines[header_idx]]))
    data_lines = lines[header_idx + 3:]  # Einheiten-Zeile + 2 Leerzeilen ueberspringen
    rows = [r for r in csv.reader(data_lines) if len(r) == len(header)]
    if not rows:
        raise ValueError(f"{path.name}: Kanalzeile gefunden, aber keine gueltigen Datenzeilen.")

    idx = {name: i for i, name in enumerate(header)}
    return {"meta": meta, "header": header, "idx": idx, "rows": rows, "source_file": path.name}


def _col(parsed: dict, name: str) -> list[float] | None:
    idx = parsed["idx"]
    if name not in idx:
        return None
    i = idx[name]
    out = []
    for r in parsed["rows"]:
        try:
            out.append(float(r[i]))
        except (ValueError, IndexError):
            out.append(None)
    return out if any(v is not None for v in out) else None


def _fmt(v, unit="", digits=1):
    if v is None:
        return "n/v"
    return f"{v:.{digits}f}{unit}"


def _detect_input_device(parsed: dict) -> str:
    """Grobe Heuristik: Gamepad-Trigger haben typischerweise deutlich weniger
    eindeutige Zwischenwerte als analoge Wheel-Pedale (Load-Cell/Potentiometer).
    Kein harter Beweis, nur ein Hinweis fuer den Analyse-Prompt, damit Gemini
    z.B. stufige Pedalwerte nicht faelschlich als 'unsauber' bewertet."""
    throttle = _col(parsed, "Throttle Pos")
    brake = _col(parsed, "Brake Pos")
    if not throttle or not brake:
        return "unbekannt (Throttle/Brake-Kanal fehlt im Export)"
    n = len(parsed["rows"])
    uniq_throttle = len(set(v for v in throttle if v is not None))
    uniq_brake = len(set(v for v in brake if v is not None))
    if n == 0:
        return "unbekannt"
    ratio = (uniq_throttle + uniq_brake) / (2 * n)
    if ratio < 0.15:
        return f"vermutlich Gamepad/Controller (nur {uniq_throttle} Gas- und {uniq_brake} Brems-Stufen bei {n} Samples - grobe Eingabe-Aufloesung)"
    return f"vermutlich Wheel/Pedalset (feine Eingabe-Aufloesung: {uniq_throttle} Gas- und {uniq_brake} Brems-Stufen bei {n} Samples)"


def _detect_brake_zones(parsed: dict) -> list[tuple[float, float, float]]:
    """Liste von (Distanz_m, Speed_kmh, Zeit_s) an jedem Bremspunkt-Beginn."""
    brake = _col(parsed, "Brake Pos")
    dist = _col(parsed, "Distance")
    speed = _col(parsed, "Ground Speed")
    time = _col(parsed, "Time")
    if not brake or not dist or not speed or not time:
        return []
    zones = []
    for i in range(1, len(brake)):
        if brake[i - 1] is None or brake[i] is None:
            continue
        if brake[i - 1] < 5 and brake[i] >= 5:
            zones.append((dist[i] or 0.0, speed[i] or 0.0, time[i] or 0.0))
    return zones


def build_motec_report(path: str | Path) -> str:
    """Baut einen Text-Report im PitBoss-Report-Stil aus einer MoTeC-CSV,
    damit er ueber dieselbe Gemini-Analyse laeuft wie normale PitBoss-Reports.
    Wirft ValueError mit einer verstaendlichen Meldung bei Formatproblemen -
    der Aufrufer (GeminiWindow.analyze) faengt das ab und zeigt es im UI an."""
    parsed = parse_motec_csv(path)
    meta = parsed["meta"]
    n = len(parsed["rows"])

    lines = [
        "PitBoss – MoTeC-Import Report",
        f"Quelle: {parsed['source_file']} (MoTeC i2 Generic-CSV-Export)",
        f"Strecke: {meta.get('Venue', 'n/v')}",
        f"Fahrzeug: {meta.get('Vehicle', 'n/v')} ({meta.get('Vehicle Desc', '')})",
        f"Fahrer: {meta.get('Driver', 'n/v')}",
        f"Datum/Zeit: {meta.get('Log Date', 'n/v')} {meta.get('Log Time', '')}",
        f"Bereich: {meta.get('Range', 'n/v')} | Dauer: {meta.get('Duration', 'n/v')}s | Samplerate: {meta.get('Sample Rate', 'n/v')}Hz",
        f"Samples: {n}",
        f"Eingabegeraet (Heuristik, keine Garantie): {_detect_input_device(parsed)}",
        "",
    ]

    throttle = _col(parsed, "Throttle Pos")
    brake = _col(parsed, "Brake Pos")
    glat = _col(parsed, "G Force Lat")
    glong = _col(parsed, "G Force Long")

    if throttle:
        full = sum(1 for t in throttle if t is not None and t > 98)
        lines.append(f"Vollgas-Anteil: {100*full/n:.1f}% der Strecke/Runde")
    if throttle and brake:
        overlap = sum(1 for i in range(n) if throttle[i] and brake[i] and throttle[i] > 5 and brake[i] > 5)
        lines.append(f"Gas+Bremse gleichzeitig aktiv (Trail-Braking-Indikator): {100*overlap/n:.1f}% der Samples")
    if glat:
        vals = [v for v in glat if v is not None]
        if vals:
            lines.append(f"Max. laterale G-Kraft: {max(vals):.2f}G / {min(vals):.2f}G")
    if glong:
        vals = [v for v in glong if v is not None]
        if vals:
            lines.append(
                f"Max. Laengs-G: +{max(vals):.2f}G (Bremsen), {min(vals):.2f}G (Beschleunigen) "
                f"— Hinweis: positives Vorzeichen = Bremsen, nicht Beschleunigen (LMU/i2-Konvention)."
            )
    lines.append("")

    zones = _detect_brake_zones(parsed)
    if zones:
        lines.append(f"Erkannte Bremspunkte ({len(zones)}):")
        for d, s, t in zones:
            lines.append(f"  bei {d:.0f}m, {s:.0f} km/h, t={t:.1f}s")
        lines.append("")

    # Reifentemperaturen (Aussen/Mitte/Innen je Ecke, falls vorhanden)
    corners = ["FL", "FR", "RL", "RR"]
    tyre_lines = []
    for c in corners:
        o = _col(parsed, f"Tyre Temp {c} Outer")
        m = _col(parsed, f"Tyre Temp {c} Centre")
        i_ = _col(parsed, f"Tyre Temp {c} Inner")
        if o and m and i_:
            avg_o = sum(v for v in o if v is not None) / len(o)
            avg_m = sum(v for v in m if v is not None) / len(m)
            avg_i = sum(v for v in i_ if v is not None) / len(i_)
            tyre_lines.append(f"  {c}: außen={avg_o:.0f}C mitte={avg_m:.0f}C innen={avg_i:.0f}C (Differenz außen-innen: {avg_o-avg_i:+.0f}C)")
    if tyre_lines:
        lines.append("Reifentemperaturen (Schnitt):")
        lines += tyre_lines
        lines.append("")

    brake_lines = []
    for c in corners:
        bt = _col(parsed, f"Brake Temp {c}")
        if bt:
            vals = [v for v in bt if v is not None]
            brake_lines.append(f"  {c}: Schnitt={sum(vals)/len(vals):.0f}C Max={max(vals):.0f}C")
    if brake_lines:
        lines.append("Bremstemperaturen:")
        lines += brake_lines
        lines.append("")

    lines.append(
        "Hinweis fuer die Analyse: dies sind deskriptive Kennzahlen aus den Rohdaten, "
        "keine validierten Coaching-Urteile. Bei Gamepad-Eingabe (siehe Eingabegeraet-Zeile "
        "oben) bitte stufige Pedalwerte NICHT als unsauberes Fahren werten, sondern als "
        "Hardware-Aufloesung einordnen."
    )
    return "\n".join(lines)
