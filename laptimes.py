"""
LMU Consistency Coach — Standard-Rundenzeiten-Referenz  (additiv, 0.4.8.3)
=========================================================================

Quelle: "Ohne Speed's - LMU laptimes" (oeffentliche Google-Tabelle).
Snapshot der ALIEN-Basiszeiten (~100% Racepace) je Klasse/Strecke, Stand
2026-07-21. Die Skill-Level ergeben sich als Prozentaufschlag auf Alien
(so rechnet die Tabelle selbst):

    Alien 100%  Competitive 101%  Good 102%  Midpack 104%  Tail-Ender 106%  Offline 107%

Damit muss nur die Alien-Zeit gespeichert werden; alle Level werden berechnet.
Voll offline, kein Cloud-Zugriff noetig.
"""

from __future__ import annotations

SNAPSHOT_DATE = "2026-07-21"
SOURCE = "Ohne Speed's - LMU laptimes"

# Skill-Level -> Faktor auf die Alien-Zeit
LEVELS = [
    ("Alien", 1.00),
    ("Competitive", 1.01),
    ("Good", 1.02),
    ("Midpack", 1.04),
    ("Tail-Ender", 1.06),
    ("Offline", 1.07),
]

CLASSES = ["LMGT3", "LMH", "LMP3", "LMP2 ELMS", "LMP2 WEC", "GTE"]

# Alien-Basiszeiten "M:SS.xx" je Klasse/Strecke
ALIEN = {
"LMGT3": {
 "Bahrain (wec)":"1:59.09","Bahrain (endurance)":"2:26.28","Bahrain (outer)":"1:12.43","Bahrain (paddock)":"1:21.10",
 "Barcelona":"1:41.05","Circuit de la Sarthe":"3:56.29","Circuit de la Sarthe (straight)":"3:40.43",
 "COTA":"2:06.13","COTA (national)":"1:30.63","Fuji (chicane)":"1:40.30","Fuji (classic)":"1:36.45",
 "Imola":"1:42.31","Interlagos":"1:33.77","Monza":"1:48.96","Monza (curvagrande)":"1:39.47",
 "Paul Ricard":"2:03.80","Paul Ricard (1A)":"1:50.62","Paul Ricard (1A v2)":"1:55.85","Paul Ricard (1A v2 short)":"1:46.36","Paul Ricard (3A)":"1:19.95",
 "Portimao":"1:43.64","Qatar":"1:54.27","Qatar (short)":"1:09.14","Silverstone (GP)":"1:58.44",
 "Silverstone (National)":"0:53.27","Silverstone (International)":"1:01.28","Sebring":"2:00.44","Sebring (school)":"1:02.90","Spa":"2:17.79"},
"LMH": {
 "Bahrain (wec)":"1:45.81","Bahrain (endurance)":"2:10.63","Bahrain (outer)":"1:04.23","Bahrain (paddock)":"1:11.80",
 "Barcelona":"1:28.97","Circuit de la Sarthe":"3:24.22","Circuit de la Sarthe (straight)":"3:10.72",
 "COTA":"1:52.38","COTA (national)":"1:21.27","Fuji (chicane)":"1:28.76","Fuji (classic)":"1:24.80",
 "Imola":"1:30.04","Interlagos":"1:22.90","Monza":"1:35.28","Monza (curvagrande)":"1:26.34",
 "Paul Ricard":"1:49.07","Paul Ricard (1A)":"1:36.84","Paul Ricard (1A v2)":"1:41.76","Paul Ricard (1A v2 short)":"1:34.17","Paul Ricard (3A)":"1:10.12",
 "Portimao":"1:31.58","Qatar":"1:39.93","Qatar (short)":"0:59.77","Silverstone (GP)":"1:42.88",
 "Silverstone (National)":"0:46.40","Silverstone (International)":"0:53.38","Sebring":"1:46.13","Sebring (school)":"0:55.48","Spa":"2:00.42"},
"LMP3": {
 "Bahrain (wec)":"1:54.02","Bahrain (endurance)":"2:19.93","Bahrain (outer)":"1:09.77","Bahrain (paddock)":"1:17.67",
 "Barcelona":"1:35.24","Circuit de la Sarthe":"3:45.20","Circuit de la Sarthe (straight)":"3:30.74",
 "COTA":"2:00.51","COTA (national)":"1:26.28","Fuji (chicane)":"1:34.94","Fuji (classic)":"1:30.81",
 "Imola":"1:37.79","Interlagos":"1:29.18","Monza":"1:43.93","Monza (curvagrande)":"1:34.51",
 "Paul Ricard":"1:57.45","Paul Ricard (1A)":"1:45.28","Paul Ricard (1A v2)":"1:49.73","Paul Ricard (1A v2 short)":"1:41.71","Paul Ricard (3A)":"1:15.90",
 "Portimao":"1:38.49","Qatar":"1:47.27","Qatar (short)":"1:05.01","Silverstone (GP)":"1:51.29",
 "Silverstone (National)":"0:50.11","Silverstone (International)":"0:57.69","Sebring":"1:54.29","Sebring (school)":"0:59.31","Spa":"2:11.17"},
"LMP2 ELMS": {
 "Bahrain (wec)":"1:46.37","Bahrain (endurance)":"2:12.20","Bahrain (outer)":"1:05.32","Bahrain (paddock)":"1:13.04",
 "Barcelona":"1:27.96","Circuit de la Sarthe":"3:27.86","Circuit de la Sarthe (straight)":"3:13.67",
 "COTA":"1:52.24","COTA (national)":"1:21.49","Fuji (chicane)":"1:29.51","Fuji (classic)":"1:25.35",
 "Imola":"1:30.39","Interlagos":"1:23.25","Monza":"1:36.35","Monza (curvagrande)":"1:27.70",
 "Paul Ricard":"1:49.79","Paul Ricard (1A)":"1:38.02","Paul Ricard (1A v2)":"1:42.23","Paul Ricard (1A v2 short)":"1:35.38","Paul Ricard (3A)":"1:11.32",
 "Portimao":"1:31.99","Qatar":"1:39.13","Qatar (short)":"0:59.35","Silverstone (GP)":"1:42.65",
 "Silverstone (National)":"0:46.63","Silverstone (International)":"0:53.83","Sebring":"1:46.06","Sebring (school)":"0:55.40","Spa":"2:01.76"},
"LMP2 WEC": {
 "Bahrain (wec)":"1:49.99","Bahrain (endurance)":"2:16.41","Bahrain (outer)":"1:07.14","Bahrain (paddock)":"1:14.74",
 "Barcelona":"1:31.85","Circuit de la Sarthe":"3:34.58","Circuit de la Sarthe (straight)":"3:19.42",
 "COTA":"1:56.91","COTA (national)":"1:24.03","Fuji (chicane)":"1:31.82","Fuji (classic)":"1:28.02",
 "Imola":"1:34.42","Interlagos":"1:26.40","Monza":"1:39.66","Monza (curvagrande)":"1:30.70",
 "Paul Ricard":"1:53.22","Paul Ricard (1A)":"1:41.27","Paul Ricard (1A v2)":"1:45.48","Paul Ricard (1A v2 short)":"1:38.40","Paul Ricard (3A)":"1:13.58",
 "Portimao":"1:35.51","Qatar":"1:43.27","Qatar (short)":"1:01.90","Silverstone (GP)":"1:46.67",
 "Silverstone (National)":"0:48.75","Silverstone (International)":"0:56.25","Sebring":"1:50.41","Sebring (school)":"0:57.36","Spa":"2:05.57"},
"GTE": {
 "Bahrain (wec)":"1:58.68","Bahrain (endurance)":"2:24.26","Bahrain (outer)":"1:11.55","Bahrain (paddock)":"1:19.68",
 "Barcelona":"1:40.21","Circuit de la Sarthe":"3:51.54","Circuit de la Sarthe (straight)":"3:37.37",
 "COTA":"2:03.30","COTA (national)":"1:27.99","Fuji (chicane)":"1:39.24","Fuji (classic)":"1:33.15",
 "Imola":"1:40.67","Interlagos":"1:32.97","Monza":"1:46.79","Monza (curvagrande)":"1:37.54",
 "Paul Ricard":"2:04.93","Paul Ricard (1A)":"1:41.87","Paul Ricard (1A v2)":"1:46.46","Paul Ricard (1A v2 short)":"1:38.81","Paul Ricard (3A)":"1:13.84",
 "Portimao":"1:43.13","Qatar":"1:52.40","Qatar (short)":"1:08.53","Silverstone (GP)":"1:47.55",
 "Silverstone (National)":"0:48.60","Silverstone (International)":"0:56.00","Sebring":"1:58.99","Sebring (school)":"1:01.67","Spa":"2:15.64"},
}


def time_to_seconds(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        if ":" in s:
            m, rest = s.split(":", 1)
            return int(m) * 60 + float(rest)
        return float(s)
    except Exception:
        return 0.0


def seconds_to_time(sec: float) -> str:
    if sec <= 0:
        return "--:--.--"
    m = int(sec // 60)
    r = sec - m * 60
    return f"{m}:{r:05.2f}"


def tracks_for(cls: str):
    return sorted(ALIEN.get(cls, {}).keys())


def level_factor(level: str) -> float:
    for name, f in LEVELS:
        if name == level:
            return f
    return 1.0


def target_time(cls: str, track: str, level: str):
    """Zielzeit (Sekunden, formatiert) fuer Klasse/Strecke/Level oder None."""
    base = time_to_seconds(ALIEN.get(cls, {}).get(track, ""))
    if base <= 0:
        return None
    sec = base * level_factor(level)
    return sec, seconds_to_time(sec)
