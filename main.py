import csv
import json
import os
# Suppress harmless Qt warnings as early as possible, before PySide6 loads.
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")
import math
import mmap
import sys
import subprocess
import shutil
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, astuple as _dc_astuple, fields as _dc_fields
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QTimer, Qt, QPointF, QRectF, QUrl, qInstallMessageHandler, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGroupBox, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget, QComboBox,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QTabWidget, QFrame,
    QCheckBox, QSpinBox, QProgressDialog, QSizeGrip
)

from pyLMUSharedMemory.lmu_data import LMUConstants, LMUObjectOut
import ctypes
from ai_quota import QuotaTracker, QuotaPanel  # 0.4.7.1: KI-Kontingent-Tracking
from tts import SpeechEngine  # 0.4.7.2: Offline-Sprachausgabe
import updater  # 0.4.7.5: Update-Pruefung ueber GitHub Releases
import motec_import  # 0.5.9.27: MoTeC-i2-CSV-Export als zusaetzliche Report-Quelle fuer die KI-Analyse
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QIcon, QPixmap, QDesktopServices, QShortcut, QKeySequence, QFont, QFontMetricsF, QLinearGradient, QPainterPath

APP_VERSION = "0.5.9.27 Beta"
AUTO_SWITCH_DEBOUNCE_SAMPLES = 20  # 0.5.9.24: ~2s bei 10 Hz, bevor ein Strecken-/Fahrzeugwechsel als real gilt
DARK_QSS = """
            QWidget { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: #e8edf4; }
            QLabel { color: #e8edf4; background: transparent; }
            QMainWindow, QWidget { background: #0a0d13; color: #e8edf4; }
            QTabWidget::pane { border: 1px solid #1e2530; border-radius: 14px; top: -1px; background: #10151d; }
            QTabBar::tab { background: #10151d; color: #8a97a8; padding: 9px 18px; margin-right: 6px; border: 1px solid transparent; border-radius: 10px; font-weight: 600; }
            QTabBar::tab:hover { color: #dbe3ee; background: #161d27; }
            QTabBar::tab:selected { color: #ffffff; background: rgba(255,106,43,0.16); border: 1px solid rgba(255,106,43,0.45); }
            QGroupBox { border: 1px solid #1e2530; border-radius: 14px; margin-top: 16px; padding: 14px; font-weight: 700; background: #10151d; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 2px 8px; color: #ff8a5c; letter-spacing: 0.5px; }
            QPushButton { background: #171e29; color: #e8edf4; border: 1px solid #262f3d; padding: 9px 16px; border-radius: 10px; font-weight: 600; }
            QPushButton:hover { background: #1e2733; border-color: #3a4759; }
            QPushButton:pressed { background: #101620; }
            QPushButton:disabled { color: #55606f; background: #10141c; border-color: #1c232d; }
            QPushButton#primary { background: #ff6a2b; color: #ffffff; border: 1px solid #ff6a2b; padding: 10px 20px; }
            QPushButton#primary:hover { background: #ff7d45; border-color: #ff7d45; }
            QPushButton#primary:pressed { background: #e85c22; }
            QTextEdit, QLineEdit, QTableWidget, QComboBox, QSpinBox { background: #0d121a; color: #e8edf4; border: 1px solid #1e2530; border-radius: 10px; selection-background-color: #ff6a2b; selection-color: #ffffff; }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid #ff6a2b; }
            QComboBox { padding-left: 36px; padding-right: 10px; min-height: 32px; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: left center; width: 30px; border-right: 1px solid #1e2530; border-left: none; background: #171e29; border-top-left-radius: 9px; border-bottom-left-radius: 9px; }
            QComboBox::drop-down:hover { background: #ff6a2b; }
            QComboBox::down-arrow { image: url(assets/dropdown_arrow_left.svg); width: 14px; height: 14px; }
            QComboBox QAbstractItemView { background: #0d121a; color: #e8edf4; selection-background-color: #ff6a2b; selection-color: #ffffff; outline: 0; border: 1px solid #1e2530; border-radius: 8px; padding: 4px; }
            QSpinBox { min-height: 28px; padding: 2px 6px; }
            QTableWidget { gridline-color: #171e27; alternate-background-color: #0f141c; border-radius: 10px; }
            QHeaderView::section { background: #121822; color: #9fabbb; padding: 8px; border: none; border-bottom: 1px solid #1e2530; font-weight: 700; }
            QTableWidget::item:selected { background: rgba(255,106,43,0.85); color: #ffffff; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 3px; }
            QScrollBar::handle:vertical { background: #2a3342; border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #ff6a2b; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { background: transparent; height: 10px; margin: 3px; }
            QScrollBar::handle:horizontal { background: #2a3342; border-radius: 5px; min-width: 30px; }
            QScrollBar::handle:horizontal:hover { background: #ff6a2b; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QMenu { background: #10151d; color: #e8edf4; border: 1px solid #1e2530; border-radius: 10px; padding: 6px; }
            QMenu::item { padding: 7px 20px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(255,106,43,0.18); color: #ffffff; }
            QToolButton { background: #171e29; color: #e8edf4; border: 1px solid #262f3d; padding: 9px 16px; border-radius: 10px; font-weight: 600; }
            QToolButton:hover { background: #1e2733; border-color: #3a4759; }
            QToolButton::menu-indicator { image: none; }
            QToolTip { background: #10151d; color: #e8edf4; border: 1px solid #2a3342; padding: 6px; border-radius: 6px; }
            QFrame#dashCard { background: #151d2a; border: 1px solid #2b3545; border-radius: 10px; padding: 10px; }
            QLabel#dashCardKey { color: #9fb0c4; font-size: 12px; background: transparent; }
            QLabel#dashCardVal { color: #ffffff; font-size: 18px; font-weight: bold; background: transparent; }
            QLabel#accentValue { color: #ff8a5c; font-size: 15px; font-weight: 800; background: transparent; }
        """
LIGHT_QSS = """
            QWidget { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: #1b2430; }
            QLabel { color: #1b2430; background: transparent; }
            QMainWindow, QWidget { background: #eef1f6; color: #1b2430; }
            QTabWidget::pane { border: 1px solid #d5dbe4; border-radius: 14px; top: -1px; background: #ffffff; }
            QTabBar::tab { background: #ffffff; color: #5b6675; padding: 9px 18px; margin-right: 6px; border: 1px solid transparent; border-radius: 10px; font-weight: 600; }
            QTabBar::tab:hover { color: #1b2430; background: #f0f3f8; }
            QTabBar::tab:selected { color: #b8431a; background: rgba(255,106,43,0.14); border: 1px solid rgba(255,106,43,0.5); }
            QGroupBox { border: 1px solid #d5dbe4; border-radius: 14px; margin-top: 16px; padding: 14px; font-weight: 700; background: #ffffff; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 2px 8px; color: #d1591f; letter-spacing: 0.5px; }
            QPushButton { background: #ffffff; color: #1b2430; border: 1px solid #cfd6e0; padding: 9px 16px; border-radius: 10px; font-weight: 600; }
            QPushButton:hover { background: #f2f5fa; border-color: #ff8a5c; }
            QPushButton:pressed { background: #e7ecf3; }
            QPushButton:disabled { color: #a7b0bd; background: #f4f6f9; border-color: #e2e7ee; }
            QPushButton#primary { background: #ff6a2b; color: #ffffff; border: 1px solid #ff6a2b; padding: 10px 20px; }
            QPushButton#primary:hover { background: #ff7d45; border-color: #ff7d45; }
            QPushButton#primary:pressed { background: #e85c22; }
            QTextEdit, QLineEdit, QTableWidget, QComboBox, QSpinBox { background: #ffffff; color: #1b2430; border: 1px solid #d5dbe4; border-radius: 10px; selection-background-color: #ff6a2b; selection-color: #ffffff; }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid #ff6a2b; }
            QComboBox { padding-left: 36px; padding-right: 10px; min-height: 32px; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: left center; width: 30px; border-right: 1px solid #d5dbe4; border-left: none; background: #f2f5fa; border-top-left-radius: 9px; border-bottom-left-radius: 9px; }
            QComboBox::drop-down:hover { background: #ff6a2b; }
            QComboBox::down-arrow { image: url(assets/dropdown_arrow_left.svg); width: 14px; height: 14px; }
            QComboBox QAbstractItemView { background: #ffffff; color: #1b2430; selection-background-color: #ff6a2b; selection-color: #ffffff; outline: 0; border: 1px solid #d5dbe4; border-radius: 8px; padding: 4px; }
            QSpinBox { min-height: 28px; padding: 2px 6px; }
            QTableWidget { gridline-color: #e6eaf0; alternate-background-color: #f7f9fc; border-radius: 10px; }
            QHeaderView::section { background: #f0f3f8; color: #5b6675; padding: 8px; border: none; border-bottom: 1px solid #d5dbe4; font-weight: 700; }
            QTableWidget::item:selected { background: rgba(255,106,43,0.85); color: #ffffff; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 3px; }
            QScrollBar::handle:vertical { background: #c4ccd8; border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #ff6a2b; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { background: transparent; height: 10px; margin: 3px; }
            QScrollBar::handle:horizontal { background: #c4ccd8; border-radius: 5px; min-width: 30px; }
            QScrollBar::handle:horizontal:hover { background: #ff6a2b; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QMenu { background: #ffffff; color: #1b2430; border: 1px solid #d5dbe4; border-radius: 10px; padding: 6px; }
            QMenu::item { padding: 7px 20px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(255,106,43,0.16); color: #1b2430; }
            QToolButton { background: #ffffff; color: #1b2430; border: 1px solid #cfd6e0; padding: 9px 16px; border-radius: 10px; font-weight: 600; }
            QToolButton:hover { background: #f2f5fa; border-color: #ff8a5c; }
            QToolButton::menu-indicator { image: none; }
            QToolTip { background: #ffffff; color: #1b2430; border: 1px solid #cfd6e0; padding: 6px; border-radius: 6px; }
            QFrame#dashCard { background: #ffffff; border: 1px solid #d5dbe4; border-radius: 10px; padding: 10px; }
            QLabel#dashCardKey { color: #5b6675; font-size: 12px; background: transparent; }
            QLabel#dashCardVal { color: #1b2430; font-size: 18px; font-weight: bold; background: transparent; }
            QLabel#accentValue { color: #d1591f; font-size: 15px; font-weight: 800; background: transparent; }
        """
APP_DIR = Path(__file__).resolve().parent

def _default_data_dir():
    """0.5.9.11: Nutzerdaten (Fahrer-Profil, Reports, Configs, Logs) unter
    Dokumente\\PitBoss statt neben der EXE. Fallback: Home bzw. exports/."""
    try:
        home = Path.home()
        docs = home / "Documents"
        return (docs if docs.is_dir() else home) / "PitBoss"
    except Exception:
        return APP_DIR / "exports"

_OLD_EXPORT_DIR = APP_DIR / "exports"   # bisheriger Ort (fuer einmalige Migration)
EXPORT_DIR = _default_data_dir()
REPORT_DIR = EXPORT_DIR / "reports"
CSV_DIR = EXPORT_DIR / "csv"
REFERENCE_DIR = EXPORT_DIR / "references"
DRIVER_PROFILE_PATH = EXPORT_DIR / "driver_hardware_profiles.json"
DRIVER_PROFILE_STATE_PATH = EXPORT_DIR / "driver_hardware_profile_state.json"
PROFILE_ASSET_DIR = EXPORT_DIR / "profile_assets"
PERSONAL_LAPTIME_REFERENCE_PATH = EXPORT_DIR / "personal_laptime_reference.csv"
GEMINI_CONFIG_PATH = EXPORT_DIR / "gemini_config.json"
LOG_DIR = EXPORT_DIR / "logs"  # 0.4.8.8: automatische Log-Dateien
BRAKE_MODEL_PATH = EXPORT_DIR / "brake_model.json"  # 0.4.9.2
DAMAGE_MODEL_PATH = EXPORT_DIR / "damage_model.json"  # 0.4.9.4
COACH_TIMING_PATH = EXPORT_DIR / "coach_timing.json"  # 0.4.9.8: Ansage-Vorlauf
OVERLAY_SIZES_PATH = EXPORT_DIR / "overlay_sizes.json"  # 0.4.9.8: Overlay-Groessen
BLINDSPOT_CONFIG_PATH = EXPORT_DIR / "blindspot.json"  # 0.5.9.13: Toter-Winkel (Flip)
GEMINI_MODEL = "gemini-3.5-flash"  # fest verankert (2.5-flash ist fuer neue Keys gesperrt)
PERSONAL_LAPTIME_REFERENCE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTN03UvJDm99byA6vQPZHKOCYVvfxLu1zkJAzdaKyROykzEKY2-Xl1rl1q5znZEf36m88dxMKsY2eaO/pub?output=csv"
# 0.5.9.11: einmalige Migration alter Daten (neben der EXE) -> Dokumente\PitBoss
try:
    if (_OLD_EXPORT_DIR.is_dir() and not EXPORT_DIR.exists()
            and _OLD_EXPORT_DIR.resolve() != EXPORT_DIR.resolve()):
        import shutil as _shutil
        _shutil.copytree(_OLD_EXPORT_DIR, EXPORT_DIR)
except Exception:
    pass
for _d in (EXPORT_DIR, REPORT_DIR, CSV_DIR, REFERENCE_DIR, PROFILE_ASSET_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)
ASSET_DIR = APP_DIR / "assets"



def qt_message_filter(mode, context, message):
    """Suppress harmless Qt font warning seen on some Windows systems.
    Keeps all other Qt messages visible.
    """
    try:
        msg = str(message)
        if "QFont::setPointSize: Point size <= 0" in msg:
            return
        print(msg, file=sys.stderr)
    except Exception:
        pass


def dec(b) -> str:
    try:
        return bytes(b).split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()
    except Exception:
        try:
            return bytes(b).split(b"\x00", 1)[0].decode("latin1", errors="ignore").strip()
        except Exception:
            return ""


def fnum(v, default=0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default



def fmt_lap_time(seconds: float, signed: bool = False) -> str:
    """Format absolute lap/sector times as [m]:ss.000, e.g. 1:54.321.
    For signed=True, keeps +/- in front of the formatted absolute value.
    """
    try:
        x = float(seconds)
    except Exception:
        return "-"
    if not math.isfinite(x) or x < -900:
        return "-"
    sign = ""
    if signed:
        if x > 0:
            sign = "+"
        elif x < 0:
            sign = "-"
        x = abs(x)
    elif x < 0:
        return "-"
    minutes = int(x // 60)
    rest = x - minutes * 60
    return f"{sign}{minutes}:{rest:06.3f}"




def parse_lap_time_to_seconds(text) -> float:
    """Accepts 3:33.177, 213.177, 03:33,177 or strings containing a lap time."""
    if text is None:
        return 0.0
    raw = str(text).strip().replace(',', '.')
    if not raw:
        return 0.0
    import re
    m = re.search(r'(\d{1,2})\s*[:;]\s*(\d{1,2}(?:\.\d{1,3})?)', raw)
    if m:
        return int(m.group(1)) * 60.0 + float(m.group(2))
    m = re.search(r'\b(\d{2,4}(?:\.\d{1,3})?)\b', raw)
    if m:
        val = float(m.group(1))
        return val if 20.0 <= val <= 1800.0 else 0.0
    return 0.0


def normalize_match_text(text: str) -> str:
    txt = (text or '').lower()
    keep = []
    for ch in txt:
        keep.append(ch if ch.isalnum() else ' ')
    return ' '.join(''.join(keep).split())

def grip_label_from_score(score: float) -> str:
    try:
        x = float(score)
    except Exception:
        x = 0.0
    if x >= 92:
        return "perfekt"
    if x >= 80:
        return "hoch"
    if x >= 60:
        return "mittel"
    return "niedrig"


def temp_color_for_tire(temp_c: float) -> QColor:
    try:
        t = float(temp_c)
    except Exception:
        t = 0.0
    if t <= 0:
        return QColor(70, 95, 120)
    if t < 55:
        return QColor(35, 135, 255)      # kalt / blau
    if t < 70:
        return QColor(240, 220, 45)      # Übergang / gelb
    if t <= 95:
        return QColor(25, 225, 55)       # optimal / grün
    if t <= 110:
        return QColor(255, 150, 25)      # warm / orange
    return QColor(240, 45, 35)           # heiß / rot

def infer_vehicle_class(vehicle_class: str, vehicle_name: str = "", vehicle_model: str = "") -> str:
    txt = f"{vehicle_class} {vehicle_name} {vehicle_model}".lower()
    if "gt3" in txt or "911gt3" in txt or "mustang" in txt or "lexus" in txt or "m4 gt" in txt:
        return "GT3"
    if "lmp2" in txt or "oreca" in txt:
        return "LMP2"
    if "hypercar" in txt or "lmh" in txt or "lmdh" in txt or "963" in txt or "499p" in txt:
        return "Hypercar"
    return (vehicle_class or "Unbekannt").strip() or "Unbekannt"


# 0.5.9.21: Breites Tier-Format der "Ohne Speed's - LMU laptimes"-Tabelle
# (eine Zeile pro Strecke/Klasse mit 8 Skill-Tier-Zeitspalten: Alien, Competitive,
# Good x2, Midpack x2, Tail-ender, Offline). Ergaenzt den bestehenden flachen
# Personal-Reference-Parser additiv, ersetzt ihn nicht.
def parse_personal_laptime_reference_wide_csv(text: str) -> List[dict]:
    if not text:
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=',;\t')
    except Exception:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect=dialect))
    n_rows = len(rows)
    entries: List[dict] = []

    def cell_at(r, c):
        return r[c].strip() if 0 <= c < len(r) else ''

    for idx, row in enumerate(rows):
        track_col = None
        for ci, cell in enumerate(row):
            if normalize_match_text(cell) == 'track':
                track_col = ci
                break
        if track_col is None:
            continue
        patch_col = track_col + 1
        hotlap_col = track_col + 2
        tier_cols = [track_col + 3 + j for j in range(8)]
        fastest_car_col = track_col + 11
        laptime_col = track_col + 12
        class_col = track_col + 15

        # Tiernamen: aus der Zeile ueber dem Header, Merged-Cell-Luecken werden
        # mit dem letzten bekannten Namen aufgefuellt (Good/Midpack belegen je 2 Spalten).
        name_row = rows[idx - 1] if idx - 1 >= 0 else []
        tier_names = []
        last_name = ''
        for c in tier_cols:
            v = cell_at(name_row, c)
            if v:
                last_name = v
            tier_names.append(last_name or '?')

        tier_pcts = []
        for c in tier_cols:
            v = cell_at(row, c).replace('~', '').replace('%', '').strip()
            try:
                tier_pcts.append(float(v))
            except Exception:
                tier_pcts.append(0.0)

        r = idx + 1
        while r < n_rows:
            drow = rows[r]
            track = cell_at(drow, track_col)
            if not track:
                break
            tiers = []
            valid = 0
            for c, tname, tpct in zip(tier_cols, tier_names, tier_pcts):
                t_s = parse_lap_time_to_seconds(cell_at(drow, c))
                if t_s > 0:
                    valid += 1
                tiers.append({'name': tname, 'pct': tpct, 'time_s': t_s})
            if valid >= 4:  # Plausibilitaets-Guard: die meisten Tiers muessen vorhanden sein
                vclass_raw = cell_at(drow, class_col)
                entries.append({
                    'track': track,
                    'patch': cell_at(drow, patch_col),
                    'hotlap_q_s': parse_lap_time_to_seconds(cell_at(drow, hotlap_col)),
                    'fastest_car': cell_at(drow, fastest_car_col),
                    'fastest_laptime_s': parse_lap_time_to_seconds(cell_at(drow, laptime_col)),
                    'vehicle_class_raw': vclass_raw,
                    'vehicle_class': infer_vehicle_class(vclass_raw),
                    'tiers': tiers,
                })
            r += 1
    return entries


# 0.5.9.21: LMU liefert ueber Shared Memory (mTrackName) Venue-/Event-Namen, die
# vom Sheet-Streckennamen abweichen (z.B. LMU "8 Hours of Bahrain" vs. Sheet
# "Bahrain (wec)"). Feste Alias-Tabelle statt Substring-Raten, validiert gegen
# die reale LMU REST-Streckenliste (/rest/race/track) - 36/36 Nicht-Showroom-Tracks
# aufgeloest. Deckt name/shortName/sceneDesc ab, falls mTrackName eine dieser
# Formen liefert.
PERSONAL_LAPTIME_TRACK_ALIAS_RAW = {
    'Portimao': ('4 Hours of Portimao', '6 Hours of Portimao', 'Algarve International Circuit 1.23', 'PORTIMAOELMS', 'PORTIMAOWEC',),
    'Imola': ('4 Hours of Imola', '6 Hours of Imola', 'Autodromo Enzo e Dino Ferrari 1.27', 'IMOLAELMS', 'IMOLAWEC',),
    'Monza': ('6 Hours of Monza', 'Autodromo Nazionale Monza 1.29', 'MONZAWEC',),
    'Monza (curvagrande)': ('Monza Curva Grande Circuit', 'MONZAWEC_GRANDE',),
    'Interlagos': ('Rolex 6 Hours Of Sao Paulo', 'Autódromo José Carlos Pace 1.27', 'INTERLAGOSWEC',),
    'Bahrain (wec)': ('8 Hours of Bahrain', 'BAHRAINWEC',),
    'Bahrain (endurance)': ('Bahrain Endurance Circuit', 'BAHRAINWEC_ENDCE',),
    'Bahrain (outer)': ('Bahrain Outer Circuit', 'BAHRAINWEC_OUTER',),
    'Bahrain (paddock)': ('Bahrain Paddock Circuit', 'BAHRAINWEC_PADDOCK',),
    'Barcelona': ('4 Hours of Barcelona', 'Circuit de Barcelona 1.03', 'BARCELONAELMS',),
    'Spa': ('4 Hours of Spa-Francorchamps', '6 Hours of Spa-Francorchamps', 'Circuit de Spa-Francorchamps Endurance', 'Circuit de Spa-Francorchamps 1.29', 'SPAELMS', 'SPAWEC', 'SPAWEC_ENDCE',),
    'Circuit de la Sarthe': ('24 Heures du Mans', 'Circuit de la Sarthe 1.33', 'LEMANSWEC',),
    'Circuit de la Sarthe (straight)': ('Circuit de la Sarthe Mulsanne', 'LEMANSWEC_MULSANNE',),
    'COTA (national)': ('COTA National Circuit', 'COTAWEC_NATIONAL',),
    'COTA': ('Lone Star Le Mans', 'Circuit of the Americas 1.27', 'COTAWEC',),
    'Daytona': ('Daytona International Speedway Road Course', 'Daytona International Speedway 1.01', 'DAYTONARC',),
    'Fuji (chicane)': ('6 Hours of Fuji', 'Fuji Speedway 1.27', 'FUJIWEC',),
    'Fuji (classic)': ('Fuji Speedway Classic', 'FUJIWEC_CL',),
    'Qatar (short)': ('Lusail Short Circuit', 'QATARWEC_SHORT',),
    'Qatar': ('Qatar 1812KM', 'Lusail International Circuit 1.27', 'QATARWEC',),
    'Paul Ricard': ('4 Hours of Castellet', 'Paul Ricard Circuit 1.07', 'PAULRICARDELMS',),
    'Paul Ricard (1A)': ('Paul Ricard - 1A', 'PAULRICARD1A',),
    'Paul Ricard (1A v2)': ('Paul Ricard - 1A-V2', 'PAULRICARD1A-V2',),
    'Paul Ricard (1A v2 short)': ('Paul Ricard - 1A-V2-Short', 'PAULRICARD1A-V2-SHORT',),
    'Paul Ricard (3A)': ('Paul Ricard - 3A', 'PAULRICARD3A',),
    'Sebring': ('1000 Miles of Sebring', 'Sebring International Raceway 1.27', 'SEBRINGWEC',),
    'Sebring (school)': ('Sebring School Circuit', 'SEBRINGWEC_SCHOOL',),
    'Silverstone (GP)': ('4 Hours of Silverstone', '6 Hours of Silverstone', 'Silverstone Circuit 1.11', 'SILVERSTONEELMS', 'SILVERSTONEWEC',),
    'Silverstone (International)': ('Silverstone International Circuit', 'SILVERSTONE_INTERNATIONAL',),
    'Silverstone (National)': ('Silverstone National Circuit', 'SILVERSTONE_NATIONAL',),
    'Laguna Seca': ('WeatherTech Raceway Laguna Seca', 'WeatherTech Raceway Laguna Seca 1.01', 'LAGUNASECA',),
}

# normalisierte Lookup-Tabelle: normalize_match_text(LMU-Variante) -> Sheet-Streckenname
PERSONAL_LAPTIME_TRACK_ALIASES = {}
for _sheet_key, _variants in PERSONAL_LAPTIME_TRACK_ALIAS_RAW.items():
    for _v in _variants:
        PERSONAL_LAPTIME_TRACK_ALIASES[normalize_match_text(_v)] = _sheet_key


def safe_filename_part(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (text or "").strip())
    return cleaned.strip("_") or "unknown"


def speed_kmh_from_vec(vec) -> float:
    return math.sqrt(fnum(vec.x) ** 2 + fnum(vec.y) ** 2 + fnum(vec.z) ** 2) * 3.6


def kelvin_to_c(v) -> float:
    val = fnum(v)
    if val <= 0:
        return 0.0
    # LMU wheel rubber temperatures are Kelvin in Shared Memory.
    return val - 273.15 if val > 150 else val


def tire_wear_pct(v) -> float:
    val = fnum(v)
    # Shared memory exposes wear as 0.0-1.0 fraction. Show as percent for readability.
    if 0.0 <= val <= 1.5:
        return val * 100.0
    return val


@dataclass
class Sample:
    timestamp: str
    game_version: int
    track: str
    player_name: str
    active_vehicles: int
    player_idx: int
    player_has_vehicle: bool
    telem_id: int
    scoring_id: int
    vehicle_name: str
    vehicle_model: str
    vehicle_class: str
    speed_kmh: float
    gear: int
    rpm: float
    fuel_l: float
    fuel_capacity_l: float
    throttle: float
    brake: float
    steering: float
    pos_x: float
    pos_y: float
    pos_z: float
    lap_number: int
    completed_laps: int
    lap_dist_m: float
    current_lap_time: float
    last_lap_time: float
    best_lap_time: float
    lap_invalidated: bool
    in_pits: bool
    place: int
    tire_fl_pressure_kpa: float = 0.0
    tire_fr_pressure_kpa: float = 0.0
    tire_rl_pressure_kpa: float = 0.0
    tire_rr_pressure_kpa: float = 0.0
    tire_fl_temp_l_c: float = 0.0
    tire_fl_temp_c_c: float = 0.0
    tire_fl_temp_r_c: float = 0.0
    tire_fr_temp_l_c: float = 0.0
    tire_fr_temp_c_c: float = 0.0
    tire_fr_temp_r_c: float = 0.0
    tire_rl_temp_l_c: float = 0.0
    tire_rl_temp_c_c: float = 0.0
    tire_rl_temp_r_c: float = 0.0
    tire_rr_temp_l_c: float = 0.0
    tire_rr_temp_c_c: float = 0.0
    tire_rr_temp_r_c: float = 0.0
    tire_fl_carcass_c: float = 0.0
    tire_fr_carcass_c: float = 0.0
    tire_rl_carcass_c: float = 0.0
    tire_rr_carcass_c: float = 0.0
    tire_fl_wear_pct: float = 0.0
    tire_fr_wear_pct: float = 0.0
    tire_rl_wear_pct: float = 0.0
    tire_rr_wear_pct: float = 0.0
    tire_fl_flat: bool = False
    tire_fr_flat: bool = False
    tire_rl_flat: bool = False
    tire_rr_flat: bool = False
    tire_fl_grip_fract: float = 0.0
    tire_fr_grip_fract: float = 0.0
    tire_rl_grip_fract: float = 0.0
    tire_rr_grip_fract: float = 0.0
    accel_lat_ms2: float = 0.0
    accel_long_ms2: float = 0.0
    session_type: int = 0  # 0.4.8.8: mSession (0 testday,1-4 practice,5-8 qual,9 warmup,10-13 race)
    path_lateral_m: float = 0.0  # 0.4.8.9: seitlicher Abstand zur (groben) Mittellinie
    track_edge_m: float = 0.0    # 0.4.8.9: Streckenrand auf der Fahrzeugseite
    track_temp_c: float = 0.0        # 0.4.9.0
    ambient_temp_c: float = 0.0
    raining: float = 0.0
    wetness_avg: float = 0.0
    wetness_min: float = 0.0
    wetness_max: float = 0.0
    dark_cloud: float = 0.0            # 0.4.9.4: Fruehindikator fuer Regen
    cloud_coverage: float = 0.0
    wind_speed_ms: float = 0.0
    session_remaining_s: float = 0.0
    session_current_et: float = 0.0     # 0.4.9.5
    session_end_et: float = 0.0
    sector_index: int = 0            # 0.4.9.0: mSector (0=S3, 1=S1, 2=S2)
    cur_sector1_s: float = 0.0
    cur_sector2_s: float = 0.0
    last_sector1_s: float = 0.0
    last_sector2_s: float = 0.0
    best_sector1_s: float = 0.0
    best_sector2_s: float = 0.0
    brake_fl_temp_raw: float = 0.0   # 0.4.9.0: mBrakeTemp roh (K oder C, Erkennung im Overlay)
    brake_fr_temp_raw: float = 0.0
    brake_rl_temp_raw: float = 0.0
    brake_rr_temp_raw: float = 0.0
    max_rpm: float = 0.0             # 0.4.9.0
    virtual_energy: float = 0.0
    ffb_torque: float = 0.0          # 0.4.9.0: generic.FFBTorque
    steering_shaft_torque: float = 0.0
    pit_state: int = 0               # 0.4.9.1: 0 keine,1 angefordert,2 Einfahrt,3 steht,4 Ausfahrt
    speed_limiter: bool = False
    num_pitstops: int = 0
    pit_lap_dist: float = 0.0
    gap_ahead_s: float = 0.0         # 0.4.9.1: Abstand nach vorn
    gap_behind_s: float = 0.0
    gap_leader_s: float = 0.0
    laps_behind_next: int = 0
    laps_behind_leader: int = 0
    parts_detached: bool = False     # 0.4.9.1: Schaeden
    overheating: bool = False
    wheel_fl_detached: bool = False
    wheel_fr_detached: bool = False
    wheel_rl_detached: bool = False
    wheel_rr_detached: bool = False
    dent_0: int = 0
    dent_1: int = 0
    dent_2: int = 0
    dent_3: int = 0
    dent_4: int = 0
    dent_5: int = 0
    dent_6: int = 0
    dent_7: int = 0
    last_impact_et: float = 0.0        # 0.4.9.4: Zeitmarke des letzten Treffers
    last_impact_magnitude: float = 0.0
    rear_brake_bias: float = 0.0     # 0.4.9.1
    brake_fl_pressure: float = 0.0
    brake_fr_pressure: float = 0.0
    brake_rl_pressure: float = 0.0
    brake_rr_pressure: float = 0.0
    tire_fl_slip_ms: float = 0.0
    tire_fr_slip_ms: float = 0.0
    tire_rl_slip_ms: float = 0.0
    tire_rr_slip_ms: float = 0.0
    # 0.4.7.1: Roh-Fahrereingabe (unfiltered) fuer das Pedal-Input-Overlay
    input_throttle: float = 0.0
    input_brake: float = 0.0
    input_clutch: float = 0.0
    input_steering: float = 0.0  # 0.4.7.1: Roh-Lenkeingabe (-1..1) fuer Pedal-/Lenk-Trace
    opponents: tuple = ()  # 0.4.9.9 Spotter: ((mID, x, z, in_pits), ...) Weltkoordinaten
    opponents_behind: tuple = ()  # 0.5.1.0 Ueberholalarm: ((place, driver, vclass, dist_m), ...)
    game_phase: int = 0            # 0.5.1.0 Flaggen
    yellow_flag_state: int = 0
    sector_flag_0: int = 0
    sector_flag_1: int = 0
    sector_flag_2: int = 0
    player_flag: int = 0




@dataclass
class LapSummary:
    lap_number: int
    samples: int
    valid_samples: int
    start_m: float
    end_m: float
    coverage_m: float
    duration_s: float
    min_speed: float
    max_speed: float
    avg_speed: float
    max_brake: float
    avg_throttle: float
    fuel_start_l: float
    fuel_end_l: float
    fuel_used_l: float
    invalidated: bool
    in_pits: bool
    has_standstill: bool
    is_complete: bool
    is_clean: bool
    reason: str


@dataclass
class SegmentSummary:
    lap_number: int
    start_m: int
    end_m: int
    samples: int
    seg_time_s: float
    avg_speed: float
    min_speed: float
    max_speed: float
    max_brake: float
    avg_throttle: float
    gear_common: str


@dataclass
class SegmentDelta:
    start_m: int
    end_m: int
    compare_lap: int
    reference_lap: int
    cmp_time_s: float
    ref_time_s: float
    delta_s: float
    cmp_avg_speed: float
    ref_avg_speed: float
    speed_delta: float
    cmp_max_brake: float
    ref_max_brake: float
    brake_delta: float
    cmp_avg_throttle: float
    ref_avg_throttle: float
    throttle_delta: float
    hint: str


class LMUReader:
    def __init__(self):
        self.size = ctypes.sizeof(LMUObjectOut)

    def read_object(self):
        # Windows-only named mmap. This is the official built-in LMU shared memory map.
        with mmap.mmap(-1, self.size, tagname=LMUConstants.LMU_SHARED_MEMORY_FILE, access=mmap.ACCESS_READ) as mm:
            return LMUObjectOut.from_buffer_copy(mm)

    def read_sample(self) -> Sample:
        data = self.read_object()
        game_version = int(data.generic.gameVersion)
        scoring_info = data.scoring.scoringInfo
        track = dec(scoring_info.mTrackName)
        player_name = dec(scoring_info.mPlayerName)
        active = int(data.telemetry.activeVehicles)
        player_idx = int(data.telemetry.playerVehicleIdx)
        has_vehicle = bool(data.telemetry.playerHasVehicle)

        if player_idx < 0 or player_idx >= LMUConstants.MAX_MAPPED_VEHICLES:
            raise RuntimeError(f"Ungültiger playerVehicleIdx: {player_idx}")
        if active <= 0:
            raise RuntimeError("Keine aktiven Fahrzeuge in Telemetry.")

        telem = data.telemetry.telemInfo[player_idx]
        telem_id = int(telem.mID)

        scoring = None
        for i in range(min(int(scoring_info.mNumVehicles), LMUConstants.MAX_MAPPED_VEHICLES)):
            cand = data.scoring.vehScoringInfo[i]
            if bool(cand.mIsPlayer) or int(cand.mID) == telem_id:
                scoring = cand
                break
        if scoring is None:
            scoring = data.scoring.vehScoringInfo[player_idx]

        vehicle_name = dec(telem.mVehicleName) or dec(scoring.mVehicleName)
        # New LMU fields may exist in pyLMUSharedMemory; use safe decoding.
        vehicle_model = dec(getattr(telem, "mVehicleModel", b""))
        vehicle_class = dec(getattr(scoring, "mVehicleClass", b""))

        wheels = list(getattr(telem, "mWheels", []))
        def wh(i):
            try:
                return wheels[i]
            except Exception:
                return None
        def w_pressure(i):
            w = wh(i); return fnum(getattr(w, "mPressure", 0.0)) if w is not None else 0.0
        def w_temp(i, j):
            w = wh(i)
            if w is None:
                return 0.0
            try:
                return kelvin_to_c(w.mTemperature[j])
            except Exception:
                return 0.0
        def w_carcass(i):
            w = wh(i); return kelvin_to_c(getattr(w, "mTireCarcassTemperature", 0.0)) if w is not None else 0.0
        def w_wear(i):
            w = wh(i); return tire_wear_pct(getattr(w, "mWear", 0.0)) if w is not None else 0.0
        def w_flat(i):
            w = wh(i); return bool(getattr(w, "mFlat", False)) if w is not None else False
        def w_grip_fract(i):
            w = wh(i); return fnum(getattr(w, "mGripFract", 0.0)) if w is not None else 0.0
        def _vec3(obj, name):
            try:
                v = getattr(obj, name); return (fnum(v.x), fnum(v.y), fnum(v.z))
            except Exception:
                return (0.0, 0.0, 0.0)
        _accel = _vec3(telem, "mLocalAccel")  # (x lat, y vert, z long) m/s^2
        _w = _vec3(scoring_info, "mWind")  # 0.4.9.4
        _wind_speed = (_w[0] ** 2 + _w[1] ** 2 + _w[2] ** 2) ** 0.5
        def w_detached(i):
            w = wh(i); return bool(getattr(w, "mDetached", False)) if w is not None else False
        def w_brake_press(i):
            w = wh(i); return fnum(getattr(w, "mBrakePressure", 0.0)) if w is not None else 0.0
        def _dent(i):
            try:
                return int(telem.mDentSeverity[i])
            except Exception:
                return 0
        # 0.4.9.1: Abstand zum Hintermann aus dessen mTimeBehindNext
        _gap_behind = 0.0
        try:
            _my_place = int(scoring.mPlace)
            for _i in range(min(int(scoring_info.mNumVehicles), LMUConstants.MAX_MAPPED_VEHICLES)):
                _v = data.scoring.vehScoringInfo[_i]
                if int(_v.mPlace) == _my_place + 1:
                    _gap_behind = fnum(getattr(_v, "mTimeBehindNext", 0.0))
                    break
        except Exception:
            _gap_behind = 0.0
        # 0.4.9.9/0.5.1.0: Gegner - Spotter-Positionen + Ueberholalarm-Abstaende
        _opps = []
        _behind = []
        _track_len = fnum(getattr(scoring_info, "mLapDist", 0.0))
        _my_dist = fnum(scoring.mLapDist)
        try:
            _ego_id = int(scoring.mID)
            for _i in range(min(int(scoring_info.mNumVehicles), LMUConstants.MAX_MAPPED_VEHICLES)):
                _v = data.scoring.vehScoringInfo[_i]
                if int(_v.mID) == _ego_id:
                    continue
                _pit = bool(_v.mInPits)
                _p = _v.mPos
                _opps.append((int(_v.mID), fnum(_p.x), fnum(_p.z), _pit))
                if not _pit and _track_len > 1.0:
                    _db = (_my_dist - fnum(_v.mLapDist)) % _track_len
                    if 0.5 < _db < 400.0:
                        _behind.append((int(getattr(_v, "mPlace", 0) or 0),
                                        dec(_v.mDriverName),
                                        dec(getattr(_v, "mVehicleClass", b"")),
                                        _db))
            _behind.sort(key=lambda e: e[3])
            _behind = _behind[:6]
        except Exception:
            _opps = []; _behind = []
        # 0.5.1.0: Flaggen-Rohwerte
        def _to_int(v):
            if isinstance(v, (bytes, bytearray)):
                return v[0] if v else 0
            try:
                return int(v)
            except Exception:
                return 0
        _game_phase = _to_int(getattr(scoring_info, "mGamePhase", 0))
        _yellow = _to_int(getattr(scoring_info, "mYellowFlagState", 0))
        try:
            _sf = getattr(scoring_info, "mSectorFlag", None)
            _sf0, _sf1, _sf2 = (_to_int(_sf[0]), _to_int(_sf[1]), _to_int(_sf[2])) if _sf is not None else (0, 0, 0)
        except Exception:
            _sf0 = _sf1 = _sf2 = 0
        _player_flag = _to_int(getattr(scoring, "mFlag", 0))
        def w_brake_temp(i):
            w = wh(i); return fnum(getattr(w, "mBrakeTemp", 0.0)) if w is not None else 0.0
        def w_slip(i):
            w = wh(i)
            if w is None:
                return 0.0
            try:
                a = fnum(getattr(w, "mLateralPatchVel", 0.0))
                b = fnum(getattr(w, "mLongitudinalPatchVel", 0.0))
                return (a * a + b * b) ** 0.5
            except Exception:
                return 0.0

        return Sample(
            timestamp=datetime.now().isoformat(timespec="milliseconds"),
            game_version=game_version,
            track=track,
            player_name=player_name,
            active_vehicles=active,
            player_idx=player_idx,
            player_has_vehicle=has_vehicle,
            telem_id=telem_id,
            scoring_id=int(scoring.mID),
            vehicle_name=vehicle_name,
            vehicle_model=vehicle_model,
            vehicle_class=vehicle_class,
            speed_kmh=speed_kmh_from_vec(telem.mLocalVel),
            gear=int(telem.mGear),
            rpm=fnum(telem.mEngineRPM),
            fuel_l=fnum(telem.mFuel),
            fuel_capacity_l=fnum(telem.mFuelCapacity),
            throttle=fnum(telem.mFilteredThrottle),
            brake=fnum(telem.mFilteredBrake),
            steering=fnum(telem.mFilteredSteering),
            input_throttle=fnum(telem.mUnfilteredThrottle),
            input_brake=fnum(telem.mUnfilteredBrake),
            input_clutch=fnum(telem.mUnfilteredClutch),
            input_steering=fnum(telem.mUnfilteredSteering),
            pos_x=fnum(telem.mPos.x),
            pos_y=fnum(telem.mPos.y),
            pos_z=fnum(telem.mPos.z),
            lap_number=int(telem.mLapNumber),
            completed_laps=int(scoring.mTotalLaps),
            lap_dist_m=fnum(scoring.mLapDist),
            current_lap_time=fnum(scoring.mTimeIntoLap),
            last_lap_time=fnum(scoring.mLastLapTime),
            best_lap_time=fnum(scoring.mBestLapTime),
            lap_invalidated=bool(getattr(telem, "mLapInvalidated", False)),
            in_pits=bool(scoring.mInPits),
            place=int(scoring.mPlace),
            tire_fl_pressure_kpa=w_pressure(0), tire_fr_pressure_kpa=w_pressure(1), tire_rl_pressure_kpa=w_pressure(2), tire_rr_pressure_kpa=w_pressure(3),
            tire_fl_temp_l_c=w_temp(0,0), tire_fl_temp_c_c=w_temp(0,1), tire_fl_temp_r_c=w_temp(0,2),
            tire_fr_temp_l_c=w_temp(1,0), tire_fr_temp_c_c=w_temp(1,1), tire_fr_temp_r_c=w_temp(1,2),
            tire_rl_temp_l_c=w_temp(2,0), tire_rl_temp_c_c=w_temp(2,1), tire_rl_temp_r_c=w_temp(2,2),
            tire_rr_temp_l_c=w_temp(3,0), tire_rr_temp_c_c=w_temp(3,1), tire_rr_temp_r_c=w_temp(3,2),
            tire_fl_carcass_c=w_carcass(0), tire_fr_carcass_c=w_carcass(1), tire_rl_carcass_c=w_carcass(2), tire_rr_carcass_c=w_carcass(3),
            tire_fl_wear_pct=w_wear(0), tire_fr_wear_pct=w_wear(1), tire_rl_wear_pct=w_wear(2), tire_rr_wear_pct=w_wear(3),
            tire_fl_flat=w_flat(0), tire_fr_flat=w_flat(1), tire_rl_flat=w_flat(2), tire_rr_flat=w_flat(3),
            tire_fl_grip_fract=w_grip_fract(0), tire_fr_grip_fract=w_grip_fract(1), tire_rl_grip_fract=w_grip_fract(2), tire_rr_grip_fract=w_grip_fract(3),
            session_type=int(getattr(scoring, "mSession", 0)),
            path_lateral_m=fnum(getattr(scoring, "mPathLateral", 0.0)),
            track_edge_m=fnum(getattr(scoring, "mTrackEdge", 0.0)),
            track_temp_c=fnum(getattr(scoring_info, "mTrackTemp", 0.0)),
            ambient_temp_c=fnum(getattr(scoring_info, "mAmbientTemp", 0.0)),
            raining=fnum(getattr(scoring_info, "mRaining", 0.0)),
            wetness_avg=fnum(getattr(scoring_info, "mAvgPathWetness", 0.0)),
            wetness_min=fnum(getattr(scoring_info, "mMinPathWetness", 0.0)),
            wetness_max=fnum(getattr(scoring_info, "mMaxPathWetness", 0.0)),
            dark_cloud=fnum(getattr(scoring_info, "mDarkCloud", 0.0)),
            cloud_coverage=float(int(getattr(scoring_info, "mCloudCoverage", 0))) / 255.0,
            wind_speed_ms=_wind_speed,
            session_remaining_s=max(0.0, fnum(getattr(scoring_info, "mEndET", 0.0))
                                    - fnum(getattr(scoring_info, "mCurrentET", 0.0))),
            session_current_et=fnum(getattr(scoring_info, "mCurrentET", 0.0)),
            session_end_et=fnum(getattr(scoring_info, "mEndET", 0.0)),
            sector_index=int(getattr(scoring, "mSector", 0)),
            cur_sector1_s=fnum(getattr(scoring, "mCurSector1", 0.0)),
            cur_sector2_s=fnum(getattr(scoring, "mCurSector2", 0.0)),
            last_sector1_s=fnum(getattr(scoring, "mLastSector1", 0.0)),
            last_sector2_s=fnum(getattr(scoring, "mLastSector2", 0.0)),
            best_sector1_s=fnum(getattr(scoring, "mBestSector1", 0.0)),
            best_sector2_s=fnum(getattr(scoring, "mBestSector2", 0.0)),
            brake_fl_temp_raw=w_brake_temp(0), brake_fr_temp_raw=w_brake_temp(1),
            brake_rl_temp_raw=w_brake_temp(2), brake_rr_temp_raw=w_brake_temp(3),
            max_rpm=fnum(getattr(telem, "mEngineMaxRPM", 0.0)),
            virtual_energy=fnum(getattr(telem, "mVirtualEnergy", 0.0)),
            ffb_torque=fnum(getattr(data.generic, "FFBTorque", 0.0)),
            steering_shaft_torque=fnum(getattr(telem, "mSteeringShaftTorque", 0.0)),
            pit_state=int(getattr(scoring, "mPitState", 0)),
            speed_limiter=bool(getattr(telem, "mSpeedLimiter", 0)),
            num_pitstops=int(getattr(scoring, "mNumPitstops", 0)),
            pit_lap_dist=fnum(getattr(scoring, "mPitLapDist", 0.0)),
            gap_ahead_s=fnum(getattr(scoring, "mTimeBehindNext", 0.0)),
            gap_behind_s=_gap_behind,
            opponents=tuple(_opps),
            opponents_behind=tuple(_behind),
            game_phase=_game_phase,
            yellow_flag_state=_yellow,
            sector_flag_0=_sf0, sector_flag_1=_sf1, sector_flag_2=_sf2,
            player_flag=_player_flag,
            gap_leader_s=fnum(getattr(scoring, "mTimeBehindLeader", 0.0)),
            laps_behind_next=int(getattr(scoring, "mLapsBehindNext", 0)),
            laps_behind_leader=int(getattr(scoring, "mLapsBehindLeader", 0)),
            parts_detached=bool(getattr(telem, "mDetached", False)),
            overheating=bool(getattr(telem, "mOverheating", False)),
            wheel_fl_detached=w_detached(0), wheel_fr_detached=w_detached(1),
            wheel_rl_detached=w_detached(2), wheel_rr_detached=w_detached(3),
            dent_0=_dent(0), dent_1=_dent(1), dent_2=_dent(2), dent_3=_dent(3),
            dent_4=_dent(4), dent_5=_dent(5), dent_6=_dent(6), dent_7=_dent(7),
            last_impact_et=fnum(getattr(telem, "mLastImpactET", 0.0)),
            last_impact_magnitude=fnum(getattr(telem, "mLastImpactMagnitude", 0.0)),
            rear_brake_bias=fnum(getattr(telem, "mRearBrakeBias", 0.0)),
            brake_fl_pressure=w_brake_press(0), brake_fr_pressure=w_brake_press(1),
            brake_rl_pressure=w_brake_press(2), brake_rr_pressure=w_brake_press(3),
            accel_lat_ms2=_accel[0], accel_long_ms2=_accel[2],
            tire_fl_slip_ms=w_slip(0), tire_fr_slip_ms=w_slip(1), tire_rl_slip_ms=w_slip(2), tire_rr_slip_ms=w_slip(3),
        )


class TrackMapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.samples: List[Sample] = []
        self.reference_samples: List[Sample] = []
        self.compare_samples: List[Sample] = []
        self.segment_deltas: List[SegmentDelta] = []
        self.problem_zones = []
        self.heatmap_mode = False
        self.heat_metric = "delta"  # 0.4.8.8/0.4.8.9: "delta" | "pedal" | "line"
        self._line_idx = []        # 0.4.8.9: [(dist, x, z, path_lateral)] der Referenz
        self._path_lat_ok = False  # mPathLateral/mTrackEdge liefern Daten?
        self.setMinimumHeight(260)

    def set_heat_metric(self, metric):
        self.heat_metric = metric if metric in ("pedal", "line", "gear") else "delta"
        self.update()

    # ---- 0.4.8.9: Linienabweichung -------------------------------------
    def _build_line_index(self):
        idx = []
        for s in self.reference_samples:
            if abs(s.pos_x) > 0.001 or abs(s.pos_z) > 0.001:
                idx.append((float(s.lap_dist_m), float(s.pos_x), float(s.pos_z),
                            float(getattr(s, "path_lateral_m", 0.0) or 0.0)))
        idx.sort(key=lambda t: t[0])
        self._line_idx = idx
        self._path_lat_ok = any(abs(t[3]) > 1e-6 for t in idx) and any(
            abs(float(getattr(s, "path_lateral_m", 0.0) or 0.0)) > 1e-6 for s in self.compare_samples)

    def _lateral_dev(self, s):
        """Seitliche Abweichung dieser Probe zur Referenzlinie in Metern (signiert).
        Nutzt mPathLateral wenn der Kanal Daten liefert, sonst rein geometrisch
        (senkrechter Abstand zur Referenz-Spur). None wenn nicht bestimmbar."""
        idx = self._line_idx
        if len(idx) < 2:
            return None
        d = float(s.lap_dist_m)
        lo, hi = 0, len(idx) - 1
        if d <= idx[0][0] or d >= idx[-1][0]:
            return None
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if idx[mid][0] <= d:
                lo = mid
            else:
                hi = mid
        d0, x0, z0, pl0 = idx[lo]
        d1, x1, z1, pl1 = idx[hi]
        span = (d1 - d0) or 1.0
        if span > 60.0:
            return None
        t = (d - d0) / span
        if self._path_lat_ok:
            ref_pl = pl0 + (pl1 - pl0) * t
            return float(getattr(s, "path_lateral_m", 0.0) or 0.0) - ref_pl
        px = x0 + (x1 - x0) * t
        pz = z0 + (z1 - z0) * t
        hx, hz = (x1 - x0), (z1 - z0)
        ln = (hx * hx + hz * hz) ** 0.5
        if ln < 1e-6:
            return None
        nx, nz = hz / ln, -hx / ln
        return (float(s.pos_x) - px) * nx + (float(s.pos_z) - pz) * nz

    def _edge_margin_min(self):
        """Kleinster Restabstand zum Streckenrand in der Vergleichsrunde (Meter)."""
        if not self._path_lat_ok:
            return None
        best = None
        for s in self.compare_samples:
            edge = abs(float(getattr(s, "track_edge_m", 0.0) or 0.0))
            if edge < 0.5 or float(s.speed_kmh) < 5.0:
                continue
            m = edge - abs(float(getattr(s, "path_lateral_m", 0.0) or 0.0))
            if best is None or m < best:
                best = m
        return best

    def set_samples(self, samples: List[Sample]):
        self.samples = list(samples)
        self.heatmap_mode = False
        self.update()

    def set_heatmap(self, all_samples: List[Sample], reference_samples: List[Sample], compare_samples: List[Sample], segment_deltas: List[SegmentDelta], problem_zones):
        self.samples = list(all_samples)
        self.reference_samples = list(reference_samples)
        self.compare_samples = list(compare_samples)
        self.segment_deltas = list(segment_deltas)
        self.problem_zones = list(problem_zones)
        self.heatmap_mode = True
        self._build_line_index()  # 0.4.8.9
        self.update()

    def _all_position_rows(self):
        rows = []
        for src in (self.samples, self.reference_samples, self.compare_samples):
            rows.extend([s for s in src if abs(s.pos_x) > 0.001 or abs(s.pos_z) > 0.001])
        return rows

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(24, 24, 24))
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        rows = self._all_position_rows()
        if len(rows) < 2:
            painter.setPen(QColor(210, 210, 210))
            painter.drawText(self.rect(), Qt.AlignCenter, "Trackmap: Recording starten und fahren")
            return

        xs = [s.pos_x for s in rows]; zs = [s.pos_z for s in rows]
        minx, maxx = min(xs), max(xs); minz, maxz = min(zs), max(zs)
        dx = max(maxx - minx, 1.0); dz = max(maxz - minz, 1.0)
        margin = 22
        w = max(self.width() - 2 * margin, 1); h = max(self.height() - 2 * margin, 1)
        scale = min(w / dx, h / dz)
        cx = (minx + maxx) / 2; cz = (minz + maxz) / 2

        def map_pt(x, z):
            px = self.width() / 2 + (x - cx) * scale
            py = self.height() / 2 - (z - cz) * scale
            return QPointF(px, py)

        def draw_path(path: List[Sample], pen_func, min_speed_for_line=1.0):
            pts = [s for s in path if s.speed_kmh >= min_speed_for_line and (abs(s.pos_x) > 0.001 or abs(s.pos_z) > 0.001)]
            if len(pts) < 2:
                return
            pts.sort(key=lambda s: (s.lap_dist_m, s.timestamp))
            for i in range(1, len(pts)):
                s0, s1 = pts[i - 1], pts[i]
                # avoid drawing a long line over start/finish wrap or bad distance jump
                if abs(s1.lap_dist_m - s0.lap_dist_m) > 160:
                    continue
                painter.setPen(pen_func(s1))
                painter.drawLine(map_pt(s0.pos_x, s0.pos_z), map_pt(s1.pos_x, s1.pos_z))

        if self.heatmap_mode and self.heat_metric == "gear" and (self.compare_samples or self.reference_samples):
            base = self.compare_samples or self.reference_samples
            gear_cols = {1: QColor(235, 70, 55), 2: QColor(245, 150, 55), 3: QColor(235, 195, 70),
                         4: QColor(140, 210, 90), 5: QColor(70, 190, 140), 6: QColor(70, 170, 235),
                         7: QColor(140, 130, 240), 8: QColor(210, 110, 235)}
            maxrpm = max([float(getattr(x, "max_rpm", 0.0) or 0.0) for x in base] + [0.0])
            if maxrpm < 1000:
                maxrpm = max([float(getattr(x, "rpm", 0.0) or 0.0) for x in base] + [1.0])

            def gear_pen(s: Sample):
                g = int(getattr(s, "gear", 0) or 0)
                col = gear_cols.get(g, QColor(140, 140, 140))
                frac = min(max(float(getattr(s, "rpm", 0.0) or 0.0) / maxrpm, 0.0), 1.0)
                return QPen(col, 2 + int(4 * frac))

            draw_path(base, gear_pen, 3.0)
            painter.setPen(QColor(230, 230, 230))
            painter.drawText(QRectF(8, 8, self.width() - 16, 44), Qt.AlignLeft,
                             "Gang & Drehzahl: Farbe = Gang (1 rot → 8 violett) · Liniendicke = Drehzahl")
            gx = 10
            for g in range(1, 9):
                painter.setPen(QPen(gear_cols[g], 4))
                painter.drawLine(QPointF(gx, self.height() - 14), QPointF(gx + 16, self.height() - 14))
                painter.setPen(QColor(220, 220, 220))
                painter.drawText(QRectF(gx + 18, self.height() - 22, 12, 16), Qt.AlignLeft, str(g))
                gx += 36
            return

        if self.heatmap_mode and self.heat_metric == "line" and self.compare_samples and self.reference_samples:
            draw_path(self.reference_samples, lambda s: QPen(QColor(120, 120, 120), 2), 5.0)

            def line_pen(s: Sample):
                dv = self._lateral_dev(s)
                if dv is None:
                    return QPen(QColor(150, 150, 150), 2)
                a = abs(dv)
                if a < 0.3:
                    return QPen(QColor(120, 200, 140), 2)
                if a < 0.8:
                    return QPen(QColor(235, 195, 70), 3)
                if a < 1.5:
                    return QPen(QColor(245, 150, 55), 4)
                return QPen(QColor(235, 70, 55), 5)

            draw_path(self.compare_samples, line_pen, 5.0)

            # groesste Abweichungen markieren (max. 3, je 50-m-Bucket)
            buckets = {}
            for s in self.compare_samples:
                if s.speed_kmh < 5.0:
                    continue
                dv = self._lateral_dev(s)
                if dv is None:
                    continue
                key = int(s.lap_dist_m // 50) * 50
                cur = buckets.get(key)
                if cur is None or abs(dv) > abs(cur[0]):
                    buckets[key] = (dv, s)
            top = sorted(buckets.values(), key=lambda t: -abs(t[0]))[:3]
            for rank, (dv, s) in enumerate(top, 1):
                if abs(dv) < 0.4:
                    continue
                pt = map_pt(s.pos_x, s.pos_z)
                painter.setBrush(QBrush(QColor(245, 150, 55, 230)))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawEllipse(pt, 15, 15)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRectF(pt.x() - 12, pt.y() - 12, 24, 24), Qt.AlignCenter, str(rank))
                side = "aussen" if dv > 0 else "innen"
                label = f"{abs(dv):.1f} m {side}"
                lr = QRectF(pt.x() + 17, pt.y() - 14, 118, 26)
                painter.setBrush(QBrush(QColor(10, 10, 10, 185)))
                painter.setPen(QPen(QColor(245, 150, 55), 1))
                painter.drawRoundedRect(lr, 5, 5)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(lr.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, label)

            src_txt = "Quelle: mPathLateral" if self._path_lat_ok else "Quelle: Positionen (mPathLateral leer)"
            margin = self._edge_margin_min()
            margin_txt = f" · engster Rand-Abstand {margin:.2f} m" if margin is not None else ""
            painter.setPen(QColor(230, 230, 230))
            painter.drawText(QRectF(8, 8, self.width() - 16, 44), Qt.AlignLeft,
                             "Linienabweichung zur Referenz: grün <0,3 m · gelb <0,8 · orange <1,5 · rot darüber | "
                             + src_txt + margin_txt)
            return

        if self.heatmap_mode and self.heat_metric == "pedal" and (self.compare_samples or self.reference_samples):
            base = self.compare_samples or self.reference_samples
            if self.reference_samples and base is not self.reference_samples:
                draw_path(self.reference_samples, lambda s: QPen(QColor(85, 85, 85), 2), 5.0)
            def pedal_pen(s: Sample):
                if s.brake > 0.05:
                    return QPen(QColor(235, 70, 55), 2 + int(3 * min(s.brake, 1.0)))
                if s.throttle > 0.05:
                    return QPen(QColor(70, 190, 90), 2 + int(2 * min(s.throttle, 1.0)))
                return QPen(QColor(235, 185, 60), 2)
            draw_path(base, pedal_pen, 3.0)
            painter.setPen(QColor(230, 230, 230))
            painter.drawText(QRectF(8, 8, self.width() - 16, 44), Qt.AlignLeft,
                             "Pedal-Input: grün = Gas · rot = Bremse · gelb = Segeln | grau = Referenz")
            return

        if self.heatmap_mode and self.reference_samples and self.compare_samples and self.segment_deltas:
            delta_by_bucket = {d.start_m: d for d in self.segment_deltas}
            draw_path(self.reference_samples, lambda s: QPen(QColor(110, 110, 110), 2), 5.0)

            def heat_pen(s: Sample):
                key = int(s.lap_dist_m // 50) * 50
                d = delta_by_bucket.get(key)
                if d is None:
                    return QPen(QColor(150, 150, 150), 2)
                if d.delta_s >= 0.14:
                    return QPen(QColor(235, 70, 55), 5)
                if d.delta_s >= 0.06:
                    return QPen(QColor(245, 170, 60), 4)
                if d.delta_s <= -0.10:
                    return QPen(QColor(70, 190, 90), 4)
                return QPen(QColor(190, 190, 190), 2)

            draw_path(self.compare_samples, heat_pen, 5.0)

            def draw_zone_segment(start_m: int, end_m: int, idx: int, loss: float):
                # Draw the complete problem zone as a thick highlighted track section.
                pts = [s for s in self.compare_samples
                       if s.speed_kmh >= 5.0 and start_m <= s.lap_dist_m <= end_m
                       and (abs(s.pos_x) > 0.001 or abs(s.pos_z) > 0.001)]
                pts.sort(key=lambda s: (s.lap_dist_m, s.timestamp))
                if len(pts) >= 2:
                    zone_color = QColor(255, 70, 55, 205) if loss >= 0.30 else QColor(245, 160, 55, 205)
                    painter.setPen(QPen(zone_color, 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    for i in range(1, len(pts)):
                        if abs(pts[i].lap_dist_m - pts[i - 1].lap_dist_m) <= 120:
                            painter.drawLine(map_pt(pts[i - 1].pos_x, pts[i - 1].pos_z), map_pt(pts[i].pos_x, pts[i].pos_z))

                mid = (start_m + end_m) / 2
                nearest = min(self.compare_samples, key=lambda s: abs(s.lap_dist_m - mid), default=None)
                if nearest is None:
                    return
                pt = map_pt(nearest.pos_x, nearest.pos_z)
                # Large numbered marker with a small text label.
                painter.setBrush(QBrush(QColor(255, 70, 55, 230)))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawEllipse(pt, 18, 18)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRectF(pt.x() - 12, pt.y() - 13, 24, 26), Qt.AlignCenter, str(idx))
                label = f"Zone {idx}: {start_m}-{end_m} m"
                label_rect = QRectF(pt.x() + 20, pt.y() - 16, 135, 30)
                painter.setBrush(QBrush(QColor(10, 10, 10, 185)))
                painter.setPen(QPen(QColor(255, 90, 80), 1))
                painter.drawRoundedRect(label_rect, 5, 5)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(label_rect.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, label)

            # Mark grouped coach zones clearly as thick colored track sections.
            for idx, zone in enumerate(self.problem_zones[:5], 1):
                start, end, loss = zone[0], zone[1], zone[2]
                draw_zone_segment(start, end, idx, loss)

            painter.setPen(QColor(230, 230, 230))
            painter.drawText(QRectF(8, 8, self.width() - 16, 44), Qt.AlignLeft,
                             "Heatmap: dicke rote Zonen + Nummern = Coach-Fokus | Grau=Referenz | Grün=besser")
        else:
            pts = self.samples
            max_speed = max([s.speed_kmh for s in pts] + [1.0])
            def live_pen(s: Sample):
                if s.brake > 0.05:
                    return QPen(QColor(230, 100, 80), 3)
                if s.throttle > 0.8:
                    return QPen(QColor(90, 180, 110), 2)
                shade = int(120 + 100 * min(max(s.speed_kmh / max_speed, 0), 1))
                return QPen(QColor(shade, shade, shade), 2)
            draw_path(pts, live_pen, 0.0)
            last = pts[-1]
            painter.setBrush(QBrush(QColor(255, 230, 80)))
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            lp = map_pt(last.pos_x, last.pos_z)
            painter.drawEllipse(lp, 5, 5)
            painter.setPen(QColor(220, 220, 220))
            painter.drawText(QRectF(8, 8, self.width() - 16, 20), Qt.AlignLeft, f"Samples: {len(self.samples)} | Speed max: {max_speed:.1f} km/h | Rot=Bremse | Grün=Gas")


def _load_overlay_sizes():
    """0.4.9.8: gemerkte Overlay-Groessen (pro Klasse) laden."""
    try:
        import json
        with open(OVERLAY_SIZES_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


_OVERLAY_SIZES = None


def _remember_overlay_size(widget):
    global _OVERLAY_SIZES
    # 0.4.9.8: Erst speichern, wenn die gemerkte Groesse angewendet wurde - sonst
    # ueberschreibt das resizeEvent beim Anzeigen die Datei mit der Standardgroesse.
    if not getattr(widget, "_size_restored", False):
        return
    if _OVERLAY_SIZES is None:
        _OVERLAY_SIZES = _load_overlay_sizes()
    try:
        _OVERLAY_SIZES[type(widget).__name__] = [int(widget.width()), int(widget.height())]
        import json
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OVERLAY_SIZES_PATH, "w", encoding="utf-8") as f:
            json.dump(_OVERLAY_SIZES, f, indent=2)
    except Exception:
        pass


def _restore_overlay_size(widget):
    global _OVERLAY_SIZES
    if getattr(widget, "_size_restored", False):
        return
    widget._size_restored = True
    if _OVERLAY_SIZES is None:
        _OVERLAY_SIZES = _load_overlay_sizes()
    try:
        wh = _OVERLAY_SIZES.get(type(widget).__name__)
        if wh and len(wh) == 2:
            w = max(int(wh[0]), widget.minimumWidth())
            h = max(int(wh[1]), widget.minimumHeight())
            widget.resize(w, h)
    except Exception:
        pass


class OverlayStyleMixin:
    """0.4.9.1: gemeinsames Erscheinungsbild aller Overlays.
    Drei Modi: 'transparent' (durchscheinend wie bisher das Reifen-Overlay),
    'dark' und 'light' (deckend, passend zum App-Theme). Die Fensterflagge
    WA_TranslucentBackground bleibt immer gesetzt - deckend wird ueber den
    Alpha-Wert gemalt, damit das Fenster nie neu erzeugt werden muss.
    Semantische Farben (gruen/gelb/rot) bleiben in allen Modi gleich."""

    def apply_overlay_style(self, mode):
        self.overlay_style = mode if mode in ("transparent", "dark", "light") else "transparent"
        try:
            self._restyle()
        except Exception:
            pass
        # 0.4.9.6: an Kind-Widgets weiterreichen (z.B. die Reifengrafiken)
        try:
            for child in self.findChildren(QWidget):
                if child is not self and hasattr(child, "apply_overlay_style"):
                    child.overlay_style = self.overlay_style
                    try:
                        child._restyle()
                    except Exception:
                        pass
                    child.update()
        except Exception:
            pass
        self.update()

    def _restyle(self):
        """Von QSS-basierten Overlays ueberschrieben."""
        return None

    def _st(self):
        return getattr(self, "overlay_style", "transparent")

    def _bg(self):
        s = self._st()
        if s == "light":
            return QColor(247, 249, 252, 255)
        if s == "dark":
            return QColor(13, 17, 23, 255)
        return QColor(13, 17, 23, 214)

    def _panel(self):
        s = self._st()
        if s == "light":
            return QColor(255, 255, 255, 255)
        if s == "dark":
            return QColor(21, 29, 42, 255)
        return QColor(21, 29, 42, 220)

    def _fg(self):
        return QColor("#1b2430") if self._st() == "light" else QColor("#e6ebf2")

    def _muted(self):
        return QColor("#5b6675") if self._st() == "light" else QColor("#8a97a8")

    def _border(self):
        return QColor("#d5dbe4") if self._st() == "light" else QColor("#2b3545")

    def _trackcol(self):
        return QColor(226, 231, 238) if self._st() == "light" else QColor(31, 39, 52)

    def _faint(self, alpha=50):
        """0.4.9.6: dezente Linien - im hellen Design dunkel statt weiss."""
        c = self._fg()
        return QColor(c.red(), c.green(), c.blue(), alpha)

    # ---- 0.4.9.8: Groesse per Ziehen veraendern -------------------------
    def _ensure_grip(self):
        """Griff unten rechts. QSizeGrip kann auch rahmenlose Fenster skalieren."""
        if getattr(self, "_size_grip", None) is not None:
            return
        try:
            g = QSizeGrip(self)
            g.setFixedSize(18, 18)
            g.setToolTip("Ziehen: Gr\u00f6\u00dfe \u00e4ndern")
            g.setStyleSheet("background: transparent;")
            self._size_grip = g
            g.show(); g.raise_()
        except Exception:
            self._size_grip = None

    def _place_grip(self):
        g = getattr(self, "_size_grip", None)
        if g is not None:
            g.move(self.width() - g.width() - 2, self.height() - g.height() - 2)
            g.raise_()

    def showEvent(self, ev):
        self._ensure_grip()
        # 0.4.9.8: Groesse erst nach dem Show-Durchlauf setzen - Qt legt die
        # Fenstergeometrie sonst danach fest und ueberschreibt das resize().
        QTimer.singleShot(0, lambda: (_restore_overlay_size(self), self._place_grip()))
        self._place_grip()
        try:
            super().showEvent(ev)
        except Exception:
            pass

    def resizeEvent(self, ev):
        self._place_grip()
        _remember_overlay_size(self)
        try:
            super().resizeEvent(ev)
        except Exception:
            pass

    def _drag_start(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def _drag_move(self, ev):
        if getattr(self, "_drag", None) is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()


class PitOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.1: Boxenstopp-Status. Oeffnet automatisch beim Einfahren in die
    Boxengasse und schliesst sich beim Verlassen wieder (nur wenn es automatisch
    geoeffnet wurde - manuell geoeffnet bleibt es stehen)."""

    STATES = {0: ("keine Anforderung", "#8a97a8"), 1: ("Stopp angefordert", "#e3b341"),
              2: ("Einfahrt Boxengasse", "#58a6ff"), 3: ("steht in der Box", "#3fb950"),
              4: ("Ausfahrt Boxengasse", "#58a6ff")}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Pit Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(250, 162)
        self.setMinimumSize(200, 140)
        self.auto_opened = False
        self._d = None
        self._drag = None

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "BOXENSTOPP")
        s = self._d
        if s is None:
            p.setPen(self._muted()); p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end(); return
        state = int(getattr(s, "pit_state", 0) or 0)
        label, col = self.STATES.get(state, ("unbekannt", "#8a97a8"))
        in_pits = bool(getattr(s, "in_pits", False))
        limiter = bool(getattr(s, "speed_limiter", False))
        fv = QFont(); fv.setPointSize(14); fv.setBold(True); p.setFont(fv); p.setPen(QColor(col))
        p.drawText(QRectF(10, 24, w - 20, 24), Qt.AlignLeft, label)

        def row(y, key, val, color=None):
            fl = QFont(); fl.setPointSize(9); p.setFont(fl); p.setPen(self._muted())
            p.drawText(QRectF(10, y, 116, 16), Qt.AlignVCenter | Qt.AlignLeft, key)
            fx = QFont(); fx.setPointSize(10); fx.setBold(True); p.setFont(fx)
            p.setPen(color or self._fg())
            p.drawText(QRectF(122, y, w - 132, 16), Qt.AlignVCenter | Qt.AlignLeft, val)

        row(54, "in der Boxengasse", "ja" if in_pits else "nein",
            QColor("#3fb950") if in_pits else self._fg())
        row(74, "Begrenzer", "AN" if limiter else "AUS",
            QColor("#3fb950") if limiter else (QColor("#f85149") if in_pits else self._muted()))
        row(94, "Tempo", f"{float(getattr(s, 'speed_kmh', 0.0) or 0.0):.0f} km/h")
        row(114, "Stopps bisher", str(int(getattr(s, "num_pitstops", 0) or 0)))
        pit_d = float(getattr(s, "pit_lap_dist", 0.0) or 0.0)
        cur_d = float(getattr(s, "lap_dist_m", 0.0) or 0.0)
        if pit_d > 1.0:
            to_pit = pit_d - cur_d
            row(134, "Box in", f"{to_pit:.0f} m" if to_pit > 0 else "\u2014")
        else:
            row(134, "Sprit", f"{float(getattr(s, 'fuel_l', 0.0) or 0.0):.1f} l")
        p.end()


class DeltaOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.1: Abstand nach vorn und hinten in Sekunden, dazu die daraus
    geschaetzte Distanz in Metern (Zeit x eigenes Tempo), plus Rueckstand auf
    den Fuehrenden. Runden-Rueckstaende werden getrennt ausgewiesen."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Delta Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(258, 150)
        self.setMinimumSize(210, 126)
        self._d = None
        self._drag = None

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "ABSTAND & DISTANZ")
        s = self._d
        if s is None:
            p.setPen(self._muted()); p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end(); return
        spd = float(getattr(s, "speed_kmh", 0.0) or 0.0) / 3.6
        place = int(getattr(s, "place", 0) or 0)
        fv = QFont(); fv.setPointSize(13); fv.setBold(True); p.setFont(fv); p.setPen(self._fg())
        p.drawText(QRectF(10, 24, w - 20, 20), Qt.AlignLeft, f"P {place}" if place else "P \u2014")

        def gap_row(y, key, gap_s, laps, color):
            fl = QFont(); fl.setPointSize(9); p.setFont(fl); p.setPen(self._muted())
            p.drawText(QRectF(10, y, 74, 18), Qt.AlignVCenter | Qt.AlignLeft, key)
            fx = QFont(); fx.setPointSize(12); fx.setBold(True); p.setFont(fx); p.setPen(color)
            if laps and laps > 0:
                txt = f"+{laps} Rd"
            elif gap_s and gap_s > 0.001:
                txt = f"{gap_s:.2f} s"
            else:
                txt = "\u2014"
            p.drawText(QRectF(84, y, 78, 18), Qt.AlignVCenter | Qt.AlignLeft, txt)
            fm = QFont(); fm.setPointSize(9); p.setFont(fm); p.setPen(self._muted())
            dist = (gap_s * spd) if (gap_s and gap_s > 0.001 and not laps) else 0.0
            p.drawText(QRectF(162, y, w - 172, 18), Qt.AlignVCenter | Qt.AlignLeft,
                       f"{dist:.0f} m" if dist > 0.5 else "")

        gap_ahead = float(getattr(s, "gap_ahead_s", 0.0) or 0.0)
        gap_behind = float(getattr(s, "gap_behind_s", 0.0) or 0.0)
        gap_leader = float(getattr(s, "gap_leader_s", 0.0) or 0.0)
        gap_row(50, "nach vorn", gap_ahead, int(getattr(s, "laps_behind_next", 0) or 0), QColor("#f85149"))
        gap_row(76, "nach hinten", gap_behind, 0, QColor("#3fb950"))
        gap_row(102, "auf F\u00fchrenden", gap_leader, int(getattr(s, "laps_behind_leader", 0) or 0), QColor("#58a6ff"))
        fn = QFont(); fn.setPointSize(7); p.setFont(fn); p.setPen(self._muted())
        p.drawText(QRectF(0, h - 16, w, 12), Qt.AlignCenter, "Distanz = Abstand x eigenes Tempo")
        p.end()


class LapTimeOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.1.0: Rundenzeiten im neuen Design (Bild 1) - links ein Delta-Ring,
    rechts ein Streifen AKTUELL / DELTA / SESSION-BEST / PROGNOSE. Delta = Live-
    Delta zur Session-Bestrunde (gruen = schneller). Prognose = Bestzeit + Delta."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Rundenzeiten Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(470, 120)
        self.setMinimumSize(360, 96)
        self._d = None
        self._delta = 0.0
        self._clock_anchor_raw = None   # 0.5.9.26: fuer Echtzeit-Extrapolation, s.u.
        self._clock_anchor_ts = None
        self._drag = None
        self._self_timer = QTimer(self)  # 0.5.9.26: eigener Repaint-Takt
        self._self_timer.setInterval(50)  # 20 Hz, unabhaengig von den anderen ~12 Overlay-Repaints
        self._self_timer.timeout.connect(self._self_tick)
        self._self_timer.start()

    def _self_tick(self):  # 0.5.9.26
        if self.isVisible():
            self.update()  # paintEvent extrapoliert AKTUELL frisch per time.monotonic()

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._clock_anchor_raw = getattr(main, "_live_clock_anchor_raw", None)  # 0.5.9.26
        self._clock_anchor_ts = getattr(main, "_live_clock_anchor_ts", None)
        try:
            self._delta = float(getattr(main, "live_delta_s", 0.0) or 0.0)
        except Exception:
            self._delta = 0.0
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 14, 14)
        s = self._d
        green = QColor("#3fb950"); red = QColor("#f85149")
        delta = self._delta
        dcol = green if delta <= 0 else red

        ring = min(h - 16, 96)
        cx, cy = 12 + ring / 2.0, h / 2.0
        rrect = QRectF(cx - ring / 2.0, cy - ring / 2.0, ring, ring)
        p.setPen(QPen(self._faint(60), 8)); p.setBrush(Qt.NoBrush)
        p.drawArc(rrect, 0, 360 * 16)
        frac = max(0.0, min(1.0, abs(delta) / 2.0))
        pen_fg = QPen(dcol, 8); pen_fg.setCapStyle(Qt.RoundCap); p.setPen(pen_fg)
        p.drawArc(rrect, 90 * 16, -int(360 * 16 * frac))
        p.setFont(QFont("Segoe UI", 8, QFont.DemiBold)); p.setPen(self._muted())
        p.drawText(rrect.adjusted(0, ring * 0.20, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "DELTA")
        p.setFont(QFont("Segoe UI", 17, QFont.Bold)); p.setPen(dcol)
        p.drawText(rrect, Qt.AlignCenter, f"{delta:+.2f}" if s is not None else "--")

        if s is None:
            p.setPen(self._muted()); p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(ring + 24, 0, w - ring - 32, h), Qt.AlignVCenter | Qt.AlignLeft, "warte auf Telemetrie")
            p.end(); return
        cur = (self._clock_anchor_raw + (time.monotonic() - self._clock_anchor_ts)) \
              if self._clock_anchor_raw is not None and self._clock_anchor_ts is not None \
              else float(getattr(s, "current_lap_time", 0.0) or 0.0)
        cur = max(0.0, cur)
        best = float(getattr(s, "best_lap_time", 0.0) or 0.0)
        last = float(getattr(s, "last_lap_time", 0.0) or 0.0)
        pred = (best + delta) if best > 0 else last
        cells = [
            ("AKTUELL", fmt_lap_time(cur) if cur > 0 else "--:--.---", self._fg()),
            ("DELTA", f"{delta:+.2f}", dcol),
            ("SESSION-BEST", fmt_lap_time(best) if best > 0 else "--:--.---", self._fg()),
            ("PROGNOSE", fmt_lap_time(pred) if pred > 0 else "--:--.---", green if delta <= 0 else red),
        ]
        x = ring + 26
        cw = (w - x - 12) / len(cells)
        for label, val, col in cells:
            p.setFont(QFont("Segoe UI", 13, QFont.Bold)); p.setPen(col)
            p.drawText(QRectF(x, h / 2 - 22, cw, 26), Qt.AlignLeft | Qt.AlignVCenter, val)
            p.setFont(QFont("Segoe UI", 8, QFont.DemiBold)); p.setPen(self._muted())
            p.drawText(QRectF(x, h / 2 + 6, cw, 14), Qt.AlignLeft | Qt.AlignVCenter, label)
            x += cw
        p.end()

class FlagOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.1.0: Flaggen-Overlay im LED-Matrix-Stil (Bild 2). Quelle: mGamePhase,
    mYellowFlagState, mSectorFlag[eigener Sektor] und das fahrzeugeigene mFlag
    (6 = blau). Prioritaet: Ziel > Rot > Voll-Gelb > Blau > lokal Gelb > Weiss >
    Gruen. Selbst-diagnostizierend ohne Session."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Flaggen Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(150, 150)
        self.setMinimumSize(90, 90)
        self._flag = "none"; self._label = "\u2014"; self._drag = None

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._flag, self._label = self._decide(s)
        self.update()

    @staticmethod
    def _decide(s):
        if s is None:
            return "none", "\u2014"
        phase = int(getattr(s, "game_phase", 0) or 0)
        yfs = int(getattr(s, "yellow_flag_state", 0) or 0)
        pf = int(getattr(s, "player_flag", 0) or 0)
        sec = int(getattr(s, "sector_index", 0) or 0)
        sec = 0 if sec < 0 else 2 if sec > 2 else sec
        local = [int(getattr(s, "sector_flag_0", 0) or 0),
                 int(getattr(s, "sector_flag_1", 0) or 0),
                 int(getattr(s, "sector_flag_2", 0) or 0)][sec]
        if phase == 8:
            return "checkered", "ZIEL"
        if yfs == 7:
            return "red", "ROT"
        if phase == 6 or yfs in (1, 2, 3, 4, 6):
            return "yellow", "GELB"
        if pf == 6:
            return "blue", "BLAU"
        if local:
            return "yellow", "GELB (LOKAL)"
        if yfs == 5:
            return "white", "WEISS"
        if phase == 5:
            return "green", "GR\u00dcN"
        return "none", "\u2014"

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        base = {
            "green": QColor("#2ecc40"), "yellow": QColor("#ffd400"),
            "blue": QColor("#0a84ff"), "white": QColor("#eef1f5"),
            "red": QColor("#ff3b30"), "checkered": QColor("#eef1f5"),
            "none": QColor(60, 66, 74),
        }[self._flag]
        pad = 10
        cols = 14
        cell = (min(w, h) - 2 * pad) / cols
        rows = max(1, int((h - 2 * pad - 20) / cell))
        ox = (w - cols * cell) / 2.0
        oy = pad
        for r in range(rows):
            for c in range(cols):
                if self._flag == "checkered":
                    col = QColor("#eef1f5") if (r + c) % 2 == 0 else QColor(30, 34, 40)
                elif self._flag == "none":
                    col = QColor(48, 54, 62)
                else:
                    col = QColor(base)
                    if (r + c) % 3 == 0:
                        col = col.darker(118)
                p.setBrush(col); p.setPen(Qt.NoPen)
                p.drawEllipse(QRectF(ox + c * cell + cell * 0.12,
                                     oy + r * cell + cell * 0.12,
                                     cell * 0.76, cell * 0.76))
        p.setFont(QFont("Segoe UI", 10, QFont.Bold)); p.setPen(self._fg())
        p.drawText(QRectF(0, h - 20, w, 16), Qt.AlignCenter, self._label)
        p.end()


class LapGraphOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.1.0: Rundenzeiten-Graph (Bild 3). Sammelt abgeschlossene Rundenzeiten
    (Erkennung ueber Rundenwechsel) und zeichnet sie als Linie; gruen = saubere
    schnelle Runde, rot = langsam/Ausreisser. Overlay-lokale Historie."""

    MAXN = 24

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Rundenzeiten-Graph")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(300, 190)
        self.setMinimumSize(220, 140)
        self._times = []
        self._last_lap = None
        self._drag = None

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if s is not None:
            lap = int(getattr(s, "lap_number", 0) or 0)
            last = float(getattr(s, "last_lap_time", 0.0) or 0.0)
            if self._last_lap is None:
                self._last_lap = lap
            elif lap != self._last_lap:
                self._last_lap = lap
                if 20.0 < last < 1800.0:
                    self._times.append(last)
                    if len(self._times) > self.MAXN:
                        del self._times[0:len(self._times) - self.MAXN]
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        p.setFont(QFont("Segoe UI", 9, QFont.Bold)); p.setPen(self._muted())
        p.drawText(QRectF(0, 6, w, 16), Qt.AlignCenter, "LAPTIME GRAPH")
        ts = self._times
        if len(ts) < 2:
            p.setPen(self._muted()); p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "sammle Rundenzeiten \u2026")
            p.end(); return
        best = min(ts)
        lo = best * 0.98
        hi = max(max(ts), best * 1.05)
        ml, mr, mt, mb = 52, 12, 28, 20
        pw = w - ml - mr; ph = h - mt - mb
        def X(i): return ml + pw * (i / (len(ts) - 1))
        def Y(v): return mt + ph * (1 - (v - lo) / (hi - lo + 1e-6))
        p.setFont(QFont("Segoe UI", 7))
        for k in range(4):
            gy = mt + ph * k / 3.0
            p.setPen(QPen(self._faint(45), 1, Qt.DotLine))
            p.drawLine(QPointF(ml, gy), QPointF(w - mr, gy))
            val = hi - (hi - lo) * k / 3.0
            p.setPen(self._muted())
            p.drawText(QRectF(2, gy - 7, ml - 6, 14), Qt.AlignRight | Qt.AlignVCenter, fmt_lap_time(val))
        thr = best * 1.03
        for i in range(1, len(ts)):
            col = QColor("#3fb950") if ts[i] <= thr else QColor("#f85149")
            p.setPen(QPen(col, 2))
            p.drawLine(QPointF(X(i - 1), Y(ts[i - 1])), QPointF(X(i), Y(ts[i])))
        for i, v in enumerate(ts):
            col = QColor("#3fb950") if v <= thr else QColor("#f85149")
            p.setBrush(col); p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(X(i) - 3, Y(v) - 3, 6, 6))
        p.end()


class OvertakeOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.1.0: Ueberholalarm (Bild 5). Listet Fahrzeuge, die auf der Strecke
    hinter mir sind, mit Zeitabstand (= Streckenabstand / eigenes Tempo) bis sie
    mich erreichen. Position, Klasse (farbig), Fahrername. Rot < 1 s, orange
    < 2 s, Pfeil = kommt naeher. Hersteller-Logos liefert das SharedMemory nicht."""

    CLASS_COLORS = [
        ("HYPER", QColor("#ff3b30")), ("LMH", QColor("#ff3b30")),
        ("LMP2", QColor("#ffd400")), ("LMP3", QColor("#33d1e0")),
        ("LMP", QColor("#ffd400")),
        ("GT3", QColor("#ff9f0a")), ("GTE", QColor("#ff375f")),
        ("GT4", QColor("#ff375f")), ("GT", QColor("#ff9f0a")),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Ueberholalarm")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(300, 176)
        self.setMinimumSize(220, 80)
        self._rows = []
        self._prev = {}
        self._drag = None

    def _class_color(self, vclass):
        u = (vclass or "").upper()
        for key, col in self.CLASS_COLORS:
            if key in u:
                return col
        return QColor("#8a97a8")

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        rows = []
        if s is not None:
            spd = float(getattr(s, "speed_kmh", 0.0) or 0.0) / 3.6
            if spd > 3.0:
                cur = {}
                for e in getattr(s, "opponents_behind", ()):
                    try:
                        place, driver, vclass, dist = int(e[0]), str(e[1]), str(e[2]), float(e[3])
                    except Exception:
                        continue
                    gap = dist / spd
                    prev = self._prev.get(driver)
                    closing = prev is not None and gap < prev - 0.02
                    cur[driver] = gap
                    rows.append((place, driver, vclass, gap, closing))
                self._prev = cur
        rows.sort(key=lambda r: r[3])
        self._rows = rows[:5]
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        p.setFont(QFont("Segoe UI", 9, QFont.Bold)); p.setPen(self._muted())
        p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "\u00dcBERHOLALARM")
        rows = self._rows
        if not rows:
            p.setPen(self._muted()); p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "frei hinten")
            p.end(); return
        y = 26.0
        rh = min(30.0, (h - 30) / max(len(rows), 1))
        for place, driver, vclass, gap, closing in rows:
            ccol = self._class_color(vclass)
            p.setPen(Qt.NoPen); p.setBrush(self._panel())
            p.drawRoundedRect(QRectF(8, y, w - 16, rh - 4), 6, 6)
            p.setBrush(ccol); p.drawRoundedRect(QRectF(12, y + 3, 34, rh - 10), 4, 4)
            p.setFont(QFont("Segoe UI", 9, QFont.Bold)); p.setPen(QColor("#0d1117"))
            p.drawText(QRectF(12, y + 3, 34, rh - 10), Qt.AlignCenter, str(place) if place else "\u2014")
            p.setFont(QFont("Segoe UI", 9, QFont.DemiBold)); p.setPen(self._fg())
            short = (vclass or "").upper()[:5]
            p.drawText(QRectF(52, y, w - 130, rh - 4), Qt.AlignVCenter | Qt.AlignLeft, f"{short}  {driver}")
            gcol = QColor("#f85149") if gap < 1.0 else (QColor("#ff9f0a") if gap < 2.0 else self._muted())
            p.setFont(QFont("Segoe UI", 11, QFont.Bold)); p.setPen(gcol)
            arrow = " \u25b2" if closing else ""
            p.drawText(QRectF(w - 78, y, 66, rh - 4), Qt.AlignVCenter | Qt.AlignRight, f"+{gap:.1f}{arrow}")
            y += rh
        p.end()


class DamageModel:
    """0.4.9.4: Schadenserfassung, die auch dann reagiert, wenn mDentSeverity
    stumm bleibt. Grund fuer den Umbau: mDentSeverity beschreibt NUR sichtbare
    Karosseriedellen an 8 Stellen. Aero-, Aufhaengungs- und Mechanikschaeden
    schreibt LMU dort nicht hinein - bei schweren Schaeden konnten alle acht
    Werte auf 0 stehen und das Overlay meldete faelschlich "keine".

    Deshalb wird zusaetzlich jeder Einschlag mitgezaehlt: mLastImpactET aendert
    sich bei jedem Treffer, mLastImpactMagnitude liefert die Staerke. Summe,
    Anzahl und groesster Treffer ergeben ein belastbares Schadensbild.

    Die Einheit von mLastImpactMagnitude ist nicht dokumentiert, die Schwellen
    sind daher Kalibrierwerte in exports/damage_model.json - das Overlay zeigt
    die Rohwerte mit an, damit sie anhand echter Faelle nachgezogen werden koennen."""

    DEFAULTS = {
        "impact_min": 50.0,        # darunter als Bordstein-/Rempler-Rauschen ignorieren
        "impact_heavy": 25000.0,   # einzelner schwerer Treffer
        "sum_total": 60000.0,      # kumulierte Summe fuer 100 % im Index
    }

    def __init__(self, config_path=None):
        self.cfg = dict(self.DEFAULTS)
        self.config_path = config_path
        self.load()
        self.reset()

    def load(self):
        if not self.config_path:
            return
        try:
            import json
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in self.DEFAULTS:
                if k in data:
                    self.cfg[k] = float(data[k])
        except Exception:
            pass

    def save(self):
        if not self.config_path:
            return
        try:
            import json
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2)
        except Exception:
            pass

    def reset(self):
        self.impacts = 0
        self.impact_sum = 0.0
        self.impact_max = 0.0
        self.last_impact_mag = 0.0
        self._last_et = None
        self.dents = [0, 0, 0, 0, 0, 0, 0, 0]   # hoechster je gesehener Wert
        self.detached = False
        self.overheating = False
        self.flats = [False, False, False, False]
        self.wheels_off = [False, False, False, False]
        self._veh = None
        self.saw_dent_channel = False
        self.saw_impact_channel = False

    def update(self, s):
        if s is None:
            return
        veh = str(getattr(s, "vehicle_name", "") or "")
        if self._veh is None:
            self._veh = veh
        elif veh != self._veh:
            self._veh = veh
            self.reset()
            self._veh = veh
        # Dellen: hoechsten Wert halten (Reparatur setzt ihn zurueck)
        cur_dents = [int(getattr(s, f"dent_{i}", 0) or 0) for i in range(8)]
        if any(cur_dents):
            self.saw_dent_channel = True
        if sum(cur_dents) < sum(self.dents) and sum(cur_dents) == 0:
            self.dents = cur_dents          # repariert
        else:
            self.dents = [max(self.dents[i], cur_dents[i]) for i in range(8)]
        # Einschlaege ueber die Zeitmarke zaehlen
        try:
            et = float(getattr(s, "last_impact_et", 0.0) or 0.0)
            mag = float(getattr(s, "last_impact_magnitude", 0.0) or 0.0)
        except Exception:
            et, mag = 0.0, 0.0
        if et > 0.0:
            self.saw_impact_channel = True
            if self._last_et is None:
                self._last_et = et
            elif et > self._last_et:
                self._last_et = et
                if mag >= float(self.cfg["impact_min"]):
                    self.impacts += 1
                    self.impact_sum += mag
                    self.last_impact_mag = mag
                    if mag > self.impact_max:
                        self.impact_max = mag
        self.detached = bool(getattr(s, "parts_detached", False)) or self.detached
        self.overheating = bool(getattr(s, "overheating", False))
        for i, k in enumerate(("fl", "fr", "rl", "rr")):
            if bool(getattr(s, f"tire_{k}_flat", False)):
                self.flats[i] = True
            if bool(getattr(s, f"wheel_{k}_detached", False)):
                self.wheels_off[i] = True

    # ---- Bewertung ----
    def index_pct(self):
        """Schadensindex in Prozent: Dellen und kumulierte Einschlaege kombiniert."""
        dent_part = sum(self.dents) / 16.0
        imp_part = self.impact_sum / max(float(self.cfg["sum_total"]), 1.0)
        return max(0.0, min(100.0, (max(dent_part, 0.0) + imp_part) * 100.0))

    def severe(self):
        return (self.detached or any(self.flats) or any(self.wheels_off)
                or max(self.dents) >= 2
                or self.impact_max >= float(self.cfg["impact_heavy"]))

    def any_damage(self):
        return (self.severe() or sum(self.dents) > 0 or self.impacts > 0
                or self.overheating)

    def repair_hint(self):
        if self.detached or any(self.wheels_off) or any(self.flats):
            return ("Reparatur n\u00f6tig \u2013 sofort Box", "bad")
        if self.severe():
            return ("Reparatur n\u00f6tig \u2013 Box ansteuern", "bad")
        if self.index_pct() >= 25 or self.impacts >= 3:
            return ("Reparatur beim n\u00e4chsten Stopp", "warn")
        if self.any_damage():
            return ("leichter Schaden \u2013 beobachten", "warn")
        return ("keine Reparatur n\u00f6tig", "good")

    def diagnostics(self):
        """Rohwerte, damit sichtbar ist, was die Sim tatsaechlich liefert."""
        d = "aktiv" if self.saw_dent_channel else "still"
        i = "aktiv" if self.saw_impact_channel else "still"
        return (f"Dellen {sum(self.dents)}/16 ({d}) \u00b7 Treffer {self.impacts} "
                f"({i}) \u00b7 max {self.impact_max:.0f}")


class DamageOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.1/0.4.9.4: Fahrzeugschaeden ueber das DamageModel. LMU liefert keinen
    Schadensprozentwert; mDentSeverity erfasst nur sichtbare Karosseriedellen und
    bleibt bei Aero-/Aufhaengungsschaeden stumm. Deshalb zaehlt das Modell
    zusaetzlich die Einschlaege (mLastImpactET/-Magnitude). Unten stehen die
    Rohwerte beider Kanaele, damit erkennbar ist, was die Sim wirklich meldet."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Schaden Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(258, 212)
        self.setMinimumSize(220, 186)
        self._d = None
        self._m = None       # 0.4.9.4: DamageModel
        self._rest = None    # 0.4.9.5
        self._drag = None

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._m = getattr(main, "damage_model", None)  # 0.4.9.4
        self._rest = getattr(main, "rest", None)  # 0.4.9.5
        self.update()

    def mousePressEvent(self, ev): self._drag_start(ev)
    def mouseMoveEvent(self, ev): self._drag_move(ev)
    def mouseReleaseEvent(self, ev): self._drag = None

    def mouseDoubleClickEvent(self, ev):   # 0.4.9.4: nach Reparatur zuruecksetzen
        if self._m is not None:
            self._m.reset()
        self.update()

    @staticmethod
    def _dents(s):
        return [int(getattr(s, f"dent_{i}", 0) or 0) for i in range(8)]

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg()); p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "SCHADEN")
        s = self._d
        if s is None:
            p.setPen(self._muted()); p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end(); return
        m = self._m
        if m is None:
            p.setPen(self._muted())
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "Schadensmodell nicht aktiv")
            p.end(); return
        dents = list(m.dents)
        total = sum(dents)
        rest = self._rest if (self._rest is not None and self._rest.has_wearables()) else None
        aero_real = rest.aero_pct() if rest is not None else None
        susp_real = rest.worst_suspension_pct() if rest is not None else None
        pct = max(aero_real or 0.0, susp_real or 0.0) if rest is not None else m.index_pct()
        detached = m.detached
        overheat = m.overheating
        flats = list(m.flats)
        wheels_off = list(m.wheels_off)
        severe = m.severe()
        col = QColor("#f85149") if severe else QColor("#e3b341") if total > 0 else QColor("#3fb950")
        fv = QFont(); fv.setPointSize(22); fv.setBold(True); p.setFont(fv); p.setPen(col)
        p.drawText(QRectF(10, 22, w - 20, 30), Qt.AlignLeft, f"{pct:.0f} %")
        fs = QFont(); fs.setPointSize(9); p.setFont(fs); p.setPen(self._muted())
        p.drawText(QRectF(10, 30, w - 20, 22), Qt.AlignRight, "Karosserie-Index")
        # Balken
        bx, by, bw, bh = 10, 56, w - 20, 9
        p.setPen(Qt.NoPen); p.setBrush(QColor(31, 39, 52) if self._st() != "light" else QColor(226, 231, 238))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        p.setBrush(col); p.drawRoundedRect(QRectF(bx, by, max(bw * min(pct / 100.0, 1.0), 3), bh), 4, 4)

        def row(y, key, val, color=None):
            fl2 = QFont(); fl2.setPointSize(9); p.setFont(fl2); p.setPen(self._muted())
            p.drawText(QRectF(10, y, 118, 16), Qt.AlignVCenter | Qt.AlignLeft, key)
            fx = QFont(); fx.setPointSize(10); fx.setBold(True); p.setFont(fx); p.setPen(color or self._fg())
            p.drawText(QRectF(128, y, w - 138, 16), Qt.AlignVCenter | Qt.AlignLeft, val)

        imp_col = QColor("#f85149") if m.impact_max >= float(m.cfg["impact_heavy"]) else \
            (QColor("#e3b341") if m.impacts else QColor("#3fb950"))
        row(72, "Treffer", (f"{m.impacts}  \u00b7  st\u00e4rkster {m.impact_max:.0f}"
                            if m.impacts else "keine"), imp_col)
        if aero_real is not None:
            row(90, "Aero-Schaden", f"{aero_real:.0f} %",
                QColor("#f85149") if aero_real >= 30 else QColor("#e3b341") if aero_real >= 8 else QColor("#3fb950"))
        else:
            row(90, "schwerste Delle", ["keine", "leicht", "schwer"][min(max(dents), 2)],
                QColor("#f85149") if max(dents) >= 2 else (QColor("#e3b341") if max(dents) == 1 else QColor("#3fb950")))
        if susp_real is not None:
            row(108, "Aufh\u00e4ngung", f"{susp_real:.0f} %" + ("  \u00b7 Teile ab" if detached else ""),
                QColor("#f85149") if susp_real >= 25 or detached else
                QColor("#e3b341") if susp_real >= 8 else QColor("#3fb950"))
        else:
            row(108, "Teile abgerissen", "JA" if detached else "nein",
                QColor("#f85149") if detached else QColor("#3fb950"))
        row(126, "\u00dcberhitzung", "JA" if overheat else "nein",
            QColor("#f85149") if overheat else QColor("#3fb950"))
        names = ["VL", "VR", "HL", "HR"]
        bad = [names[i] for i in range(4) if flats[i] or wheels_off[i]]
        row(144, "R\u00e4der", ", ".join(bad) if bad else "in Ordnung",
            QColor("#f85149") if bad else QColor("#3fb950"))
        # Reparatur-Hinweis
        hint, kind = m.repair_hint()
        hc = {"bad": QColor("#f85149"), "warn": QColor("#e3b341"), "good": QColor("#3fb950")}.get(kind, self._fg())
        fh = QFont(); fh.setPointSize(9); fh.setBold(True); p.setFont(fh)
        p.setPen(hc); p.drawText(QRectF(10, h - 32, w - 20, 16), Qt.AlignLeft, hint)
        # Diagnose: was liefert die Sim wirklich?
        fdg = QFont(); fdg.setPointSize(7); p.setFont(fdg); p.setPen(self._muted())
        p.drawText(QRectF(10, h - 15, w - 20, 12), Qt.AlignLeft,
                   ("Quelle: LMU-API (echte Werte) \u00b7 " if rest is not None else "Quelle: Telemetrie \u00b7 ")
                   + m.diagnostics())
        p.end()


class OverlayWindow(OverlayStyleMixin, QWidget):
    """Schlankes Always-on-top Monitor/Coach-Overlay im HUD-Stil.
    Kein VR-Overlay und kein Click-through: stabil und verschiebbar.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Coach Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(1.0)
        self.resize(330, 118)
        self.setMinimumSize(300, 108)
        self._drag_pos = None
        self._flatspot_hold = {"VL": 0, "VR": 0, "HL": 0, "HR": 0}
        self._flatspot_text = {"VL": "OK", "VR": "OK", "HL": "OK", "HR": "OK"}
        self.setStyleSheet("""
            QWidget { background:transparent; color:#ffffff; font-size:12px; }
            QLabel { color:#ffffff; background:transparent; }
            QFrame { background:transparent; border:0px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(2)

        header = QHBoxLayout()
        title = QLabel("Coach")
        title.setObjectName("ovlTitle")  # 0.4.9.7: Farbe kommt aus _restyle
        self.compact_status = QLabel("LIVE")
        self.compact_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.compact_status.setStyleSheet("font-size:12px;font-weight:bold;color:#7df59a;background:transparent;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.compact_status)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(1)
        self.values = {}
        # Minimal-Overlay: Runden-, Speed- und Reifendaten sind im LMU-HUD bzw. Reifen-Overlay sichtbar.
        # Dieses Fenster zeigt nur noch Referenz/Delta/Coach.
        rows = [
            ("Referenz", "—"),
            ("Delta", "—"),
            ("Coach", "—"),
        ]
        for r, (name, val) in enumerate(rows):
            k = QLabel(name)
            k.setFixedWidth(58)
            k.setObjectName("ovlKey")  # 0.4.9.7
            v = QLabel(val)
            v.setWordWrap(False)
            v.setObjectName("ovlVal")  # 0.4.9.7
            grid.addWidget(k, r, 0)
            grid.addWidget(v, r, 1)
            self.values[name] = v
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

    def paintEvent(self, event):
        # Gleicher halbtransparenter HUD-Look wie Reifen-Overlay, aber kompakter.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg()))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 9, 9)
        painter.setBrush(QBrush(self._panel()))
        painter.drawRoundedRect(self.rect().adjusted(5, 5, -6, -6), 8, 8)

    def _restyle(self):
        light = self._st() == "light"
        c = "#1b2430" if light else "#ffffff"
        key = "#5b6675" if light else "#c7d2df"
        self.setStyleSheet(
            "QWidget { background:transparent; color:%s; font-size:12px; }"
            "QLabel { color:%s; background:transparent; }"
            "QLabel#ovlTitle { color:%s; font-size:14px; font-weight:bold; }"
            "QLabel#ovlKey { color:%s; font-size:10px; }"
            "QLabel#ovlVal { color:%s; font-size:11px; font-weight:bold; }"
            % (c, c, c, key, c))
        self._restyle_status()  # 0.4.9.7

    def _sem_color(self, kind):
        """0.4.9.7: Warnfarben im hellen Design abdunkeln, sonst unlesbar."""
        light = self._st() == "light"
        if kind == "bad":
            return "#c62828" if light else "#ff6767"
        return "#8a6100" if light else "#ffd45a"

    def _restyle_status(self):
        lab = getattr(self, "compact_status", None)
        if lab is None:
            return
        kind = getattr(self, "_status_kind", "warn")
        lab.setStyleSheet("font-size:12px;font-weight:bold;color:%s;background:transparent;"
                          % self._sem_color(kind))

    def _start_drag(self, event):
        try:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True
        except Exception:
            return False

    def _move_drag(self, event):
        try:
            if self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
                return True
        except Exception:
            pass
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_drag(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._move_drag(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def set_value(self, key: str, value: str):
        if key in self.values:
            self.values[key].setText(value)

    def _short_ref(self, main) -> str:
        try:
            txt = main.reference_display_label(short=True)
            # Sehr kurze Anzeige fürs Overlay.
            txt = txt.replace("Silverstone National Circuit | ", "")
            if txt in ("Auto / offen", "—") and getattr(main, "live_best_reference_lap", None) is not None:
                return f"Live-Ref Lap {main.live_best_reference_lap}"
            if len(txt) > 34:
                txt = txt[:31] + "…"
            return txt
        except Exception:
            return "—"

    def update_from_main(self, main):
        last = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if main.recording:
            self.compact_status.setText("● REC")
            self._status_kind = "bad"; self._restyle_status()  # 0.4.9.7
        elif last:
            self.compact_status.setText("● LIVE")
            self.compact_status.setStyleSheet("font-size:12px;font-weight:bold;color:#7df59a;background:transparent;")
        else:
            self.compact_status.setText("WARTET")
            self._status_kind = "warn"; self._restyle_status()  # 0.4.9.7

        # Runde/Speed/Reifen bleiben bewusst ausgeblendet: LMU-HUD + Reifen-Overlay übernehmen das.
        self.set_value("Referenz", self._short_ref(main))

        if getattr(main, "live_delta_s", None) is not None:
            self.set_value("Delta", f"{main.live_delta_s:+.3f} s")
            coach = getattr(main, "live_coach_line", "Live-Vergleich aktiv") or "Live-Vergleich aktiv"
            if len(coach) > 42:
                coach = coach[:39] + "…"
            self.set_value("Coach", coach)
        elif getattr(main, "segment_deltas", None) and getattr(main, "compare_lap", None):
            total = sum(d.delta_s for d in main.segment_deltas)
            self.set_value("Delta", f"Lap {main.compare_lap.lap_number}: {total:+.3f} s")
            zones = main.grouped_problem_zones() if main.segment_deltas else []
            if zones:
                z = zones[0]
                self.set_value("Coach", f"Zone {z[0]}-{z[1]} m · {z[2]:+.3f}s")
            else:
                self.set_value("Coach", "keine große Verlustzone")
        else:
            self.set_value("Delta", "Referenz laden")
            self.set_value("Coach", "Live sammelt Daten")


class TireMiniWidget(OverlayStyleMixin, QWidget):
    """Skalierbare Reifenanzeige (VR-tauglich). 0.5.9.4: drei Balken je Zone
    (A/M/I). Balkenhoehe + %-Wert darueber = Verschleiss der Zone, Ampel
    (>=75 gruen / >=40 gelb / sonst rot); Zonentemperatur darunter. Kopfzeile:
    Druck (bar) + Carcass-Temp. Ohne Pro-Zone-Quelle zeigen alle drei denselben
    Verschleiss (wear_zones-Fallback). Flat/Lock-Warnung nur wenn warn_enabled."""
    def __init__(self, name: str, value_side: str = "right"):
        super().__init__()
        self.name = name
        self.value_side = value_side
        self.pressure_kpa = 0.0
        self.out_t = 0.0; self.mid_t = 0.0; self.in_t = 0.0
        self.carcass = 0.0
        self.wear = 0.0
        self.wear_out = 0.0; self.wear_mid = 0.0; self.wear_in = 0.0  # 0.5.5.1: pro Zone (MFD)
        self.wear_trend = 0.0
        self.grip_score = 0
        self.flat_status = "OK"
        self.warn_enabled = True
        self.scale = 1.0
        self._apply_min_size()
        self.setToolTip("Reifen: 3 Balken je Zone (A/M/I=aussen/mitte/innen). "
                        "Balkenhoehe + % darueber = Verschleiss (voll/gruen=100 %, gelb <75 %, "
                        "rot <40 %). Zahl darunter = Zonentemperatur. Kopfzeile: Druck (bar) + "
                        "Carc (Karkass-Temp). Flat/Lock-Warnung nur bei Nicht-GT3.")

    def _apply_min_size(self):
        self.setMinimumSize(int(196 * self.scale), int(172 * self.scale))

    def set_scale(self, scale):
        self.scale = max(0.6, min(2.5, float(scale) or 1.0))
        self._apply_min_size()
        self.updateGeometry()
        self.update()

    def set_data(self, pressure, out_t, mid_t, in_t, carcass, wear, grip_score=0,
                 flat_status="OK", wear_trend=0.0, warn_enabled=True, wear_zones=None):
        self.pressure_kpa = pressure or 0.0
        self.out_t = out_t or 0.0; self.mid_t = mid_t or 0.0; self.in_t = in_t or 0.0
        self.carcass = carcass or 0.0
        self.wear = max(0.0, min(100.0, wear or 0.0))
        if wear_zones and len(wear_zones) == 3:
            self.wear_out, self.wear_mid, self.wear_in = [max(0.0, min(100.0, x or 0.0)) for x in wear_zones]
        else:
            self.wear_out = self.wear_mid = self.wear_in = self.wear
        self.wear_trend = wear_trend or 0.0
        self.grip_score = int(max(0, min(100, grip_score or 0)))
        self.flat_status = flat_status or "OK"
        self.warn_enabled = bool(warn_enabled)
        self.update()

    def rest_color(self) -> QColor:
        if self.wear >= 85:
            return QColor(25, 225, 45)
        if self.wear >= 65:
            return QColor(235, 215, 45)
        if self.wear >= 45:
            return QColor(255, 145, 25)
        return QColor(240, 40, 30)

    @staticmethod
    def _wear_color(wv):
        # 0.5.5.1: Farbe nach Rest-Verschleiss: viel Rest = gruen, abgefahren = rot
        if wv >= 85:
            return QColor(25, 225, 45)
        if wv >= 65:
            return QColor(235, 215, 45)
        if wv >= 45:
            return QColor(255, 145, 25)
        return QColor(240, 40, 30)

    @staticmethod
    def _temp_pct(t):
        """0.5.5.0: Zonentemperatur als Prozent im Arbeitsfenster (80-100 C = 100 %).
        Einzige echte Pro-Zone-Groesse in LMU ist die Temperatur - der Verschleiss
        (mWear) ist ein Einzelwert. Deshalb speist die Temperatur die %-Balken."""
        if t <= 0:
            return 0.0
        if 80.0 <= t <= 100.0:
            return 100.0
        if t < 80.0:
            return max(0.0, (t - 55.0) / 25.0 * 100.0)
        return max(0.0, (120.0 - t) / 20.0 * 100.0)

    @staticmethod
    def _bar_color(wear):
        # 0.5.9.1: Verschleiss-Ampel nach Vorgabe:
        #   >= 75 % Rest -> gruen, >= 40 % -> gelb, sonst rot.
        if wear >= 75.0:
            return QColor(25, 225, 45)
        if wear >= 40.0:
            return QColor(235, 205, 40)
        return QColor(240, 45, 30)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width(); h = self.height()

        def F(px, bold=False):
            f = p.font(); f.setPointSizeF(max(6.0, px)); f.setBold(bold); p.setFont(f)

        # 0.5.9.5: Layout nach Mockup. Pro Zone (A/M/I = aussen/mitte/innen):
        #   %-Wert oben + Balkenhoehe = Verschleiss (Ampel >=75 gruen/>=40 gelb/
        #   sonst rot), Zonentemperatur darunter. Fusszeile: Rad-ID, Druck (bar),
        #   Carcass-Temp. HINWEIS: LMU-Shared-Memory hat mWear nur EINMAL pro Rad
        #   -> ohne Pro-Zone-Quelle zeigen alle drei denselben Wert (wear_zones-
        #   Fallback); differenziert sich automatisch, sobald tireinfo/MFD liefert.
        zt = [self.out_t, self.mid_t, self.in_t]
        zw = [self.wear_out, self.wear_mid, self.wear_in]
        # 0.5.9.6: schmaler + enger zusammen -> wirkt wie eine Reifen-Lauffflaeche.
        group_w = w * 0.56
        x0 = (w - group_w) / 2.0
        gap = group_w * 0.05
        b_w = (group_w - 2 * gap) / 3.0
        cellw = b_w + gap
        pct_top = h * 0.05; pct_h = h * 0.115
        bar_top = h * 0.20; bar_bot = h * 0.68; bar_h = bar_bot - bar_top
        temp_top = h * 0.70; temp_h = h * 0.12

        # 0.5.9.7: Schriftgroessen skalieren mit dem Overlay UND passen garantiert
        # in die (schmale) Spalte -> Werte bleiben immer lesbar, nie abgeschnitten.
        # Fit gegen den breitesten Fall ("100%"/"100C"), damit alle drei gleich gross.
        def fit_pt(text, max_w, max_h, start):
            f = p.font(); f.setBold(True); s = float(start)
            f.setPointSizeF(max(6.0, s)); fm = QFontMetricsF(f)
            while s > 6.5 and (fm.horizontalAdvance(text) > max_w or fm.height() > max_h):
                s -= 0.5; f.setPointSizeF(s); fm = QFontMetricsF(f)
            return max(6.0, s)
        pct_pt = fit_pt("100%", cellw * 0.98, pct_h, min(cellw * 0.62, h * 0.14))
        temp_pt = fit_pt("100C", cellw * 0.98, temp_h, min(cellw * 0.55, h * 0.12))

        for i in range(3):
            bx = x0 + i * (b_w + gap)
            cellx = bx - gap / 2.0
            wv = max(0.0, min(100.0, zw[i]))
            wc = self._bar_color(wv)
            # %-Wert oben (Ampelfarbe), skaliert + fit
            F(pct_pt, True); p.setPen(wc)
            p.drawText(QRectF(cellx, pct_top, cellw, pct_h), Qt.AlignCenter, f"{wv:.0f}%")
            # Balken: Track + Fuellung nach Verschleiss
            p.setPen(QPen(self._border(), 1)); p.setBrush(QBrush(self._trackcol()))
            p.drawRoundedRect(QRectF(bx, bar_top, b_w, bar_h), 4, 4)
            fillh = bar_h * (wv / 100.0)
            if fillh > 1.0:
                p.setPen(Qt.NoPen); p.setBrush(QBrush(wc))
                p.drawRoundedRect(QRectF(bx, bar_bot - fillh, b_w, fillh), 4, 4)
            # Zonentemperatur unter dem Balken (temperaturfarbig), skaliert + fit
            F(temp_pt, True); p.setPen(temp_color_for_tire(zt[i]))
            p.drawText(QRectF(cellx, temp_top, cellw, temp_h), Qt.AlignCenter, f"{zt[i]:.0f}C")

        # Fusszeile: Rad-ID, Druck (bar), Carcass-Temp
        F(min(h * 0.066, 10), False); p.setPen(self._muted())
        p.drawText(QRectF(0, h * 0.86, w, h * 0.12), Qt.AlignCenter,
                   f"{self.name}   {self.pressure_kpa / 100.0:.2f} bar   Carc {self.carcass:.0f}\u00b0")

        # Flat/Lock-Warnung (opt-in) rahmt die Balkengruppe
        fs = (self.flat_status or "OK").upper()
        if self.warn_enabled and fs != "OK":
            warn = QColor(255, 60, 50) if ("KRIT" in fs or "PLATT" in fs or "FLAT" in fs) else QColor(255, 165, 35)
            p.setPen(QPen(warn, 2)); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(x0 - 5, bar_top - 4, group_w + 10, bar_h + 8), 6, 6)
            F(min(h * 0.07, 9), True); p.setPen(warn)
            label = "FLAT" if ("PLATT" in fs or "FLAT" in fs) else ("ABS!" if "ABS!" in fs else ("ABS" if "ABS" in fs else ("LOCK!" if ("LOCK!" in fs or "KRIT" in fs) else "LOCK")))
            p.drawText(QRectF(x0 - 5, bar_top - h * 0.075, group_w + 10, h * 0.07), Qt.AlignCenter, label)
        p.end()

class TireOverlayWindow(OverlayStyleMixin, QWidget):
    """Separates, kompaktes Always-on-top Reifenoverlay für Monitor/OBS."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Reifen Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(1.0)
        self.resize(410, 390)
        self.setMinimumSize(400, 380)
        self._drag_pos = None
        self._flatspot_hold = {"VL": 0, "VR": 0, "HL": 0, "HR": 0}
        self._flatspot_text = {"VL": "OK", "VR": "OK", "HL": "OK", "HR": "OK"}
        self.setStyleSheet("""
            QWidget { background:transparent; color:#ffffff; font-size:15px; }
            QLabel { color:#ffffff; background:transparent; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 12)
        root.setSpacing(2)
        title = QLabel("Reifen")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("ovlTitle")  # 0.4.9.7
        root.addWidget(title)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(12)
        self.tire_widgets = {}
        positions = [("VL", 0, 0, "left"), ("VR", 0, 1, "right"), ("HL", 1, 0, "left"), ("HR", 1, 1, "right")]
        for name, row, col, side in positions:
            wid = TireMiniWidget(name, side)
            self.grid.addWidget(wid, row, col)
            self.tire_widgets[name] = wid
            wid.installEventFilter(self)
        root.addLayout(self.grid)
        self.status = QLabel("")
        self.status.setVisible(False)
        title.installEventFilter(self)
        self.installEventFilter(self)
        # VR-Tauglichkeit: Skalierung + Deckkraft. Trend-Basiswerte pro Reifen.
        self.ui_scale = 1.0
        self.ui_opacity = 1.0
        self._wear_start = {}
        self.set_ui_scale(1.3)

    def set_ui_scale(self, scale):
        self.ui_scale = max(0.7, min(2.2, float(scale) or 1.0))
        for wdg in self.tire_widgets.values():
            wdg.set_scale(self.ui_scale)
        self.grid.setHorizontalSpacing(int(8 * self.ui_scale))
        self.grid.setVerticalSpacing(int(12 * self.ui_scale))
        self.setMinimumSize(int(360 * self.ui_scale), int(340 * self.ui_scale))
        self.resize(int(410 * self.ui_scale), int(390 * self.ui_scale))
        self.update()

    def set_ui_opacity(self, op):
        self.ui_opacity = max(0.25, min(1.0, float(op)))
        self.setWindowOpacity(self.ui_opacity)

    def wheelEvent(self, event):
        d = event.angleDelta().y()
        if d != 0:
            self.set_ui_scale(self.ui_scale + (0.1 if d > 0 else -0.1))
            event.accept()

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        sm = menu.addMenu("Skalierung")
        for label, val in [("75 %", 0.75), ("100 %", 1.0), ("125 %", 1.25), ("150 %", 1.5), ("175 %", 1.75), ("200 %", 2.0)]:
            sm.addAction(label, lambda v=val: self.set_ui_scale(v))
        om = menu.addMenu("Deckkraft")
        for label, val in [("40 %", 0.4), ("60 %", 0.6), ("75 %", 0.75), ("90 %", 0.9), ("100 %", 1.0)]:
            om.addAction(label, lambda v=val: self.set_ui_opacity(v))
        menu.exec(event.globalPos())

    def paintEvent(self, event):
        # Etwas stärkerer HUD-Hintergrund: transparenter als ein Fenster, aber mit genug Kontrast.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg()))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)
        painter.setBrush(QBrush(self._panel()))
        painter.drawRoundedRect(self.rect().adjusted(6, 6, -7, -7), 8, 8)

    def _restyle(self):
        c = "#1b2430" if self._st() == "light" else "#ffffff"
        self.setStyleSheet(
            "QWidget { background:transparent; color:%s; font-size:15px; }"
            "QLabel { color:%s; background:transparent; }"
            "QLabel#ovlTitle { color:%s; font-size:18px; font-weight:bold; }" % (c, c, c))

    def _start_drag(self, event):
        try:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True
        except Exception:
            return False

    def _move_drag(self, event):
        try:
            if self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
                return True
        except Exception:
            pass
        return False

    def eventFilter(self, obj, event):
        try:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                return self._start_drag(event)
            if event.type() == event.Type.MouseMove and event.buttons() & Qt.LeftButton:
                return self._move_drag(event)
            if event.type() == event.Type.MouseButtonRelease:
                self._drag_pos = None
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_drag(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._move_drag(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _score_from_grip_hint(self, text: str) -> int:
        import re
        m = re.search(r"(\d+)\s*%", text or "")
        if m:
            return int(m.group(1))
        low = (text or "").lower()
        if "perfekt" in low:
            return 95
        if "hoch" in low or "gut" in low:
            return 85
        if "mittel" in low:
            return 70
        return 50

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            return
        rows = [
            ("VL", s.tire_fl_pressure_kpa, s.tire_fl_temp_l_c, s.tire_fl_temp_c_c, s.tire_fl_temp_r_c, s.tire_fl_carcass_c, s.tire_fl_wear_pct, s.tire_fl_flat, s.tire_fl_grip_fract),
            ("VR", s.tire_fr_pressure_kpa, s.tire_fr_temp_l_c, s.tire_fr_temp_c_c, s.tire_fr_temp_r_c, s.tire_fr_carcass_c, s.tire_fr_wear_pct, s.tire_fr_flat, s.tire_fr_grip_fract),
            ("HL", s.tire_rl_pressure_kpa, s.tire_rl_temp_l_c, s.tire_rl_temp_c_c, s.tire_rl_temp_r_c, s.tire_rl_carcass_c, s.tire_rl_wear_pct, s.tire_rl_flat, s.tire_rl_grip_fract),
            ("HR", s.tire_rr_pressure_kpa, s.tire_rr_temp_l_c, s.tire_rr_temp_c_c, s.tire_rr_temp_r_c, s.tire_rr_carcass_c, s.tire_rr_wear_pct, s.tire_rr_flat, s.tire_rr_grip_fract),
        ]
        # Flat/Lock-Warnung nur bei Nicht-GT3 (GT3-Flatspots kommen vom Dreher, nicht vom Lockup).
        vclass = infer_vehicle_class(getattr(s, "vehicle_class", ""), getattr(s, "vehicle_name", ""), getattr(s, "vehicle_model", ""))
        warn_enabled = vclass not in ("GT3",)
        for name, pressure, out_t, mid_t, in_t, carc, wear, flat, grip_fract in rows:
            try:  # 0.5.5.2: echten MFD-Wert (REST wearables.tires) bevorzugen
                _ti = {"VL": 0, "VR": 1, "HL": 2, "HR": 3}[name]
                _rc = getattr(main, "rest", None)
                if _rc is not None and getattr(_rc, "tire_condition", None) and _rc.tire_condition[_ti] >= 0.0:
                    wear = _rc.tire_condition[_ti] * 100.0
            except Exception:
                pass
            status = main.flatspot_status(flat, grip_fract, s.brake, s.speed_kmh, s) if hasattr(main, "flatspot_status") else "OK"
            if status != "OK":
                self._flatspot_hold[name] = 80
                self._flatspot_text[name] = status
            elif self._flatspot_hold.get(name, 0) > 0:
                self._flatspot_hold[name] -= 1
                status = self._flatspot_text.get(name, "OK")
            else:
                self._flatspot_text[name] = "OK"
            # Verschleiss-Trend im Stint: Rest jetzt minus Rest bei erstem gueltigen Messwert.
            trend = 0.0
            if wear and wear > 0:
                self._wear_start.setdefault(name, wear)
                trend = wear - self._wear_start.get(name, wear)
            self.tire_widgets[name].set_data(pressure, out_t, mid_t, in_t, carc, wear, 0, status, trend, warn_enabled)
        # Keine Statuszeile im Reifen-HUD: möglichst kompakt und störungsfrei.
        return


class PedalOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.7.1: Scrollendes Pedal-/Lenk-Trace-Overlay (History-Graph).
    Zeigt die Roh-Fahrereingabe ueber die Zeit: Gas (gruen, mit Flaeche),
    Bremse (rot), Lenkung (cyan, um die Mittellinie). Keine Kupplung.
    Desktop-Overlay wie das Reifen-Overlay - kein SteamVR; laeuft im VDXR-Mirror mit."""

    HISTORY = 240  # sichtbare Datenpunkte = Fensterbreite in Samples

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Pedal Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # klaut LMU nicht den Fokus
        self.resize(300, 108)
        self.setMinimumSize(180, 70)
        self._thr = []
        self._brk = []
        self._str = []
        self._live = False
        self._drag = None
        self._col_thr = QColor("#3fb950")
        self._col_brk = QColor("#f85149")
        self._col_str = QColor("#58a6ff")
        self._gear = 0
        self._last_push_ts = time.monotonic()  # 0.5.9.26: fuer sanftes Zwischen-Scrollen
        self._self_timer = QTimer(self)  # 0.5.9.26: eigener Repaint-Takt, s. paintEvent-Shift
        self._self_timer.setInterval(33)  # ~30 Hz
        self._self_timer.timeout.connect(self._self_tick)
        self._self_timer.start()

    def _self_tick(self):  # 0.5.9.26
        if self.isVisible():
            self.update()

    def _push(self, thr, brk, srt):
        for buf, val in ((self._thr, thr), (self._brk, brk), (self._str, srt)):
            buf.append(val)
            if len(buf) > self.HISTORY:
                del buf[0:len(buf) - self.HISTORY]
        self._last_push_ts = time.monotonic()  # 0.5.9.26

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            self._live = False
            self._gear = 0
            self._push(0.0, 0.0, 0.0)  # Trace laeuft weiter, flacht ab
            self.update()
            return
        c01 = lambda v: 0.0 if v < 0 else 1.0 if v > 1 else v
        c11 = lambda v: -1.0 if v < -1 else 1.0 if v > 1 else v
        thr = c01(float(getattr(s, "input_throttle", 0.0) or 0.0))
        brk = c01(float(getattr(s, "input_brake", 0.0) or 0.0))
        srt = c11(float(getattr(s, "input_steering", 0.0) or 0.0))
        self._live = True
        self._gear = int(getattr(s, "gear", 0) or 0)
        self._push(thr, brk, srt)
        self.update()

    # verschiebbar (rahmenlos)
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def _step(self, plot_w):
        return plot_w / (self.HISTORY - 1)

    def _scroll_shift_px(self, plot_w):  # 0.5.9.26: sanfter Zwischen-Scroll statt 100ms-Sprung
        step = self._step(plot_w)
        period = 0.1  # Sample-Intervall (10 Hz Recorder/Live-Tick)
        frac = (time.monotonic() - self._last_push_ts) / period
        return min(step, max(0.0, frac) * step)

    def _path(self, buf, x0, plot_w, y_at, shift_px=0.0):
        path = QPainterPath()
        n = len(buf)
        if n < 2:
            return path
        step = self._step(plot_w)
        start = self.HISTORY - n  # rechtsbuendig: neueste Werte rechts
        for i, v in enumerate(buf):
            x = x0 + (start + i) * step - shift_px
            y = y_at(v)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Karte
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg())
        p.drawRoundedRect(self.rect(), 10, 10)
        p.setPen(QColor(48, 54, 61))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        ml, mr, mt, mb = 8, 8, 8, 8
        gutter = 72 if self.width() > 210 else 0   # 0.5.1.0: Balken rechts (Bild 4)
        x0 = ml
        plot_w = self.width() - ml - mr - gutter
        top = mt
        bottom = self.height() - mb
        h = bottom - top
        if plot_w <= 2 or h <= 2:
            return

        y_ped = lambda v: bottom - v * h                    # Pedale 0..1 von unten
        mid = top + h / 2.0
        y_str = lambda v: mid - v * (h / 2.0) * 0.9          # Lenkung -1..1 um die Mitte

        # Mittellinie (Lenkung = 0)
        p.setPen(QPen(QColor(70, 78, 88), 1, Qt.DashLine))
        p.drawLine(int(x0), int(mid), int(x0 + plot_w), int(mid))

        # Gas: Flaeche + Linie
        shift_px = self._scroll_shift_px(plot_w)  # 0.5.9.26
        thr_path = self._path(self._thr, x0, plot_w, y_ped, shift_px)
        if not thr_path.isEmpty():
            first_x = x0 + (self.HISTORY - len(self._thr)) * self._step(plot_w) - shift_px
            fill = QPainterPath(thr_path)
            fill.lineTo(x0 + plot_w, bottom)
            fill.lineTo(first_x, bottom)
            fill.closeSubpath()
            fc = QColor(self._col_thr); fc.setAlpha(55)
            p.setPen(Qt.NoPen); p.setBrush(fc); p.drawPath(fill)
            p.setPen(QPen(self._col_thr, 2)); p.setBrush(Qt.NoBrush); p.drawPath(thr_path)

        # Bremse: Linie
        brk_path = self._path(self._brk, x0, plot_w, y_ped, shift_px)
        if not brk_path.isEmpty():
            p.setPen(QPen(self._col_brk, 2)); p.setBrush(Qt.NoBrush); p.drawPath(brk_path)

        # Lenkung: Linie um die Mitte
        str_path = self._path(self._str, x0, plot_w, y_str, shift_px)
        if not str_path.isEmpty():
            p.setPen(QPen(self._col_str, 1.6)); p.setBrush(Qt.NoBrush); p.drawPath(str_path)

        # Mini-Legende
        f = QFont("Segoe UI", 7, QFont.DemiBold)
        p.setFont(f)
        lx = x0 + 2
        for label, col in (("GAS", self._col_thr), ("BREMSE", self._col_brk), ("LENK", self._col_str)):
            p.setPen(col)
            p.drawText(int(lx), int(top + 8), label)
            lx += p.fontMetrics().horizontalAdvance(label) + 10

        # 0.5.1.0: rechte Balken - Bremse / Gang / Gas (Bild 4)
        if gutter > 0:
            cur_thr = self._thr[-1] if self._thr else 0.0
            cur_brk = self._brk[-1] if self._brk else 0.0
            gw = 12
            gx = x0 + plot_w + 10
            def _vbar(bx, frac, col, cap):
                p.setPen(Qt.NoPen); p.setBrush(QColor(52, 58, 66))
                p.drawRoundedRect(QRectF(bx, top, gw, h), 3, 3)
                fh = max(0.0, min(1.0, frac)) * h
                p.setBrush(col); p.drawRoundedRect(QRectF(bx, bottom - fh, gw, fh), 3, 3)
                fc = QFont("Segoe UI", 7, QFont.DemiBold); p.setFont(fc); p.setPen(self._muted())
                p.drawText(QRectF(bx - 6, top - 12, gw + 12, 11), Qt.AlignCenter, cap)
            _vbar(gx, cur_brk, self._col_brk, str(int(round(cur_brk * 100))))
            gearx = gx + gw + 8
            p.setFont(QFont("Segoe UI", 15, QFont.Bold)); p.setPen(self._fg())
            gtxt = str(self._gear) if self._gear > 0 else ("N" if self._gear == 0 else "R")
            p.drawText(QRectF(gearx - 3, mid - 13, 24, 26), Qt.AlignCenter, gtxt)
            p.setFont(QFont("Segoe UI", 7, QFont.DemiBold)); p.setPen(self._muted())
            p.drawText(QRectF(gearx - 6, top - 12, 30, 11), Qt.AlignCenter, "GANG")
            _vbar(gearx + 22, cur_thr, self._col_thr, str(int(round(cur_thr * 100))))
        if not self._live:
            p.setPen(QColor("#ff5a1f")); p.setFont(f)
            p.drawText(self.rect().adjusted(0, 2, -6, 0), Qt.AlignRight | Qt.AlignTop, "warte auf Daten")


class SettingsWindow(QWidget):
    """0.5.4.0: Einstellungen in eigenem Fenster - App-Konfiguration, aus dem
    frueher ueberladenen 'Mehr'-Menue herausgeloest."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWindowTitle("Einstellungen – PitBoss")
        self.resize(430, 300)
        lay = QVBoxLayout(self)
        title = QLabel("App-Einstellungen")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        lay.addWidget(title)

        def row(text, slot, tip=""):
            b = QPushButton(text)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(slot)
            lay.addWidget(b)
            return b

        row("Design: Hell / Dunkel umschalten", self.main.toggle_theme)
        row("System-Log ein- / ausblenden", self.main.toggle_log)
        lay.addSpacing(10)
        row("Bremsmodell kalibrieren …", self.main.calibrate_brake_model,
            "Schwellwerte des Bremsmodells an echten Daten nachziehen.")
        row("Nach Updates suchen …", self.main._check_updates)
        lay.addStretch(1)
        hint = QLabel("Overlay-Design (transparent / dunkel / hell) liegt weiterhin im Overlays-Menü.")
        hint.setWordWrap(True); hint.setStyleSheet("color:#8a97a8;")
        lay.addWidget(hint)
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.close)
        lay.addWidget(btn_close)


class SetupAdvisor:
    """0.5.9.0: liest die getPlayerGarage-Map und erzeugt KONKRETE Setup-Hinweise.
    Zwei Quellen: (a) datengetrieben aus den gemessenen Reifen-Temperaturzonen /
    Achsbalance (verknuepft mit den ECHTEN aktuellen Setup-Werten), (b) symptom-
    basiert (Fahrer waehlt ein Fahrverhalten, bekommt konkrete Parameter + Richtung
    mit aktuellem Wert). Rein lesend - aendert NIE das Setup im Spiel."""

    # Rad-Suffixe: Coach VL/VR/HL/HR  <->  Garage FL/FR/RL/RR
    WHEELS = [("VL", "FL"), ("VR", "FR"), ("HL", "RL"), ("HR", "RR")]
    NOTADJ = {"N/V", "N/A", "NON-ADJUSTABLE", "FIXED", "ABMONTIERT", ""}

    # Gruppierte, lesbare Namen der wichtigsten Einzel-Parameter
    GROUPS = [
        ("Fahrhilfen", [
            ("VM_ANTILOCKBRAKESYSTEMMAP", "ABS-Kennfeld"),
            ("VM_TRACTIONCONTROLMAP", "Traktionskontrolle (TC)"),
            ("VM_TRACTIONCONTROLPOWERCUTMAP", "TC Power-Cut"),
            ("VM_TRACTIONCONTROLSLIPANGLEMAP", "TC Schlupfwinkel"),
            ("VM_ENGINE_MIXTURE", "Motor-Gemisch"),
        ]),
        ("Bremsen", [
            ("VM_BRAKE_BALANCE", "Bremsbalance"),
            ("VM_BRAKE_PRESSURE", "Bremsdruck"),
            ("VM_BRAKE_MIGRATION", "Brake Migration"),
            ("VM_BRAKE_DUCTS", "Bremskuehlung vorn"),
            ("VM_BRAKE_DUCTS_REAR", "Bremskuehlung hinten"),
        ]),
        ("Aerodynamik", [
            ("VM_FRONT_WING", "Frontfluegel"),
            ("VM_REAR_WING", "Heckfluegel"),
        ]),
        ("Fahrwerk / Balance", [
            ("VM_FRONT_ANTISWAY", "Stabilisator vorn"),
            ("VM_REAR_ANTISWAY", "Stabilisator hinten"),
            ("VM_DIFF_PRELOAD", "Diff-Vorspannung"),
        ]),
        ("Ausrichtung", [
            ("VM_FRONT_TOEIN", "Vorspur vorn"),
            ("VM_REAR_TOEIN", "Vorspur hinten"),
            ("VM_STEER_LOCK", "Lenkeinschlag"),
        ]),
        ("Kuehlung / Energie", [
            ("VM_OIL_RADIATOR", "Oelkuehler"),
            ("VM_WATER_RADIATOR", "Wasserkuehler"),
            ("VM_FUEL_LEVEL", "Tankfuellung"),
            ("VM_VIRTUAL_ENERGY", "Virtuelle Energie"),
        ]),
    ]
    # Pro-Rad-Parameter (Suffix -W_FL etc.)
    WHEEL_GROUPS = [
        ("WM_PRESSURE", "Reifendruck", "kPa"),
        ("WM_CAMBER", "Sturz", ""),
        ("WM_SPRING", "Feder", ""),
        ("WM_RIDEHEIGHT", "Fahrhoehe", ""),
        ("WM_SLOWBUMP", "Daempfer Druck langsam", ""),
        ("WM_FASTBUMP", "Daempfer Druck schnell", ""),
        ("WM_SLOWREBOUND", "Daempfer Zug langsam", ""),
        ("WM_FASTREBOUND", "Daempfer Zug schnell", ""),
    ]

    @staticmethod
    def _p(garage, key):
        v = garage.get(key)
        return v if isinstance(v, dict) else None

    @classmethod
    def _adjustable(cls, p):
        if not p or not p.get("available", False):
            return False
        try:
            if int(p.get("minValue", 0)) >= int(p.get("maxValue", 0)):
                return False
        except Exception:
            return False
        return str(p.get("stringValue", "")).strip().upper() not in cls.NOTADJ

    @classmethod
    def _cur(cls, garage, key):
        """aktueller lesbarer Wert oder None wenn nicht vorhanden/nicht einstellbar."""
        p = cls._p(garage, key)
        if not cls._adjustable(p):
            return None
        return str(p.get("stringValue", "")).strip()

    @classmethod
    def _changed(cls, p):
        return (str(p.get("stringValue", "")).strip()
                != str(p.get("lastSavedStringValue", "")).strip())

    # ---------- Setup-Uebersicht ----------
    @classmethod
    def overview_lines(cls, garage):
        if not garage:
            return ["Kein Setup geladen. LMU offen? Sonst 'Setup aus Datei laden'."]
        out = []
        for gname, keys in cls.GROUPS:
            rows = []
            for key, label in keys:
                p = cls._p(garage, key)
                if not cls._adjustable(p):
                    continue
                mark = "  *geaendert*" if cls._changed(p) else ""
                rows.append(f"   {label}: {str(p.get('stringValue','')).strip()}{mark}")
            if rows:
                out.append(f"[{gname}]")
                out.extend(rows)
                out.append("")
        # Pro-Rad-Block
        wheel_rows = []
        for key, label, unit in cls.WHEEL_GROUPS:
            vals = []
            any_adj = False
            for _c, suf in cls.WHEELS:
                p = cls._p(garage, f"{key}-W_{suf}")
                if cls._adjustable(p):
                    any_adj = True
                    vals.append(str(p.get("stringValue", "")).strip())
                else:
                    vals.append("—")
            if any_adj:
                wheel_rows.append(f"   {label}: FL {vals[0]} · FR {vals[1]} · RL {vals[2]} · RR {vals[3]}")
        if wheel_rows:
            out.append("[Pro Rad  (FL · FR · RL · RR)]")
            out.extend(wheel_rows)
        return out or ["Keine einstellbaren Parameter im Setup gefunden."]

    # ---------- datengetriebene Hinweise ----------
    @classmethod
    def data_advice_lines(cls, garage, stats):
        """Verknuepft gemessene Reifen-Temperaturzonen/Balance mit echten Werten."""
        out = []
        if not stats:
            return ["Noch keine Reifen-Telemetrie. Recording starten und 5–10 Runden fahren."]
        have_setup = bool(garage)

        # 1) Reifendruck je Rad aus Mitte-vs-Schulter
        press_hits = []
        for cname, suf in cls.WHEELS:
            v = stats.get(cname)
            if not v:
                continue
            mid = v.get("mid", 0.0); out_t = v.get("out", 0.0); in_t = v.get("in", 0.0)
            shoulders = [x for x in (out_t, in_t) if x]
            if not shoulders or not mid:
                continue
            cur = cls._cur(garage, f"WM_PRESSURE-W_{suf}") if have_setup else None
            curtxt = f" (aktuell {cur})" if cur else ""
            if mid > max(shoulders) + 6:
                press_hits.append(f"   {cname}: Mitte {mid-max(shoulders):.0f}°C waermer als Schultern → Druck zu HOCH{curtxt}. In kleinen Schritten senken (~2–4 kPa).")
            elif mid + 6 < min(shoulders):
                press_hits.append(f"   {cname}: Mitte {min(shoulders)-mid:.0f}°C kuehler als Schultern → Druck zu NIEDRIG{curtxt}. In kleinen Schritten erhoehen (~2–4 kPa).")
        if press_hits:
            out.append("Reifendruck (aus Temperatur-Profil):")
            out.extend(press_hits); out.append("")

        # 2) Sturz je Achse aus Innen-vs-Aussen (konservativ, kurvenabhaengig)
        def axle_camber(side_c, suf, achse):
            v = stats.get(side_c)
            if not v:
                return None
            sp = v.get("spread", 0.0)  # >0 = innen waermer
            cur = cls._cur(garage, f"WM_CAMBER-W_{suf}") if have_setup else None
            curtxt = f" (aktuell {cur})" if cur else ""
            if sp > 10:
                return f"   {achse}: Innenschulter deutlich waermer{curtxt} → tendenziell zu viel negativer Sturz. Etwas WENIGER negativ testen."
            if sp < -10:
                return f"   {achse}: Aussenschulter deutlich waermer{curtxt} → wenig Sturzabstuetzung. Etwas MEHR negativ testen."
            return None
        cam = [x for x in (axle_camber("VL", "FL", "Vorn links"),
                           axle_camber("VR", "FR", "Vorn rechts"),
                           axle_camber("HL", "RL", "Hinten links"),
                           axle_camber("HR", "RR", "Hinten rechts")) if x]
        if cam:
            out.append("Sturz (aus Schulter-Temperaturen, ueber mehrere Runden pruefen):")
            out.extend(cam); out.append("")

        # 3) Achsbalance aus Temperatur/Verschleiss
        try:
            ft = (stats["VL"]["temp_avg"] + stats["VR"]["temp_avg"]) / 2.0
            rt = (stats["HL"]["temp_avg"] + stats["HR"]["temp_avg"]) / 2.0
            fw = (stats["VL"]["wear"] + stats["VR"]["wear"]) / 2.0
            rw = (stats["HL"]["wear"] + stats["HR"]["wear"]) / 2.0
        except Exception:
            ft = rt = fw = rw = None
        if ft is not None:
            farb = cls._cur(garage, "VM_FRONT_ANTISWAY")
            rarb = cls._cur(garage, "VM_REAR_ANTISWAY")
            rwing = cls._cur(garage, "VM_REAR_WING")
            arbtxt = ""
            if farb or rarb:
                arbtxt = f" [Stabi vorn {farb or '—'}, hinten {rarb or '—'}]"
            if ft - rt > 8 or rw - fw > 4:
                out.append("Balance: Vorderachse ueberlastet → Untersteuer-Tendenz." + arbtxt)
                out.append("   Konkret: Stabi vorn WEICHER oder Stabi hinten HAERTER; ggf. mehr Front-Grip (Sturz/Druck vorn)." )
                if rwing:
                    out.append(f"   Heckfluegel steht auf {rwing} — nur wenn Topspeed reicht, minimal flacher fuer mehr Front-Anteil.")
                out.append("")
            elif rt - ft > 8 or fw - rw > 4:
                out.append("Balance: Hinterachse ueberlastet → Uebersteuer-/Traktions-Tendenz." + arbtxt)
                out.append("   Konkret: Stabi hinten WEICHER; Diff-Vorspannung pruefen; Gasannahme sanfter.")
                if rwing:
                    out.append(f"   Heckfluegel {rwing} — bei Instabilitaet am Ausgang etwas steiler.")
                out.append("")
            else:
                out.append("Balance: Vorder-/Hinterachse relativ ausgeglichen.\n")

        if not have_setup:
            out.append("Hinweis: Kein Live-Setup geladen — Werte in Klammern fehlen. LMU-API/Datei laden fuer exakte Ausgangswerte.")
        out.append("Immer nur EINE Aenderung pro Test, dann 5–8 gleiche Runden.")
        return out

    # ---------- symptombasierte Hinweise ----------
    SYMPTOMS = [
        "Untersteuern beim Einlenken",
        "Untersteuern am Kurvenausgang",
        "Uebersteuern beim Einlenken",
        "Uebersteuern am Kurvenausgang",
        "Vorne blockiert beim Bremsen",
        "Hinten instabil beim Bremsen",
        "Schlechte Traktion am Ausgang",
        "Nervoes / instabil auf Geraden",
    ]

    @classmethod
    def symptom_lines(cls, garage, symptom):
        g = garage or {}
        def cur(key):
            c = cls._cur(g, key)
            return f" (aktuell {c})" if c else ""
        L = []
        if symptom == "Untersteuern beim Einlenken":
            L = [f"• Stabilisator vorn WEICHER{cur('VM_FRONT_ANTISWAY')}",
                 f"• Sturz vorn etwas negativer{cur('WM_CAMBER-W_FL')}",
                 f"• Bremsbalance minimal nach HINTEN{cur('VM_BRAKE_BALANCE')} (mehr Einlenken beim Trail-Braking)",
                 f"• Vorspur vorn Richtung 0{cur('VM_FRONT_TOEIN')}",
                 "• Fahr-Check: nicht zu schnell rein / zu viel Lenkwinkel"]
        elif symptom == "Untersteuern am Kurvenausgang":
            L = [f"• Diff-Vorspannung REDUZIEREN{cur('VM_DIFF_PRELOAD')}",
                 f"• Stabilisator hinten WEICHER{cur('VM_REAR_ANTISWAY')}",
                 f"• TC etwas geringer{cur('VM_TRACTIONCONTROLMAP')} (falls TC zu frueh eingreift)",
                 "• Fahr-Check: Gas geduldiger aufmachen"]
        elif symptom == "Uebersteuern beim Einlenken":
            L = [f"• Stabilisator vorn HAERTER{cur('VM_FRONT_ANTISWAY')} oder hinten weicher{cur('VM_REAR_ANTISWAY')}",
                 f"• Bremsbalance nach VORN{cur('VM_BRAKE_BALANCE')}",
                 f"• Heckfluegel mehr{cur('VM_REAR_WING')}",
                 f"• Vorspur hinten mehr (Stabilitaet){cur('VM_REAR_TOEIN')}"]
        elif symptom == "Uebersteuern am Kurvenausgang":
            L = [f"• Heckfluegel STEILER{cur('VM_REAR_WING')}",
                 f"• Diff-Vorspannung reduzieren{cur('VM_DIFF_PRELOAD')}",
                 f"• TC erhoehen{cur('VM_TRACTIONCONTROLMAP')}",
                 f"• Stabilisator hinten WEICHER{cur('VM_REAR_ANTISWAY')}",
                 "• Fahr-Check: Gas sanfter, spaeter voll"]
        elif symptom == "Vorne blockiert beim Bremsen":
            L = [f"• Bremsbalance nach HINTEN{cur('VM_BRAKE_BALANCE')}",
                 f"• Bremsdruck senken{cur('VM_BRAKE_PRESSURE')}",
                 f"• ABS-Kennfeld erhoehen{cur('VM_ANTILOCKBRAKESYSTEMMAP')} (falls ABS-Auto)",
                 "• Fahr-Check: Bremsdruck weicher anlegen"]
        elif symptom == "Hinten instabil beim Bremsen":
            L = [f"• Bremsbalance nach VORN{cur('VM_BRAKE_BALANCE')}",
                 f"• Brake Migration pruefen{cur('VM_BRAKE_MIGRATION')}",
                 f"• Stabilisator hinten WEICHER{cur('VM_REAR_ANTISWAY')}",
                 "• Fahr-Check: gerade bremsen, spaeter einlenken"]
        elif symptom == "Schlechte Traktion am Ausgang":
            L = [f"• Diff-Vorspannung reduzieren{cur('VM_DIFF_PRELOAD')}",
                 f"• Reifendruck hinten leicht senken{cur('WM_PRESSURE-W_RL')} (mehr Kontaktflaeche)",
                 f"• Stabilisator hinten WEICHER{cur('VM_REAR_ANTISWAY')}",
                 f"• TC erhoehen{cur('VM_TRACTIONCONTROLMAP')}"]
        elif symptom == "Nervoes / instabil auf Geraden":
            L = [f"• Heckfluegel mehr{cur('VM_REAR_WING')}",
                 f"• Vorspur hinten mehr{cur('VM_REAR_TOEIN')}",
                 f"• Fahrhoehe hinten pruefen{cur('WM_RIDEHEIGHT-W_RL')}",
                 "• Fahr-Check: Boeen/Randstein/Windschatten ausschliessen"]
        if not L:
            return ["Kein Hinweis hinterlegt."]
        if not garage:
            L.append("")
            L.append("(Aktuelle Werte fehlen — Live-Setup laden fuer exakte Ausgangspunkte.)")
        return L


# ---------------------------------------------------------------------------
# 0.5.9.8: .svm-Setup-Reader.
# In LMU MANUELL gespeicherte Setups sind .svm (rFactor2/LMU-Format), NICHT
# JSON. Aufbau ist INI-artig:  [SEKTION]  gefolgt von Zeilen der Form
#     Param=Index//Anzeigewert     (z.B.  PressureSetting=41//138 kPa)
# Wir parsen tolerant, ziehen den Anzeigewert aus dem //-Kommentar und bilden
# die bekannten Parameter auf die getPlayerGarage-Schluessel ab, die der
# SetupAdvisor nutzt (VM_* / WM_*-W_*). So laeuft der komplette Advisor
# UNVERAENDERT auch mit einer .svm-Datei. Unbekannte Parameter gehen nicht
# verloren -> Rohdump + Abdeckungs-Diagnose im Fenster. Best-effort-Mapping;
# mit einer echten LMU-.svm laesst sich das Mapping exakt nachziehen.
# ---------------------------------------------------------------------------

# Ecken-Sektion -> Radsuffix (beide Schreibweisen)
_SVM_WHEEL_SECTIONS = {
    "LEFTFRONT": "FL", "FRONTLEFT": "FL",
    "RIGHTFRONT": "FR", "FRONTRIGHT": "FR",
    "LEFTREAR": "RL", "REARLEFT": "RL",
    "RIGHTREAR": "RR", "REARRIGHT": "RR",
}

# Pro-Rad-Parameter (in den Ecken-Sektionen) -> WM_-Basis des Coaches
_SVM_WHEEL_PARAMS = {
    "PRESSURE": "WM_PRESSURE",
    "CAMBER": "WM_CAMBER",
    "SPRING": "WM_SPRING",
    "SPRINGMOVER": "WM_SPRING",
    "RIDEHEIGHT": "WM_RIDEHEIGHT",
    "SLOWBUMP": "WM_SLOWBUMP",
    "FASTBUMP": "WM_FASTBUMP",
    "SLOWREBOUND": "WM_SLOWREBOUND",
    "FASTREBOUND": "WM_FASTREBOUND",
}

# Globale Parameter (Sektion egal) -> VM_-Schluessel des Coaches
_SVM_GLOBAL_PARAMS = {
    "BRAKEBIAS": "VM_BRAKE_BALANCE",
    "BRAKEBALANCE": "VM_BRAKE_BALANCE",
    "FRONTBRAKEBIAS": "VM_BRAKE_BALANCE",
    "BRAKEPRESSURE": "VM_BRAKE_PRESSURE",
    "BRAKEMIGRATION": "VM_BRAKE_MIGRATION",
    "REARBRAKE": "VM_BRAKE_BALANCE",       # LMU-.svm: RearBrakeSetting = Bremsbalance (front:rear)
    "BRAKEDUCT": "VM_BRAKE_DUCTS",
    "FRONTBRAKEDUCT": "VM_BRAKE_DUCTS",
    "REARBRAKEDUCT": "VM_BRAKE_DUCTS_REAR",
    "BRAKEDUCTREAR": "VM_BRAKE_DUCTS_REAR",  # LMU-.svm: BrakeDuctRearSetting
    "FW": "VM_FRONT_WING",
    "FRONTWING": "VM_FRONT_WING",
    "RW": "VM_REAR_WING",
    "REARWING": "VM_REAR_WING",
    "FRONTANTISWAY": "VM_FRONT_ANTISWAY",
    "FRONTARB": "VM_FRONT_ANTISWAY",
    "REARANTISWAY": "VM_REAR_ANTISWAY",
    "REARARB": "VM_REAR_ANTISWAY",
    "PRELOAD": "VM_DIFF_PRELOAD",
    "DIFFPRELOAD": "VM_DIFF_PRELOAD",
    "FRONTTOEIN": "VM_FRONT_TOEIN",
    "REARTOEIN": "VM_REAR_TOEIN",
    "STEERLOCK": "VM_STEER_LOCK",
    "STEERINGLOCK": "VM_STEER_LOCK",
    "FUEL": "VM_FUEL_LEVEL",
    "VIRTUALENERGY": "VM_VIRTUAL_ENERGY",
    # WICHTIG: die *Map*-Setting ist die STUFE; TCSetting/ABSSetting sind nur
    # Verfuegbarkeits-Flags ("Available") und werden bewusst NICHT gemappt.
    "TRACTIONCONTROLMAP": "VM_TRACTIONCONTROLMAP",
    "TRACTIONCONTROL": "VM_TRACTIONCONTROLMAP",
    "TCPOWERCUTMAP": "VM_TRACTIONCONTROLPOWERCUTMAP",
    "TRACTIONCONTROLPOWERCUT": "VM_TRACTIONCONTROLPOWERCUTMAP",
    "TCSLIPANGLEMAP": "VM_TRACTIONCONTROLSLIPANGLEMAP",
    "TRACTIONCONTROLSLIPANGLE": "VM_TRACTIONCONTROLSLIPANGLEMAP",
    "ANTILOCKBRAKESYSTEMMAP": "VM_ANTILOCKBRAKESYSTEMMAP",
    "ANTILOCKBRAKES": "VM_ANTILOCKBRAKESYSTEMMAP",
    "ENGINEMIXTURE": "VM_ENGINE_MIXTURE",
    "MIXTURE": "VM_ENGINE_MIXTURE",
    "OILRADIATOR": "VM_OIL_RADIATOR",
    "WATERRADIATOR": "VM_WATER_RADIATOR",
}

# Toe ist in .svm pro Ecke -> auf die Achs-Schluessel des Coaches abbilden
# (nur linke Ecke fuellt den Achswert, reicht fuer die "aktuell X"-Anzeige)
_SVM_TOE_AXLE = {"FL": "VM_FRONT_TOEIN", "RL": "VM_REAR_TOEIN"}


def _svm_norm(tok):
    return "".join(ch for ch in tok.upper() if ch.isalnum())


def _svm_strip_setting(name):
    n = _svm_norm(name)
    if n.endswith("SETTING"):
        n = n[:-7]
    return n


def _svm_split_value(rhs):
    """rhs = 'Index//Anzeige' | 'Index' | 'Anzeige' -> (index_str, anzeige)."""
    rhs = rhs.strip()
    if "//" in rhs:
        idx, disp = rhs.split("//", 1)
        idx = idx.strip(); disp = disp.strip()
        return idx, (disp or idx)
    return rhs, rhs


def _svm_param(index_str, display):
    """Erzeugt einen getPlayerGarage-kompatiblen Parameter-dict.
    .svm IST der gespeicherte Stand -> stringValue == lastSavedStringValue.
    min/max nur so gesetzt, dass SetupAdvisor._adjustable() greift."""
    try:
        val = int(index_str)
    except Exception:
        try:
            val = float(index_str)
        except Exception:
            val = display
    return {
        "value": val,
        "stringValue": display,
        "lastSavedStringValue": display,
        "minValue": 0,
        "maxValue": 1000000,
        "available": True,
        "isFreeSetting": True,
    }


def parse_svm_setup(text):
    """Parst eine rF2/LMU-.svm (oder aehnliche INI-Setupdatei).
    Rueckgabe: (garage_dict, diag). garage_dict nutzt die getPlayerGarage-
    Schluessel des SetupAdvisors; diag enthaelt Zaehler + Rohliste aller Werte."""
    garage = {}
    raw = []          # (Sektion, Param, Anzeige, ziel_key_or_None)
    n_lines = 0
    n_mapped = 0
    section = ""
    cur_suf = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in (";", "#") or s.startswith("//"):
            continue
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1].strip()
            cur_suf = _SVM_WHEEL_SECTIONS.get(_svm_norm(section))
            continue
        if "=" not in s:
            continue
        name, rhs = s.split("=", 1)
        name = name.strip()
        index_str, display = _svm_split_value(rhs)
        n_lines += 1
        base = _svm_strip_setting(name)
        target = None
        if cur_suf and base in _SVM_WHEEL_PARAMS:                 # Pro-Rad
            target = f"{_SVM_WHEEL_PARAMS[base]}-W_{cur_suf}"
        elif cur_suf and base in ("TOEIN", "TOE") and cur_suf in _SVM_TOE_AXLE:
            target = _SVM_TOE_AXLE[cur_suf]                        # Toe pro Achse
        elif base in _SVM_GLOBAL_PARAMS:                          # global
            target = _SVM_GLOBAL_PARAMS[base]
        if target and target not in garage:
            garage[target] = _svm_param(index_str, display)
            n_mapped += 1
        raw.append((section, name, display, target))
    diag = {"type": "svm", "lines": n_lines, "mapped": n_mapped, "raw": raw}
    return garage, diag


SETUP_COACH_CONFIG_PATH = EXPORT_DIR / "setup_coach.json"  # 0.5.9.9: Auto-Laden (Ordner/letzte Datei)


def _drives():
    import string
    try:
        return [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]
    except Exception:
        return ["C:\\"]


def _steam_library_roots():
    """Alle Steam-Bibliothekspfade aus libraryfolders.vdf (auch auf anderen
    Laufwerken/SteamLibrary). So finden wir LMU egal wo es installiert ist."""
    import re
    roots = []
    for dr in _drives():
        for base in (r"Program Files (x86)\Steam", r"Program Files\Steam", "Steam"):
            vdf = os.path.join(dr, base, "steamapps", "libraryfolders.vdf")
            try:
                if os.path.isfile(vdf):
                    txt = open(vdf, encoding="utf-8", errors="replace").read()
                    for m in re.finditer(r'"path"\s*"([^"]+)"', txt):
                        roots.append(m.group(1).replace("\\\\", "\\"))
                    roots.append(os.path.join(dr, base))  # Steam-Root selbst
            except Exception:
                pass
    return roots


def _lmu_install_roots():
    """Le-Mans-Ultimate-Installationsordner: feste Kandidaten auf allen
    Laufwerken + alle Steam-Bibliotheken."""
    subs = [
        r"Program Files (x86)\Steam\steamapps\common\Le Mans Ultimate",
        r"Program Files\Steam\steamapps\common\Le Mans Ultimate",
        r"Steam\steamapps\common\Le Mans Ultimate",
        r"SteamLibrary\steamapps\common\Le Mans Ultimate",
        r"Games\Le Mans Ultimate",
        r"Le Mans Ultimate",
    ]
    roots = []
    for dr in _drives():
        for sub in subs:
            p = os.path.join(dr, sub)
            if os.path.isdir(p):
                roots.append(p)
    for lib in _steam_library_roots():
        p = os.path.join(lib, "steamapps", "common", "Le Mans Ultimate")
        if os.path.isdir(p):
            roots.append(p)
    out, seen = [], set()
    for r in roots:
        try:
            rp = os.path.realpath(r)
        except Exception:
            rp = r
        if rp not in seen:
            seen.add(rp)
            out.append(r)
    return out


def _lmu_settings_dirs():
    """LMU-Setup-Suchordner. WICHTIG: rF2/LMU legt .svm unter
    UserData\\<Profil>\\Settings\\<Strecke>\\ ab — der Profilordner heisst NICHT
    zwingend 'player'. Darum geben wir das komplette UserData (bzw. den
    Installationsordner) zurueck; die .svm-Suche laeuft rekursiv darueber."""
    out = []
    for r in _lmu_install_roots():
        ud = os.path.join(r, "UserData")
        out.append(ud if os.path.isdir(ud) else r)
    return out


def find_newest_svm(extra_dir=None, vehicle_hint=None):
    """Neueste .svm (nach Aenderungsdatum) aus extra_dir (falls gesetzt) + den
    automatisch gefundenen LMU-Setup-Ordnern. None, wenn nichts gefunden.

    0.5.9.14: vehicle_hint (aktueller Fahrzeugname aus der Telemetrie) grenzt
    die Kandidaten auf .svm-Dateien ein, deren Pfad/Dateiname zum Fahrzeug
    passt (LMU legt Setups je Auto in eigenen Unterordnern/Dateinamen ab, z.B.
    'SRA_992GT3R_...svm'). Ohne Filterung wurde sonst die zeitlich neueste .svm
    IRGENDEINES Autos gewaehlt — das erschien 'willkuerlich', wenn sie nicht
    zum aktuell gefahrenen Auto passte. Kein Treffer -> Fallback ungefiltert,
    damit nie schlechter als vorher."""
    roots = []
    if extra_dir and os.path.isdir(extra_dir):
        roots.append(extra_dir)
    roots += _lmu_settings_dirs()
    seen = set()
    all_files = []  # (mtime, path)
    for d in roots:
        try:
            rp = os.path.realpath(d)
        except Exception:
            rp = d
        if rp in seen:
            continue
        seen.add(rp)
        try:
            for p in Path(d).rglob("*.svm"):
                try:
                    m = p.stat().st_mtime
                except OSError:
                    continue
                all_files.append((m, str(p)))
        except Exception:
            continue
    if not all_files:
        return None

    def newest_of(files):
        return max(files, key=lambda t: t[0])[1] if files else None

    hint = normalize_match_text(vehicle_hint) if vehicle_hint else ""
    if hint:
        tokens = [t for t in hint.split(" ") if len(t) >= 3]
        if tokens:
            # NUR der Dateiname zaehlt (LMU kodiert das Auto dort, z.B.
            # 'SRA_992GT3R_...svm'); Ordnernamen (Profil/Strecke) koennen
            # zufaellig aehnliche Zahlen/Woerter enthalten und wuerden sonst
            # zu falschen Treffern fuehren.
            matched = [f for f in all_files
                       if any(t in normalize_match_text(os.path.basename(f[1])) for t in tokens)]
            if matched:
                return newest_of(matched)
    return newest_of(all_files)


def svm_search_summary(extra_dir=None):
    """0.5.9.11: Diagnose fuers Auto-Laden — wie viele Ordner durchsucht,
    wie viele .svm gefunden. Rueckgabe (anzahl_ordner, anzahl_svm)."""
    roots = []
    if extra_dir and os.path.isdir(extra_dir):
        roots.append(extra_dir)
    roots += _lmu_settings_dirs()
    seen = set()
    n = 0
    for d in roots:
        try:
            rp = os.path.realpath(d)
        except Exception:
            rp = d
        if rp in seen:
            continue
        seen.add(rp)
        try:
            n += sum(1 for _ in Path(d).rglob("*.svm"))
        except Exception:
            pass
    return len(seen), n


class SetupCoachWindow(QWidget):
    """0.5.9.0: Setup-Coach in EIGENEM Fenster. Zeigt (1) konkrete datengetriebene
    Hinweise (Reifen-Temperaturen/Balance x echtes Setup), (2) Symptom-Auswahl mit
    konkreten Parameter-Empfehlungen, (3) die aktuelle Setup-Uebersicht. Liest das
    Setup aus der LMU-REST-API (getPlayerGarage) oder aus einer Datei."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWindowTitle("Setup-Coach – PitBoss")
        self.resize(720, 720)
        self.setStyleSheet(LIGHT_QSS if getattr(main, "_theme", "dark") == "light" else DARK_QSS)
        self._file_garage = None  # optional aus Datei geladen
        self._file_diag = None    # 0.5.9.8: Diagnose der geladenen .svm
        self._file_name = None    # 0.5.9.8: Dateiname der Quelle
        self._file_source = None  # 0.5.9.9: 'manual' | 'auto' | None
        cfg = {}
        try:
            if SETUP_COACH_CONFIG_PATH.exists():
                cfg = json.loads(SETUP_COACH_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        self._setups_dir = cfg.get("setups_dir") or None   # 0.5.9.9: gemerkter Ordner
        self._last_file = cfg.get("last_file") or None      # 0.5.9.9: letzte Datei (Fallback)

        lay = QVBoxLayout(self)
        title = QLabel("Setup-Coach")
        title.setStyleSheet("font-size:17px; font-weight:700;")
        lay.addWidget(title)
        self.src_label = QLabel("")
        self.src_label.setWordWrap(True)
        self.src_label.setStyleSheet("color:#8a97a8;")
        lay.addWidget(self.src_label)

        btnrow = QHBoxLayout()
        self.btn_reload = QPushButton("Aktualisieren")
        self.btn_reload.setObjectName("primary")
        self.btn_reload.clicked.connect(self._manual_refresh)
        self.btn_file = QPushButton("Setup aus Datei laden …")
        self.btn_file.clicked.connect(self.load_from_file)
        btnrow.addWidget(self.btn_reload)
        btnrow.addWidget(self.btn_file)
        btnrow.addStretch(1)
        lay.addLayout(btnrow)

        btnrow2 = QHBoxLayout()
        self.btn_dir = QPushButton("LMU-Setup-Ordner …")
        self.btn_dir.setToolTip("Ordner mit deinen .svm-Setups (…\\UserData\\<Profil>\\Settings). "
                                "Wird gemerkt; die NEUESTE .svm wird automatisch geladen.")
        self.btn_dir.clicked.connect(self._choose_setups_dir)
        btnrow2.addWidget(self.btn_dir)
        btnrow2.addStretch(1)
        lay.addLayout(btnrow2)

        lay.addWidget(QLabel("Konkrete Hinweise (aus deinen Reifen-/Balance-Daten × aktuellem Setup):"))
        self.advice = QTextEdit(); self.advice.setReadOnly(True); self.advice.setMinimumHeight(200)
        lay.addWidget(self.advice)

        symrow = QHBoxLayout()
        symrow.addWidget(QLabel("Fahrverhalten:"))
        self.sym_combo = QComboBox()
        self.sym_combo.addItems(SetupAdvisor.SYMPTOMS)
        self.sym_combo.currentTextChanged.connect(self._on_symptom)
        symrow.addWidget(self.sym_combo, 1)
        lay.addLayout(symrow)
        self.sym_text = QTextEdit(); self.sym_text.setReadOnly(True); self.sym_text.setMaximumHeight(150)
        lay.addWidget(self.sym_text)

        lay.addWidget(QLabel("Aktuelles Setup (nur einstellbare Parameter, *geaendert* ggü. gespeichert):"))
        self.overview = QTextEdit(); self.overview.setReadOnly(True); self.overview.setMinimumHeight(160)
        lay.addWidget(self.overview)

        note = QLabel("Empfehlungen, keine automatische Setup-Änderung. Immer nur eine Änderung pro Test.")
        note.setWordWrap(True); note.setStyleSheet("color:#8a97a8;")
        lay.addWidget(note)
        btn_close = QPushButton("Schließen"); btn_close.clicked.connect(self.close)
        lay.addWidget(btn_close)

    def _garage(self):
        rest = getattr(self.main, "rest", None)
        if rest is not None and rest.has_garage():
            return dict(rest.garage)
        return self._file_garage or {}

    # ---------- 0.5.9.9: automatisches Laden ----------
    def _save_cfg(self):
        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            SETUP_COACH_CONFIG_PATH.write_text(
                json.dumps({"setups_dir": self._setups_dir, "last_file": self._last_file},
                           ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_setup_path(self, path, source):
        """Laedt EINE Datei (.svm oder getPlayerGarage-JSON) und setzt den Zustand.
        Rueckgabe (ok, fehlertext)."""
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            return False, f"Datei-Fehler: {e}"
        g = None
        diag = None
        if text.lstrip()[:1] in ("{", "["):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    g = {k: v for k, v in data.items()
                         if isinstance(v, dict) and "value" in v}
            except Exception:
                g = None
        if not g:
            try:
                g, diag = parse_svm_setup(text)
            except Exception as e:
                return False, f"Datei-Fehler (.svm): {e}"
        if not g:
            return False, "keine Setup-Parameter erkannt (weder getPlayerGarage-JSON noch .svm)"
        self._file_garage = g
        self._file_diag = diag
        self._file_name = path.replace("\\", "/").rsplit("/", 1)[-1]
        self._file_source = source
        return True, None

    def _current_vehicle_name(self):
        s = getattr(self.main, "last_live_sample", None) or \
            (self.main.samples[-1] if getattr(self.main, "samples", None) else None)
        return str(getattr(s, "vehicle_name", "") or "") if s is not None else ""

    def _auto_load(self):
        """Laedt automatisch die NEUESTE .svm des AKTUELL GEFAHRENEN Autos aus dem
        (gemerkten oder auto-gefundenen) LMU-Setup-Ordner; Fallback = zuletzt
        manuell geladene Datei."""
        newest = find_newest_svm(self._setups_dir, vehicle_hint=self._current_vehicle_name())
        if newest and self._load_setup_path(newest, "auto")[0]:
            return True
        if self._last_file and os.path.exists(self._last_file) \
                and self._load_setup_path(self._last_file, "auto")[0]:
            return True
        return False

    def _choose_setups_dir(self):
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(
            self, "LMU-Setup-Ordner wählen (…\\UserData\\player\\Settings)",
            self._setups_dir or "")
        if not d:
            return
        self._setups_dir = d
        self._save_cfg()
        self._file_source = None   # erzwingt frischen Auto-Load
        self._file_garage = None
        self.refresh()

    def _manual_refresh(self):
        """'Aktualisieren' erzwingt frische Prioritaet: live -> neueste .svm ->
        zuletzt geladene Datei (nicht an manuellem Zustand kleben bleiben).
        0.5.9.14: fragt getPlayerGarage zusaetzlich SOFORT synchron ab, statt
        bis zu POLL_S (12s) auf den Hintergrund-Thread zu warten — sonst wirkte
        es so, als wuerde 'Aktualisieren' ein falsches/altes Setup zeigen,
        obwohl live laengst verfuegbar war."""
        self._file_source = None
        rest = getattr(self.main, "rest", None)
        if rest is not None:
            try:
                rest.fetch_garage()
            except Exception:
                pass
        self.refresh()

    def refresh(self):
        rest = getattr(self.main, "rest", None)
        live = bool(rest is not None and rest.has_garage())
        # Auto-Laden, wenn KEIN Live-Setup und noch nichts / zuletzt automatisch geladen
        if not live and self._file_source in (None, "auto"):
            self._auto_load()
        diag = getattr(self, "_file_diag", None)
        if live:
            garage = dict(rest.garage)
            src = "Quelle: LMU-API (live, getPlayerGarage)"
        elif self._file_garage:
            garage = self._file_garage
            fname = getattr(self, "_file_name", None) or "Datei"
            tag = "automatisch" if self._file_source == "auto" else "manuell"
            live_hint = ""
            if rest is not None and not live:
                le = getattr(rest, "last_error", "") or ""
                if le:
                    live_hint = f" [LMU-API nicht live: {le}]"
                else:
                    live_hint = " [LMU-API meldet aktuell kein Setup — laeuft LMU? ggf. kurz warten/neu 'Aktualisieren'.]"
            if diag and diag.get("type") == "svm":
                src = (f"Quelle: {fname} ({tag} geladen, LMU-.svm, Momentaufnahme) — "
                       f"{diag.get('lines', 0)} Parameter gelesen, "
                       f"{diag.get('mapped', 0)} für Coach-Hinweise erkannt{live_hint}")
            else:
                src = f"Quelle: {fname} ({tag} geladen){live_hint}"
        else:
            garage = {}
            ndir, nsvm = svm_search_summary(self._setups_dir)
            if ndir == 0:
                diagtxt = " [kein LMU-Setup-Ordner automatisch gefunden — bitte 'LMU-Setup-Ordner …' setzen]"
            else:
                diagtxt = f" [durchsucht: {ndir} Ordner, {nsvm} .svm gefunden]"
            hint = "" if self._setups_dir else " — Tipp: einmal 'LMU-Setup-Ordner …' setzen."
            src = ("Quelle: — kein Setup gefunden. LMU offen lassen und 'Aktualisieren', "
                   "'Setup aus Datei laden', oder Ordner setzen." + hint + diagtxt)
        self.src_label.setText(src)
        stats = self.main.tire_stats_summary() if hasattr(self.main, "tire_stats_summary") else {}
        self.advice.setPlainText("\n".join(SetupAdvisor.data_advice_lines(garage, stats)))
        ov = SetupAdvisor.overview_lines(garage)
        if (not live) and self._file_garage and diag and diag.get("type") == "svm":
            ov = ov + self._svm_raw_block(diag)
        self.overview.setPlainText("\n".join(ov))
        self._on_symptom(self.sym_combo.currentText())

    def _svm_raw_block(self, diag):
        """0.5.9.8: haengt ALLE aus der .svm gelesenen Werte an die Uebersicht,
        markiert die, die in die Coach-Hinweise einfliessen. So sieht Marcel
        seine kompletten Setup-Werte, auch wenn (noch) nicht alles gemappt ist."""
        raw = diag.get("raw") or []
        if not raw:
            return []
        dead = {"N/A", "N/V", "NON-ADJUSTABLE", "FIXED", "DETACHED", "ABMONTIERT", ""}
        out = ["", "[Alle einstellbaren Werte aus der .svm-Datei]"]
        last_sec = object()
        shown = 0
        hidden = 0
        for sec, name, disp, tgt in raw:
            if str(disp).strip().upper() in dead:      # tote/nicht einstellbare Zeilen raus
                hidden += 1
                continue
            if sec != last_sec:
                out.append(f"  > {sec or 'Allgemein'}")
                last_sec = sec
            mark = "   <= Coach" if tgt else ""
            out.append(f"     {name}: {disp}{mark}")
            shown += 1
        out.append("")
        if hidden:
            out.append(f"({hidden} nicht einstellbare Zeilen (N/A / fixed) ausgeblendet.)")
        out.append("Markiert (<= Coach) = fliesst in die Hinweise ein.")
        return out

    def _on_symptom(self, symptom):
        self.sym_text.setPlainText("\n".join(SetupAdvisor.symptom_lines(self._garage(), symptom)))

    def load_from_file(self):
        """0.5.9.8/9: laedt manuell eine .svm (rF2/LMU) ODER einen getPlayerGarage-
        JSON/-txt-Dump. Format wird automatisch erkannt; Datei wird gemerkt."""
        from PySide6.QtWidgets import QFileDialog
        start = self._setups_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Setup laden (LMU .svm oder getPlayerGarage .json/.txt)", start,
            "LMU-Setup / getPlayerGarage (*.svm *.json *.txt);;Alle Dateien (*.*)")
        if not path:
            return
        ok, err = self._load_setup_path(path, "manual")
        if not ok:
            self.src_label.setText(f"Datei-Fehler: {err}")
            return
        self._last_file = path
        # Ordner der gewaehlten Datei als Setup-Ordner merken (fuer kuenftiges Auto-Laden)
        if not self._setups_dir:
            self._setups_dir = os.path.dirname(path)
        self._save_cfg()
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()


class GeminiWindow(QWidget):
    """Eigenes Fenster fuer die KI-Analyse (Gemini). Modell fest: GEMINI_MODEL."""
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWindowTitle("KI-Analyse (Gemini)")
        self.resize(760, 640)
        self.setStyleSheet(LIGHT_QSS if getattr(main, "_theme", "dark") == "light" else DARK_QSS)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Google Gemini  ·  Modell: {GEMINI_MODEL}"))
        # 0.5.9.25: Report-Auswahl — Live-Session ODER ein beliebiger gespeicherter Report
        report_row = QHBoxLayout()
        report_row.addWidget(QLabel("Report:"))
        self.report_combo = QComboBox()
        self.report_combo.setMinimumWidth(320)
        report_row.addWidget(self.report_combo, stretch=1)
        self.btn_report_refresh = QPushButton("Aktualisieren")
        self.btn_report_refresh.setToolTip("Liste der gespeicherten Reports neu einlesen.")
        report_row.addWidget(self.btn_report_refresh)
        self.btn_report_browse = QPushButton("Datei wählen…")
        self.btn_report_browse.setToolTip("Report-Datei von einem anderen Ort laden.")
        report_row.addWidget(self.btn_report_browse)
        lay.addLayout(report_row)
        self.btn_report_refresh.clicked.connect(self.refresh_report_list)
        self.btn_report_browse.clicked.connect(self.browse_report_file)
        row = QHBoxLayout()
        row.addWidget(QLabel("API-Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Google-AI-Studio API-Key (lokal gespeichert, nie im Code)")
        row.addWidget(self.key_edit, stretch=1)
        self.btn_save = QPushButton("Key speichern")
        row.addWidget(self.btn_save)
        lay.addLayout(row)
        btnrow = QHBoxLayout()
        self.btn_analyze = QPushButton("Report analysieren")
        self.btn_analyze.setObjectName("primary")  # 0.4.8.0 Akzent-Primaerbutton
        btnrow.addWidget(self.btn_analyze)
        btnrow.addStretch(1)
        lay.addLayout(btnrow)
        # 0.4.7.2: Offline-Sprachausgabe (SAPI, sonst PowerShell System.Speech)
        tts_row = QHBoxLayout()
        tts_row.addWidget(QLabel("Stimme:"))
        self.voice_combo = QComboBox()
        _voices = self.main.tts.list_voices()
        self.voice_combo.addItems(_voices if _voices else ["(keine)"])
        if self.main.tts.voice_name and self.main.tts.voice_name in _voices:
            self.voice_combo.setCurrentText(self.main.tts.voice_name)
        tts_row.addWidget(self.voice_combo, 1)
        tts_row.addWidget(QLabel("Tempo:"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-10, 10)
        self.rate_spin.setValue(self.main.tts.rate)
        tts_row.addWidget(self.rate_spin)
        self.btn_tts_test = QPushButton("\U0001F50A Testtext")
        self.btn_tts_read = QPushButton("Analyse vorlesen")
        self.btn_tts_stop = QPushButton("Stop")
        tts_row.addWidget(self.btn_tts_test)
        tts_row.addWidget(self.btn_tts_read)
        tts_row.addWidget(self.btn_tts_stop)
        self.btn_tts_piper = QPushButton("Nat\u00fcrliche Stimme (Piper)\u2026")  # 0.4.7.3
        tts_row.addWidget(self.btn_tts_piper)
        lay.addLayout(tts_row)
        self.btn_tts_test.clicked.connect(self._tts_test)
        self.btn_tts_read.clicked.connect(self._tts_read_output)
        self.btn_tts_stop.clicked.connect(lambda: self.main.tts.stop())
        self.btn_tts_piper.clicked.connect(self._tts_setup_piper)
        self.voice_combo.currentTextChanged.connect(self._tts_voice_changed)
        self.rate_spin.valueChanged.connect(self.main.tts.set_rate)
        self.chk_autoread = QCheckBox("Analyse automatisch vorlesen")  # 0.4.7.4
        self.chk_autoread.setChecked(self.main.tts.auto_read)
        self.chk_autoread.toggled.connect(self.main.tts.set_auto_read)
        lay.addWidget(self.chk_autoread)
        if not self.main.tts.is_available():
            for _w in (self.voice_combo, self.rate_spin, self.btn_tts_test, self.btn_tts_read, self.btn_tts_stop, self.chk_autoread):
                _w.setEnabled(False)
        self.status = QLabel("")
        self.status.setStyleSheet("color:#8b97a8;")
        lay.addWidget(self.status)
        # 0.4.7.1: KI-Kontingent-Uebersicht + Warnungen (80/90/95 %)
        self.quota_panel = QuotaPanel(self.main.quota_tracker)
        lay.addWidget(self.quota_panel)
        self.main.quota_tracker.threshold_reached.connect(self._on_quota_threshold)
        self.main.quota_tracker.rate_limited.connect(self._on_quota_rate_limited)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("font-size:14px; line-height:1.4;")
        lay.addWidget(self.output, stretch=1)
        self.btn_save.clicked.connect(self.save_key)
        self.btn_analyze.clicked.connect(self.analyze)
        key = getattr(main, "gemini_api_key", "") or ""
        self.key_edit.setText(key)
        self.status.setText("API-Key geladen." if key else "Kein API-Key gespeichert.")
        self.refresh_report_list()  # 0.5.9.25: erst nach self.status befuellen

    def save_key(self):
        key = self.key_edit.text().strip()
        self.main.gemini_api_key = key
        try:
            GEMINI_CONFIG_PATH.write_text(json.dumps({"api_key": key, "model": GEMINI_MODEL}, indent=2), encoding="utf-8")
            self.status.setText("Gespeichert (lokal in exports/gemini_config.json).")
        except Exception as e:
            self.status.setText(f"Speichern fehlgeschlagen: {e}")

    def refresh_report_list(self):  # 0.5.9.25
        current_path = self.report_combo.currentData() if self.report_combo.count() else None
        self.report_combo.blockSignals(True)
        self.report_combo.clear()
        self.report_combo.addItem("Aktuelle Session (Live)", None)
        try:
            files = sorted(REPORT_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            files = []
        for f in files:
            self.report_combo.addItem(f.name, str(f))
        # zuvor gewaehlte Datei nach Refresh wieder anwaehlen, falls noch vorhanden
        if current_path:
            idx = self.report_combo.findData(current_path)
            if idx >= 0:
                self.report_combo.setCurrentIndex(idx)
        self.report_combo.blockSignals(False)
        if not files:
            self.status.setText("Keine gespeicherten Reports gefunden (Dokumente\\PitBoss\\reports).")

    def browse_report_file(self):  # 0.5.9.25, erweitert 0.5.9.27 um MoTeC-CSV
        path, _ = QFileDialog.getOpenFileName(
            self, "Report- oder MoTeC-CSV-Datei wählen", str(REPORT_DIR) if REPORT_DIR.is_dir() else "",
            "Report/MoTeC (*.txt *.csv);;PitBoss-Reports (*.txt);;MoTeC-CSV-Export (*.csv);;Alle Dateien (*)"
        )
        if not path:
            return
        idx = self.report_combo.findData(path)
        if idx < 0:
            self.report_combo.insertItem(1, Path(path).name, path)
            idx = 1
        self.report_combo.setCurrentIndex(idx)

    def analyze(self):
        self.main.gemini_api_key = self.key_edit.text().strip()
        sel_path = self.report_combo.currentData() if self.report_combo.count() else None
        if sel_path is None:
            try:
                report = self.main.build_report()
            except Exception as e:
                self.status.setText(f"Report-Erzeugung fehlgeschlagen: {e}")
                return
            source_label = "aktuelle Live-Session"
        else:
            try:
                if str(sel_path).lower().endswith(".csv"):
                    report = motec_import.build_motec_report(sel_path)  # 0.5.9.27
                else:
                    report = Path(sel_path).read_text(encoding="utf-8")
            except ValueError as e:
                # motec_import wirft ValueError mit verstaendlicher Meldung bei Formatproblemen
                self.status.setText(f"MoTeC-CSV konnte nicht gelesen werden: {e}")
                return
            except Exception as e:
                self.status.setText(f"Report-Datei konnte nicht gelesen werden: {e}")
                return
            source_label = Path(sel_path).name
        if not report or not report.strip():
            self.status.setText("Kein Report vorhanden. Erst eine Runde aufzeichnen oder anderen Report wählen.")
            return
        self.status.setText(f"Sende Report ({source_label}) an Gemini ...")
        QApplication.processEvents()
        system = ("Du bist ein erfahrener Sim-Racing-Renningenieur fuer Le Mans Ultimate. "
                  "Analysiere den folgenden Telemetrie-Report und gib konkretes, priorisiertes "
                  "Coaching auf Deutsch: die 3 wichtigsten Zeitfresser mit je einem umsetzbaren Tipp, "
                  "kurz und praxisnah. Wiederhole den Report nicht.")
        try:
            answer = self.main.gemini_generate(report, system=system, timeout=45)
            self.output.setPlainText(answer)
            if getattr(self, "chk_autoread", None) is not None and self.chk_autoread.isChecked() \
                    and self.main.tts.is_available() and self.main.tts.speak(answer, interrupt=True):
                self.status.setText(f"KI-Analyse fertig \u2013 wird vorgelesen ({self.main.tts.backend()}).")
            else:
                self.status.setText("KI-Analyse fertig.")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:400]
            except Exception:
                pass
            self.status.setText(f"HTTP {e.code}: {detail or e.reason}")
        except urllib.error.URLError as e:
            self.status.setText(f"Netzwerkfehler: {e.reason}")
        except Exception as e:
            self.status.setText(f"Fehler: {e}")

    def _on_quota_threshold(self, pct, used, budget):
        self.status.setText(f"\u26a0 KI-Kontingent: {pct} % erreicht ({used}/{budget} Requests heute)")
        self.status.setStyleSheet("color:#f0883e; font-weight:600;")
        if hasattr(self.main, "log"):
            self.main.log.append(f"KI-Kontingent-Warnung: {pct} % ({used}/{budget} Requests).")
        if pct >= 95:
            QMessageBox.warning(self, "KI-Kontingent",
                f"{pct} % des Tagesbudgets erreicht ({used}/{budget} Requests).\nReset Mitternacht Pacific Time.")

    def _on_quota_rate_limited(self, kind, msg):
        self.status.setText(f"\u26d4 Gemini-Limit erreicht ({kind}). RPD: Reset Mitternacht PT \u2013 RPM/TPM: kurz warten.")
        self.status.setStyleSheet("color:#f85149; font-weight:600;")
        if hasattr(self.main, "log"):
            self.main.log.append(f"Gemini-Limit erreicht ({kind}): {msg}")

    def _tts_test(self):
        ok = self.main.tts.speak("Sprachausgabe aktiv. Renningenieur bereit.", interrupt=True)
        if not ok:
            self.status.setText("Sprachausgabe nicht verfuegbar (nur Windows; pywin32 oder PowerShell noetig).")
        else:
            b = self.main.tts.backend()
            hinweis = " (natuerlich)" if b == "piper" else " (Systemstimme)"
            self.status.setText(f"Sprachausgabe-Backend: {b}{hinweis}")

    def _tts_read_output(self):
        txt = self.output.toPlainText().strip()
        if not txt:
            self.status.setText("Noch keine Analyse zum Vorlesen.")
            return
        if not self.main.tts.speak(txt, interrupt=True):
            self.status.setText("Sprachausgabe nicht verfuegbar.")

    def _tts_voice_changed(self, name):
        if name and name != "(keine)":
            self.main.tts.set_voice(name)

    def _tts_setup_piper(self):
        exe, _ = QFileDialog.getOpenFileName(self, "Piper-Programm w\u00e4hlen (piper.exe)", "",
                                             "Programm (*.exe);;Alle Dateien (*)")
        if not exe:
            return
        model, _ = QFileDialog.getOpenFileName(self, "Piper-Stimme w\u00e4hlen (Modell .onnx)", "",
                                               "Piper-Modell (*.onnx);;Alle Dateien (*)")
        if not model:
            return
        if self.main.tts.set_piper(exe, model):
            for _w in (self.btn_tts_test, self.btn_tts_read, self.btn_tts_stop):
                _w.setEnabled(True)
            self.status.setText("Nat\u00fcrliche Stimme (Piper) aktiv.")
        else:
            self.status.setText("Piper-Dateien ung\u00fcltig \u2013 SAPI bleibt aktiv.")


class SectorTracker:
    """0.4.9.0: echte Sektorzeiten des Spiels (mLastSector1/2, mLastLapTime).
    Bisher nutzte die App nur eigene 50-m-Segmente. Hier kommen die offiziellen
    S1/S2/S3 dazu, inklusive Bestsektoren und theoretischer Bestrunde."""

    def __init__(self):
        self.last = [0.0, 0.0, 0.0]
        self.best = [0.0, 0.0, 0.0]
        self.best_lap = 0.0
        self._seen_lap = None

    @staticmethod
    def _split(s1_cum, s2_cum, lap):
        """LMU liefert S2 kumuliert (S1+S2). Auf Einzelsektoren umrechnen."""
        if s1_cum <= 0 or s2_cum <= 0 or lap <= 0 or s2_cum <= s1_cum or lap <= s2_cum:
            return None
        return [s1_cum, s2_cum - s1_cum, lap - s2_cum]

    def on_sample(self, s):
        """Gibt die Sektoren der gerade beendeten Runde zurueck oder None."""
        lap_no = int(getattr(s, "lap_number", 0) or 0)
        if self._seen_lap is None:
            self._seen_lap = lap_no
            return None
        if lap_no == self._seen_lap:
            return None
        self._seen_lap = lap_no
        secs = self._split(float(getattr(s, "last_sector1_s", 0.0) or 0.0),
                           float(getattr(s, "last_sector2_s", 0.0) or 0.0),
                           float(getattr(s, "last_lap_time", 0.0) or 0.0))
        if secs is None:
            return None
        self.last = secs
        for i, v in enumerate(secs):
            if v > 0 and (self.best[i] <= 0 or v < self.best[i]):
                self.best[i] = v
        lap_t = sum(secs)
        if self.best_lap <= 0 or lap_t < self.best_lap:
            self.best_lap = lap_t
        return secs

    def theoretical_best(self):
        return sum(self.best) if all(v > 0 for v in self.best) else 0.0


class LmuRestClient:
    """0.4.9.5: liest LMUs lokale REST-API (Port 6397). Diese Quelle liefert
    Werte, die im Shared Memory schlicht fehlen:

      /rest/garage/UIScreen/RepairAndRefuel
          wearables.body.aero      -> Aero-Schaden          0.0 - 1.0
          wearables.brakes[4]      -> BREMSVERSCHLEISS      0.0 - 1.0  (echt!)
          wearables.suspension[4]  -> Aufhaengungsschaden   0.0 - 1.0
      /rest/sessions/weather
          PRACTICE/QUALIFY/RACE -> START, NODE_25, NODE_50, NODE_75, FINISH
          je Knoten WNV_SKY / WNV_TEMPERATURE / WNV_RAIN_CHANCE / WNV_HUMIDITY /
          WNV_WINDSPEED / WNV_WINDDIRECTION, jeweils unter "currentValue"
          -> ECHTE Wettervorhersage ueber die Sessionlaenge

    Laeuft in einem Hintergrund-Thread mit kurzem Timeout und schluckt jeden
    Fehler: ist LMU nicht offen oder die API abgeschaltet, bleibt available False
    und die App nutzt weiter ihre Schaetzmodelle. Reine stdlib (urllib+json)."""

    WEARABLES_PATH = "/rest/garage/UIScreen/RepairAndRefuel"
    WEATHER_PATH = "/rest/sessions/weather"
    GARAGE_PATH = "/rest/garage/getPlayerGarageData"  # 0.5.9.16: echter Endpunktname (Marcel-Log), "getPlayerGarage" ohne "Data" gab immer 404
    NODE_NAMES = ("START", "NODE_25", "NODE_50", "NODE_75", "FINISH")
    NODE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
    POLL_S = 12.0
    TIMEOUT_S = 2.0

    def __init__(self, base="http://localhost:6397", poll_s=None):
        self.base = base.rstrip("/")
        if poll_s is not None:
            self.POLL_S = poll_s
        self.available = False
        self.last_error = ""
        self.aero_damage = -1.0
        self.brake_wear = [-1.0, -1.0, -1.0, -1.0]
        self.suspension_damage = [-1.0, -1.0, -1.0, -1.0]
        self.tire_condition = [-1.0, -1.0, -1.0, -1.0]  # 0.5.5.2: wearables.tires (Rest 0..1)
        self.forecast = []          # [{"fraction","sky","temp_c","rain_chance","wind_ms"}]
        self.garage = {}            # 0.5.9.0: getPlayerGarage (key -> Parameter-dict)
        self.session_type = 0
        self._stop = False
        self._thread = None

    # ---- Hintergrund-Schleife ----
    def start(self):
        if self._thread is not None:
            return
        import threading
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    def _loop(self):
        import time as _t
        while not self._stop:
            try:
                self.poll_once()
            except Exception as e:
                self.last_error = str(e)
            _t.sleep(self.POLL_S)

    def poll_once(self):
        ok_w = self.fetch_wearables()
        ok_f = self.fetch_forecast()
        ok_g = self.fetch_garage()
        self.available = bool(ok_w or ok_f or ok_g)
        return self.available

    def fetch_garage(self):
        """0.5.9.0: /rest/garage/getPlayerGarage -> komplettes aktuelles Setup.
        Jeder Parameter: value (roher Index), stringValue (lesbar), min/maxValue,
        lastSavedStringValue, available, isFreeSetting. Wir speichern die rohe
        Map; die Auswertung (einstellbar? geaendert?) macht setup_advice_lines()."""
        try:
            data = self._get_json(self.GARAGE_PATH)
        except Exception as e:
            self.last_error = f"getPlayerGarage: {e}"
            return False
        if not isinstance(data, dict) or not data:
            self.last_error = "getPlayerGarage: leere Antwort"
            return False
        g = {}
        for k, v in data.items():
            if isinstance(v, dict) and "value" in v:
                g[k] = v
        if not g:
            self.last_error = "getPlayerGarage: keine Parameter"
            return False
        self.garage = g
        return True

    def has_garage(self):
        return bool(self.garage)

    # ---- HTTP ----
    def _get_json(self, path):
        import json
        import urllib.request
        req = urllib.request.Request(self.base + path,
                                     headers={"User-Agent": "LMU-Consistency-Coach"})
        with urllib.request.urlopen(req, timeout=self.TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    @staticmethod
    def _wheels(val):
        if isinstance(val, list) and len(val) >= 4:
            out = []
            for i in range(4):
                try:
                    out.append(float(val[i]))
                except Exception:
                    out.append(-1.0)
            return out
        return [-1.0, -1.0, -1.0, -1.0]

    def fetch_wearables(self):
        try:
            data = self._get_json(self.WEARABLES_PATH)
        except Exception as e:
            self.last_error = f"RepairAndRefuel: {e}"
            return False
        w = (data or {}).get("wearables")
        if not isinstance(w, dict):
            self.last_error = "RepairAndRefuel: kein 'wearables'-Objekt"
            return False
        try:
            self.aero_damage = float(((w.get("body") or {}).get("aero", -1.0)))
        except Exception:
            self.aero_damage = -1.0
        self.brake_wear = self._wheels(w.get("brakes"))
        self.suspension_damage = self._wheels(w.get("suspension"))
        self.tire_condition = self._wheels(w.get("tires"))  # 0.5.5.2
        self.last_error = ""
        return True

    def fetch_forecast(self):
        key = ("PRACTICE" if self.session_type <= 4
               else "QUALIFY" if self.session_type <= 8 else "RACE")
        try:
            data = self._get_json(self.WEATHER_PATH)
        except Exception as e:
            self.last_error = f"Weather: {e}"
            return False
        sess = (data or {}).get(key)
        if not isinstance(sess, dict):
            self.last_error = f"Weather: Sessionschluessel {key} fehlt"
            return False

        def val(node, field):
            v = node.get(field)
            if isinstance(v, dict):
                v = v.get("currentValue")
            try:
                return float(v)
            except Exception:
                return None

        nodes = []
        for i, name in enumerate(self.NODE_NAMES):
            node = sess.get(name)
            if not isinstance(node, dict):
                continue
            rain = val(node, "WNV_RAIN_CHANCE")
            nodes.append({
                "fraction": self.NODE_FRACTIONS[i],
                "sky": val(node, "WNV_SKY"),
                "temp_c": val(node, "WNV_TEMPERATURE"),
                # LMU liefert die Regenwahrscheinlichkeit in Prozent (0-100)
                "rain_chance": max(0.0, min(1.0, rain / 100.0)) if rain is not None else None,
                "humidity": val(node, "WNV_HUMIDITY"),
                "wind_ms": val(node, "WNV_WINDSPEED"),
            })
        if not nodes:
            self.last_error = "Weather: keine Knoten"
            return False
        self.forecast = nodes
        self.last_error = ""
        return True

    # ---- Auswertung ----
    def has_wearables(self):
        return self.aero_damage >= 0.0 or any(v >= 0.0 for v in self.brake_wear)

    def has_forecast(self):
        return bool(self.forecast)

    def brake_wear_pct(self, i):
        v = self.brake_wear[i] if 0 <= i < 4 else -1.0
        return v * 100.0 if v >= 0.0 else None

    def tire_condition_pct(self, i):
        # 0.5.5.2: Reifen-Rest in Prozent (1.0 = frisch), aus wearables.tires
        v = self.tire_condition[i] if 0 <= i < 4 else -1.0
        return v * 100.0 if v >= 0.0 else None

    def worst_suspension_pct(self):
        vals = [v for v in self.suspension_damage if v >= 0.0]
        return max(vals) * 100.0 if vals else None

    def aero_pct(self):
        return self.aero_damage * 100.0 if self.aero_damage >= 0.0 else None

    def forecast_lines(self, current_et, end_et):
        """Prognose-Zeilen aus den echten Knoten, zeitlich eingeordnet."""
        if not self.forecast:
            return []
        out = []
        for node in self.forecast:
            rc = node.get("rain_chance")
            if rc is None:
                continue
            eta = None
            if end_et and end_et > 0:
                eta = node["fraction"] * end_et - (current_et or 0.0)
                if eta < -60.0:      # Knoten liegt in der Vergangenheit
                    continue
            when = "jetzt" if (eta is None or eta <= 60.0) else f"in {int(eta // 60)} min"
            temp = node.get("temp_c")
            temp_txt = f", {temp:.0f} \u00b0C" if temp is not None else ""
            kind = "bad" if rc >= 0.5 else "warn" if rc >= 0.25 else "good"
            out.append((f"{when}: {rc * 100:.0f} % Regen{temp_txt}", kind))
        return out[:4]


class WeatherForecastModel:
    """0.4.9.4: Wetter-Trend und Prognose. Wichtig: LMU/rF2 geben KEINE Vorhersage
    im Shared Memory aus - es gibt nur Momentanwerte. Deshalb wird hier aus dem
    beobachteten Verlauf extrapoliert (lineare Regression ueber ein Zeitfenster):

      Steigung = d(Wert)/dt  ->  Zeit bis Schwelle = (Schwelle - Wert) / Steigung

    Verwendet werden mRaining, mAvgPathWetness, mDarkCloud und mTrackTemp.
    mDarkCloud ist dabei der nuetzlichste Fruehindikator: die Wolken ziehen in
    rF2/LMU vor dem Regen auf. Alle Angaben sind Trendrechnung, keine Sim-Prognose:
    wenn das Wetterskript umschlaegt, aendert sich die Prognose entsprechend."""

    WINDOW_S = 420.0        # Beobachtungsfenster fuer die Steigung (7 min)
    MIN_POINTS = 12
    MAX_ETA_S = 3600.0      # weiter als 60 min wird nicht prognostiziert
    RAIN_ON = 0.03          # ab hier gilt es als Regen
    WET_TIRES_AT = 0.30     # Naesse, ab der Regenreifen sinnvoll werden
    DRY_AT = 0.05           # darunter gilt die Strecke wieder als trocken
    CLOUD_WARN = 0.45       # dunkle Wolken -> Regenrisiko

    def __init__(self):
        self.hist = []      # [(t, raining, wetness, cloud, track_temp)]
        self._last_add = 0.0

    def reset(self):
        self.hist = []

    def update(self, s):
        if s is None:
            return
        try:
            import time as _t
            now = _t.monotonic()
        except Exception:
            return
        if now - self._last_add < 2.0:   # 0,5 Hz reicht fuer Wettertrends
            return
        self._last_add = now
        try:
            row = (now,
                   float(getattr(s, "raining", 0.0) or 0.0),
                   float(getattr(s, "wetness_avg", 0.0) or 0.0),
                   float(getattr(s, "dark_cloud", 0.0) or 0.0),
                   float(getattr(s, "track_temp_c", 0.0) or 0.0))
        except Exception:
            return
        self.hist.append(row)
        cutoff = now - self.WINDOW_S
        while len(self.hist) > 2 and self.hist[0][0] < cutoff:
            self.hist.pop(0)

    def _slope(self, idx):
        """Steigung pro Sekunde per kleinster Quadrate; None wenn zu wenig Daten."""
        n = len(self.hist)
        if n < self.MIN_POINTS:
            return None
        t0 = self.hist[0][0]
        xs = [r[0] - t0 for r in self.hist]
        ys = [r[idx] for r in self.hist]
        mx = sum(xs) / n
        my = sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        if den < 1e-9:
            return None
        return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den

    def _eta(self, cur, target, slope):
        """Sekunden bis der Wert die Schwelle erreicht; None wenn nicht absehbar."""
        if slope is None or abs(slope) < 1e-6:
            return None
        dt = (target - cur) / slope
        if dt <= 0 or dt > self.MAX_ETA_S:
            return None
        return dt

    @staticmethod
    def _mins(sec):
        if sec is None:
            return None
        return max(1, int(round(sec / 60.0)))

    def ready(self):
        return len(self.hist) >= self.MIN_POINTS

    def trends(self):
        """(rain_slope, wet_slope, cloud_slope, temp_slope) je Sekunde."""
        return (self._slope(1), self._slope(2), self._slope(3), self._slope(4))

    def forecast(self, s):
        """Liste von (Text, Farb-Hinweis) - fertig zum Zeichnen."""
        out = []
        if not self.ready():
            return [("Prognose sammelt Daten \u2026", "muted")]
        rain = float(getattr(s, "raining", 0.0) or 0.0)
        wet = float(getattr(s, "wetness_avg", 0.0) or 0.0)
        cloud = float(getattr(s, "dark_cloud", 0.0) or 0.0)
        temp = float(getattr(s, "track_temp_c", 0.0) or 0.0)
        r_sl, w_sl, c_sl, t_sl = self.trends()

        # --- Regen ---
        if rain >= self.RAIN_ON:
            if r_sl is not None and r_sl < -1e-5:
                m = self._mins(self._eta(rain, 0.0, r_sl))
                out.append((f"Regen laesst nach, trocken in ~{m} min" if m else "Regen laesst nach", "info"))
            elif r_sl is not None and r_sl > 1e-5:
                out.append(("Regen nimmt zu", "bad"))
            else:
                out.append(("Regen konstant", "info"))
        else:
            m = self._mins(self._eta(rain, self.RAIN_ON, r_sl)) if r_sl and r_sl > 0 else None
            if m:
                out.append((f"Regen wahrscheinlich in ~{m} min", "bad"))
            elif cloud >= self.CLOUD_WARN and c_sl is not None and c_sl > 1e-5:
                out.append(("Wolken ziehen auf \u2013 Regenrisiko", "warn"))
            else:
                out.append(("kein Regen absehbar", "good"))

        # --- Naesse / Reifenwahl ---
        if w_sl is not None and w_sl > 1e-6 and wet < self.WET_TIRES_AT:
            m = self._mins(self._eta(wet, self.WET_TIRES_AT, w_sl))
            if m:
                out.append((f"Regenreifen sinnvoll in ~{m} min", "warn"))
        elif w_sl is not None and w_sl < -1e-6 and wet > self.DRY_AT:
            m = self._mins(self._eta(wet, self.DRY_AT, w_sl))
            if m:
                out.append((f"Strecke trocken in ~{m} min", "good"))
        if wet >= self.WET_TIRES_AT:
            out.append((f"Naesse {wet * 100:.0f} % \u2013 Regenreifen", "bad"))

        # --- Asphalttemperatur ---
        if t_sl is not None and abs(t_sl) > 1e-5:
            d10 = t_sl * 600.0
            if abs(d10) >= 0.5:
                arrow = "\u2191" if d10 > 0 else "\u2193"
                out.append((f"Asphalt {arrow} {abs(d10):.1f} \u00b0C in 10 min", "info"))

        # --- Restzeit der Session ---
        rem = float(getattr(s, "session_remaining_s", 0.0) or 0.0)
        if rem > 0:
            out.append((f"Session noch {int(rem // 60)} min", "muted"))
        return out[:5]


class WeatherOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.0: Streckenzustand - Asphalt-/Lufttemperatur, Regen, Naessegrad."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Wetter Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(268, 244)
        self.setMinimumSize(220, 200)
        self._d = None
        self._fc = None      # 0.4.9.4
        self._rest = None    # 0.4.9.5
        self._drag = None

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._fc = getattr(main, "weather_forecast", None)  # 0.4.9.4
        self._rest = getattr(main, "rest", None)  # 0.4.9.5
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft(); ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag); ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        s = self._d
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted())
        p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "STRECKENZUSTAND")
        if s is None:
            p.setPen(self._muted()); p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end(); return
        track = float(getattr(s, "track_temp_c", 0.0) or 0.0)
        air = float(getattr(s, "ambient_temp_c", 0.0) or 0.0)
        rain = float(getattr(s, "raining", 0.0) or 0.0)
        wet = float(getattr(s, "wetness_avg", 0.0) or 0.0)
        wet_max = float(getattr(s, "wetness_max", 0.0) or 0.0)

        def row(y, label, value, color):
            fl = QFont(); fl.setPointSize(9); p.setFont(fl)
            p.setPen(self._muted()); p.drawText(QRectF(10, y, 92, 18), Qt.AlignVCenter | Qt.AlignLeft, label)
            fv = QFont(); fv.setPointSize(12); fv.setBold(True); p.setFont(fv)
            p.setPen(color); p.drawText(QRectF(100, y, w - 110, 18), Qt.AlignVCenter | Qt.AlignLeft, value)

        t_col = QColor("#f85149") if track >= 40 else QColor("#e3b341") if track >= 28 else QColor("#58a6ff")
        row(28, "Asphalt", f"{track:.1f} \u00b0C", t_col)
        row(50, "Luft", f"{air:.1f} \u00b0C", self._fg())
        r_col = QColor("#58a6ff") if rain > 0.02 else self._muted()
        row(72, "Regen", f"{rain * 100:.0f} %", r_col)
        w_col = QColor("#d24bff") if wet_max > 0.5 else QColor("#58a6ff") if wet > 0.05 else QColor("#3fb950")
        row(94, "N\u00e4sse \u00d8", f"{wet * 100:.0f} %  (max {wet_max * 100:.0f} %)", w_col)
        cloud = float(getattr(s, "dark_cloud", 0.0) or 0.0)
        wind = float(getattr(s, "wind_speed_ms", 0.0) or 0.0) * 3.6
        row(116, "Wolken / Wind", f"{cloud * 100:.0f} %  \u00b7  {wind:.0f} km/h", self._fg())

        # 0.4.9.4: Prognose (Trendrechnung, keine Sim-Vorhersage)
        p.setPen(QPen(self._border(), 1)); p.drawLine(QPointF(10, 140), QPointF(w - 10, 140))
        fh = QFont(); fh.setPointSize(8); fh.setBold(True); p.setFont(fh); p.setPen(self._muted())
        real_fc = self._rest is not None and self._rest.has_forecast()
        p.drawText(QRectF(10, 144, w - 20, 14), Qt.AlignLeft,
                   "PROGNOSE (LMU-API)" if real_fc else "PROGNOSE (TREND)")
        colors = {"good": QColor("#3fb950"), "warn": QColor("#e3b341"),
                  "bad": QColor("#f85149"), "info": QColor("#58a6ff"), "muted": self._muted()}
        lines = []
        if real_fc:
            try:
                lines = self._rest.forecast_lines(
                    float(getattr(s, "session_current_et", 0.0) or 0.0),
                    float(getattr(s, "session_end_et", 0.0) or 0.0))
            except Exception:
                lines = []
        if not lines and self._fc is not None:
            try:
                lines = self._fc.forecast(s)
            except Exception:
                lines = []
        if not lines:
            lines = [("Prognose sammelt Daten \u2026", "muted")]
        fy = 160
        fl3 = QFont(); fl3.setPointSize(9); p.setFont(fl3)
        for text, kind in lines:
            p.setPen(colors.get(kind, self._fg()))
            p.drawText(QRectF(10, fy, w - 20, 15), Qt.AlignVCenter | Qt.AlignLeft, "\u2022 " + text)
            fy += 16
        p.end()


class BlindSpotOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.9.13: Toter-Winkel-Warnung. Zwei Anzeigen LINKS/RECHTS leuchten
    bernsteinfarben, sobald ein Auto seitlich im toten Winkel ist. Das Shared
    Memory liefert KEINE Fahrzeug-Orientierung -> die Fahrtrichtung wird aus der
    Positionsaenderung abgeleitet (geglaettet). Falls links/rechts vertauscht
    sind: 'Toter Winkel: Seiten spiegeln' im Overlay-Menue."""
    MAX_DIST = 12.0    # m: weiter entfernte Autos ignorieren
    FWD_MAX = 6.0      # m: |Laengsversatz| (etwa neben mir, vorn bis hinten)
    LAT_MIN = 1.0      # m: naeher = eigenes Auto / direkt daneben
    LAT_MAX = 5.5      # m: weiter = Nachbarspur, kein toter Winkel
    AMBER = QColor("#f5a623")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Toter-Winkel Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(360, 120)
        self.setMinimumSize(240, 96)
        self._left = False
        self._right = False
        self._prev = None
        self._hx = 0.0
        self._hz = 0.0
        self._flip = self._load_flip()
        self._drag = None

    @staticmethod
    def _load_flip():
        try:
            if BLINDSPOT_CONFIG_PATH.exists():
                return bool(json.loads(BLINDSPOT_CONFIG_PATH.read_text(encoding="utf-8")).get("flip", True))
        except Exception:
            pass
        return True  # 0.5.9.16: an echter Runde validiert - ungefippt war seitenverkehrt

    def set_flip(self, on):
        self._flip = bool(on)
        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            BLINDSPOT_CONFIG_PATH.write_text(json.dumps({"flip": self._flip}), encoding="utf-8")
        except Exception:
            pass
        self.update()

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._compute(s)
        self.update()

    def _compute(self, s):
        self._left = self._right = False
        if s is None:
            return
        px = float(getattr(s, "pos_x", 0.0) or 0.0)
        pz = float(getattr(s, "pos_z", 0.0) or 0.0)
        spd = float(getattr(s, "speed_kmh", 0.0) or 0.0)
        # Fahrtrichtung aus Positionsdelta (nur in Bewegung), exponentiell geglaettet
        if self._prev is not None:
            dx = px - self._prev[0]
            dz = pz - self._prev[1]
            d = (dx * dx + dz * dz) ** 0.5
            if d > 0.25 and spd > 12.0:
                a = 0.35
                self._hx = (1 - a) * self._hx + a * (dx / d)
                self._hz = (1 - a) * self._hz + a * (dz / d)
        self._prev = (px, pz)
        hlen = (self._hx * self._hx + self._hz * self._hz) ** 0.5
        if hlen < 1e-3:
            return
        hx, hz = self._hx / hlen, self._hz / hlen
        for opp in (getattr(s, "opponents", ()) or ()):
            try:
                ox, oz, in_pits = float(opp[1]), float(opp[2]), bool(opp[3])
            except Exception:
                continue
            if in_pits:
                continue
            relx = ox - px
            relz = oz - pz
            dist = (relx * relx + relz * relz) ** 0.5
            if dist < 0.5 or dist > self.MAX_DIST:
                continue
            fwd = relx * hx + relz * hz          # Laengsversatz (+ vor mir)
            cross = relx * hz - relz * hx         # Seitenversatz (Vorzeichen = Seite)
            lat = abs(cross)
            if abs(fwd) > self.FWD_MAX or lat < self.LAT_MIN or lat > self.LAT_MAX:
                continue
            left = cross > 0
            if self._flip:
                left = not left
            if left:
                self._left = True
            else:
                self._right = True

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def _indicator(self, p, x, y, sq, active, label):
        fill = QColor(self.AMBER) if active else self._panel()
        if not active:
            fill.setAlpha(90)
        # Ecken-Rahmen
        p.setPen(QPen(self._faint(90) if not active else QColor(self.AMBER), 2))
        p.setBrush(Qt.NoBrush)
        cl = max(8, sq * 0.28)
        for (ex, ey, dx1, dy1, dx2, dy2) in (
            (x, y, cl, 0, 0, cl),
            (x + sq, y, -cl, 0, 0, cl),
            (x, y + sq, cl, 0, 0, -cl),
            (x + sq, y + sq, -cl, 0, 0, -cl),
        ):
            p.drawLine(QPointF(ex, ey), QPointF(ex + dx1, ey + dy1))
            p.drawLine(QPointF(ex, ey), QPointF(ex + dx2, ey + dy2))
        # Fuellung
        inset = sq * 0.16
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(x + inset, y + inset, sq - 2 * inset, sq - 2 * inset),
                          (sq - 2 * inset) * 0.3, (sq - 2 * inset) * 0.3)
        # Beschriftung oben/unten
        p.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
        p.setPen(self._muted())
        p.drawText(QRectF(x - 6, y - 15, sq + 12, 12), Qt.AlignCenter, "BLIND SPOT")
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        p.setPen(self._muted())
        p.drawText(QRectF(x - 6, y + sq + 3, sq + 12, 12), Qt.AlignCenter, label)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        sq = min(h - 34, (w - 36) / 2)
        sq = max(24, sq)
        cy = (h - sq) / 2 + 3
        self._indicator(p, 14, cy, sq, self._left, "LEFT")
        self._indicator(p, w - 14 - sq, cy, sq, self._right, "RIGHT")
        p.end()


class TrackStateOverlayWindow(OverlayStyleMixin, QWidget):
    """0.5.9.13: Streckenzustand-Panel (kompakt, Karten-Stil): Asphalttemperatur,
    Naessegrad (Verlaufsbalken + Label), Niederschlag, Windgeschwindigkeit und
    eine Kurzprognose NOW/1/5/10 min (aus dem Wetter-Trendmodell). Alle Werte aus
    Shared Memory; keine Sim-Vorhersage, der Trend wird linear projiziert."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Streckenzustand-Panel")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(196, 430)
        self.setMinimumSize(168, 340)
        self._d = None
        self._fc = None
        self._drag = None

    def update_from_main(self, main):
        self._d = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        self._fc = getattr(main, "weather_forecast", None)
        self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    @staticmethod
    def _wet_label(wet):
        if wet < 0.03:
            return "Dry"
        if wet < 0.12:
            return "Lightly wet"
        if wet < 0.35:
            return "Wet"
        if wet < 0.60:
            return "Very wet"
        return "Flooded"

    def _card(self, p, x, y, w, h):
        p.setPen(QPen(self._border(), 1))
        p.setBrush(self._panel())
        p.drawRoundedRect(QRectF(x, y, w, h), 10, 10)

    def _forecast_cols(self, s):
        rain = float(getattr(s, "raining", 0.0) or 0.0)
        temp = float(getattr(s, "track_temp_c", 0.0) or 0.0)
        r_sl = t_sl = None
        fc = self._fc
        if fc is not None:
            try:
                if fc.ready():
                    tr = fc.trends()
                    r_sl, t_sl = tr[0], tr[3]
            except Exception:
                pass
        out = []
        for lbl, mins in (("NOW", 0), ("1m", 1), ("5m", 5), ("10m", 10)):
            if mins > 0 and r_sl is None:
                out.append((lbl, "\u2026", "\u2014", self._muted()))
                continue
            rp = rain if mins == 0 or r_sl is None else max(0.0, min(1.0, rain + r_sl * mins * 60.0))
            tp = temp if mins == 0 or t_sl is None else temp + t_sl * mins * 60.0
            col = QColor("#58a6ff") if rp > 0.40 else (QColor("#3fb950") if rp < 0.10 else QColor("#e3b341"))
            out.append((lbl, f"{rp * 100:.0f}%", f"{tp:.0f}\u00b0", col))
        return out

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        s = self._d
        if s is None:
            p.setPen(self._muted())
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end()
            return
        track = float(getattr(s, "track_temp_c", 0.0) or 0.0)
        wet = float(getattr(s, "wetness_avg", 0.0) or 0.0)
        rain = float(getattr(s, "raining", 0.0) or 0.0)
        wind = float(getattr(s, "wind_speed_ms", 0.0) or 0.0) * 3.6
        pad = 8
        cx = pad
        cw = w - 2 * pad
        y = pad
        lblf = QFont("Segoe UI", 7, QFont.DemiBold)

        # TRACK TEMP
        ch = 50
        self._card(p, cx, y, cw, ch)
        p.setFont(lblf)
        p.setPen(self._muted())
        p.drawText(QRectF(cx + 10, y + 7, cw - 20, 12), Qt.AlignLeft, "TRACK TEMP")
        t_col = QColor("#f85149") if track >= 40 else (QColor("#e3b341") if track >= 28 else QColor("#58a6ff"))
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.setPen(t_col)
        p.drawText(QRectF(cx + 10, y + 20, cw - 20, 24), Qt.AlignLeft | Qt.AlignVCenter, f"{track:.1f} \u00b0C")
        y += ch + 8

        # TRACK WETNESS
        ch = 56
        self._card(p, cx, y, cw, ch)
        p.setFont(lblf)
        p.setPen(self._muted())
        p.drawText(QRectF(cx + 10, y + 7, cw - 20, 12), Qt.AlignLeft, "TRACK WETNESS")
        bx, by, bw, bh = cx + 10, y + 24, cw - 20, 8
        grad = QLinearGradient(bx, 0, bx + bw, 0)
        grad.setColorAt(0.0, QColor("#3fb950"))
        grad.setColorAt(0.5, QColor("#58a6ff"))
        grad.setColorAt(1.0, QColor("#d24bff"))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        mx = bx + max(0.0, min(1.0, wet / 0.60)) * bw
        p.setBrush(self._fg())
        p.drawEllipse(QPointF(mx, by + bh / 2), 5, 5)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.setPen(self._fg())
        p.drawText(QRectF(cx + 10, y + 34, cw - 20, 18), Qt.AlignLeft | Qt.AlignVCenter, self._wet_label(wet))
        y += ch + 8

        # PRECIPITATION
        ch = 44
        self._card(p, cx, y, cw, ch)
        p.setFont(lblf)
        p.setPen(self._muted())
        p.drawText(QRectF(cx + 10, y + 7, cw - 20, 12), Qt.AlignLeft, "PRECIPITATION")
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.setPen(QColor("#58a6ff") if rain > 0.02 else self._fg())
        p.drawText(QRectF(cx + 10, y + 19, cw - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, f"{rain * 100:.0f} %")
        y += ch + 8

        # WIND SPEED
        ch = 44
        self._card(p, cx, y, cw, ch)
        p.setFont(lblf)
        p.setPen(self._muted())
        p.drawText(QRectF(cx + 10, y + 7, cw - 20, 12), Qt.AlignLeft, "WIND SPEED")
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.setPen(self._fg())
        p.drawText(QRectF(cx + 10, y + 19, cw - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, f"{wind:.0f} kph")
        y += ch + 8

        # FORECAST
        ch = h - y - pad
        if ch >= 46:
            self._card(p, cx, y, cw, ch)
            p.setFont(lblf)
            p.setPen(self._muted())
            p.drawText(QRectF(cx + 10, y + 7, cw - 20, 12), Qt.AlignLeft, "FORECAST")
            cols = self._forecast_cols(s)
            n = max(1, len(cols))
            colw = (cw - 12) / n
            for i, (lbl, rainp, tmp, col) in enumerate(cols):
                xx = cx + 6 + i * colw
                p.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
                p.setPen(self._muted())
                p.drawText(QRectF(xx, y + 24, colw, 12), Qt.AlignCenter, lbl)
                p.setFont(QFont("Segoe UI", 9, QFont.Bold))
                p.setPen(col)
                p.drawText(QRectF(xx, y + 39, colw, 14), Qt.AlignCenter, rainp)
                p.setFont(QFont("Segoe UI", 8))
                p.setPen(self._fg())
                p.drawText(QRectF(xx, y + 55, colw, 12), Qt.AlignCenter, tmp)
        p.end()


class BrakeWearModel:
    """0.4.9.2: Schaetzung der Bremsbelastung, weil LMU/rF2 keinen Verschleisskanal
    ausgibt (die Physik kennt ihn, Studio 397 schreibt ihn nicht in den Telemetrie-
    Buffer). Zwei unabhaengige Groessen werden ueber die Zeit integriert:

      1. Thermischer Stress  =  Integral( max(T_Bremse - T_opt, 0) ) dt   [Grad C * s]
         Reale Einheit, keine Annahme ausser der Schwelle T_opt.

      2. Reibarbeit (Index)  =  Integral( Bremsdruck * Geschwindigkeit ) dt
         Proportional zu Integral(F * v) dt. Die absolute Bremskraft ist nicht
         bekannt (mBrakePressure ist 0..1), deshalb ein relativer Index, keine Joule.

    Daraus wird ein Belag-Verschleiss in Prozent geschaetzt. Die beiden
    Referenzwerte dafuer sind Kalibrierwerte, keine Messwerte - sie liegen in
    exports/brake_model.json und koennen nach einem echten Stint angepasst werden.
    Die Prozentzahl ist also ein Modell, kein Sim-Wert."""

    DEFAULTS = {
        "t_opt_c": 500.0,        # ab hier zaehlt Hitze als Stress
        "t_fade_c": 700.0,       # ab hier Fading-Warnung
        "friction_ref": 60000.0, # Reibarbeits-Index fuer 100 % Belagverschleiss
        "thermal_ref": 600000.0, # thermischer Stress (Grad C * s) fuer 100 %
    }

    def __init__(self, config_path=None):
        self.cfg = dict(self.DEFAULTS)
        self.config_path = config_path
        self.load()
        self.thermal = [0.0, 0.0, 0.0, 0.0]   # Grad C * s je Rad
        self.friction = [0.0, 0.0, 0.0, 0.0]  # Index je Rad
        self.peak_c = [0.0, 0.0, 0.0, 0.0]
        self._last_t = None
        self._veh = None
        self._unit_min = None

    def load(self):
        if not self.config_path:
            return
        try:
            import json
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in self.DEFAULTS:
                if k in data:
                    self.cfg[k] = float(data[k])
        except Exception:
            pass

    def save(self):
        if not self.config_path:
            return
        try:
            import json
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2)
        except Exception:
            pass

    def reset(self):
        self.thermal = [0.0, 0.0, 0.0, 0.0]
        self.friction = [0.0, 0.0, 0.0, 0.0]
        self.peak_c = [0.0, 0.0, 0.0, 0.0]
        self._last_t = None

    def _to_c(self, v):
        """Kelvin/Celsius wie im Overlay ueber das Sessionminimum erkennen."""
        if v <= 1.0:
            return None
        if self._unit_min is not None and self._unit_min > 200.0:
            return v - 273.15
        return v

    def temps_c(self):
        return [self._to_c(v) for v in self._raw_last] if hasattr(self, "_raw_last") else [None] * 4

    def update(self, s):
        """Pro Telemetrie-Tick aufrufen. Laeuft unabhaengig davon, ob das
        Overlay offen ist - sonst gingen Werte beim Schliessen verloren."""
        if s is None:
            return
        try:
            import time as _t
            now = _t.monotonic()
        except Exception:
            return
        veh = str(getattr(s, "vehicle_name", "") or "")
        if veh != self._veh:
            self._veh = veh
            self.reset()
        raw = [float(getattr(s, f"brake_{k}_temp_raw", 0.0) or 0.0) for k in ("fl", "fr", "rl", "rr")]
        self._raw_last = raw
        vals = [v for v in raw if v > 1.0]
        if vals:
            m = min(vals)
            self._unit_min = m if self._unit_min is None else min(self._unit_min, m)
        if self._last_t is None:
            self._last_t = now
            return
        dt = now - self._last_t
        self._last_t = now
        if dt <= 0 or dt > 1.0:      # Pause/Hänger nicht mitzaehlen
            return
        if bool(getattr(s, "in_pits", False)):
            return
        v_ms = float(getattr(s, "speed_kmh", 0.0) or 0.0) / 3.6
        press = [float(getattr(s, f"brake_{k}_pressure", 0.0) or 0.0) for k in ("fl", "fr", "rl", "rr")]
        t_opt = float(self.cfg["t_opt_c"])
        for i in range(4):
            c = self._to_c(raw[i])
            if c is not None:
                if c > self.peak_c[i]:
                    self.peak_c[i] = c
                over = c - t_opt
                if over > 0:
                    self.thermal[i] += over * dt
            p = press[i]
            if p > 0.02 and v_ms > 1.0:
                self.friction[i] += p * v_ms * dt

    def wear_pct(self, i):
        fr = float(self.cfg["friction_ref"]) or 1.0
        th = float(self.cfg["thermal_ref"]) or 1.0
        return max(0.0, min(999.0, (self.friction[i] / fr + self.thermal[i] / th) * 100.0))

    def worst_wear(self):
        return max(self.wear_pct(i) for i in range(4))

    def fading_risk(self):
        """True, wenn ein Rad aktuell ueber der Fading-Schwelle liegt."""
        temps = self.temps_c()
        f = float(self.cfg["t_fade_c"])
        return any(c is not None and c >= f for c in temps)

    def calibrate_to(self, pct):
        """Skaliert die Referenzen so, dass der aktuelle Zustand pct Prozent
        entspricht - damit laesst sich das Modell nach einem echten Stint
        an das tatsaechliche Verhalten anpassen."""
        if pct <= 0:
            return False
        cur = self.worst_wear()
        if cur <= 0.01:
            return False
        factor = cur / float(pct)
        self.cfg["friction_ref"] = float(self.cfg["friction_ref"]) * factor
        self.cfg["thermal_ref"] = float(self.cfg["thermal_ref"]) * factor
        self.save()
        return True


class BrakeTempOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.0/0.4.9.2: Bremsscheibentemperaturen je Rad (mBrakeTemp) plus
    geschaetzter Belagverschleiss aus dem BrakeWearModel (thermischer Stress +
    Reibarbeit), weil LMU keinen Verschleisskanal ausgibt. Die Prozentzahl ist ein
    Modellwert - Doppelklick setzt die Stint-Werte zurueck."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Bremstemperatur Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(244, 210)
        self.setMinimumSize(200, 180)
        self._raw = [0.0, 0.0, 0.0, 0.0]
        self._model = None   # 0.4.9.2
        self._rest = None    # 0.4.9.5
        self._bias = 0.0
        self._press = 0.0
        self._min_seen = None
        self._live = False
        self._drag = None

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            self._live = False; self.update(); return
        self._raw = [float(getattr(s, f"brake_{k}_temp_raw", 0.0) or 0.0) for k in ("fl", "fr", "rl", "rr")]
        self._model = getattr(main, "brake_model", None)  # 0.4.9.2
        self._rest = getattr(main, "rest", None)  # 0.4.9.5
        self._bias = float(getattr(s, "rear_brake_bias", 0.0) or 0.0)
        self._press = max(float(getattr(s, f"brake_{k}_pressure", 0.0) or 0.0) for k in ("fl", "fr", "rl", "rr"))
        vals = [v for v in self._raw if v > 1.0]
        if vals:
            m = min(vals)
            self._min_seen = m if self._min_seen is None else min(self._min_seen, m)
        self._live = bool(vals)
        self.update()

    def mouseDoubleClickEvent(self, ev):   # 0.4.9.2
        if self._model is not None:
            self._model.reset()
        self.update()

    def _to_c(self, v):
        if v <= 1.0:
            return None
        if self._min_seen is not None and self._min_seen > 200.0:
            return v - 273.15
        return v

    def _col(self, c):   # 0.4.9.2: war @staticmethod und rief self._muted() -> NameError
        if c is None:
            return self._muted()
        if c < 150:
            return QColor("#58a6ff")     # kalt
        if c < 350:
            return QColor("#3fb950")     # Arbeitsfenster
        if c < 600:
            return QColor("#e3b341")
        return QColor("#f85149")         # ueberhitzt

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft(); ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag); ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "BREMSEN \u00b0C")
        if not self._live:
            p.setPen(self._muted())
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "kein mBrakeTemp")
            p.end(); return
        pad = 12; top = 28
        cw = (w - 3 * pad) / 2.0
        ch = (h - top - pad - 14) / 2.0
        labels = ["VL", "VR", "HL", "HR"]
        for i in range(4):
            r = i // 2; c = i % 2
            x = pad + c * (cw + pad); y = top + r * (ch + 8)
            cval = self._to_c(self._raw[i])
            col = self._col(cval)
            p.setPen(QPen(self._border(), 1)); p.setBrush(self._panel())
            p.drawRoundedRect(QRectF(x, y, cw, ch), 7, 7)
            fl = QFont(); fl.setPointSize(8); p.setFont(fl); p.setPen(self._muted())
            p.drawText(QRectF(x + 6, y + 3, cw - 12, 12), Qt.AlignLeft, labels[i])
            fv = QFont(); fv.setPointSize(13); fv.setBold(True); p.setFont(fv); p.setPen(col)
            p.drawText(QRectF(x, y + 10, cw, ch - 26), Qt.AlignCenter,
                       "\u2014" if cval is None else f"{cval:.0f}")
            # 0.4.9.2/0.4.9.5: Verschleiss je Rad - echte REST-Werte bevorzugt
            real = self._rest.brake_wear_pct(i) if (self._rest is not None and self._rest.has_wearables()) else None
            if real is not None or self._model is not None:
                wpct = real if real is not None else self._model.wear_pct(i)
                wcol = QColor("#f85149") if wpct >= 85 else QColor("#e3b341") if wpct >= 60 else QColor("#3fb950")
                bw2 = cw - 12
                p.setPen(Qt.NoPen); p.setBrush(self._trackcol())
                p.drawRoundedRect(QRectF(x + 6, y + ch - 14, bw2, 5), 2, 2)
                p.setBrush(wcol)
                p.drawRoundedRect(QRectF(x + 6, y + ch - 14, max(bw2 * min(wpct / 100.0, 1.0), 2), 5), 2, 2)
                fw2 = QFont(); fw2.setPointSize(8); p.setFont(fw2); p.setPen(wcol)
                p.drawText(QRectF(x, y + ch - 26, cw - 6, 12), Qt.AlignRight, f"{wpct:.0f} %")
        fn = QFont(); fn.setPointSize(7); p.setFont(fn); p.setPen(self._muted())
        unit = "K\u2192\u00b0C" if (self._min_seen or 0) > 200.0 else "\u00b0C roh"
        # 0.4.9.1: Bremsbalance + Druck; Verschleiss existiert im Shared Memory nicht
        p.drawText(QRectF(0, h - 28, w, 12), Qt.AlignCenter,
                   f"{unit}  \u00b7  Balance hinten {self._bias * 100:.0f} %  \u00b7  Druck {self._press * 100:.0f} %")
        if self._model is not None:
            m = self._model
            fade = m.fading_risk()
            fl2 = QFont(); fl2.setPointSize(8); fl2.setBold(fade); p.setFont(fl2)
            p.setPen(QColor("#f85149") if fade else self._muted())
            hot = max([c for c in m.temps_c() if c is not None] or [0.0])
            real_src = self._rest is not None and self._rest.has_wearables()
            p.drawText(QRectF(0, h - 15, w, 13), Qt.AlignCenter,
                       ("FADING-GEFAHR \u00b7 " if fade else "")
                       + ("Verschlei\u00df: LMU-API" if real_src else "Verschlei\u00df gesch\u00e4tzt")
                       + f" \u00b7 Peak {hot:.0f} \u00b0C")
        p.end()


class FuelOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.0: Kraftstoff - Inhalt in Litern und Prozent, Kapazitaet, Verbrauch
    der letzten Runde, Schnitt und Reichweite in Runden. Bei Hypercars zusaetzlich
    die virtuelle Energie (mVirtualEnergy)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Sprit Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(238, 158)
        self.setMinimumSize(190, 130)
        self.fuel = 0.0
        self.cap = 0.0
        self.venergy = 0.0
        self.last_use = 0.0
        self.avg_use = 0.0
        self._uses = []
        self._lap = None
        self._fuel_at_lap = None
        self._live = False
        self._drag = None

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            self._live = False; self.update(); return
        self.fuel = float(getattr(s, "fuel_l", 0.0) or 0.0)
        self.cap = float(getattr(s, "fuel_capacity_l", 0.0) or 0.0)
        self.venergy = float(getattr(s, "virtual_energy", 0.0) or 0.0)
        lap = int(getattr(s, "lap_number", 0) or 0)
        if self._lap is None:
            self._lap = lap; self._fuel_at_lap = self.fuel
        elif lap != self._lap:
            if self._fuel_at_lap is not None:
                used = self._fuel_at_lap - self.fuel
                if 0.05 < used < 30.0 and not bool(getattr(s, "in_pits", False)):
                    self.last_use = used
                    self._uses.append(used)
                    if len(self._uses) > 5:
                        del self._uses[0:len(self._uses) - 5]
                    self.avg_use = sum(self._uses) / len(self._uses)
            self._lap = lap; self._fuel_at_lap = self.fuel
        self._live = True
        self.update()

    def laps_left(self):
        base = self.avg_use or self.last_use
        return (self.fuel / base) if base > 0.01 else None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft(); ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag); ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "KRAFTSTOFF")
        if not self._live:
            p.setPen(self._muted()); p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "warte auf Telemetrie")
            p.end(); return
        pct = (self.fuel / self.cap) if self.cap > 0.1 else 0.0
        col = QColor("#f85149") if pct < 0.10 else QColor("#e3b341") if pct < 0.25 else QColor("#3fb950")
        fv = QFont(); fv.setPointSize(19); fv.setBold(True); p.setFont(fv); p.setPen(col)
        p.drawText(QRectF(10, 24, w - 20, 26), Qt.AlignLeft, f"{self.fuel:.1f} l")
        fs = QFont(); fs.setPointSize(10); p.setFont(fs); p.setPen(self._muted())
        p.drawText(QRectF(10, 26, w - 20, 24), Qt.AlignRight,
                   f"{pct * 100:.0f} %  von {self.cap:.0f} l" if self.cap > 0.1 else "Kapazit\u00e4t \u2014")
        # Balken
        bx, by, bw, bh = 10, 54, w - 20, 10
        p.setPen(Qt.NoPen); p.setBrush(self._trackcol()); p.drawRoundedRect(QRectF(bx, by, bw, bh), 5, 5)
        p.setBrush(col); p.drawRoundedRect(QRectF(bx, by, max(bw * min(pct, 1.0), 3), bh), 5, 5)

        def row(y, label, value, color=self._fg()):
            fl = QFont(); fl.setPointSize(9); p.setFont(fl); p.setPen(self._muted())
            p.drawText(QRectF(10, y, 108, 16), Qt.AlignVCenter | Qt.AlignLeft, label)
            fx = QFont(); fx.setPointSize(10); fx.setBold(True); p.setFont(fx); p.setPen(color)
            p.drawText(QRectF(110, y, w - 120, 16), Qt.AlignVCenter | Qt.AlignLeft, value)

        row(72, "letzte Runde", f"{self.last_use:.2f} l" if self.last_use > 0 else "\u2014")
        row(92, "\u00d8 (5 Runden)", f"{self.avg_use:.2f} l" if self.avg_use > 0 else "\u2014")
        ll = self.laps_left()
        row(112, "Reichweite", f"{ll:.1f} Runden" if ll else "\u2014",
            QColor("#f85149") if (ll is not None and ll < 2) else self._fg())
        if self.venergy > 0.0001:
            row(132, "Virt. Energie", f"{self.venergy * 100:.0f} %", QColor("#58a6ff"))
        p.end()


class FFBOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.9.0: Force-Feedback-Monitor. Zeigt den Rohwert aus dem Shared Memory
    (generic.FFBTorque) als Balken um die Mitte, dazu Peak-Hold und eine
    Clipping-Anzeige. Clipping = Betrag am oberen Anschlag: dann geht Detail
    verloren und der FFB-Gain sollte runter. Zusaetzlich das physikalische
    Lenkmoment (mSteeringShaftTorque) als Referenz."""

    HISTORY = 160
    CLIP_AT = 0.985

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU FFB Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(268, 150)
        self.setMinimumSize(200, 120)
        self._hist = []
        self.val = 0.0
        self.peak = 0.0
        self.shaft = 0.0
        self.clip_frames = 0
        self.total_frames = 0
        self._seen = False
        self._drag = None

    def reset_stats(self):
        self.peak = 0.0; self.clip_frames = 0; self.total_frames = 0; self._hist = []

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            self.update(); return
        v = float(getattr(s, "ffb_torque", 0.0) or 0.0)
        self.val = v
        self.shaft = float(getattr(s, "steering_shaft_torque", 0.0) or 0.0)
        if abs(v) > 1e-6:
            self._seen = True
        a = abs(v)
        if a > self.peak:
            self.peak = a
        self.total_frames += 1
        if a >= self.CLIP_AT:
            self.clip_frames += 1
        self._hist.append(v)
        if len(self._hist) > self.HISTORY:
            del self._hist[0:len(self._hist) - self.HISTORY]
        self.update()

    def clip_pct(self):
        return (self.clip_frames / self.total_frames * 100.0) if self.total_frames else 0.0

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft(); ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag); ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def mouseDoubleClickEvent(self, ev):
        self.reset_stats(); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen); p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.setPen(self._muted()); p.drawText(QRectF(10, 6, w - 20, 16), Qt.AlignLeft, "FORCE FEEDBACK")
        if not self._seen and self.total_frames > 30:
            p.setPen(self._muted())
            p.drawText(QRectF(0, h / 2 - 10, w, 20), Qt.AlignCenter, "kein FFBTorque-Kanal")
            p.end(); return
        a = abs(self.val)
        clipping = a >= self.CLIP_AT
        col = QColor("#f85149") if clipping else QColor("#e3b341") if a > 0.85 else QColor("#3fb950")
        # Balken um die Mitte
        bx, by, bw, bh = 12, 30, w - 24, 20
        cx = bx + bw / 2.0
        p.setPen(Qt.NoPen); p.setBrush(self._trackcol()); p.drawRoundedRect(QRectF(bx, by, bw, bh), 5, 5)
        half = (bw / 2.0) * min(a, 1.0)
        if self.val >= 0:
            p.setBrush(col); p.drawRect(QRectF(cx, by, max(half, 1.0), bh))
        else:
            p.setBrush(col); p.drawRect(QRectF(cx - max(half, 1.0), by, max(half, 1.0), bh))
        # Peak-Marker
        p.setPen(QPen(QColor("#58a6ff"), 2))
        px = (bw / 2.0) * min(self.peak, 1.0)
        p.drawLine(QPointF(cx + px, by), QPointF(cx + px, by + bh))
        p.drawLine(QPointF(cx - px, by), QPointF(cx - px, by + bh))
        p.setPen(QPen(self._faint(60), 1)); p.drawLine(QPointF(cx, by), QPointF(cx, by + bh))
        # Verlauf
        gy, gh = by + bh + 8, 34
        if len(self._hist) > 1:
            path = QPainterPath()
            step = (w - 24) / (self.HISTORY - 1)
            start = self.HISTORY - len(self._hist)
            for i, v in enumerate(self._hist):
                x = 12 + (start + i) * step
                y = gy + gh / 2.0 - max(-1.0, min(1.0, v)) * (gh / 2.0 - 1)
                path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
            p.setPen(QPen(QColor(120, 200, 255, 150), 1)); p.setBrush(Qt.NoBrush); p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawLine(QPointF(12, gy + gh / 2.0), QPointF(w - 12, gy + gh / 2.0))
        # Werte
        fv = QFont(); fv.setPointSize(13); fv.setBold(True); p.setFont(fv); p.setPen(col)
        p.drawText(QRectF(10, h - 40, w - 20, 20), Qt.AlignLeft, f"{self.val:+.2f}")
        fs = QFont(); fs.setPointSize(9); p.setFont(fs)
        p.setPen(QColor("#f85149") if self.clip_pct() > 1.0 else self._muted())
        p.drawText(QRectF(10, h - 40, w - 20, 20), Qt.AlignRight,
                   ("CLIPPING  " if clipping else "") + f"Clip {self.clip_pct():.1f} %")
        fn = QFont(); fn.setPointSize(8); p.setFont(fn); p.setPen(self._muted())
        p.drawText(QRectF(10, h - 20, w - 20, 14), Qt.AlignLeft,
                   f"Peak {self.peak:.2f}  \u00b7  Lenkmoment {self.shaft:.1f} Nm")
        p.end()


class LimitOverlayWindow(OverlayStyleMixin, QWidget):
    """0.4.8.7 Limit-Meter (visuell, kein Ton): Grip-Kreis aus mLocalAccel.
    Zeigt die kombinierte g-Kraft als Punkt im g-g-Diagramm und in Prozent deines
    in dieser Session gezeigten Maximums. Gruen = Luft, Rot = am Limit, Magenta =
    drueber (Rutschen/Blockieren ueber die Schlupf-Kanaele). Selbst-diagnostizierend:
    meldet, wenn der Beschleunigungskanal leer durchkommt. Doppelklick = Kalibrierung
    zuruecksetzen. Verschiebbar wie die anderen Overlays (rahmenlos, always-on-top)."""

    TRAIL = 24
    SLIP_LIMIT = 2.5      # m/s Schlupf am Patch -> "drueber"
    G_CAP = 2.3           # implausible Spitzen (Curbs) ignorieren
    CALIB_G = 1.0         # ab diesem gezeigten Max gilt % als kalibriert

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMU Limit Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # klaut LMU nicht den Fokus
        self.resize(210, 250)
        self.setMinimumSize(160, 190)
        self._lat = 0.0
        self._long = 0.0
        self._gmax = 0.0
        self._slip = 0.0
        self._trail = []
        self._live = False
        self._accel_seen = False
        self._slip_seen = False
        self._samples = 0
        self._veh = None
        self._drag = None

    def reset_calibration(self):
        self._gmax = 0.0
        self._trail = []

    def update_from_main(self, main):
        s = getattr(main, "last_live_sample", None) or (main.samples[-1] if getattr(main, "samples", None) else None)
        if not s:
            self._live = False
            self.update()
            return
        veh = getattr(s, "vehicle_name", "") or ""
        if veh != self._veh:
            self._veh = veh
            self.reset_calibration()
        lat = float(getattr(s, "accel_lat_ms2", 0.0) or 0.0) / 9.81
        lng = float(getattr(s, "accel_long_ms2", 0.0) or 0.0) / 9.81
        self._lat = lat
        self._long = lng
        self._slip = max(float(getattr(s, "tire_fl_slip_ms", 0.0) or 0.0),
                         float(getattr(s, "tire_fr_slip_ms", 0.0) or 0.0),
                         float(getattr(s, "tire_rl_slip_ms", 0.0) or 0.0),
                         float(getattr(s, "tire_rr_slip_ms", 0.0) or 0.0))
        self._samples += 1
        if abs(lat) > 1e-4 or abs(lng) > 1e-4:
            self._accel_seen = True
        if self._slip > 1e-4:
            self._slip_seen = True
        comb = (lat * lat + lng * lng) ** 0.5
        moving = (float(getattr(s, "speed_kmh", 0.0) or 0.0) > 50.0
                  and not bool(getattr(s, "in_pits", False)))
        if moving and comb <= self.G_CAP and comb > self._gmax:
            self._gmax = comb
        self._trail.append((lat, lng))
        if len(self._trail) > self.TRAIL:
            del self._trail[0:len(self._trail) - self.TRAIL]
        self._live = True
        self.update()

    def _comb(self):
        return (self._lat * self._lat + self._long * self._long) ** 0.5

    def _pct(self):
        if self._gmax < 1e-3:
            return None
        return self._comb() / self._gmax

    def _state(self):
        """(Farbe, Kurzlabel, prozenttext)"""
        if not self._accel_seen and self._samples > 30:
            return (self._muted(), "kein Accel-Kanal", "--")
        if self._slip_seen and self._slip >= self.SLIP_LIMIT:
            return (QColor("#d24bff"), "DRÜBER", self._pct_text())
        if self._gmax < self.CALIB_G:
            return (QColor("#58a6ff"), "kalibriert …", "--")
        pct = self._pct() or 0.0
        if pct < 0.85:
            return (QColor("#3fb950"), "Luft", self._pct_text())
        if pct < 0.97:
            return (QColor("#e3b341"), "nah", self._pct_text())
        return (QColor("#f85149"), "AM LIMIT", self._pct_text())

    def _pct_text(self):
        p = self._pct()
        if p is None:
            return "--"
        return f"{min(p, 1.35) * 100:.0f}%"

    # verschiebbar (rahmenlos)
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def mouseDoubleClickEvent(self, ev):
        self.reset_calibration()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        h = self.height()
        # Hintergrund
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg())
        p.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)

        color, label, ptxt = self._state()

        # Kreis-Geometrie (oben), Text (unten)
        pad = 12
        gauge_h = h - 66
        cx = w / 2.0
        cy = pad + gauge_h / 2.0
        R = min(w - 2 * pad, gauge_h) / 2.0 - 2

        # aeusserer Grip-Kreis
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self._border(), 2))
        p.drawEllipse(QPointF(cx, cy), R, R)
        # 85%- und 97%-Ringe zur Orientierung
        p.setPen(QPen(self._faint(48), 1, Qt.DashLine))
        p.drawEllipse(QPointF(cx, cy), R * 0.85, R * 0.85)
        p.drawEllipse(QPointF(cx, cy), R * 0.97, R * 0.97)
        # Fadenkreuz
        p.setPen(QPen(self._faint(52), 1))
        p.drawLine(QPointF(cx - R, cy), QPointF(cx + R, cy))
        p.drawLine(QPointF(cx, cy - R), QPointF(cx, cy + R))

        # Skala: R entspricht dem gezeigten Maximum (bzw. 1.2g bis kalibriert)
        scale = self._gmax if self._gmax >= self.CALIB_G else 1.2

        def to_pt(lat, lng):
            # lat -> x (rechts +), long -> y: Bremsen (negativ) nach unten
            x = cx + max(-1.4, min(1.4, lat / scale)) * R
            y = cy + max(-1.4, min(1.4, lng / scale)) * R
            return QPointF(x, y)

        # Trail
        if len(self._trail) > 1:
            path = QPainterPath()
            for i, (la, lo) in enumerate(self._trail):
                pt = to_pt(la, lo)
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 90), 2))
            p.drawPath(path)

        # aktueller Punkt
        cur = to_pt(self._lat, self._long)
        p.setPen(QPen(self._bg(), 2))
        p.setBrush(color)
        p.drawEllipse(cur, 6, 6)

        # Prozent gross
        p.setPen(color)
        f = QFont(); f.setPointSize(20); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(0, h - 58, w, 30), Qt.AlignCenter, ptxt)
        # Label
        f2 = QFont(); f2.setPointSize(10); f2.setBold(True); p.setFont(f2)
        p.drawText(QRectF(0, h - 30, w, 16), Qt.AlignCenter, label)
        # g-Wert + gezeigtes Max klein
        f3 = QFont(); f3.setPointSize(8); p.setFont(f3)
        p.setPen(self._muted())
        info = f"{self._comb():.2f} g   ·   Max {self._gmax:.2f} g" if self._accel_seen else "warte auf Telemetrie"
        p.drawText(QRectF(0, h - 15, w, 13), Qt.AlignCenter, info)
        p.end()


class UpdateDownloadWorker(QThread):
    """0.4.8.8: laedt den Installer im Hintergrund und meldet Fortschritt."""
    progress = Signal(int, int)
    finished_result = Signal(str, str)  # (pfad, fehler)

    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            updater.download_asset(self.url, self.dest,
                                   progress_cb=lambda d, t: self.progress.emit(int(d), int(t)))
            self.finished_result.emit(self.dest, "")
        except Exception as e:
            self.finished_result.emit("", str(e))


class GeminiCoachWorker(QThread):
    """0.4.8.4: baut asynchron EINEN kurzen Coach-Satz via Gemini. Laeuft im eigenen
    Thread, damit die 10-Hz-Live-Schleife nicht blockiert. Ergebnis per Signal zurueck."""
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, main, prompt, system):
        super().__init__()
        self._main = main
        self._prompt = prompt
        self._system = system

    def run(self):
        try:
            text = self._main.gemini_generate(self._prompt, system=self._system, timeout=12)
            self.done.emit(text or "")
        except Exception as e:
            self.failed.emit(str(e))


class LiveCoach(QObject):
    """0.4.8.4 Live-Coaching: baut bei Rundenende einen kurzen Hinweis (Gemini mit
    Offline-Fallback) und spricht ihn per TTS *getimt auf der Geraden* aus, damit nicht
    mitten in der Kurve geredet wird. Opt-in ueber Mehr-Menue / F11.

    Ablauf: on_lap_completed() setzt (asynchron via Worker oder offline) einen
    pending_text. maybe_speak_on_straight() wird bei jedem live_tick gerufen und
    spricht den pending_text erst, wenn das Auto schnell/gesetzt auf einer Geraden
    ist und der Cooldown abgelaufen ist. So kommt pro Runde hoechstens ein Satz.
    """

    COOLDOWN_S = 8.0            # min. Abstand zwischen zwei gesprochenen Hinweisen
    STRAIGHT_MIN_SPEED = 120.0  # km/h - klassenunabhaengig "schnell & gesetzt"
    _PLACEHOLDERS = ("aktuell ok", "Live sammelt Daten", "Referenz laden",
                     "Referenz importieren/Analyse", "Live-Vergleich aktiv", "")

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.enabled = False
        self.pending_text = None
        self.last_spoken_ts = 0.0
        self.last_lap_done = None
        self._worker = None
        self._pending_facts = {"lap": 0, "delta_s": None, "hint": ""}

    def set_enabled(self, on):
        self.enabled = bool(on)
        if not self.enabled:
            self.pending_text = None

    # ---- Rundenende -> Hinweis bauen -------------------------------------
    def on_lap_completed(self, rows, lap_number, delta_s, coach_line):
        if not self.enabled or lap_number is None:
            return
        if not self.main.tts.is_available():
            return
        if self.last_lap_done == lap_number:
            return  # eine Runde -> hoechstens eine Anfrage
        self.last_lap_done = lap_number
        facts = self._facts(lap_number, delta_s, coach_line)
        if not self._meaningful(facts):
            return  # nichts Sinnvolles zu sagen -> still bleiben
        self._pending_facts = facts
        key = (getattr(self.main, "gemini_api_key", "") or "").strip()
        if key and (self._worker is None or not self._worker.isRunning()):
            try:
                self._worker = GeminiCoachWorker(self.main, self._prompt(facts), self._system())
                self._worker.done.connect(self._on_ai_ready)
                self._worker.failed.connect(self._on_ai_failed)
                self._worker.start()
                return
            except Exception:
                pass
        # kein Key oder Worker belegt -> sofort Offline-Fallback
        self.pending_text = self._local_line(facts)

    def _facts(self, lap_number, delta_s, coach_line):
        try:
            d = float(delta_s) if delta_s is not None else None
        except Exception:
            d = None
        return {"lap": int(lap_number), "delta_s": d, "hint": (coach_line or "").strip()}

    def _meaningful(self, facts):
        if facts["hint"] not in self._PLACEHOLDERS:
            return True
        return facts["delta_s"] is not None and abs(facts["delta_s"]) >= 0.10

    def _system(self):
        return ("Du bist ein knapper, ruhiger Renningenieur am Boxenfunk. "
                "Antworte mit GENAU EINEM kurzen deutschen Satz, hoechstens 14 Woerter, "
                "Imperativ, ohne Begruessung, ohne Emojis, ohne Zahlenkolonnen. "
                "Nenne die eine wichtigste Sache fuer die naechste Runde.")

    def _prompt(self, facts):
        parts = [f"Runde {facts['lap']} beendet."]
        if facts["delta_s"] is not None:
            parts.append(f"Gesamt-Delta zur Referenz: {facts['delta_s']:+.2f} s.")
        if facts["hint"] and facts["hint"] not in self._PLACEHOLDERS:
            parts.append(f"Groesster Zeitverlust laut Telemetrie: {facts['hint']}.")
        parts.append("Gib genau einen Coaching-Satz fuer die naechste Runde.")
        return " ".join(parts)

    def _local_line(self, facts):
        # Offline-Fallback ohne Netz: kurzer Satz aus Hinweis bzw. Delta.
        hint = facts["hint"]
        if hint and hint not in self._PLACEHOLDERS:
            topic = hint.split("\u00b7")[-1].strip() if "\u00b7" in hint else hint
            return f"Fokus naechste Runde: {topic}."
        if facts["delta_s"] is not None and facts["delta_s"] <= -0.10:
            return "Gute Runde, genau so weiter."
        return "Sauber bleiben, Linie halten."

    def _sanitize(self, text):
        t = " ".join((text or "").split())
        for sep in (". ", "! ", "? "):
            if sep in t:
                t = t.split(sep)[0] + sep.strip()
                break
        return t[:140].strip()

    def _on_ai_ready(self, text):
        line = self._sanitize(text) or self._local_line(self._pending_facts)
        if self.enabled:
            self.pending_text = line

    def _on_ai_failed(self, _err):
        if self.enabled:
            self.pending_text = self._local_line(self._pending_facts)

    # ---- Ausgabe getimt auf der Geraden ----------------------------------
    def _is_straight(self, s):
        try:
            return (float(s.throttle) >= 0.95 and float(s.brake) <= 0.03
                    and abs(float(s.steering)) <= 0.06
                    and float(s.speed_kmh) >= self.STRAIGHT_MIN_SPEED
                    and not bool(getattr(s, "in_pits", False)))
        except Exception:
            return False

    def maybe_speak_on_straight(self, s):
        if not self.enabled or not self.pending_text or s is None:
            return
        now = datetime.now().timestamp()
        if now - self.last_spoken_ts < self.COOLDOWN_S:
            return
        if not self._is_straight(s):
            return
        try:
            if self.main.tts.is_available() and self.main.tts.speak(self.pending_text, interrupt=True):
                self.last_spoken_ts = now
        finally:
            self.pending_text = None


class BrakeCoach(QObject):
    """0.4.8.6 Kurven-Coach: leitet aus DEINER Live-Bestlap pro harter Kurve drei
    Referenzpunkte ab - Bremspunkt, Einlenkpunkt, Gaspunkt - und sagt sie getimt an:
    Bremspunkt als Countdown (drei/zwei/eins/bremsen), Einlenken und Gas als kurze
    Einzel-Cues. Rein telemetriebasiert, kein Netz. Vorsynthetisierte Piper-Clips
    (latenzarm ueber winsound). Opt-in / F12. Einlenken und Gas einzeln abschaltbar.

    Bremspunkte/Cues stammen aus deiner schnellsten Live-Runde (live_best_reference_lap).
    Faellt diese Referenz weg, schweigt der Coach.
    """

    HARD_DROP_KMH = 40.0     # nur Bremszonen mit >= 40 km/h Tempoabbau
    BRAKE_ON = 0.55          # Bremse gilt als "an"
    BRAKE_OFF = 0.15         # Bremse gilt als "aus"
    MERGE_DIST_M = 40.0      # nahe Bremspunkte zusammenfassen
    START_LEAD_S = 3.6       # ab hier wird ein Bremspunkt aktiv verfolgt
    BRAKE_LEAD_S = 0.70      # 0.4.9.8: Standard weiter vorgezogen (war 0.45), einstellbar
    MIN_SPEED_MPS = 12.0     # darunter kein sinnvoller Countdown (Pit/langsam)

    STEER_ON = 0.14          # 0.4.8.8: hoeher gegen Fehl-Trigger durch Lenk-Noise
    TURNIN_WINDOW_M = 160.0  # Einlenkpunkt max. so weit nach dem Bremspunkt suchen
    THROTTLE_ON = 0.55       # Gas gilt als "committed" am Ausgang
    GAS_WINDOW_M = 420.0     # Gaspunkt max. so weit nach dem Bremspunkt suchen
    CUE_ARM_S = 1.2          # ab hier wird ein Einzel-Cue (Einlenken/Gas) scharf
    TURNIN_LEAD_S = 0.45     # 0.4.8.8: Einlenken frueher ansagen
    GAS_LEAD_S = 0.40        # 0.4.8.8: Gas frueher ansagen

    CLIPS = {"3": "drei", "2": "zwei", "1": "eins", "0": "bremsen",
             "T": "einlenken", "G": "Gas"}

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.enabled = False
        self.load_timing()        # 0.4.9.8: gespeicherter Vorlauf
        self.say_turnin = True    # Einlenken-Hinweis (Menue)
        self.say_gas = True       # Gas-Hinweis (Menue)
        self.corners = []         # [{"brake","entry","drop","turnin","gas"}]
        self.events = []          # flach & sortiert: [{"dist","kind"}]
        self.ref_lap = None
        self._active = None       # dist des aktuell verfolgten Events
        self._said = set()        # angesagte Marker fuer das aktive Event

    # ---- 0.4.9.8: Vorlauf laden/setzen/speichern ------------------------
    LEAD_KEYS = {"brake": "BRAKE_LEAD_S", "turnin": "TURNIN_LEAD_S", "gas": "GAS_LEAD_S"}

    def load_timing(self):
        try:
            import json
            with open(COACH_TIMING_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for kind, attr in self.LEAD_KEYS.items():
                if kind in cfg:
                    setattr(self, attr, max(0.0, min(3.0, float(cfg[kind]))))
        except Exception:
            pass

    def get_lead(self, kind):
        return float(getattr(self, self.LEAD_KEYS.get(kind, "BRAKE_LEAD_S")))

    def set_lead(self, kind, value):
        attr = self.LEAD_KEYS.get(kind)
        if not attr:
            return False
        setattr(self, attr, max(0.0, min(3.0, float(value))))
        try:
            import json
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(COACH_TIMING_PATH, "w", encoding="utf-8") as f:
                json.dump({k: self.get_lead(k) for k in self.LEAD_KEYS}, f, indent=2)
        except Exception:
            pass
        return True

    def set_enabled(self, on):
        self.enabled = bool(on)
        self._active = None
        self._said = set()
        if self.enabled:
            try:
                self.main.tts.prewarm_clips(self.CLIPS)
            except Exception:
                pass

    def has_points(self):
        return bool(self.corners)

    # ---- Referenzpunkte aus der Bestlap extrahieren ----------------------
    def set_reference_from_rows(self, rows):
        corners = self._extract_corners(rows)
        if corners:
            self.corners = corners
            self.events = self._build_events(corners)
            self.ref_lap = getattr(self.main, "live_best_reference_lap", None)

    def _extract_corners(self, rows):
        data = []
        for r in rows:
            try:
                d = float(r.lap_dist_m)
                if d >= 0:
                    data.append((d, float(r.brake), float(r.speed_kmh),
                                 abs(float(r.steering)), float(r.throttle)))
            except Exception:
                continue
        if len(data) < 200:
            return []
        data.sort(key=lambda x: x[0])
        n = len(data)
        corners = []
        armed = True
        for i in range(1, n):
            d, b, v, st, thr = data[i]
            pb = data[i - 1][1]
            if armed and pb < self.BRAKE_ON <= b:
                entry = v
                k = i - 1
                while k >= 0 and (d - data[k][0]) < 25.0:
                    entry = max(entry, data[k][2]); k -= 1
                minv = v; m = i
                while m < n and data[m][1] > self.BRAKE_OFF and (data[m][0] - d) < 400.0:
                    minv = min(minv, data[m][2]); m += 1
                if (entry - minv) >= self.HARD_DROP_KMH:
                    corners.append({
                        "brake": d, "entry": entry, "drop": entry - minv,
                        "turnin": self._find_turnin(data, i, d),
                        "gas": self._find_gas(data, i, d),
                    })
                armed = False
            elif b < self.BRAKE_OFF:
                armed = True
        # nahe Bremspunkte zusammenfassen, staerksten behalten
        corners.sort(key=lambda c: c["brake"])
        merged = []
        for c in corners:
            if merged and (c["brake"] - merged[-1]["brake"]) < self.MERGE_DIST_M:
                if c["drop"] > merged[-1]["drop"]:
                    merged[-1] = c
            else:
                merged.append(c)
        return merged

    def _find_turnin(self, data, i, brake_dist):
        # erster nennenswerter Lenkeinschlag nach dem Bremsbeginn
        n = len(data)
        j = i
        while j < n and (data[j][0] - brake_dist) < self.TURNIN_WINDOW_M:
            if data[j][3] >= self.STEER_ON and (j + 1 >= n or data[j + 1][3] >= self.STEER_ON * 0.8):
                dd = data[j][0]
                return dd if dd > brake_dist else None
            j += 1
        return None

    def _find_gas(self, data, i, brake_dist):
        # erster Gas-Punkt am Ausgang: Bremse aus UND Gas >= THROTTLE_ON
        n = len(data)
        j = i
        brake_released = False
        while j < n and (data[j][0] - brake_dist) < self.GAS_WINDOW_M:
            if data[j][1] < self.BRAKE_OFF:
                brake_released = True
            if brake_released and data[j][4] >= self.THROTTLE_ON and (j + 1 >= n or data[j + 1][4] >= self.THROTTLE_ON):
                dd = data[j][0]
                return dd if dd > brake_dist else None
            j += 1
        return None

    def _build_events(self, corners):
        ev = []
        for c in corners:
            ev.append({"dist": c["brake"], "kind": "brake"})
            if c["turnin"] is not None:
                ev.append({"dist": c["turnin"], "kind": "turnin"})
            if c["gas"] is not None:
                ev.append({"dist": c["gas"], "kind": "gas"})
        ev.sort(key=lambda e: e["dist"])
        return ev

    def _kind_enabled(self, kind):
        if kind == "turnin":
            return self.say_turnin
        if kind == "gas":
            return self.say_gas
        return True  # brake immer

    def _next_event(self, cur_dist):
        best = None
        for e in self.events:
            if e["dist"] > cur_dist and self._kind_enabled(e["kind"]):
                if best is None or e["dist"] < best["dist"]:
                    best = e
        return best

    # ---- Ansage im live_tick ---------------------------------------------
    def update(self, s):
        if not self.enabled or not self.events or s is None:
            return
        if getattr(self.main, "live_best_reference_lap", None) is None:
            return  # Referenz weg -> still
        try:
            if bool(getattr(s, "in_pits", False)):
                self._active = None; self._said = set(); return
            # 0.4.8.8: im Training auch bei ungueltiger Runde ansagen; nur im Rennen unterdruecken
            if int(getattr(s, "session_type", 0)) >= 10 and bool(getattr(s, "lap_invalidated", False)):
                self._active = None; self._said = set(); return
            cur = float(s.lap_dist_m)
            spd = float(s.speed_kmh) / 3.6
        except Exception:
            return
        if cur < 0 or spd < self.MIN_SPEED_MPS:
            self._active = None; self._said = set(); return
        ev = self._next_event(cur)
        if ev is None:
            self._active = None; self._said = set(); return
        tt = (ev["dist"] - cur) / spd
        if self._active != ev["dist"]:
            arm = (max(self.START_LEAD_S, self.BRAKE_LEAD_S + 0.6) if ev["kind"] == "brake"
                   else max(self.CUE_ARM_S, self.get_lead(ev["kind"]) + 0.4))  # 0.4.9.8
            if tt <= arm:
                self._active = ev["dist"]; self._said = set()
            else:
                return
        if ev["kind"] == "brake":
            if tt <= self.BRAKE_LEAD_S:
                self._announce("0"); return
            for mrk in (1, 2, 3):
                if (mrk - 1) < tt <= mrk:
                    self._announce(str(mrk))
                    break
        else:
            lead = self.TURNIN_LEAD_S if ev["kind"] == "turnin" else self.GAS_LEAD_S
            if tt <= lead:
                self._announce("T" if ev["kind"] == "turnin" else "G")

    def _announce(self, key):
        if key in self._said:
            return
        self._said.add(key)
        try:
            self.main.tts.play_clip(key, self.CLIPS.get(key, ""))
        except Exception:
            pass


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PitBoss – {APP_VERSION}")
        self.resize(1520, 920)
        logo_path = ASSET_DIR / "lmu_app_icon.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.reader = LMUReader()
        self.hardware_profiles = self.load_hardware_profiles()
        self.current_profile_name = self.load_last_active_profile_name()
        self.samples: List[Sample] = []
        self.lap_summaries: List[LapSummary] = []
        self.reference_lap: Optional[LapSummary] = None
        self.compare_lap: Optional[LapSummary] = None
        self.segment_deltas = []
        self.manual_reference_lap: Optional[int] = None
        self.manual_compare_lap: Optional[int] = None
        self.external_reference = None
        self.use_external_reference = False
        self.recording = False
        self.recording_signature = None
        self.rejected_sample_count = 0
        self.overlay_window = None
        self.tire_overlay_window = None
        self.pedal_overlay_window = None  # 0.4.7.1
        self.limit_overlay_window = None  # 0.4.8.7
        self.weather_overlay_window = None   # 0.4.9.0
        self.trackstate_overlay_window = None  # 0.5.9.13: Streckenzustand-Panel
        self.blindspot_overlay_window = None   # 0.5.9.13: Toter-Winkel-Overlay
        self.brake_overlay_window = None     # 0.4.9.0
        self.fuel_overlay_window = None      # 0.4.9.0
        self.ffb_overlay_window = None       # 0.4.9.0
        self.sector_tracker = SectorTracker()  # 0.4.9.0
        self.pit_overlay_window = None       # 0.4.9.1
        self.delta_overlay_window = None
        self.laptime_overlay_window = None
        self.damage_overlay_window = None
        self.overlay_style = self.load_overlay_style()  # 0.4.9.1
        self.brake_model = BrakeWearModel(config_path=str(BRAKE_MODEL_PATH))  # 0.4.9.2
        self.weather_forecast = WeatherForecastModel()  # 0.4.9.4
        self.damage_model = DamageModel(config_path=str(DAMAGE_MODEL_PATH))  # 0.4.9.4
        self.rest = LmuRestClient()  # 0.4.9.5: echte Verschleiss-/Vorhersagedaten
        self.rest.start()
        self.quota_tracker = QuotaTracker(store_path=str(EXPORT_DIR / "ai_quota_usage.json"))  # 0.4.7.1
        self.tts = SpeechEngine(config_path=str(EXPORT_DIR / "tts_config.json"))  # 0.4.7.2
        self.tire_overlay_autostart = True
        self._tire_overlay_autoshown = False
        self.auto_bestlap_export_enabled = True
        self.auto_switch_recording_enabled = True  # 0.5.9.24: Auto-Stop/Start bei Strecken-/Fahrzeugwechsel
        self.pending_switch_signature = None
        self.pending_switch_count = 0
        self.auto_bestlap_export_path = None
        self.auto_bestlap_lap_number = None
        self.auto_bestlap_time_s = None
        self.auto_bestlap_live_mode = True
        self.last_record_hotkey_ts = 0.0
        self.last_overlay_hotkey_ts = 0.0
        self.last_auto_hotkey_ts = 0.0
        self.last_snapshot_hotkey_ts = 0.0
        self.last_report_save_error = ""
        self.last_csv_save_error = ""
        self.global_hotkey_state = {"F6": False, "F7": False, "F8": False, "F9": False, "F10": False, "F11": False, "F12": False}
        self.last_tire_overlay_hotkey_ts = 0.0
        self.last_live_sample = None
        self.live_log_enabled = False  # 0.5.9.26: Live-Telemetrie-Log, unabhaengig vom Recording
        self.live_log_writer = None
        self.live_log_fh = None
        self.live_log_path = None
        self.live_log_row_count = 0
        self.live_smooth_lap_time = None  # 0.5.9.26: eigener Echtzeit-Rundentimer, s.u.
        self._live_clock_anchor_raw = None
        self._live_clock_anchor_ts = None
        self._live_clock_lap = None
        self.live_lap_number = None
        self.live_lap_samples: List[Sample] = []
        self.live_delta_s = None
        self.live_coach_line = "Referenz laden"
        self.live_coach_enabled = False  # 0.4.8.4: Live-Sprach-Coaching (opt-in)
        self.live_coach = LiveCoach(self)  # 0.4.8.4
        self.brake_coach_enabled = False  # 0.4.8.5: Brems-Countdown (opt-in)
        self.brake_coach = BrakeCoach(self)  # 0.4.8.5
        self.live_best_reference_segments = {}
        self.live_best_reference_lap = None
        self.live_best_reference_time_s = None
        self.personal_laptime_reference = self.load_personal_laptime_reference()
        self.personal_laptime_reference_tracks = self.load_personal_laptime_reference_tracks()  # 0.5.9.21: Tier-Format
        self.personal_reference_source = str(PERSONAL_LAPTIME_REFERENCE_PATH) if PERSONAL_LAPTIME_REFERENCE_PATH.exists() else "nicht geladen"
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(100)
        self.live_timer.timeout.connect(self.live_tick)
        self.live_timer.start()
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # 10 Hz live recorder
        self.timer.timeout.connect(self.capture_tick)

        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        self._root = root
        self._theme = self._load_theme()
        self.apply_theme(self._theme)
        header = QHBoxLayout()
        logo = QLabel()
        logo_path = ASSET_DIR / "lmu_header_logo.png"
        if logo_path.exists():
            logo.setPixmap(QPixmap(str(logo_path)).scaled(196, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo.setMinimumWidth(200)
            logo.setStyleSheet("background:#0a0d13; border-radius:8px; padding:4px;")  # 0.5.3.0: kompakter
        header.addWidget(logo)
        head_text = QVBoxLayout()
        title = QLabel("PitBoss")
        title.setStyleSheet("font-size:27px;font-weight:800;letter-spacing:0.5px;")
        subtitle = QLabel(f"{APP_VERSION} – Rundenzeiten-Referenz (Skill-Level)")
        subtitle.setStyleSheet("font-size:13px;color:#8a97a8;letter-spacing:0.3px;")
        subtitle.setWordWrap(True)
        head_text.addWidget(title); head_text.addWidget(subtitle)
        header.addLayout(head_text, stretch=1)
        # 0.4.9.3: JCM-Motorsport-Logo oben rechts
        self.jcm_logo = QLabel()
        jcm_path = ASSET_DIR / "jcm_logo.png"
        if jcm_path.exists():
            self.jcm_logo.setPixmap(QPixmap(str(jcm_path)).scaled(
                112, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.jcm_logo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._style_jcm_logo()
            header.addWidget(self.jcm_logo, alignment=Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(header)

        refbox = QGroupBox("Optional/Debug: SimHub-Werte zum Vergleich eintragen")
        grid = QGridLayout(refbox)
        self.ref_speed = QLineEdit(); self.ref_gear = QLineEdit(); self.ref_fuel = QLineEdit(); self.ref_rpm = QLineEdit()
        self.ref_throttle = QLineEdit(); self.ref_brake = QLineEdit(); self.ref_steer = QLineEdit(); self.ref_trackm = QLineEdit()
        labels = ["Speed km/h", "Gear", "Fuel L", "RPM", "Throttle", "Brake", "Steering", "Track m"]
        edits = [self.ref_speed, self.ref_gear, self.ref_fuel, self.ref_rpm, self.ref_throttle, self.ref_brake, self.ref_steer, self.ref_trackm]
        for i, (lab, edit) in enumerate(zip(labels, edits)):
            grid.addWidget(QLabel(lab), i // 4, (i % 4) * 2)
            grid.addWidget(edit, i // 4, (i % 4) * 2 + 1)
        refbox.setVisible(False)
        layout.addWidget(refbox)

        buttons = QHBoxLayout()
        self.btn_snapshot = QPushButton("Snapshot lesen")
        self.btn_record = QPushButton("Recording starten")
        self.btn_record.setStyleSheet(  # 0.5.4.0: Kfz-Motor-Startknopf
            "QPushButton { background:#c1272d; color:#fff; font-weight:800; font-size:15px;"
            " border:2px solid #7a1519; border-radius:22px; padding:10px 24px; }"
            "QPushButton:hover { background:#d83a3f; }"
            "QPushButton:pressed { background:#8f1d22; }")
        self.btn_stop = QPushButton("Recording stoppen")
        self.btn_report = QPushButton("Report speichern")
        self.btn_csv = QPushButton("CSV speichern")
        self.btn_clear = QPushButton("Löschen")
        self.btn_export = QPushButton("Export-Ordner öffnen")
        self.btn_ref_export = QPushButton("Referenz exportieren")
        self.btn_ref_import = QPushButton("Referenz importieren")
        self.btn_pb_reference = QPushButton("PB-Referenz laden")
        self.btn_overlay = QPushButton("Monitor-Overlay")
        self.btn_tire_overlay = QPushButton("Reifen-Overlay")
        self.btn_pedal_overlay = QPushButton("Pedal-Overlay")  # 0.4.7.1
        self.btn_auto_bestlap = QPushButton("Auto-Bestlap: AN")
        self.btn_auto_switch = QPushButton("Auto-Wechsel: AN")  # 0.5.9.24
        self.btn_live_log = QPushButton("Live-Log: AUS")  # 0.5.9.26
        self.btn_live_log.setToolTip(
            "Zeichnet die komplette rohe Live-Telemetrie (unabhaengig vom normalen "
            "Recording) laufend in eine CSV auf \u2013 z.B. um ein konkretes Overlay-\n"
            "Problem exakt nachzuvollziehen. Datei liegt in Dokumente\\PitBoss\\csv."
        )
        # 0.4.8.1: Recording als Toggle, Overlays als Dropdown, Snapshot automatisch/manuell im Menue
        primary = [self.btn_record, self.btn_report]
        overflow = [self.btn_snapshot, self.btn_stop, self.btn_csv, self.btn_ref_export, self.btn_ref_import, self.btn_pb_reference, self.btn_auto_bestlap, self.btn_auto_switch, self.btn_live_log, self.btn_overlay, self.btn_tire_overlay, self.btn_pedal_overlay, self.btn_export, self.btn_clear]
        for b in primary:
            buttons.addWidget(b)
        for b in overflow:
            buttons.addWidget(b)
            b.setVisible(False)
        from PySide6.QtWidgets import QToolButton, QMenu
        self.btn_overlays = QToolButton()
        self.btn_overlays.setText("Overlays  \u25be")
        self.btn_overlays.setPopupMode(QToolButton.InstantPopup)
        # 0.4.8.2: btn_overlays erbt Theme-Style
        _ov = QMenu(self.btn_overlays)
        _ov.addAction("Reifen-Overlay", self.toggle_tire_overlay)
        _ov.addAction("Pedal-Overlay", self.toggle_pedal_overlay)
        _ov.addAction("Monitor-Overlay", self.toggle_overlay)
        _ov.addSeparator()
        _ov.addAction("Rundenzeiten (Delta/Prognose)", self.toggle_laptime_overlay)
        _ov.addAction("Rundenzeiten-Graph", self.toggle_lapgraph_overlay)
        _ov.addAction("Flaggen (auto bei Flagge)", self.toggle_flag_overlay)
        _ov.addAction("Überholalarm (hinten)", self.toggle_overtake_overlay)
        _ov.addAction("Abstand & Distanz", self.toggle_delta_overlay)
        _ov.addAction("Boxenstopp", self.toggle_pit_overlay)
        _ov.addAction("Fahrzeugsch\u00e4den", self.toggle_damage_overlay)
        _ov.addAction("Streckenzustand (Wetter/Temp)", self.toggle_weather_overlay)
        _ov.addAction("Streckenzustand-Panel (kompakt)", self.toggle_trackstate_overlay)  # 0.5.9.13
        _ov.addAction("Toter Winkel", self.toggle_blindspot_overlay)  # 0.5.9.13
        self.act_blindspot_flip = _ov.addAction("Toter Winkel: Seiten spiegeln")  # 0.5.9.13
        self.act_blindspot_flip.setCheckable(True)
        self.act_blindspot_flip.setChecked(BlindSpotOverlayWindow._load_flip())
        self.act_blindspot_flip.toggled.connect(self.set_blindspot_flip)
        _ov.addAction("Bremstemperaturen (inkl. Verschlei\u00df-Sch\u00e4tzung)", self.toggle_brake_overlay)
        _ov.addAction("Kraftstoff", self.toggle_fuel_overlay)
        _ov.addAction("Force Feedback", self.toggle_ffb_overlay)
        _ov.addAction("Limit-Meter", self.toggle_limit_overlay)
        _ov.addSeparator()
        _stylemenu = _ov.addMenu("Design aller Overlays")
        self.overlay_style_actions = {}
        for _key, _label in (("transparent", "Transparent (durchscheinend)"),
                             ("dark", "Deckend dunkel"),
                             ("light", "Deckend hell")):
            _a = _stylemenu.addAction(_label)
            _a.setCheckable(True)
            _a.setChecked(getattr(self, "overlay_style", "transparent") == _key)
            _a.triggered.connect(lambda _c=False, k=_key: self.set_overlay_style(k))
            self.overlay_style_actions[_key] = _a
        self.btn_overlays.setMenu(_ov)
        buttons.addWidget(self.btn_overlays)
        # 0.5.4.0: Coaching-Schalter in eigenen "Coach"-Button
        self.btn_coach = QToolButton()
        self.btn_coach.setText("Coach  ▾")
        self.btn_coach.setPopupMode(QToolButton.InstantPopup)
        _coach = QMenu(self.btn_coach)
        self.act_live_coach = _coach.addAction("Live-Coach (Sprachhinweise)")
        self.act_live_coach.setCheckable(True)
        self.act_live_coach.setChecked(self.live_coach_enabled)
        self.act_live_coach.toggled.connect(self.set_live_coach_enabled)
        self.act_brake_coach = _coach.addAction("Kurven-Coach: Bremsen/Einlenken/Gas (F12)")
        self.act_brake_coach.setCheckable(True)
        self.act_brake_coach.setChecked(self.brake_coach_enabled)
        self.act_brake_coach.toggled.connect(self.set_brake_coach_enabled)
        self.act_cue_turnin = _coach.addAction("   • Einlenken-Hinweis")
        self.act_cue_turnin.setCheckable(True)
        self.act_cue_turnin.setChecked(self.brake_coach.say_turnin)
        self.act_cue_turnin.toggled.connect(lambda on: setattr(self.brake_coach, "say_turnin", bool(on)))
        self.act_cue_gas = _coach.addAction("   • Gas-Hinweis")
        self.act_cue_gas.setCheckable(True)
        self.act_cue_gas.setChecked(self.brake_coach.say_gas)
        self.act_cue_gas.toggled.connect(lambda on: setattr(self.brake_coach, "say_gas", bool(on)))
        _coach.addSeparator()
        _coach.addAction("Ansage-Vorlauf …", self.set_coach_lead_all)  # 0.5.8.0: ein Dialog, drei Slider
        _coach.addSeparator()
        _coach.addAction("Setup-Coach (eigenes Fenster) …", self.open_setup_coach_window)  # 0.5.9.0
        self.btn_coach.setMenu(_coach)
        buttons.addWidget(self.btn_coach)

        # 0.5.4.0: "Mehr" nur noch Datei-/Aufnahme-Aktionen
        self.btn_more = QToolButton()
        self.btn_more.setText("Mehr  ▾")
        self.btn_more.setPopupMode(QToolButton.InstantPopup)
        _more = QMenu(self.btn_more)
        _more.addAction("CSV speichern", self.btn_csv.click)
        _more.addAction("Referenz exportieren", self.btn_ref_export.click)
        _more.addAction("Referenz importieren", self.btn_ref_import.click)
        _more.addAction("PB-Referenz laden", self.btn_pb_reference.click)
        _more.addSeparator()
        _more.addAction("Auto-Bestlap umschalten", self.btn_auto_bestlap.click)
        _more.addAction("Auto-Wechsel umschalten", self.btn_auto_switch.click)
        _more.addAction("Live-Log umschalten", self.btn_live_log.click)
        _more.addAction("Snapshot lesen (manuell)", lambda: self.snapshot())
        _more.addSeparator()
        _more.addAction("Export-Ordner öffnen", self.btn_export.click)
        _more.addAction("Aufzeichnung löschen", self.btn_clear.click)
        self.btn_more.setMenu(_more)
        buttons.addWidget(self.btn_more)

        # 0.5.4.0: Einstellungen in eigenem Fenster
        self.btn_settings = QToolButton()
        self.btn_settings.setText("Einstellungen")
        self.btn_settings.clicked.connect(self.open_settings_window)
        buttons.addWidget(self.btn_settings)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        setup_bar = QHBoxLayout()
        setup_bar.addWidget(QLabel("Setup:"))
        self.setup_selector = QComboBox()
        self.setup_selector.setEditable(True)
        self.setup_selector.addItems([
            "nicht gesetzt / LMU-Setup",
            "Baseline",
            "Race",
            "Quali",
            "Stable/Safe",
            "Custom"
        ])
        self.setup_selector.setMinimumWidth(420)
        self.setup_selector.lineEdit().setPlaceholderText("Setup manuell eintragen, z. B. Arnout Race, Quali, Stable …")
        self.setup_selector.setToolTip("Manuelle Setup-Dokumentation: erscheint im Dashboard, Report und Referenzexport. LMU liefert den Setup-Dateinamen nicht zuverlässig per Shared Memory.")
        setup_bar.addWidget(self.setup_selector)
        self.btn_fahrer_hardware = QPushButton("Fahrer & Hardware")
        self.btn_fahrer_hardware.setToolTip("Zur Ansicht Fahrer & Hardware wechseln.")
        setup_bar.addWidget(self.btn_fahrer_hardware)
        self.btn_ki_analyse = QPushButton("KI-Analyse")
        self.btn_ki_analyse.setToolTip("KI-Analyse (Gemini) in eigenem Fenster oeffnen.")
        setup_bar.addWidget(self.btn_ki_analyse)
        setup_bar.addStretch(1)
        layout.addLayout(setup_bar)

        driver_bar = QHBoxLayout()
        driver_bar.addWidget(QLabel("Fahrer-Profil:"))
        self.driver_profile_selector = QComboBox()
        self.driver_profile_selector.setEditable(True)
        self.driver_profile_selector.addItems(list(self.hardware_profiles.keys()))
        if self.current_profile_name in self.hardware_profiles:
            self.driver_profile_selector.setCurrentText(self.current_profile_name)
        self.driver_profile_selector.setMinimumWidth(260)
        self.driver_profile_selector.setToolTip("Fahrer-/Hardwareprofil wählen. Wird im Report gespeichert und später für Hardware-Coaching genutzt.")
        driver_bar.addWidget(self.driver_profile_selector)
        self.btn_profile_new = QPushButton("Profil neu")
        self.btn_profile_load = QPushButton("Profil laden")
        self.btn_profile_save = QPushButton("Profil speichern")
        self.btn_profile_delete = QPushButton("Profil löschen")
        self.btn_profile_load.setToolTip("driver_hardware_profiles.json oder ein einzelnes Profil-JSON importieren. Bestehende Profile werden nicht überschrieben.")
        # 0.4.8.2: vier Profil-Buttons als ein Dropdown
        from PySide6.QtWidgets import QToolButton as _QTB, QMenu as _QMenu
        self.btn_profile_menu = _QTB()
        self.btn_profile_menu.setText("Profil  \u25be")
        self.btn_profile_menu.setPopupMode(_QTB.InstantPopup)
        _pm = _QMenu(self.btn_profile_menu)
        _pm.addAction("Profil neu", self.btn_profile_new.click)
        _pm.addAction("Profil laden", self.btn_profile_load.click)
        _pm.addAction("Profil speichern", self.btn_profile_save.click)
        _pm.addAction("Profil l\u00f6schen", self.btn_profile_delete.click)
        self.btn_profile_menu.setMenu(_pm)
        driver_bar.addWidget(self.btn_profile_menu)
        driver_bar.addStretch(1)
        layout.addLayout(driver_bar)

        self.status = QLabel("Bereit. LMU starten, ins Auto gehen, Snapshot lesen.")
        layout.addWidget(self.status)
        # 0.4.8.3: Standard-Rundenzeit-Referenz (Skill-Level) aus laptimes-Snapshot
        import laptimes as _lt
        self._lt = _lt
        std_bar = QHBoxLayout()
        std_bar.addWidget(QLabel("Referenz-Zeiten \u2013 Klasse"))
        self.std_class = QComboBox(); self.std_class.addItems(_lt.CLASSES)
        std_bar.addWidget(self.std_class)
        std_bar.addWidget(QLabel("Strecke"))
        self.std_track = QComboBox()
        std_bar.addWidget(self.std_track, 1)
        std_bar.addWidget(QLabel("Level"))
        self.std_level = QComboBox(); self.std_level.addItems([n for n, _f in _lt.LEVELS])
        std_bar.addWidget(self.std_level)
        std_bar.addWidget(QLabel("Ziel-Rundenzeit:"))
        self.std_target = QLabel("--:--.--")
        self.std_target.setObjectName("accentValue")
        std_bar.addWidget(self.std_target)
        self.std_live = QLabel("")  # 0.5.7.0: Live-Strecken-Zuordnung
        std_bar.addWidget(self.std_live)
        std_bar.addStretch(1)
        layout.addLayout(std_bar)
        self.standard_ref_time_s = 0.0
        self._std_reload_tracks()
        self._load_standard_reference_selection()
        self.std_class.currentTextChanged.connect(lambda _t: (self._std_reload_tracks(), self._update_standard_reference()))
        self.std_track.currentTextChanged.connect(lambda _t: self._update_standard_reference())
        self.std_level.currentTextChanged.connect(lambda _t: self._update_standard_reference())
        self._update_standard_reference()

        self.tabs = QTabWidget()
        self.coach_tabs = QTabWidget()  # 0.5.0.0: Coach-Views gebuendelt
        layout.addWidget(self.tabs, stretch=6)

        dash_tab = QWidget(); dash_layout = QVBoxLayout(dash_tab)
        self.dash_cards = {}
        card_grid = QGridLayout()
        for i, key in enumerate(["Verbindung", "Recording", "Runden", "Fahrer", "Setup", "Referenz", "Ext. Referenz", "PB-Bereich", "Auto-Bestlap", "Reifen", "Vergleich", "Coach-Fokus"]):
            frame = QFrame(); frame.setFrameShape(QFrame.StyledPanel)
            frame.setObjectName("dashCard")
            fl = QVBoxLayout(frame)
            lab = QLabel(key); lab.setObjectName("dashCardKey")
            val = QLabel("—"); val.setObjectName("dashCardVal"); val.setWordWrap(True)
            fl.addWidget(lab); fl.addWidget(val)
            self.dash_cards[key] = val
            card_grid.addWidget(frame, i // 3, i % 3)
        dash_layout.addLayout(card_grid)
        self.dash_coach = QTextEdit(); self.dash_coach.setReadOnly(True)
        self.dash_coach.setMinimumHeight(250)
        self.dash_coach.setStyleSheet("font-size:15px; line-height:1.35;")
        dash_layout.addWidget(QLabel("Aktueller Coach-Fokus"))
        dash_layout.addWidget(self.dash_coach)
        self.tabs.addTab(dash_tab, "Dashboard")

        live_tab = QWidget(); live_layout = QVBoxLayout(live_tab)
        self.trackmap = TrackMapWidget()
        live_layout.addWidget(self.trackmap, stretch=2)
        self.live_summary = QTableWidget(0, 8)
        self.live_summary.setHorizontalHeaderLabels([
            "Aktuelle Runde", "Track m", "Speed", "Gang", "Fuel", "Letzte Runde", "Beste Runde", "Status"
        ])
        self.live_summary.horizontalHeader().setStretchLastSection(True)
        live_layout.addWidget(QLabel("Live-Übersicht: bewusst nur Runden-/Statusdaten. 50-m-Sektoren bleiben intern. Monitor-Overlay über F10/Button, Reifen-Overlay über F6/Button öffnen."))
        self.sector_label = QLabel("Sektorzeiten: warte auf erste vollst\u00e4ndige Runde \u2026")  # 0.4.9.0
        self.sector_label.setWordWrap(True)
        live_layout.addWidget(self.sector_label)
        self.brake_status_label = QLabel("Bremsen: warte auf Telemetrie \u2026")  # 0.4.9.4
        self.brake_status_label.setWordWrap(True)
        live_layout.addWidget(self.brake_status_label)
        live_layout.addWidget(self.live_summary, stretch=1)
        self.tabs.addTab(live_tab, "Live")

        tires_tab = QWidget(); tires_layout = QVBoxLayout(tires_tab)
        tires_layout.addWidget(QLabel("Reifenanalyse live aus LMU Shared Memory. Temperaturen außen/mitte/innen pro Reifen, Druck in kPa und bar, Wear/Restwert, Bremsplatten-/ABS-Warnung und Sturz-/Druck-Hinweise."))
        self.tire_table = QTableWidget(0, 10)
        self.tire_table.setHorizontalHeaderLabels(["Reifen", "Druck kPa", "Druck bar", "Temp außen", "Temp mitte", "Temp innen", "Carcass", "Wear/Rest %", "Flat/ABS", "Hinweis"])
        self.tire_table.horizontalHeader().setStretchLastSection(True)
        tires_layout.addWidget(self.tire_table)
        self.tire_note = QLabel("Noch keine Reifendaten.")
        self.tire_note.setWordWrap(True)
        tires_layout.addWidget(self.tire_note)
        self.tabs.addTab(tires_tab, "Reifen")

        setup_tab = QWidget(); setup_layout = QVBoxLayout(setup_tab)
        setup_layout.addWidget(QLabel("Reifen-/Setup-Coach 4.4: erzeugt konkrete Hinweise aus Temperatur-Spread, Druckentwicklung, Wear/Rest und Temperatur-/Druckverlauf. Werte sind Empfehlungen, keine automatische Setup-Änderung."))
        _btn_setupwin = QPushButton("▸ Setup-Coach in eigenem Fenster öffnen (mit echtem Setup aus LMU)")  # 0.5.9.0
        _btn_setupwin.setObjectName("primary")
        _btn_setupwin.clicked.connect(self.open_setup_coach_window)
        setup_layout.addWidget(_btn_setupwin)
        self.setup_coach_text = QTextEdit(); self.setup_coach_text.setReadOnly(True)
        self.setup_coach_text.setMinimumHeight(360)
        self.setup_coach_text.setStyleSheet("font-size:15px; line-height:1.35;")
        setup_layout.addWidget(self.setup_coach_text)
        self.coach_tabs.addTab(setup_tab, "Setup-Coach")

        analysis_tab = QWidget(); analysis_layout = QVBoxLayout(analysis_tab)
        self.zone_table = QTableWidget(0, 7)
        self.zone_table.setHorizontalHeaderLabels(["Zone", "Bereich", "Verlust", "Priorität", "Diagnose", "Handlung", "Speed Diff"])
        self.zone_table.horizontalHeader().setStretchLastSection(True)
        analysis_layout.addWidget(QLabel("Analyse: sichtbare Coach-Zonen statt 50-m-Sektorflut. Die Detailsektoren werden nur noch intern und im Report genutzt."))
        analysis_layout.addWidget(self.zone_table)
        self.segment_table = QTableWidget(0, 9)
        self.segment_table.setHorizontalHeaderLabels(["Sektor", "Meter", "Samples", "Avg Speed", "Min Speed", "Max Brake", "Avg Thr", "Gear häufig", "Hinweis"])
        self.segment_table.setVisible(False)
        analysis_layout.addWidget(self.segment_table)
        self.tabs.addTab(analysis_tab, "Analyse")

        laps_tab = QWidget(); laps_layout = QVBoxLayout(laps_tab)
        laps_layout.addWidget(QLabel("Rundenübersicht: S1/S2/S3 sind stabile interne Streckendrittel aus Speed/Lap-Distanz. Grün = bester Wert, Rot = schwächster gültiger Wert."))
        self.lap_overview_table = QTableWidget(0, 8)
        self.lap_overview_table.setHorizontalHeaderLabels([
            "Lap", "S1", "S2", "S3", "Rundenzeit", "Min", "Max", "Durchschn."
        ])
        self.lap_overview_table.horizontalHeader().setStretchLastSection(True)
        self.lap_overview_table.setMinimumHeight(500)
        self.lap_overview_table.setAlternatingRowColors(True)
        self.lap_overview_table.verticalHeader().setDefaultSectionSize(30)
        laps_layout.addWidget(self.lap_overview_table, stretch=7)

        detail_label = QLabel("Detaildaten / Clean-Lap-Filter: Outlap/Pit/Standphase wird aussortiert. Beste gültige Runde wird als Referenz markiert.")
        detail_label.setMaximumHeight(22)
        laps_layout.addWidget(detail_label)
        self.laps_table = QTableWidget(0, 13)
        self.laps_table.setHorizontalHeaderLabels([
            "Lap", "Status", "Grund", "Samples", "Coverage m", "Dauer", "Max Speed",
            "Avg Speed", "Max Brake", "Fuel Used", "Start m", "End m", "Stand/Pit"
        ])
        self.laps_table.horizontalHeader().setStretchLastSection(True)
        self.laps_table.setMaximumHeight(170)
        self.laps_table.setMinimumHeight(90)
        self.laps_table.verticalHeader().setDefaultSectionSize(22)
        laps_layout.addWidget(self.laps_table, stretch=0)
        self.tabs.addTab(laps_tab, "Runden")

        compare_tab = QWidget(); compare_layout = QVBoxLayout(compare_tab)
        compare_layout.addWidget(QLabel("Lap-vs-Referenz: positive Delta-Werte bedeuten Zeitverlust gegenüber der Referenzrunde."))
        compare_controls = QHBoxLayout()
        compare_controls.addWidget(QLabel("Referenz:"))
        self.ref_lap_combo = QComboBox(); self.ref_lap_combo.addItem("Auto", None)
        compare_controls.addWidget(self.ref_lap_combo)
        compare_controls.addWidget(QLabel("Vergleich:"))
        self.cmp_lap_combo = QComboBox(); self.cmp_lap_combo.addItem("Auto", None)
        compare_controls.addWidget(self.cmp_lap_combo)
        self.btn_apply_laps = QPushButton("Auswahl anwenden")
        compare_controls.addWidget(self.btn_apply_laps)
        self.btn_compare_import_ref = QPushButton("Referenz importieren")
        compare_controls.addWidget(self.btn_compare_import_ref)
        compare_controls.addStretch(1)
        compare_layout.addLayout(compare_controls)
        self.compare_table = QTableWidget(0, 13)
        self.compare_table.setHorizontalHeaderLabels([
            "Sektor", "Meter", "Vergleich", "Referenz", "Delta s", "Vgl Zeit", "Ref Zeit",
            "Vgl Avg", "Ref Avg", "Speed Diff", "Brake Diff", "Throttle Diff", "Hinweis"
        ])
        self.compare_table.horizontalHeader().setStretchLastSection(True)
        compare_layout.addWidget(self.compare_table)
        self.tabs.addTab(compare_tab, "Vergleich")

        heatmap_tab = QWidget(); heatmap_layout = QVBoxLayout(heatmap_tab)
        heatmap_layout.addWidget(QLabel("Trackmap-Heatmap: Vergleichsrunde gegen Referenz. Rot/Orange = Verlust, Grün = besser, Kreise = Coach-Zonen."))
        self.heatmap_metric_combo = QComboBox()
        self.heatmap_metric_combo.addItems(["Färbung: Delta (Zeitverlust)", "Färbung: Pedal-Input (Gas/Bremse)",
                                           "Färbung: Linienabweichung (Meter)", "Färbung: Gang & Drehzahl"])
        self.heatmap_metric_combo.currentIndexChanged.connect(
            lambda i: self.heatmap.set_heat_metric({1: "pedal", 2: "line", 3: "gear"}.get(i, "delta")))
        heatmap_layout.addWidget(self.heatmap_metric_combo)
        self.heatmap = TrackMapWidget()
        self.heatmap.setMinimumHeight(420)
        heatmap_layout.addWidget(self.heatmap, stretch=1)
        self.heatmap_note = QLabel("Nach Recording-Stopp oder Rundenauswahl wird die Heatmap automatisch aktualisiert.")
        self.heatmap_note.setWordWrap(True)
        heatmap_layout.addWidget(self.heatmap_note)
        self.tabs.addTab(heatmap_tab, "Heatmap")

        coach_tab = QWidget(); coach_layout = QVBoxLayout(coach_tab)
        coach_layout.addWidget(QLabel("Coach-Hinweise: zusammenhängende Kurven-/Bremszonen mit kumuliertem Verlust, Priorität und klarer Fahranweisung."))
        self.coach_text = QTextEdit(); self.coach_text.setReadOnly(True); self.coach_text.setStyleSheet("font-size:15px; line-height:1.35;")
        coach_layout.addWidget(self.coach_text)
        self.coach_tabs.addTab(coach_tab, "Coach")

        limit_tab = QWidget(); limit_layout = QVBoxLayout(limit_tab)
        limit_layout.addWidget(QLabel("Fahr-Limit-Coach 0.4.5.4: kombiniert Vergleichszonen, Gas/Bremse, Rollenphase und Reifen-/Lockup-Status zu einem Limit-Level."))
        self.limit_coach_text = QTextEdit(); self.limit_coach_text.setReadOnly(True); self.limit_coach_text.setStyleSheet("font-size:15px; line-height:1.35;")
        limit_layout.addWidget(self.limit_coach_text, stretch=1)
        self.coach_tabs.addTab(limit_tab, "Limit-Coach")

        input_tab = QWidget(); input_layout = QVBoxLayout(input_tab)
        input_layout.addWidget(QLabel("Input-Coach: zeichnet Gas- und Bremsverhalten pro Runde auf. Ziel: spätere Coaching-Sessions zu Bremspunkt, Bremslösung, Rollenphase und Gasannahme."))
        self.input_table = QTableWidget(0, 9)
        self.input_table.setHorizontalHeaderLabels(["Lap", "Max Bremse", "Ø Bremse", "Hartbrems.", "Löse-Sprünge", "Gas-Sprünge", "Rollen %", "Überlapp %", "Hinweis"])
        self.input_table.horizontalHeader().setStretchLastSection(True)
        self.input_table.setMinimumHeight(280)
        input_layout.addWidget(self.input_table, stretch=2)
        self.input_coach_text = QTextEdit(); self.input_coach_text.setReadOnly(True); self.input_coach_text.setStyleSheet("font-size:15px; line-height:1.35;")
        input_layout.addWidget(self.input_coach_text, stretch=1)
        self.coach_tabs.addTab(input_tab, "Input-Coach")
        self.tabs.addTab(self.coach_tabs, "Coach")  # 0.5.0.0: gebuendelte Coach-Ansicht
        self.coach_tabs.setCurrentWidget(coach_tab)  # Standard: Haupt-Coach

        hw_tab = QWidget(); hw_layout = QVBoxLayout(hw_tab)
        hw_layout.addWidget(QLabel("Fahrer-/Hardware-Profil: allgemein nutzbar für Teamkollegen. Settings-Screenshots werden ins Profil kopiert und für spätere KI-Auswertung vorbereitet."))
        self.hw_edits = {}
        hw_grid = QGridLayout()
        hw_specs = [
            ("driver_name", "Fahrername", "z. B. Marcel / Xkinect / MiCa"),
            ("team", "Team/Handle", "z. B. JCM / PM_76"),
            ("wheelbase", "Lenkradbasis", "Simucube, Fanatec, Moza, Asetek, Logitech …"),
            ("wheel_settings", "FFB/Lenkung Settings", "Stärke, Damping, Friction, Slew Rate, Rotation …"),
            ("wheel_settings_screenshot", "Screenshot Lenkrad/FFB", "Bilddatei mit TrueDrive/Fanatec/Moza/FFB-Settings …"),
            ("pedals", "Pedale", "Simsonn, Heusinkveld, Fanatec, Asetek …"),
            ("brake_setup", "Brems-Setup", "Elastomere/Federn, Max-Kraft, Weg, Kalibrierung …"),
            ("pedal_settings_screenshot", "Screenshot Pedale", "Bilddatei mit Pedal-Kalibrierung/Bremskurve …"),
            ("brake_curve", "Bremskurve", "linear/progressiv, Deadzone, Gamma …"),
            ("throttle_setup", "Gas-Setup", "linear/progressiv, Deadzone, Feder, Weg …"),
            ("haptics", "Haptik", "HF8, Buttkicker, SimHub, keine …"),
            ("buttonbox", "Buttonbox 1 / Stream Deck", "Stream Deck, Buttonbox, Arduino, keine …"),
            ("buttonbox_2", "Buttonbox 2", "zweite Buttonbox, DDU, Zusatzpanel …"),
            ("buttonbox_3", "Buttonbox 3", "dritte Buttonbox / weiteres Eingabegerät …"),
            ("shifter", "Shifter/Handbremse", "sequentiell, H-Pattern, Handbremse, keine …"),
            ("display", "Anzeige", "VR, Triple, Ultrawide, Monitor …"),
            ("notes", "Notizen", "Besonderheiten, Verletzungen, Vorlieben …"),
        ]
        hw_dropdowns = {
            "wheelbase": ["", "Simucube 2 Sport", "Simucube 2 Pro", "Simucube 2 Ultimate", "Fanatec CSL DD", "Fanatec GT DD Pro", "Fanatec ClubSport DD", "Fanatec Podium DD1", "Fanatec Podium DD2", "Moza R5", "Moza R9", "Moza R12", "Moza R16", "Moza R21", "Asetek La Prima", "Asetek Forte", "Asetek Invicta", "SIMAGIC Alpha Mini", "SIMAGIC Alpha", "SIMAGIC Alpha Ultimate", "Logitech G Pro Wheel", "Thrustmaster T300", "Thrustmaster T818", "VRS DirectForce Pro", "Cammus", "Sonstige"],
            "pedals": ["", "Simsonn Plus", "Simsonn Plus X", "Simjack Pro", "Heusinkveld Sprint", "Heusinkveld Ultimate+", "Fanatec CSL Pedals LC", "Fanatec ClubSport V3", "Moza SR-P", "Moza CRP", "Asetek La Prima", "Asetek Forte", "Asetek Invicta", "SIMAGIC P1000", "SIMAGIC P2000", "VRS Pedals", "Venym Atrax", "Logitech G Pro Pedals", "Thrustmaster T-LCM", "Sonstige"],
            "brake_curve": ["", "linear", "leicht progressiv", "progressiv", "stark progressiv", "custom", "unbekannt"],
            "throttle_setup": ["", "linear", "leicht progressiv", "progressiv", "weicher Anfang", "Deadzone klein", "custom", "unbekannt"],
            "haptics": ["", "keine", "HF8", "Buttkicker", "Dayton/Nobsound", "SimHub Haptics", "Sonstige"],
            "buttonbox": ["", "keine", "Stream Deck Mini", "Stream Deck MK.2", "Stream Deck XL", "Buttonbox USB", "Arduino/DIY", "Leo Bodnar", "DDU", "Sonstige"],
            "buttonbox_2": ["", "keine", "Stream Deck Mini", "Stream Deck MK.2", "Stream Deck XL", "Buttonbox USB", "Arduino/DIY", "Leo Bodnar", "DDU", "Sonstige"],
            "buttonbox_3": ["", "keine", "Stream Deck Mini", "Stream Deck MK.2", "Stream Deck XL", "Buttonbox USB", "Arduino/DIY", "Leo Bodnar", "DDU", "Sonstige"],
            "shifter": ["", "keine", "Fanatec SQ", "SHH Shifter", "Thrustmaster TH8A", "Moza HGP", "Simagic DS-8X", "sequentiell", "H-Pattern", "Handbremse", "Sonstige"],
            "display": ["", "VR - Meta Quest 3", "VR - Meta Quest 2", "VR - Pimax", "VR - HP Reverb G2", "VR - Valve Index", "Single Monitor", "Ultrawide", "Triple Screen", "Sonstige"],
        }
        for i, (key, label, ph) in enumerate(hw_specs):
            hw_grid.addWidget(QLabel(label + ":"), i, 0)
            if key in hw_dropdowns:
                edit = QComboBox(); edit.setEditable(True); edit.addItems(hw_dropdowns[key]); edit.setToolTip("Links auf das Pfeilsymbol klicken oder eigenen Text eintippen.")
                if edit.lineEdit(): edit.lineEdit().setAlignment(Qt.AlignLeft)
                edit.setPlaceholderText(ph)
                self.hw_edits[key] = edit
                hw_grid.addWidget(edit, i, 1)
            elif key in ("wheel_settings_screenshot", "pedal_settings_screenshot"):
                edit = QLineEdit(); edit.setPlaceholderText(ph); edit.setReadOnly(False); edit.setToolTip("Pfad zum gespeicherten Profil-Screenshot. Bild wählen kopiert die Datei ins Profilverzeichnis.")
                btn = QPushButton("Bild wählen")
                btn.setToolTip("Screenshot/Bilddatei auswählen. Die Datei wird in den Profil-Assets-Ordner kopiert.")
                btn.clicked.connect(lambda _checked=False, k=key: self.select_settings_screenshot(k))
                row = QHBoxLayout(); row.setContentsMargins(0,0,0,0)
                row.addWidget(edit, stretch=1); row.addWidget(btn)
                cell = QWidget(); cell.setLayout(row)
                self.hw_edits[key] = edit
                hw_grid.addWidget(cell, i, 1)
            else:
                edit = QLineEdit(); edit.setPlaceholderText(ph)
                self.hw_edits[key] = edit
                hw_grid.addWidget(edit, i, 1)
        hw_grid.addWidget(QLabel("Pedal-Typ:"), len(hw_specs), 0)
        self.hw_pedal_type = QComboBox(); self.hw_pedal_type.addItems(["Loadcell", "Hydraulisch", "Potentiometer", "Sonstige/Unbekannt"]); self.hw_pedal_type.setToolTip("Links auf das Pfeilsymbol klicken.")
        self.hw_edits["pedal_type"] = self.hw_pedal_type
        hw_grid.addWidget(self.hw_pedal_type, len(hw_specs), 1)
        hw_layout.addLayout(hw_grid)
        # 0.4.8.1: Hilfetext entfernt
        self.hardware_coach_text = QTextEdit(); self.hardware_coach_text.setReadOnly(True); self.hardware_coach_text.setMaximumHeight(150)
        self.hardware_coach_text.setVisible(False)  # 0.4.8.1: aus der Ansicht genommen

        self.tabs.addTab(hw_tab, "Fahrer & Hardware")

        # Declutter 0.4.6.3: breite Tab-Leiste ausblenden, Navigation ueber gruppiertes Dropdown.
        self.tabs.tabBar().hide()
        from PySide6.QtGui import QStandardItem
        self.nav_combo = QComboBox()
        self.nav_combo.setObjectName("navCombo")
        self.nav_combo.setStyleSheet("QComboBox#navCombo { font-size:15px; font-weight:600; min-height:38px; }")
        nav_groups = [
            ("Dashboard", ["Dashboard"]),
            ("Live", ["Live"]),
            ("Reifen", ["Reifen"]),
            ("Analyse", ["Analyse", "Runden", "Vergleich", "Heatmap"]),
            ("Coach", ["Coach"]),  # 0.5.0.0: Setup-/Limit-/Input-Coach jetzt Unterreiter
            ("Fahrer & Hardware", ["Fahrer & Hardware"]),
        ]
        tab_index = {self.tabs.tabText(i): i for i in range(self.tabs.count())}
        nav_model = self.nav_combo.model()
        # 0.4.8.2: flache Ansicht-Liste ohne Gruppen-Ueberschriften (COACHING/ANALYSE)
        for group_name, views in nav_groups:
            for v in views:
                if v not in tab_index:
                    continue
                item = QStandardItem(v)
                item.setData(tab_index[v], Qt.UserRole)
                nav_model.appendRow(item)
        self.nav_combo.currentIndexChanged.connect(self._on_nav_changed)
        nav_row = QHBoxLayout()
        nav_label = QLabel("Ansicht:")
        nav_row.addWidget(nav_label)
        nav_row.addWidget(self.nav_combo, stretch=1)
        nav_row.addStretch(2)
        layout.insertLayout(layout.indexOf(self.tabs), nav_row)
        # Startansicht Dashboard
        for i in range(self.nav_combo.count()):
            if self.nav_combo.itemData(i, Qt.UserRole) == 0:
                self.nav_combo.setCurrentIndex(i)
                break

        self.log = QTextEdit(); self.log.setReadOnly(True)
        self._setup_file_logging()  # 0.4.8.8
        self.log.setMaximumHeight(115)
        self.log.setStyleSheet("font-size:11px;color:#c9d3e2;")
        self.log_label = QLabel("System-Log / Debug")
        layout.addWidget(self.log_label)
        layout.addWidget(self.log, stretch=1)
        self.log_label.setVisible(False); self.log.setVisible(False)  # 0.4.8.1: standardmaessig aus
        self.apply_profile_to_fields(self.current_profile_name)

        self.set_auto_bestlap_ui()
        self.set_auto_switch_ui()
        self.btn_snapshot.clicked.connect(self.snapshot)
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_stop.clicked.connect(self.stop_recording)
        self.btn_report.clicked.connect(self.save_report)
        self.btn_csv.clicked.connect(self.save_csv)
        self.btn_clear.clicked.connect(self.clear)
        self.btn_export.clicked.connect(self.open_export_folder)
        self.btn_ref_export.clicked.connect(self.export_reference_lap)
        self.btn_ref_import.clicked.connect(self.import_reference_lap)
        self.btn_pb_reference.clicked.connect(self.import_personal_laptime_reference)
        self.btn_auto_bestlap.clicked.connect(self.toggle_auto_bestlap_export)
        self.btn_auto_switch.clicked.connect(self.toggle_auto_switch_recording)
        self.btn_live_log.clicked.connect(self.toggle_live_log)
        self.btn_overlay.clicked.connect(self.toggle_overlay)
        self.btn_tire_overlay.clicked.connect(self.toggle_tire_overlay)
        self.btn_pedal_overlay.clicked.connect(self.toggle_pedal_overlay)
        self.btn_apply_laps.clicked.connect(self.apply_lap_selection)
        self.btn_compare_import_ref.clicked.connect(self.import_reference_lap)
        self.setup_selector.currentTextChanged.connect(lambda _txt: self.refresh_dashboard())
        self.driver_profile_selector.currentTextChanged.connect(self.on_profile_changed)
        self.btn_profile_save.clicked.connect(self.save_current_hardware_profile)
        self.btn_profile_load.clicked.connect(self.import_hardware_profile_file)
        self.btn_profile_new.clicked.connect(self.new_hardware_profile)
        self.btn_profile_delete.clicked.connect(self.delete_current_hardware_profile)
        self.btn_fahrer_hardware.clicked.connect(self.select_fahrer_hardware_view)
        self.btn_ki_analyse.clicked.connect(self.open_gemini_window)
        self.apply_gemini_config()
        self.apply_gemini_config()
        self.setup_hotkeys()
        self.setup_windows_global_hotkeys()
        self.refresh_dashboard()



    def load_last_active_profile_name(self) -> str:
        """0.4.5.3: zuletzt aktives Fahrer-/Hardwareprofil merken."""
        try:
            if DRIVER_PROFILE_STATE_PATH.exists():
                data = json.loads(DRIVER_PROFILE_STATE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    name = str(data.get("last_active_profile", "")).strip()
                    if name and name in self.hardware_profiles:
                        return name
        except Exception:
            pass
        return next(iter(self.hardware_profiles.keys()), "Standard")

    def save_last_active_profile_name(self, name: str = None):
        try:
            n = (name or self.current_profile_name or self.selected_driver_profile_name() or "Standard").strip() or "Standard"
            DRIVER_PROFILE_STATE_PATH.write_text(json.dumps({"last_active_profile": n}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def default_hardware_profile(self, name: str = "Standard") -> dict:
        return {
            "driver_name": name,
            "team": "",
            "wheelbase": "",
            "wheel_settings": "",
            "wheel_settings_screenshot": "",
            "pedals": "",
            "pedal_type": "Loadcell",
            "brake_setup": "",
            "pedal_settings_screenshot": "",
            "brake_curve": "",
            "throttle_setup": "",
            "haptics": "",
            "buttonbox": "",
            "buttonbox_2": "",
            "buttonbox_3": "",
            "shifter": "",
            "display": "",
            "notes": "",
            "detected_devices": "",
            "detected_at": "",
        }

    def load_hardware_profiles(self) -> dict:
        try:
            if DRIVER_PROFILE_PATH.exists():
                data = json.loads(DRIVER_PROFILE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data:
                    return {str(k): (v if isinstance(v, dict) else self.default_hardware_profile(str(k))) for k, v in data.items()}
        except Exception:
            pass
        return {"Standard": self.default_hardware_profile("Standard")}

    def save_hardware_profiles(self):
        try:
            DRIVER_PROFILE_PATH.write_text(json.dumps(self.hardware_profiles, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            try:
                self.log.append(f"Hardware-Profil konnte nicht gespeichert werden: {e}")
            except Exception:
                pass


    def normalize_imported_profile(self, name: str, value) -> dict:
        prof = self.default_hardware_profile(name)
        if isinstance(value, dict):
            prof.update(value)
        prof["profile_name"] = str(prof.get("profile_name") or name).strip() or name
        if not str(prof.get("driver_name") or "").strip():
            prof["driver_name"] = name
        return prof

    def unique_import_profile_name(self, base: str) -> str:
        base = (str(base or "Importiertes Profil").strip() or "Importiertes Profil")
        if base not in self.hardware_profiles:
            return base
        i = 2
        while True:
            candidate = f"{base} import {i}"
            if candidate not in self.hardware_profiles:
                return candidate
            i += 1

    def imported_profiles_from_json(self, data) -> dict:
        """Akzeptiert komplette driver_hardware_profiles.json oder ein einzelnes Profil-JSON."""
        if not isinstance(data, dict) or not data:
            return {}
        profile_keys = {"driver_name", "profile_name", "wheelbase", "pedals", "pedal_type", "brake_setup", "wheel_settings"}
        if any(k in data for k in profile_keys):
            base = str(data.get("profile_name") or data.get("driver_name") or "Importiertes Profil").strip() or "Importiertes Profil"
            return {base: self.normalize_imported_profile(base, data)}
        out = {}
        for key, value in data.items():
            if isinstance(value, dict):
                base = str(value.get("profile_name") or value.get("driver_name") or key).strip() or str(key)
                out[base] = self.normalize_imported_profile(base, value)
        return out

    def refresh_profile_selector_items(self):
        try:
            current = self.current_profile_name or self.selected_driver_profile_name()
            self.driver_profile_selector.blockSignals(True)
            self.driver_profile_selector.clear()
            self.driver_profile_selector.addItems(list(self.hardware_profiles.keys()))
            if current in self.hardware_profiles:
                self.driver_profile_selector.setCurrentText(current)
            self.driver_profile_selector.blockSignals(False)
        except Exception:
            try:
                self.driver_profile_selector.blockSignals(False)
            except Exception:
                pass

    def import_hardware_profile_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Hardware-Profil laden",
                "",
                "JSON-Profile (*.json);;Alle Dateien (*.*)",
            )
            if not file_path:
                return
            src = Path(file_path)
            data = json.loads(src.read_text(encoding="utf-8"))
            imported = self.imported_profiles_from_json(data)
            if not imported:
                QMessageBox.warning(self, "Profil laden", "In dieser Datei wurde kein gültiges Hardwareprofil gefunden.")
                return
            added = []
            for base, prof in imported.items():
                name = self.unique_import_profile_name(base)
                prof["profile_name"] = name
                if not str(prof.get("driver_name") or "").strip():
                    prof["driver_name"] = name
                self.hardware_profiles[name] = prof
                added.append(name)
            self.current_profile_name = added[0]
            self.save_hardware_profiles()
            self.save_last_active_profile_name(self.current_profile_name)
            self.refresh_profile_selector_items()
            self.driver_profile_selector.setCurrentText(self.current_profile_name)
            self.apply_profile_to_fields(self.current_profile_name)
            msg = f"{len(added)} Profil(e) importiert: " + ", ".join(added[:4])
            if len(added) > 4:
                msg += f" … +{len(added)-4}"
            self.status.setText(msg)
            if hasattr(self, "log"):
                self.log.append(msg)
        except Exception as e:
            QMessageBox.warning(self, "Profil laden", f"Profil konnte nicht geladen werden:\n{e}")

    def select_settings_screenshot(self, key: str):
        """Select and copy a settings screenshot into the profile asset folder."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Settings-Screenshot auswählen",
                "",
                "Bilder (*.png *.jpg *.jpeg *.webp *.bmp);;Alle Dateien (*.*)",
            )
            if not file_path:
                return
            src = Path(file_path)
            if not src.exists():
                QMessageBox.warning(self, "Screenshot", "Die ausgewählte Datei wurde nicht gefunden.")
                return
            profile = self.selected_driver_profile_name()
            safe_profile = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in profile)[:40] or "profile"
            target_dir = PROFILE_ASSET_DIR / safe_profile
            target_dir.mkdir(parents=True, exist_ok=True)
            prefix = "wheel" if "wheel" in key else "pedals"
            target = target_dir / f"{prefix}_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}{src.suffix.lower()}"
            shutil.copy2(src, target)
            rel = str(target.relative_to(APP_DIR)) if target.is_relative_to(APP_DIR) else str(target)
            if key in getattr(self, "hw_edits", {}):
                self.set_widget_value(self.hw_edits[key], rel)
            # Direkt im aktuellen Profil sichern, damit der Bildpfad nicht verloren geht.
            try:
                prof = self.current_hardware_profile_from_fields()
                name = self.selected_driver_profile_name()
                self.hardware_profiles[name] = prof
                self.current_profile_name = name
                self.save_hardware_profiles()
            except Exception:
                pass
            if hasattr(self, "hardware_coach_text"):
                self.hardware_coach_text.setPlainText("\n".join(self.hardware_context_lines()))
            self.status.setText(f"Screenshot gespeichert: {rel}")
        except Exception as e:
            QMessageBox.warning(self, "Screenshot", f"Screenshot konnte nicht übernommen werden:\n{e}")

    def selected_driver_profile_name(self) -> str:
        try:
            txt = self.driver_profile_selector.currentText().strip()
        except Exception:
            txt = self.current_profile_name or "Standard"
        return txt or "Standard"

    def widget_value(self, w) -> str:
        try:
            if isinstance(w, QComboBox):
                return w.currentText().strip()
            return w.text().strip()
        except Exception:
            return ""

    def set_widget_value(self, w, val: str):
        val = str(val or "")
        try:
            if isinstance(w, QComboBox):
                idx = w.findText(val)
                if idx >= 0:
                    w.setCurrentIndex(idx)
                else:
                    w.setCurrentText(val)
            else:
                w.setText(val)
        except Exception:
            pass

    def current_hardware_profile_from_fields(self) -> dict:
        prof = self.default_hardware_profile(self.selected_driver_profile_name())
        old_prof = self.hardware_profiles.get(self.selected_driver_profile_name(), {}) if hasattr(self, "hardware_profiles") else {}
        if isinstance(old_prof, dict):
            prof["detected_devices"] = old_prof.get("detected_devices", "")
            prof["detected_at"] = old_prof.get("detected_at", "")
        if hasattr(self, "hw_edits"):
            for key, w in self.hw_edits.items():
                prof[key] = self.widget_value(w)
        prof["profile_name"] = self.selected_driver_profile_name()
        if not prof.get("driver_name"):
            prof["driver_name"] = self.selected_driver_profile_name()
        return prof

    def apply_profile_to_fields(self, name: str):
        if not hasattr(self, "hw_edits"):
            return
        prof = self.hardware_profiles.get(name) or self.default_hardware_profile(name)
        self.current_profile_name = name
        self.save_last_active_profile_name(name)
        for key, w in self.hw_edits.items():
            self.set_widget_value(w, prof.get(key, ""))
        if hasattr(self, "hardware_coach_text"):
            self.hardware_coach_text.setPlainText("\n".join(self.hardware_context_lines()))
        self.refresh_dashboard()

    def on_profile_changed(self, name: str):
        name = (name or "Standard").strip() or "Standard"
        if name in self.hardware_profiles:
            self.apply_profile_to_fields(name)
        else:
            # Noch nicht speichern: erst Felder als neues Profil vorbereiten.
            self.current_profile_name = name
            if hasattr(self, "hw_edits"):
                prof = self.default_hardware_profile(name)
                for key, w in self.hw_edits.items():
                    self.set_widget_value(w, prof.get(key, ""))
            self.refresh_dashboard()

    def save_current_hardware_profile(self):
        name = self.selected_driver_profile_name()
        prof = self.current_hardware_profile_from_fields()
        self.hardware_profiles[name] = prof
        self.current_profile_name = name
        self.save_last_active_profile_name(name)
        # Combo aktualisieren ohne Duplikate
        if self.driver_profile_selector.findText(name) < 0:
            self.driver_profile_selector.addItem(name)
        self.save_hardware_profiles()
        if hasattr(self, "hardware_coach_text"):
            self.hardware_coach_text.setPlainText("\n".join(self.hardware_context_lines()))
        self.status.setText(f"Hardware-Profil gespeichert: {name}")
        self.refresh_dashboard()

    def new_hardware_profile(self):
        base = "Neuer Fahrer"
        name = base
        i = 2
        while name in self.hardware_profiles:
            name = f"{base} {i}"; i += 1
        self.hardware_profiles[name] = self.default_hardware_profile(name)
        self.driver_profile_selector.addItem(name)
        self.driver_profile_selector.setCurrentText(name)
        self.apply_profile_to_fields(name)
        self.save_hardware_profiles()
        self.status.setText(f"Neues Hardware-Profil angelegt: {name}")

    def delete_current_hardware_profile(self):
        name = self.selected_driver_profile_name()
        if name == "Standard" or len(self.hardware_profiles) <= 1:
            QMessageBox.information(self, "Profil löschen", "Das Standard-/letzte Profil kann nicht gelöscht werden.")
            return
        self.hardware_profiles.pop(name, None)
        idx = self.driver_profile_selector.findText(name)
        if idx >= 0:
            self.driver_profile_selector.removeItem(idx)
        self.save_hardware_profiles()
        next_name = next(iter(self.hardware_profiles.keys()), "Standard")
        self.driver_profile_selector.setCurrentText(next_name)
        self.apply_profile_to_fields(next_name)
        self.save_last_active_profile_name(next_name)
        self.status.setText(f"Hardware-Profil gelöscht: {name}")

    def selected_hardware_profile(self) -> dict:
        # Felder haben Vorrang, damit auch ungespeicherte Änderungen im Report landen.
        return self.current_hardware_profile_from_fields() if hasattr(self, "hw_edits") else self.hardware_profiles.get(self.current_profile_name, self.default_hardware_profile())

    def hardware_profile_summary(self, short: bool = False) -> str:
        p = self.selected_hardware_profile()
        name = p.get("driver_name") or p.get("profile_name") or self.selected_driver_profile_name()
        pedal = p.get("pedal_type") or "?"
        if short:
            return f"{name} | {pedal}"
        bits = [name]
        if p.get("wheelbase"):
            bits.append(p.get("wheelbase"))
        if p.get("pedals"):
            bits.append(p.get("pedals"))
        if pedal:
            bits.append(pedal)
        return " | ".join(bits)

    def resolve_profile_asset_path(self, value: str) -> Optional[Path]:
        value = str(value or "").strip()
        if not value:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = APP_DIR / p
        return p

    def settings_screenshot_state(self, value: str) -> str:
        p = self.resolve_profile_asset_path(value)
        if not p:
            return "nicht gesetzt"
        return "vorhanden" if p.exists() else "Pfad gesetzt, Datei nicht gefunden"

    def settings_screenshot_status_text(self, profile: dict) -> str:
        wheel = self.settings_screenshot_state(profile.get("wheel_settings_screenshot"))
        pedals = self.settings_screenshot_state(profile.get("pedal_settings_screenshot"))
        return f"Lenkrad/FFB: {wheel} | Pedale: {pedals}"

    def hardware_context_lines(self) -> List[str]:
        p = self.selected_hardware_profile()
        lines = ["Hardware-/Settings-Kontext:"]
        lines.append(f"Fahrer: {p.get('driver_name') or self.selected_driver_profile_name()} | Team: {p.get('team') or '-'}")
        lines.append(f"Wheelbase: {p.get('wheelbase') or '-'} | Pedale: {p.get('pedals') or '-'} | Pedal-Typ: {p.get('pedal_type') or '-'}")
        lines.append(f"Bremse: {p.get('brake_setup') or '-'} | Kurve: {p.get('brake_curve') or '-'}")
        lines.append(f"Gas: {p.get('throttle_setup') or '-'} | Haptik: {p.get('haptics') or '-'} | Anzeige: {p.get('display') or '-'}")
        boxes = [p.get("buttonbox"), p.get("buttonbox_2"), p.get("buttonbox_3")]
        boxes_txt = " | ".join([b for b in boxes if b and b.lower() != "keine"]) or "-"
        lines.append(f"Buttonboxen: {boxes_txt} | Shifter/Handbremse: {p.get('shifter') or '-'}")
        shots = []
        if p.get("wheel_settings_screenshot"):
            shots.append("Lenkrad")
        if p.get("pedal_settings_screenshot"):
            shots.append("Pedale")
        if shots:
            lines.append("Settings-Screenshots: " + ", ".join(shots))
        lines.append("Settings-Bilder: " + self.settings_screenshot_status_text(p))
        lines.append("Coach-Regel: Erst Fahrtechnik prüfen, dann Hardware/Settings nur als mögliche Ursache vorschlagen.")
        return lines

    def hardware_report_lines(self) -> List[str]:
        p = self.selected_hardware_profile()
        lines = ["", "Fahrer-/Hardware-Profil 0.4.5.4:"]
        fields = [
            ("Profil", p.get("profile_name") or self.selected_driver_profile_name()),
            ("Fahrer", p.get("driver_name")),
            ("Team/Handle", p.get("team")),
            ("Lenkradbasis", p.get("wheelbase")),
            ("FFB/Lenkung Settings", p.get("wheel_settings")),
            ("Screenshot Lenkrad/FFB", p.get("wheel_settings_screenshot")),
            ("Pedale", p.get("pedals")),
            ("Pedal-Typ", p.get("pedal_type")),
            ("Brems-Setup", p.get("brake_setup")),
            ("Screenshot Pedale", p.get("pedal_settings_screenshot")),
            ("Bremskurve", p.get("brake_curve")),
            ("Gas-Setup", p.get("throttle_setup")),
            ("Haptik", p.get("haptics")),
            ("Buttonbox 1 / Stream Deck", p.get("buttonbox")),
            ("Buttonbox 2", p.get("buttonbox_2")),
            ("Buttonbox 3", p.get("buttonbox_3")),
            ("Shifter/Handbremse", p.get("shifter")),
            ("Anzeige", p.get("display")),
            ("Notizen", p.get("notes")),
            ("Settings-Screenshot Status", self.settings_screenshot_status_text(p)),
            ("KI-Auswertung vorbereitet", "ja" if (p.get("wheel_settings_screenshot") or p.get("pedal_settings_screenshot")) else "nein"),
        ]
        for label, val in fields:
            lines.append(f"{label}: {val or '-'}")
        lines.append("Hinweis: Dieses Profil wird manuell per Dropdown/freier Eingabe gepflegt. Screenshots werden als Profil-Assets gespeichert und bereiten die spätere KI-Auswertung der Lenkrad-/Pedalsettings vor.")
        return lines

    def hardware_input_hint(self, focus: str, rows: List[dict]) -> str:
        p = self.selected_hardware_profile()
        pedal_type = (p.get("pedal_type") or "").lower()
        if "Bremse ruhiger" in focus:
            if "load" in pedal_type:
                return "Hardware-Kontext: Bei Loadcell-Pedalen ggf. Max-Kraft/Kalibrierung oder eine leicht progressivere Bremskurve prüfen, falls das ruppige Lösen reproduzierbar bleibt."
            if "hyd" in pedal_type:
                return "Hardware-Kontext: Bei hydraulischen Pedalen Pedalweg, Endanschlag und Rückstellgefühl prüfen, falls das ruppige Lösen reproduzierbar bleibt."
            if "pot" in pedal_type:
                return "Hardware-Kontext: Bei Potentiometer-Pedalen Kalibrierung/Deadzone prüfen, falls die Bremse sprunghaft wirkt."
            return "Hardware-Kontext: Pedalkalibrierung, Pedalweg und Bremskurve prüfen, falls das ruppige Lösen reproduzierbar bleibt."
        if "Gas progressiver" in focus:
            return "Hardware-Kontext: Wenn die Gas-Sprünge trotz ruhigem Fuß bleiben, Gas-Pedalweg, Feder, Deadzone oder eine minimal weichere Gaskurve prüfen."
        if "Rollenphase" in focus:
            return "Hardware-Kontext: Wenn Rollen ungewollt entsteht, Brems-/Gas-Deadzone und Pedalruhe prüfen; zuerst aber Bremse/Gas fahrtechnisch klarer übergeben."
        return "Hardware-Kontext: Aktuell kein klarer Hardware-Eingriff nötig. Erst Fahrtechnik/Referenzzonen vergleichen."

    def _set_hw_if_empty(self, key: str, value: str):
        """Fill a hardware profile field only if it is still empty."""
        if not value or key not in getattr(self, "hw_edits", {}):
            return
        w = self.hw_edits[key]
        if not self.widget_value(w):
            self.set_widget_value(w, value)

    def scan_hardware_devices(self):
        """Best-effort Windows hardware scan for driver profiles.
        4.4.20 uses several Windows sources, but fills categories conservatively.
        Stale Joystick registry entries are kept as raw info only, not as trusted current hardware.
        """
        devices = []
        error = ""

        def add_device(name="", manufacturer="", cls="", device_id="", source=""):
            name = str(name or "").strip()
            manufacturer = str(manufacturer or "").strip()
            cls = str(cls or "").strip()
            device_id = str(device_id or "").strip()
            source = str(source or "").strip()
            if not name and not device_id:
                return
            devices.append({
                "name": name or device_id,
                "manufacturer": manufacturer,
                "class": cls,
                "device_id": device_id,
                "source": source,
            })

        if sys.platform.startswith("win"):
            ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$all = @()
$all += Get-CimInstance Win32_PnPEntity | Select-Object @{n='Source';e={'PnPEntity'}},Name,Manufacturer,PNPClass,DeviceID
$all += Get-PnpDevice -PresentOnly | Select-Object @{n='Source';e={'PnpDevice'}},@{n='Name';e={$_.FriendlyName}},Manufacturer,@{n='PNPClass';e={$_.Class}},@{n='DeviceID';e={$_.InstanceId}}
$usb = Get-CimInstance Win32_USBControllerDevice
foreach ($u in $usb) {
    try {
        $dep = [WMI]$u.Dependent
        if ($dep) { $all += $dep | Select-Object @{n='Source';e={'USBController'}},Name,Manufacturer,PNPClass,DeviceID }
    } catch {}
}
$joyPaths = @(
 'HKCU:\System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\*',
 'HKLM:\SYSTEM\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\*'
)
foreach ($jp in $joyPaths) {
    Get-ItemProperty $jp | ForEach-Object {
        $n = $_.OEMName
        if ($n) {
            [PSCustomObject]@{Source='JoystickOEM';Name=$n;Manufacturer='';PNPClass='GameController';DeviceID=$_.PSChildName}
        }
    } | ForEach-Object { $all += $_ }
}
$all | Where-Object { $_.Name -or $_.DeviceID } | ConvertTo-Json -Depth 3
"""
            try:
                ps_cmd = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; $OutputEncoding=[System.Text.Encoding]::UTF8; " + ps
                cp = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                                    capture_output=True, text=False, timeout=20)
                stdout = (cp.stdout or b"").decode("utf-8", errors="replace")
                stderr = (cp.stderr or b"").decode("utf-8", errors="replace")
                if cp.returncode == 0 and stdout.strip():
                    data = json.loads(stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data if isinstance(data, list) else []:
                        add_device(
                            item.get("Name"),
                            item.get("Manufacturer"),
                            item.get("PNPClass"),
                            item.get("DeviceID"),
                            item.get("Source"),
                        )
                else:
                    error = (stderr or stdout or "PowerShell lieferte keine Geräte.").strip()[:500]
            except Exception as e:
                error = str(e)
        else:
            error = "Hardware-Scan ist aktuell für Windows ausgelegt."

        names = []
        seen = set()
        for d in devices:
            did = d.get("device_id", "")
            line = " | ".join([x for x in [d.get("name"), d.get("manufacturer"), d.get("class"), did, d.get("source")] if x])
            key = line.lower()
            if line and key not in seen:
                seen.add(key)
                names.append(line)

        def low_line(line):
            return line.lower().replace("_", " ").replace("-", " ")

        def find_any(keywords, exclude=()):
            """Return a conservative category suggestion.
            Important: Windows keeps old joystick OEM registry entries. Those are useful
            as raw info, but must not automatically become the current wheelbase/pedal.
            """
            best = ""
            best_score = -999
            for line in names:
                low = low_line(line)
                if exclude and any(e in low for e in exclude):
                    continue
                if not any(k in low for k in keywords):
                    continue
                # JoystickOEM entries are often stale/old devices. Keep them in raw scan,
                # but do not use them to fill current hardware fields.
                if "joystickoem" in low:
                    continue
                score = 0
                known_brand = any(k in low for k in ["simucube", "fanatec", "moza", "asetek", "simagic", "heusinkveld", "simsonn", "simjack", "stream deck", "elgato", "quest", "pico", "vive", "pimax", "buttkicker", "hf8"])
                if known_brand:
                    score += 10
                if "pnpdevice" in low or "pnpentity" in low or "usbcontroller" in low:
                    score += 3
                if "gamecontroller" in low:
                    score += 1
                if "hidclass" in low or "usb input device" in low or "hid compliant" in low:
                    score -= 3
                if "keyboard" in low or "mouse" in low:
                    score -= 8
                # Need a reasonably specific hit before autofill.
                if score > best_score and score >= 6:
                    best_score = score
                    best = line.split(" | ")[0]
            return best

        wheel_keywords = [
            "simucube", "granite", "fanatec", "clubsport", "podium", "csl dd", "moza", "r5", "r9", "r12", "r16", "r21",
            "asetek", "la prima", "forte", "invicta", "simagic", "alpha", "logitech", "g pro", "thrustmaster", "t300", "t818",
            "cammus", "vrs directforce", "directforce", "wheel base", "wheelbase", "racing wheel"
        ]
        pedal_keywords = [
            "simsonn", "heusinkveld", "sprint", "ultimate", "fanatec pedals", "clubsport pedals", "csl pedals", "moza pedals",
            "crp", "sr p", "asetek pedals", "invicta pedals", "forte pedals", "simagic p", "p1000", "p2000", "simjack", "vrs pedals", "venym", "pedal", "load cell", "loadcell"
        ]
        haptic_keywords = ["hf8", "haptic", "buttkicker", "next level racing", "nobsound", "dayton audio", "simhub"]
        display_keywords = ["quest", "oculus", "meta", "pico", "vive", "valve index", "reverb", "pimax", "vr headset", "mixed reality"]
        button_keywords = ["stream deck", "elgato", "button box", "buttonbox", "arduino", "leo bodnar", "bbi", "joystick controller", "game controller"]
        shifter_keywords = ["shifter", "shift", "handbrake", "hand brake", "sequential", "h-pattern", "th8a", "shh", "sq v", "ds-8x", "hgp"]

        wheel = find_any(wheel_keywords, exclude=("pedal", "button", "stream deck"))
        pedals = find_any(pedal_keywords, exclude=("wheel base", "wheelbase", "stream deck"))
        haptics = find_any(haptic_keywords)
        display = find_any(display_keywords)
        buttonbox = find_any(button_keywords, exclude=("keyboard", "mouse"))
        shifter = find_any(shifter_keywords, exclude=("keyboard", "mouse"))

        generic_controllers = []
        for line in names:
            low = low_line(line)
            if any(k in low for k in ["hid compliant game controller", "usb input device", "gamecontroller", "joystick"]):
                if not any(bad in low for bad in ["keyboard", "mouse", "touchpad"]):
                    generic_controllers.append(line.split(" | ")[0])
        generic_controllers = list(dict.fromkeys(generic_controllers))[:8]

        # Nur eindeutige, aktuelle Treffer automatisch übernehmen.
        # Alte Registry-/Joystick-OEM-Einträge bleiben als Rohdaten sichtbar,
        # werden aber nicht mehr in Base/Pedale/Shifter geschrieben.
        self._set_hw_if_empty("wheelbase", wheel)
        self._set_hw_if_empty("pedals", pedals)
        self._set_hw_if_empty("haptics", haptics)
        self._set_hw_if_empty("buttonbox", buttonbox)
        self._set_hw_if_empty("shifter", shifter)
        self._set_hw_if_empty("display", display)

        notes_widget = self.hw_edits.get("notes")
        notes = self.widget_value(notes_widget)
        note_lines = []
        if buttonbox and buttonbox.lower() not in notes.lower():
            note_lines.append(f"Buttonbox/Controller-Vorschlag: {buttonbox}")
        if shifter and shifter.lower() not in notes.lower():
            note_lines.append(f"Shifter/Handbremse-Vorschlag: {shifter}")
        if generic_controllers:
            note_lines.append("Generische HID/Gamecontroller erkannt, bitte manuell zuordnen: " + ", ".join(generic_controllers))
        stale = [ln.split(" | ")[0] for ln in names if "joystickoem" in low_line(ln)]
        if stale:
            note_lines.append("Alte/Registry-Gamecontroller gefunden, nicht automatisch übernommen: " + ", ".join(list(dict.fromkeys(stale))[:8]))
        if note_lines and notes_widget is not None:
            add = "\n".join(note_lines)
            self.set_widget_value(notes_widget, (notes + "\n" + add).strip() if notes else add)

        prof = self.current_hardware_profile_from_fields()
        prof["detected_at"] = datetime.now().isoformat(timespec="seconds")
        prof["detected_devices"] = "; ".join(names[:120]) if names else ("Scan ohne Ergebnis" + (f": {error}" if error else ""))
        prof["detected_summary"] = " | ".join([x for x in [f"Wheelbase: {wheel}" if wheel else "", f"Pedale: {pedals}" if pedals else "", f"Haptik: {haptics}" if haptics else "", f"Anzeige/VR: {display}" if display else "", f"Buttonbox: {buttonbox}" if buttonbox else "", f"Shifter: {shifter}" if shifter else ""] if x]) or "Keine eindeutige Kategorie erkannt"
        name = self.selected_driver_profile_name()
        self.hardware_profiles[name] = prof
        self.current_profile_name = name
        self.save_hardware_profiles()
        if hasattr(self, "hardware_coach_text"):
            lines = self.hardware_context_lines()
            lines.append("")
            lines.append("Hardware-Scan 4.4.20:")
            lines.append(prof.get("detected_summary", ""))
            if generic_controllers:
                lines.append("Hinweis: Einige Geräte melden sich nur generisch. Diese stehen in den Notizen und können manuell zugeordnet werden.")
            lines.append("Hinweis: Alte Windows-Registry/Joystick-OEM-Geräte werden nicht mehr automatisch als aktuelle Hardware übernommen.")
            if names:
                lines.append("")
                lines.append(f"Erkannte Geräte/Rohdaten: {len(names)}")
                for line in names[:28]:
                    lines.append("- " + line)
                if len(names) > 28:
                    lines.append(f"... {len(names)-28} weitere im Profil gespeichert")
            else:
                lines.append("")
                lines.append("Keine Geräte erkannt. " + error)
            self.hardware_coach_text.setPlainText("\n".join(lines))
        self.status.setText(f"Hardware-Scan abgeschlossen: {len(names)} Einträge, Kategorie: {prof.get('detected_summary','')}")
        self.refresh_dashboard()

    def cleanup_duplicate_overlays(self):
        # Sicherheitsnetz: Es darf pro App nur ein Overlay-Fenster geben.
        # Falls durch ältere Builds/Hotkey-Doppelung mehrere Top-Level-Overlays existieren,
        # werden alle außer self.overlay_window geschlossen.
        try:
            for w in QApplication.topLevelWidgets():
                if isinstance(w, OverlayWindow) and w is not self.overlay_window:
                    w.close()
                    w.deleteLater()
        except Exception as e:
            self.log.append(f"Overlay-Duplikat-Cleanup Hinweis: {e}")

    def cleanup_duplicate_tire_overlays(self):
        try:
            for w in QApplication.topLevelWidgets():
                if isinstance(w, TireOverlayWindow) and w is not self.tire_overlay_window:
                    w.close()
                    w.deleteLater()
        except Exception as e:
            self.log.append(f"Reifen-Overlay-Duplikat-Cleanup Hinweis: {e}")

    def _on_nav_changed(self, idx):
        # Gruppierte Dropdown-Navigation -> Tab-Index (Gruppen-Header sind nicht auswaehlbar).
        from PySide6.QtCore import Qt as _Qt
        data = self.nav_combo.itemData(idx, _Qt.UserRole)
        if data is None:
            return
        try:
            data = int(data)
        except (TypeError, ValueError):
            return
        if data >= 0:
            self.tabs.setCurrentIndex(data)

    def maybe_autoshow_tire_overlay(self, s):
        # Overlay einmal pro Sitzung automatisch oeffnen, sobald der Fahrer auf der Strecke ist.
        # Danach bleibt es dem Nutzer ueberlassen (Button/F6). Kein erneutes Aufpoppen nach Schliessen.
        if not getattr(self, "tire_overlay_autostart", True):
            return
        if getattr(self, "_tire_overlay_autoshown", False):
            return
        try:
            on_track = (not self.is_non_driving_sample(s)) and s.speed_kmh > 3 and bool(getattr(s, "player_has_vehicle", True))
        except Exception:
            on_track = False
        if not on_track:
            return
        try:
            if self.tire_overlay_window is None:
                self.tire_overlay_window = TireOverlayWindow()
                try:
                    self.tire_overlay_window.apply_overlay_style(getattr(self, "overlay_style", "transparent"))  # 0.4.9.1
                except Exception:
                    pass
            self.cleanup_duplicate_tire_overlays()
            if not self.tire_overlay_window.isVisible():
                self.tire_overlay_window.update_from_main(self)
                self.tire_overlay_window.show()
                self.tire_overlay_window.raise_()
                self.log.append("Reifen-Overlay automatisch geoeffnet (Fahrt erkannt).")
            self._tire_overlay_autoshown = True
        except Exception as e:
            try:
                self.log.append(f"Auto-Overlay Hinweis: {e}")
            except Exception:
                pass

    def toggle_tire_overlay(self):
        if self.tire_overlay_window is None:
            self.tire_overlay_window = TireOverlayWindow()
            try:
                self.tire_overlay_window.apply_overlay_style(getattr(self, "overlay_style", "transparent"))  # 0.4.9.1
            except Exception:
                pass
        self.cleanup_duplicate_tire_overlays()
        if self.tire_overlay_window.isVisible():
            self.tire_overlay_window.hide()
            self.log.append("Reifen-Overlay ausgeblendet.")
        else:
            self.cleanup_duplicate_tire_overlays()
            self.tire_overlay_window.update_from_main(self)
            self.tire_overlay_window.show()
            self.tire_overlay_window.raise_()
            self.log.append("Reifen-Overlay geöffnet. Separates Fenster neben dem Coach-Overlay.")

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def open_settings_window(self):
        if getattr(self, "settings_window", None) is None:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show(); self.settings_window.raise_(); self.settings_window.activateWindow()

    def open_setup_coach_window(self):  # 0.5.9.0
        if getattr(self, "setup_coach_window", None) is None:
            self.setup_coach_window = SetupCoachWindow(self)
        self.setup_coach_window.show()
        self.setup_coach_window.raise_(); self.setup_coach_window.activateWindow()
        self.setup_coach_window._manual_refresh()  # 0.5.9.14: sofort live pruefen statt bis zu 12s warten

    def toggle_log(self):
        vis = not self.log.isVisible()
        self.log.setVisible(vis); self.log_label.setVisible(vis)

    def _theme_path(self):
        return str(EXPORT_DIR / "ui_theme.txt")

    def _load_theme(self):
        try:
            with open(self._theme_path(), encoding="utf-8") as fh:
                m = fh.read().strip()
                return m if m in ("dark", "light") else "dark"
        except Exception:
            return "dark"

    def _save_theme(self, mode):
        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._theme_path(), "w", encoding="utf-8") as fh:
                fh.write(mode)
        except Exception:
            pass

    def _style_jcm_logo(self):
        """0.4.9.3: Das Logo ist schwarz/rot auf transparentem Grund. Im dunklen
        Design bekommt es einen hellen Chip, damit die schwarzen Flaechen sichtbar
        bleiben; im hellen Design steht es frei auf dem Hintergrund."""
        lab = getattr(self, "jcm_logo", None)
        if lab is None:
            return
        if getattr(self, "_theme", "dark") == "light":
            lab.setStyleSheet("background:transparent; padding:4px 2px;")
        else:
            lab.setStyleSheet("background:#eef1f5; border-radius:10px; padding:6px 10px;")

    def apply_theme(self, mode):
        self._theme = mode if mode in ("dark", "light") else "dark"
        qss = LIGHT_QSS if self._theme == "light" else DARK_QSS
        self._root.setStyleSheet(qss)
        gw = getattr(self, "gemini_window", None)
        if gw is not None:
            gw.setStyleSheet(qss)
        self._style_jcm_logo()  # 0.4.9.3

    def toggle_theme(self):
        self.apply_theme("light" if self._theme == "dark" else "dark")
        self._save_theme(self._theme)

    def _std_reload_tracks(self):
        cls = self.std_class.currentText()
        cur = self.std_track.currentText()
        self.std_track.blockSignals(True)
        self.std_track.clear()
        self.std_track.addItems(self._lt.tracks_for(cls))
        if cur:
            i = self.std_track.findText(cur)
            if i >= 0:
                self.std_track.setCurrentIndex(i)
        self.std_track.blockSignals(False)

    def _std_path(self):
        return str(EXPORT_DIR / "standard_reference.json")

    def _load_standard_reference_selection(self):
        try:
            with open(self._std_path(), encoding="utf-8") as fh:
                d = json.load(fh)
            if d.get("class") in self._lt.CLASSES:
                self.std_class.setCurrentText(d["class"]); self._std_reload_tracks()
            if d.get("track"):
                i = self.std_track.findText(d["track"])
                if i >= 0:
                    self.std_track.setCurrentIndex(i)
            if d.get("level"):
                self.std_level.setCurrentText(d["level"])
        except Exception:
            pass

    def _auto_reference_from_live(self, s):
        # 0.5.7.0: aktuelle Strecke automatisch der Referenz zuordnen; neue/unbekannte
        # Strecken klar als "keine Referenz" markieren statt still die falsche zu zeigen.
        try:
            trk = (getattr(s, "track", "") or "").strip()
            if trk == getattr(self, "_last_ref_track", None):
                return
            self._last_ref_track = trk
            if not trk:
                self.std_live.setText(""); return
            key = self._lt.resolve_track(trk, self.std_class.currentText())
            if key:
                i = self.std_track.findText(key)
                if i >= 0:
                    self.std_track.setCurrentIndex(i)
                self.std_live.setText(f"Aktuell: {trk} \u2192 {key}")
                self.std_live.setStyleSheet("color:#3fb950;")
            else:
                self.std_live.setText(f"Aktuell: {trk} \u2013 keine Referenz hinterlegt")
                self.std_live.setStyleSheet("color:#ff9f0a;")
        except Exception:
            pass

    def _update_standard_reference(self):
        cls = self.std_class.currentText(); trk = self.std_track.currentText(); lvl = self.std_level.currentText()
        res = self._lt.target_time(cls, trk, lvl)
        if res:
            self.standard_ref_time_s, txt = res
            self.std_target.setText(txt)
        else:
            self.standard_ref_time_s = 0.0
            self.std_target.setText("--:--.--")
        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._std_path(), "w", encoding="utf-8") as fh:
                json.dump({"class": cls, "track": trk, "level": lvl}, fh)
        except Exception:
            pass

    def _check_updates(self):
        self.log.append("Pruefe auf Updates \u2026")
        QApplication.processEvents()
        try:
            info = updater.check_for_update(APP_VERSION)
        except Exception as e:
            QMessageBox.warning(self, "Update", f"Update-Pruefung fehlgeschlagen: {e}")
            return
        if info is None:
            QMessageBox.information(self, "Update", f"Du bist aktuell (v{APP_VERSION}).")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Update verf\u00fcgbar")
        box.setText(f"Neue Version {info['version']} verf\u00fcgbar.\nInstalliert: {APP_VERSION}.")
        if info.get("notes"):
            box.setInformativeText(info["notes"][:600])
        dl_btn = None
        if info.get("asset_url"):
            dl_btn = box.addButton("Herunterladen & installieren", QMessageBox.AcceptRole)
        open_btn = box.addButton("Download-Seite \u00f6ffnen", QMessageBox.AcceptRole)
        box.addButton("Sp\u00e4ter", QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if dl_btn is not None and clicked is dl_btn:
            self._download_and_launch(info)
        elif clicked is open_btn:
            QDesktopServices.openUrl(QUrl(info["url"]))

    def _download_and_launch(self, info):
        import os
        url = info.get("asset_url") or ""
        if not url:
            QDesktopServices.openUrl(QUrl(info["url"])); return
        updates_dir = EXPORT_DIR / "updates"
        try:
            updates_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        fname = url.split("/")[-1] or f"lmu_setup_{info.get('version','')}.exe"
        dest = str(updates_dir / fname)
        dlg = QProgressDialog("Lade Update …", "Abbrechen", 0, 100, self)
        dlg.setWindowTitle("Update"); dlg.setAutoClose(False); dlg.setAutoReset(False); dlg.setValue(0)
        self._upd_worker = UpdateDownloadWorker(url, dest)

        def on_prog(d, t):
            dlg.setValue(int(d * 100 / t) if t else 0)

        def on_done(path, err):
            dlg.close()
            if err or not path:
                QMessageBox.warning(self, "Update", f"Download fehlgeschlagen: {err}\n\nIch öffne die Download-Seite.")
                QDesktopServices.openUrl(QUrl(info["url"])); return
            try:
                self.log.append(f"Update geladen: {path}. Starte Installer – App wird beendet.")
                if hasattr(os, "startfile"):
                    os.startfile(path)  # type: ignore[attr-defined]
                else:
                    import subprocess; subprocess.Popen([path])
            except Exception as e:
                QMessageBox.warning(self, "Update", f"Installer-Start fehlgeschlagen: {e}\nDatei liegt in exports/updates.")
                return
            QApplication.quit()

        self._upd_worker.progress.connect(on_prog)
        self._upd_worker.finished_result.connect(on_done)
        dlg.canceled.connect(self._upd_worker.requestInterruption)
        self._upd_worker.start()
        dlg.exec()

    def toggle_pedal_overlay(self):
        if self.pedal_overlay_window is None:
            self.pedal_overlay_window = PedalOverlayWindow()
            try:
                self.pedal_overlay_window.apply_overlay_style(getattr(self, "overlay_style", "transparent"))  # 0.4.9.1
            except Exception:
                pass
        if self.pedal_overlay_window.isVisible():
            self.pedal_overlay_window.hide()
            self.log.append("Pedal-Overlay ausgeblendet.")
        else:
            self.pedal_overlay_window.update_from_main(self)
            self.pedal_overlay_window.show()
            self.pedal_overlay_window.raise_()
            self.log.append("Pedal-Overlay geoeffnet. Zeigt Roh-Input (Gas/Bremse/Kupplung).")

    def _setup_file_logging(self):
        """0.4.8.8: spiegelt alle Log-Zeilen automatisch in eine Datei unter
        exports/logs und faengt unerwartete Fehler ab. Behaelt die letzten 20 Logs."""
        import sys as _sys, glob as _glob, os as _os
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            existing = sorted(_glob.glob(str(LOG_DIR / "lmu_coach_*.log")))
            for old in existing[:-19]:
                try: _os.remove(old)
                except Exception: pass
            path = LOG_DIR / f"lmu_coach_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self._logfile = open(path, "a", encoding="utf-8", buffering=1)
            self._logfile.write(f"=== PitBoss {APP_VERSION} – {datetime.now().isoformat(timespec='seconds')} ===\n")
            _orig_append = self.log.append
            def _tee(msg, _o=_orig_append):
                try:
                    self._logfile.write(f"{datetime.now().strftime('%H:%M:%S')}  {msg}\n")
                except Exception:
                    pass
                _o(msg)
            self.log.append = _tee
            _prev_hook = _sys.excepthook
            def _hook(et, ev, tb, _p=_prev_hook):
                try:
                    import traceback as _tbm
                    self._logfile.write("!! UNCAUGHT " + "".join(_tbm.format_exception(et, ev, tb)) + "\n")
                except Exception:
                    pass
                _p(et, ev, tb)
            _sys.excepthook = _hook
            self.log.append(f"Logdatei: {path}")
        except Exception:
            pass

    def _toggle_simple_overlay(self, attr, cls, name):
        win = getattr(self, attr, None)
        if win is None:
            win = cls(); setattr(self, attr, win)
            try:
                win.apply_overlay_style(getattr(self, "overlay_style", "transparent"))
            except Exception:
                pass
        if win.isVisible():
            win.hide(); self.log.append(f"{name} ausgeblendet.")
        else:
            win.update_from_main(self); win.show(); win.raise_()
            self.log.append(f"{name} geoeffnet.")

    def update_sector_times(self, s):
        """0.4.9.0: echte Sektorzeiten des Spiels auswerten (S2 kommt kumuliert)."""
        try:
            secs = self.sector_tracker.on_sample(s)
        except Exception:
            return
        t = self.sector_tracker
        if secs is not None:
            best = t.best
            marks = ["*" if abs(secs[i] - best[i]) < 1e-6 else "" for i in range(3)]
            self.log.append("Sektoren Lap {}: S1 {:.3f}{}  S2 {:.3f}{}  S3 {:.3f}{}  =  {}".format(
                int(getattr(s, "lap_number", 0) or 0) - 1,
                secs[0], marks[0], secs[1], marks[1], secs[2], marks[2],
                fmt_lap_time(sum(secs))))
        if getattr(self, "sector_label", None) is None:
            return
        if t.best_lap <= 0:
            return
        tb = t.theoretical_best()
        txt = ("Sektoren – letzte: S1 {:.3f} · S2 {:.3f} · S3 {:.3f}   |   "
               "beste: S1 {:.3f} · S2 {:.3f} · S3 {:.3f}").format(
            t.last[0], t.last[1], t.last[2], t.best[0], t.best[1], t.best[2])
        if tb > 0:
            txt += "   |   theoretische Bestrunde {}  (beste gefahren {}, Potenzial {:.3f} s)".format(
                fmt_lap_time(tb), fmt_lap_time(t.best_lap), max(t.best_lap - tb, 0.0))
        self.sector_label.setText(txt)

    def update_brake_status(self):
        """0.4.9.4: Bremstemperatur/-verschleiss auch ohne offenes Overlay im
        Hauptfenster zeigen (der Verschleiss ist eine Schaetzung aus 0.4.9.2)."""
        lab = getattr(self, "brake_status_label", None)
        if lab is None:
            return
        m = getattr(self, "brake_model", None)
        if m is None:
            return
        temps = m.temps_c()
        if not any(t is not None for t in temps):
            return
        names = ["VL", "VR", "HL", "HR"]
        parts = []
        for i in range(4):
            t = temps[i]
            parts.append(f"{names[i]} {t:.0f}\u00b0C / {m.wear_pct(i):.0f} %" if t is not None else f"{names[i]} \u2014")
        rest = getattr(self, "rest", None)
        real = rest is not None and rest.has_wearables()
        if real:
            parts = []
            for i in range(4):
                t = temps[i]; rw = rest.brake_wear_pct(i)
                parts.append(f"{names[i]} {t:.0f}\u00b0C / {rw:.0f} %" if (t is not None and rw is not None)
                             else f"{names[i]} \u2014")
        txt = ("Bremsen (Temp / Verschlei\u00df " + ("LMU-API" if real else "gesch\u00e4tzt") + "): "
               + "  \u00b7  ".join(parts))
        if m.fading_risk():
            txt += "   \u2013 FADING-GEFAHR"
        lab.setText(txt)

    def set_coach_lead(self, kind):
        """0.4.9.8: Vorlauf der Sprachansage einstellen. Groesserer Wert =
        frueher angesagt. Wert gilt ab sofort und wird gespeichert."""
        from PySide6.QtWidgets import QInputDialog
        names = {"brake": "Bremsen", "turnin": "Einlenken", "gas": "Gas"}
        cur = self.brake_coach.get_lead(kind)
        val, ok = QInputDialog.getDouble(
            self, f"Ansage-Vorlauf: {names.get(kind, kind)}",
            f"Sekunden VOR dem Punkt ansagen (h\u00f6her = fr\u00fcher).\n"
            f"Aktuell: {cur:.2f} s   \u00b7   Bereich 0,0 \u2013 3,0 s",
            cur, 0.0, 3.0, 2, 0.05)
        if not ok:
            return
        self.brake_coach.set_lead(kind, val)
        self.log.append(f"Ansage-Vorlauf {names.get(kind, kind)}: {val:.2f} s "
                        f"(gespeichert in exports/coach_timing.json).")
        self.status.setText(f"Vorlauf {names.get(kind, kind)} = {val:.2f} s")

    def set_coach_lead_all(self):
        """0.5.8.0: Ansage-Vorlauf fuer Bremsen/Einlenken/Gas in EINEM Dialog mit
        drei Schiebereglern (0,00-3,00 s, hoeher = frueher). Loest die drei
        einzelnen Popups ab. Sofort wirksam, gespeichert in coach_timing.json."""
        from PySide6.QtWidgets import (QDialog, QSlider, QVBoxLayout, QHBoxLayout,
                                       QLabel, QDialogButtonBox, QWidget)
        from PySide6.QtCore import Qt as _Qt
        bc = self.brake_coach
        specs = [("brake", "Bremsen"), ("turnin", "Einlenken"), ("gas", "Gas")]
        dlg = QDialog(self)
        dlg.setWindowTitle("Ansage-Vorlauf")
        lay = QVBoxLayout(dlg)
        intro = QLabel("Sekunden VOR dem Punkt ansagen (h\u00f6her = fr\u00fcher).\n"
                       "Bereich 0,00 \u2013 3,00 s.")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        sliders = {}
        for key, name in specs:
            row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0, 0, 0, 0)
            cap = QLabel(name); cap.setMinimumWidth(90)
            sld = QSlider(_Qt.Horizontal)
            sld.setMinimum(0); sld.setMaximum(60)  # x 0,05 s = 0..3,00 s
            sld.setSingleStep(1); sld.setPageStep(2)
            sld.setValue(int(round(bc.get_lead(key) / 0.05)))
            val = QLabel(); val.setMinimumWidth(56)
            sld.valueChanged.connect(
                (lambda lbl: (lambda v: lbl.setText(f"{v * 0.05:.2f} s")))(val))
            val.setText(f"{sld.value() * 0.05:.2f} s")
            rl.addWidget(cap); rl.addWidget(sld, 1); rl.addWidget(val)
            lay.addWidget(row)
            sliders[key] = sld
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        for key, name in specs:
            bc.set_lead(key, round(sliders[key].value() * 0.05, 2))
        self.log.append("Ansage-Vorlauf gesetzt: "
                        + ", ".join(f"{n} {bc.get_lead(k):.2f}s" for k, n in specs)
                        + " (exports/coach_timing.json).")
        self.status.setText("Ansage-Vorlauf aktualisiert.")

    def calibrate_brake_model(self):
        """0.4.9.2: Modell an einen real beobachteten Verschleiss anpassen."""
        from PySide6.QtWidgets import QInputDialog
        cur = self.brake_model.worst_wear()
        val, ok = QInputDialog.getDouble(
            self, "Bremsmodell kalibrieren",
            f"Das Modell schaetzt aktuell {cur:.1f} % am staerksten belasteten Rad.\n"
            "Wie hoch war der tatsaechliche Verschleiss in Prozent?",
            cur if cur > 0 else 10.0, 0.1, 100.0, 1)
        if not ok:
            return
        if self.brake_model.calibrate_to(val):
            self.log.append(f"Bremsmodell kalibriert: {cur:.1f} % entsprechen jetzt {val:.1f} %. "
                            f"Gespeichert in exports/brake_model.json.")
        else:
            self.log.append("Kalibrierung nicht moeglich - erst ein paar Bremsungen fahren.")

    def toggle_pit_overlay(self):
        self._toggle_simple_overlay("pit_overlay_window", PitOverlayWindow, "Pit-Overlay")

    def toggle_delta_overlay(self):
        self._toggle_simple_overlay("delta_overlay_window", DeltaOverlayWindow, "Delta-Overlay")

    def toggle_laptime_overlay(self):
        self._toggle_simple_overlay("laptime_overlay_window", LapTimeOverlayWindow, "Rundenzeiten-Overlay")

    def toggle_damage_overlay(self):
        self._toggle_simple_overlay("damage_overlay_window", DamageOverlayWindow, "Schaden-Overlay")

    def maybe_autoshow_flag_overlay(self, s):
        # 0.5.5.0: Flaggen-Overlay nur zeigen, wenn das Spiel eine echte Flagge meldet
        # (gelb/blau/weiss/rot/kariert). Gruen oder keine Flagge -> ausblenden.
        if not getattr(self, "flag_overlay_armed", False):
            return
        try:
            flag, _lbl = FlagOverlayWindow._decide(s)
        except Exception:
            flag = "none"
        real = flag not in ("green", "none")
        win = getattr(self, "flag_overlay_window", None)
        if real:
            if win is None:
                win = FlagOverlayWindow(); self.flag_overlay_window = win
                try:
                    win.apply_overlay_style(getattr(self, "overlay_style", "transparent"))
                except Exception:
                    pass
            win.update_from_main(self)
            if not win.isVisible():
                win.show(); win.raise_()
        elif win is not None and win.isVisible():
            win.hide()

    def toggle_flag_overlay(self):
        # 0.5.5.0: schaltet die automatische Flaggen-Anzeige scharf/aus.
        self.flag_overlay_armed = not getattr(self, "flag_overlay_armed", False)
        if self.flag_overlay_armed:
            self.log.append("Flaggen-Overlay scharf: erscheint automatisch, sobald das Spiel eine Flagge zeigt.")
        else:
            w = getattr(self, "flag_overlay_window", None)
            if w is not None and w.isVisible():
                w.hide()
            self.log.append("Flaggen-Overlay aus.")

    def toggle_lapgraph_overlay(self):
        self._toggle_simple_overlay("lapgraph_overlay_window", LapGraphOverlayWindow, "Rundenzeiten-Graph")

    def toggle_overtake_overlay(self):
        self._toggle_simple_overlay("overtake_overlay_window", OvertakeOverlayWindow, "Überholalarm")

    def toggle_trackstate_overlay(self):  # 0.5.9.13
        self._toggle_simple_overlay("trackstate_overlay_window", TrackStateOverlayWindow, "Streckenzustand-Panel")

    def toggle_blindspot_overlay(self):  # 0.5.9.13
        self._toggle_simple_overlay("blindspot_overlay_window", BlindSpotOverlayWindow, "Toter-Winkel-Overlay")

    def set_blindspot_flip(self, on):  # 0.5.9.13
        on = bool(on)
        win = getattr(self, "blindspot_overlay_window", None)
        if win is not None:
            win.set_flip(on)
        else:
            try:
                EXPORT_DIR.mkdir(parents=True, exist_ok=True)
                BLINDSPOT_CONFIG_PATH.write_text(json.dumps({"flip": on}), encoding="utf-8")
            except Exception:
                pass
        try:
            self.status.setText("Toter Winkel: Seiten " + ("gespiegelt." if on else "normal."))
        except Exception:
            pass

    def all_overlay_windows(self):
        """0.4.9.1: alle Overlay-Fenster, die es aktuell gibt."""
        out = []
        for a in ("overlay_window", "tire_overlay_window", "pedal_overlay_window",
                  "limit_overlay_window", "weather_overlay_window", "brake_overlay_window",
                  "fuel_overlay_window", "ffb_overlay_window", "pit_overlay_window",
                  "delta_overlay_window", "laptime_overlay_window", "damage_overlay_window",
                  "flag_overlay_window", "lapgraph_overlay_window", "overtake_overlay_window",
                  "trackstate_overlay_window", "blindspot_overlay_window"):
            w = getattr(self, a, None)
            if w is not None:
                out.append(w)
        return out

    def overlay_style_path(self):
        return str(EXPORT_DIR / "overlay_style.txt")

    def load_overlay_style(self):
        try:
            with open(self.overlay_style_path(), "r", encoding="utf-8") as f:
                v = f.read().strip()
            return v if v in ("transparent", "dark", "light") else "transparent"
        except Exception:
            return "transparent"

    def set_overlay_style(self, mode):
        """0.4.9.1: Stil auf ALLE Overlays anwenden und merken."""
        self.overlay_style = mode if mode in ("transparent", "dark", "light") else "transparent"
        for w in self.all_overlay_windows():
            try:
                w.apply_overlay_style(self.overlay_style)
            except Exception:
                pass
        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.overlay_style_path(), "w", encoding="utf-8") as f:
                f.write(self.overlay_style)
        except Exception:
            pass
        for key, act in getattr(self, "overlay_style_actions", {}).items():
            try:
                act.setChecked(key == self.overlay_style)
            except Exception:
                pass
        self.log.append(f"Overlay-Design: {self.overlay_style}.")

    def maybe_autoshow_pit_overlay(self, s):
        """0.4.9.1: Pit-Overlay automatisch beim Einfahren zeigen und beim
        Verlassen wieder schliessen (nur wenn es automatisch geoeffnet wurde)."""
        try:
            in_pit = bool(getattr(s, "in_pits", False)) or int(getattr(s, "pit_state", 0) or 0) in (1, 2, 3, 4)
        except Exception:
            return
        win = self.pit_overlay_window
        if in_pit:
            if win is None:
                win = PitOverlayWindow(); self.pit_overlay_window = win
                win.apply_overlay_style(self.overlay_style)
            if not win.isVisible():
                win.auto_opened = True
                win.update_from_main(self); win.show(); win.raise_()
                self.log.append("Boxengasse erkannt \u2013 Pit-Overlay automatisch geoeffnet.")
        elif win is not None and win.isVisible() and getattr(win, "auto_opened", False):
            win.hide(); win.auto_opened = False
            self.log.append("Boxengasse verlassen \u2013 Pit-Overlay automatisch geschlossen.")

    def toggle_weather_overlay(self):
        self._toggle_simple_overlay("weather_overlay_window", WeatherOverlayWindow, "Wetter-Overlay")

    def toggle_brake_overlay(self):
        self._toggle_simple_overlay("brake_overlay_window", BrakeTempOverlayWindow, "Bremstemperatur-Overlay")

    def toggle_fuel_overlay(self):
        self._toggle_simple_overlay("fuel_overlay_window", FuelOverlayWindow, "Sprit-Overlay")

    def toggle_ffb_overlay(self):
        self._toggle_simple_overlay("ffb_overlay_window", FFBOverlayWindow, "FFB-Overlay (Doppelklick = Statistik zuruecksetzen)")

    def toggle_limit_overlay(self):
        if self.limit_overlay_window is None:
            self.limit_overlay_window = LimitOverlayWindow()
            try:
                self.limit_overlay_window.apply_overlay_style(getattr(self, "overlay_style", "transparent"))  # 0.4.9.1
            except Exception:
                pass
        if self.limit_overlay_window.isVisible():
            self.limit_overlay_window.hide()
            self.log.append("Limit-Meter ausgeblendet.")
        else:
            self.limit_overlay_window.update_from_main(self)
            self.limit_overlay_window.show()
            self.limit_overlay_window.raise_()
            self.log.append("Limit-Meter geoeffnet. Grip-Kreis aus mLocalAccel; Doppelklick = Kalibrierung zuruecksetzen. Push eine harte Kurve/Bremsung zum Kalibrieren.")

    def toggle_overlay(self):
        if self.overlay_window is None:
            self.overlay_window = OverlayWindow()
            try:
                self.overlay_window.apply_overlay_style(getattr(self, "overlay_style", "transparent"))  # 0.4.9.1
            except Exception:
                pass
        self.cleanup_duplicate_overlays()
        if self.overlay_window.isVisible():
            self.overlay_window.hide()
            self.log.append("Monitor-Overlay ausgeblendet.")
        else:
            self.cleanup_duplicate_overlays()
            self.overlay_window.update_from_main(self)
            self.overlay_window.show()
            self.overlay_window.raise_()
            self.overlay_window.activateWindow()
            self.log.append("Monitor-Overlay geöffnet. Singleton aktiv: nur ein Coach-Overlay; Reifen-Overlay bleibt separat möglich.")

    def refresh_overlay(self):
        if self.overlay_window is not None and self.overlay_window.isVisible():
            self.overlay_window.update_from_main(self)
        if self.tire_overlay_window is not None and self.tire_overlay_window.isVisible():
            self.tire_overlay_window.update_from_main(self)
        if self.pedal_overlay_window is not None and self.pedal_overlay_window.isVisible():
            self.pedal_overlay_window.update_from_main(self)
        if self.limit_overlay_window is not None and self.limit_overlay_window.isVisible():
            self.limit_overlay_window.update_from_main(self)
        for _a in ("weather_overlay_window", "brake_overlay_window",
                   "fuel_overlay_window", "ffb_overlay_window",
                   "pit_overlay_window", "delta_overlay_window",
                   "laptime_overlay_window", "damage_overlay_window",
                   "flag_overlay_window", "lapgraph_overlay_window", "overtake_overlay_window",
                   "trackstate_overlay_window", "blindspot_overlay_window"):  # 0.4.9.0/0.4.9.1/0.5.1.0/0.5.9.13
            _w = getattr(self, _a, None)
            if _w is not None and _w.isVisible():
                _w.update_from_main(self)

    def set_dash_card(self, key: str, value: str):
        if hasattr(self, "dash_cards") and key in self.dash_cards:
            self.dash_cards[key].setText(value)

    def load_personal_laptime_reference(self) -> List[dict]:
        path = PERSONAL_LAPTIME_REFERENCE_PATH
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8-sig', newline='') as f:
                return self.parse_personal_laptime_reference_csv(f.read())
        except Exception as e:
            try:
                self.log.append(f"PB-Referenz konnte nicht geladen werden: {e}")
            except Exception:
                pass
            return []

    def load_personal_laptime_reference_tracks(self) -> List[dict]:
        """0.5.9.21: Laedt dieselbe lokal zwischengespeicherte CSV-Datei zusaetzlich
        im breiten Tier-Format (Strecke x Skill-Level-Zeiten). Additiv zur bestehenden
        flachen Referenz; wird beim Dashboard/Report bevorzugt genutzt, sofern die
        aktuelle Strecke/Klasse dort gefunden wird."""
        path = PERSONAL_LAPTIME_REFERENCE_PATH
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8-sig', newline='') as f:
                return parse_personal_laptime_reference_wide_csv(f.read())
        except Exception:
            return []

    def parse_personal_laptime_reference_csv(self, text: str) -> List[dict]:
        if not text:
            return []
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        except Exception:
            dialect = csv.excel
        rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
        if not rows:
            return []
        def find_col(names):
            cols = list(rows[0].keys())
            norm = {normalize_match_text(c): c for c in cols if c is not None}
            for want in names:
                wantn = normalize_match_text(want)
                for n, orig in norm.items():
                    if wantn == n or wantn in n:
                        return orig
            return None
        col_time = find_col(['laptime', 'lap time', 'time', 'zeit', 'rundenzeit', 'best', 'pb'])
        col_track = find_col(['track', 'strecke', 'circuit'])
        col_class = find_col(['class', 'klasse', 'vehicle class', 'category'])
        col_car = find_col(['car', 'vehicle', 'fahrzeug', 'auto', 'modell'])
        col_driver = find_col(['driver', 'fahrer', 'name'])
        entries = []
        for r in rows:
            # If no explicit time column is found, scan the whole row for the first plausible time.
            t = parse_lap_time_to_seconds(r.get(col_time, '')) if col_time else 0.0
            if t <= 0:
                for v in r.values():
                    t = parse_lap_time_to_seconds(v)
                    if t > 0:
                        break
            if not (20.0 <= t <= 1800.0):
                continue
            entries.append({
                'lap_time_s': t,
                'track': (r.get(col_track, '') if col_track else ''),
                'vehicle_class': (r.get(col_class, '') if col_class else ''),
                'car': (r.get(col_car, '') if col_car else ''),
                'driver': (r.get(col_driver, '') if col_driver else ''),
                'raw': r,
            })
        entries.sort(key=lambda e: e['lap_time_s'])
        return entries

    def import_personal_laptime_reference(self):
        msg = ("PB-Referenz laden:\n\nJa = Online aus der veröffentlichten Google-Tabelle laden\n"
               "Nein = lokale CSV-Datei auswählen\nAbbrechen = nichts tun")
        choice = QMessageBox.question(self, "PB-Referenz laden", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if choice == QMessageBox.Cancel:
            return
        try:
            if choice == QMessageBox.Yes:
                with urllib.request.urlopen(PERSONAL_LAPTIME_REFERENCE_URL, timeout=12) as resp:
                    data = resp.read().decode('utf-8-sig', errors='replace')
                PERSONAL_LAPTIME_REFERENCE_PATH.write_text(data, encoding='utf-8')
                self.personal_reference_source = "Online: Ohne Speed's LMU laptimes"
            else:
                path, _ = QFileDialog.getOpenFileName(self, "PB-Referenz CSV laden", str(EXPORT_DIR), "CSV (*.csv);;Alle Dateien (*)")
                if not path:
                    return
                data = Path(path).read_text(encoding='utf-8-sig', errors='replace')
                PERSONAL_LAPTIME_REFERENCE_PATH.write_text(data, encoding='utf-8')
                self.personal_reference_source = path
            self.personal_laptime_reference = self.parse_personal_laptime_reference_csv(data)
            self.personal_laptime_reference_tracks = parse_personal_laptime_reference_wide_csv(data)  # 0.5.9.21
            tier_info = f" | {len(self.personal_laptime_reference_tracks)} Strecken/Klassen mit Skill-Tiers" if self.personal_laptime_reference_tracks else ""
            self.log.append(f"PB-Referenz geladen: {len(self.personal_laptime_reference)} plausible Zeiten{tier_info} | Quelle: {self.personal_reference_source}")
            self.refresh_dashboard()
            QMessageBox.information(self, "PB-Referenz geladen", f"{len(self.personal_laptime_reference)} plausible Zeiten geladen.{tier_info}\nDie persönliche Bestzeit wird jetzt im Dashboard/Report eingeordnet.")
        except Exception as e:
            QMessageBox.warning(self, "PB-Referenz laden", f"PB-Referenz konnte nicht geladen werden:\n{e}\n\nTipp: Tabelle als CSV herunterladen und lokal laden.")

    def current_best_lap_time_s(self) -> float:
        best = self.lmu_best_lap_from_scoring() if self.samples else 0.0
        if best > 0:
            return best
        clean = [self.lap_time_for_report(l) for l in self.lap_summaries if l.is_clean and self.lap_time_for_report(l) > 0]
        return min(clean) if clean else 0.0

    def personal_laptime_reference_tier_match(self) -> Optional[dict]:
        """0.5.9.21: Praezise Einordnung anhand der Skill-Tier-Tabelle (Strecke + Klasse
        exakt gematcht). Liefert None, wenn keine passende Zeile gefunden wird - der
        Aufrufer faellt dann auf die bestehende, generische Prozent-Einordnung zurueck."""
        pb = self.current_best_lap_time_s()
        if pb <= 0:
            return None
        tracks = getattr(self, 'personal_laptime_reference_tracks', []) or []
        if not tracks:
            return None
        last = self.samples[-1] if self.samples else None
        if last is None:
            return None
        cur_track_raw = getattr(last, 'track', '')
        cur_track = normalize_match_text(cur_track_raw)
        cur_class = infer_vehicle_class(getattr(last, 'vehicle_class', ''), getattr(last, 'vehicle_name', ''), getattr(last, 'vehicle_model', ''))
        if not cur_track:
            return None
        # 0.5.9.21: feste Alias-Aufloesung zuerst (LMU-Venue-Name -> Sheet-Streckenname),
        # da LMU-Namen (z.B. "8 Hours of Bahrain") oft keinerlei Substring-Ueberlappung
        # mit dem Sheet-Namen (z.B. "Bahrain (wec)") haben.
        alias_target = PERSONAL_LAPTIME_TRACK_ALIASES.get(cur_track)
        if alias_target:
            candidates = [e for e in tracks if normalize_match_text(e['track']) == normalize_match_text(alias_target)]
        else:
            candidates = [e for e in tracks if normalize_match_text(e['track']) == cur_track]
        if not candidates:
            candidates = [e for e in tracks if cur_track in normalize_match_text(e['track']) or normalize_match_text(e['track']) in cur_track]
        if not candidates:
            return None
        class_matches = [e for e in candidates if e.get('vehicle_class') == cur_class]
        row = class_matches[0] if class_matches else candidates[0]
        tiers = row.get('tiers') or []
        tiers_valid = [t for t in tiers if t.get('time_s', 0) > 0]
        if not tiers_valid:
            return None
        tiers_sorted = sorted(tiers_valid, key=lambda t: t['time_s'])
        faster_than_pb = [t for t in tiers_sorted if t['time_s'] < pb]
        slower_or_eq = [t for t in tiers_sorted if t['time_s'] >= pb]
        if not faster_than_pb:
            band = f"schneller als {tiers_sorted[0]['name']}"
        elif not slower_or_eq:
            band = f"langsamer als {tiers_sorted[-1]['name']}"
        else:
            band = slower_or_eq[0]['name']
        class_note = f" ({row.get('vehicle_class_raw')})" if row.get('vehicle_class_raw') else ""
        if not class_matches:
            class_note += " – Klasse nicht exakt gematcht, nächstbeste Strecke verwendet"
        txt = f"PB {fmt_lap_time(pb)} | {band}{class_note} | {row['track']}"
        detail = ["", "Persönlicher Bestzeiten-Referenzbereich 0.5.9.21 (Skill-Tiers):",
                   f"Quelle: {getattr(self, 'personal_reference_source', 'nicht geladen')}",
                   f"Strecke: {row['track']}{class_note}",
                   f"Aktuelle persönliche Bestzeit: {fmt_lap_time(pb)} | Einordnung: {band}"]
        pb_marker_tier = slower_or_eq[0] if slower_or_eq else None
        for t in tiers_sorted:
            marker = " <- du" if t is pb_marker_tier else ""
            detail.append(f"  {t['name']} ({t['pct']:.0f}%): {fmt_lap_time(t['time_s'])}{marker}")
        if row.get('fastest_car'):
            detail.append(f"Schnellstes Auto in der Tabelle: {row['fastest_car']} | {fmt_lap_time(row.get('fastest_laptime_s', 0))}")
        return {'status': band, 'text': txt, 'lines': detail}

    def personal_laptime_reference_match(self) -> dict:
        tier_result = self.personal_laptime_reference_tier_match()  # 0.5.9.21: praezise Tabelle bevorzugen
        if tier_result:
            return tier_result
        pb = self.current_best_lap_time_s()
        if pb <= 0:
            return {'status': 'keine PB', 'text': 'noch keine gültige Bestzeit'}
        entries = getattr(self, 'personal_laptime_reference', []) or []
        if not entries:
            return {'status': 'nicht geladen', 'text': f"PB {fmt_lap_time(pb)} | Referenz nicht geladen"}
        last = self.samples[-1] if self.samples else None
        track = normalize_match_text(getattr(last, 'track', '') if last else '')
        vclass = normalize_match_text(infer_vehicle_class(getattr(last, 'vehicle_class', ''), getattr(last, 'vehicle_name', ''), getattr(last, 'vehicle_model', '')) if last else '')
        car = normalize_match_text(getattr(last, 'vehicle_name', '') if last else '')
        def score(e):
            st = 0
            et = normalize_match_text(e.get('track', ''))
            ec = normalize_match_text(e.get('vehicle_class', ''))
            ecar = normalize_match_text(e.get('car', ''))
            if track and et and (track in et or et in track): st += 8
            if vclass and ec and (vclass in ec or ec in vclass): st += 4
            if car and ecar and (car in ecar or ecar in car): st += 1
            return st
        scored = [(score(e), e) for e in entries]
        best_score = max([x[0] for x in scored], default=0)
        matched = [e for sc, e in scored if sc == best_score and sc > 0]
        if len(matched) < 3:
            # Fallback: at least class match, else all entries.
            matched = [e for e in entries if vclass and vclass in normalize_match_text(e.get('vehicle_class', ''))] or entries
        matched = sorted(matched, key=lambda e: e['lap_time_s'])
        n = len(matched)
        faster = sum(1 for e in matched if e['lap_time_s'] < pb)
        pos = faster + 1
        pct = pos / max(n, 1)
        if pct <= 0.10:
            band = 'Top 10%'
        elif pct <= 0.25:
            band = 'Top 25%'
        elif pct <= 0.50:
            band = 'vordere Hälfte'
        elif pct <= 0.75:
            band = 'Mittelfeld'
        else:
            band = 'hinteres Feld/Einsteigerbereich'
        ahead = matched[faster-1] if faster > 0 else None
        behind = matched[faster] if faster < n else None
        txt = f"PB {fmt_lap_time(pb)} | {band} | ca. Platz {pos}/{n} im passenden Referenzfeld"
        detail = ["", "Persönlicher Bestzeiten-Referenzbereich 0.4.5.4:", f"Quelle: {getattr(self, 'personal_reference_source', 'nicht geladen')}", f"Aktuelle persönliche Bestzeit: {fmt_lap_time(pb)}", f"Match-Feld: {n} Zeiten | Einordnung: {band} | Position ca. {pos}/{n}"]
        if ahead:
            detail.append(f"Nächstschnellerer Bereich: {fmt_lap_time(ahead['lap_time_s'])}" + (f" | {ahead.get('driver','')}" if ahead.get('driver') else ''))
        if behind:
            detail.append(f"Nächstlangsamerer Bereich: {fmt_lap_time(behind['lap_time_s'])}" + (f" | {behind.get('driver','')}" if behind.get('driver') else ''))
        detail.append("Hinweis: Die Einordnung nutzt Strecke/Fahrzeugklasse/Fahrzeugnamen, soweit diese Spalten in der CSV vorhanden sind. Bei unvollständigen Spalten wird konservativ breiter gematcht.")
        return {'status': band, 'text': txt, 'lines': detail}

    def personal_laptime_reference_report_lines(self) -> List[str]:
        m = self.personal_laptime_reference_match()
        return m.get('lines') or ["", "Persönlicher Bestzeiten-Referenzbereich 0.4.5.4:", m.get('text', 'keine Daten')]

    def refresh_dashboard(self):
        last = self.samples[-1] if self.samples else None
        self.set_dash_card("Verbindung", "LMU verbunden" if last else "Wartet auf LMU")
        self.set_dash_card("Recording", "🔴 LÄUFT" if self.recording else "gestoppt")
        clean = [l for l in self.lap_summaries if l.is_clean]
        self.set_dash_card("Runden", f"{len(clean)} gültig / {len(self.lap_summaries)} erkannt" if self.lap_summaries else "noch keine Analyse")
        self.set_dash_card("Fahrer", self.hardware_profile_summary(short=True))
        self.set_dash_card("Setup", self.selected_setup_label())
        ref_text = self.reference_display_label(short=True) if self.reference_lap or self.external_reference else "Auto / offen"
        self.set_dash_card("Referenz", ref_text)
        ext_txt = ("aktiv: " if self.use_external_reference else "geladen: ") + self.external_reference_label(short=True) if self.external_reference else "nicht geladen"
        self.set_dash_card("Ext. Referenz", ext_txt)
        self.set_dash_card("PB-Bereich", self.personal_laptime_reference_match().get("text", "Referenz nicht geladen"))
        if self.auto_bestlap_export_path:
            auto_txt = f"Lap {self.auto_bestlap_lap_number} | {fmt_lap_time(self.auto_bestlap_time_s)}"
        else:
            auto_txt = "AN · live" if self.auto_bestlap_export_enabled else "AUS"
        self.set_dash_card("Auto-Bestlap", auto_txt)
        if last:
            tire_txt = f"VL/VR {last.tire_fl_pressure_kpa:.0f}/{last.tire_fr_pressure_kpa:.0f} kPa | HL/HR {last.tire_rl_pressure_kpa:.0f}/{last.tire_rr_pressure_kpa:.0f} kPa"
        else:
            tire_txt = "noch keine Daten"
        self.set_dash_card("Reifen", tire_txt)
        self.set_dash_card("Vergleich", f"Lap {self.compare_lap.lap_number}" if self.compare_lap else "Auto / offen")
        zones = self.grouped_problem_zones() if self.segment_deltas else []
        if zones:
            z = zones[0]
            self.set_dash_card("Coach-Fokus", f"Zone 1 | {z[0]}-{z[1]} m | {z[2]:+.3f} s")
        else:
            self.set_dash_card("Coach-Fokus", "nach Rundenvergleich")
        if hasattr(self, "dash_coach"):
            lines = self.coach_report_lines()
            # Dashboard kurz halten: nur Vergleich, Top-Zonen und Kurzfazit.
            keep = []
            for line in lines:
                if line.startswith("Vergleich") or line.startswith("Zone 1") or line.startswith("Zone 2") or line.startswith("Kurzfazit") or line.startswith("Der größte"):
                    keep.append(line)
            self.dash_coach.setPlainText("\n".join(keep) if keep else "Nach Recording-Stopp erscheinen hier die wichtigsten Coach-Hinweise.")
        if hasattr(self, "setup_coach_text"):
            sc_lines = self.tire_setup_coach_lines()
            self.setup_coach_text.setPlainText("\n".join(sc_lines) if sc_lines else "Noch keine Reifen-/Setup-Daten.")
        if hasattr(self, "limit_coach_text"):
            lc_lines = self.limit_coach_report_lines(summary_only=False)
            self.limit_coach_text.setPlainText("\n".join(lc_lines) if lc_lines else "Noch keine Limit-Daten.")
            lvl, _, _ = self.limit_coach_assessment()
            self.set_dash_card("Limit", lvl)
        if hasattr(self, "input_coach_text") and self.samples and self.lap_summaries:
            ic_lines = self.input_coach_report_lines(summary_only=True)
            self.input_coach_text.setPlainText("\n".join(ic_lines) if ic_lines else "Nach Recording-Stopp erscheinen hier Gas-/Brems-Hinweise.")
        if hasattr(self, "hardware_coach_text"):
            self.hardware_coach_text.setPlainText("\n".join(self.hardware_context_lines()))
        self.refresh_overlay()

    def selected_setup_label(self) -> str:
        try:
            txt = self.setup_selector.currentText().strip()
        except Exception:
            txt = ""
        return txt or "nicht gesetzt / LMU-Setup"

    def current_context(self):
        s = self.samples[-1] if self.samples else None
        if s:
            return s.track, infer_vehicle_class(s.vehicle_class, s.vehicle_name, s.vehicle_model), s.vehicle_name
        return "", "Unbekannt", ""

    def external_reference_label(self, short: bool = False) -> str:
        if not self.external_reference:
            return "nicht geladen"
        m = self.external_reference.get("meta", {})
        lap_time = m.get("lap_time_s")
        time_txt = fmt_lap_time(lap_time) if isinstance(lap_time, (int, float)) else "-"
        if short:
            return f"{m.get('track','?')} | {m.get('vehicle_class','?')} | {time_txt}"
        return f"{m.get('track','?')} | {m.get('vehicle_class','?')} | {m.get('vehicle_name','?')} | {time_txt}"

    def reference_display_label(self, short: bool = False) -> str:
        if self.external_reference and self.use_external_reference:
            return "Extern: " + self.external_reference_label(short=short)
        if self.reference_lap:
            return f"Lap {self.reference_lap.lap_number}"
        return "Auto / offen"

    def segment_to_dict(self, seg: SegmentSummary) -> dict:
        return {
            "lap_number": seg.lap_number, "start_m": seg.start_m, "end_m": seg.end_m,
            "samples": seg.samples, "seg_time_s": seg.seg_time_s, "avg_speed": seg.avg_speed,
            "min_speed": seg.min_speed, "max_speed": seg.max_speed, "max_brake": seg.max_brake,
            "avg_throttle": seg.avg_throttle, "gear_common": seg.gear_common,
        }

    def dict_to_segment(self, d: dict) -> SegmentSummary:
        return SegmentSummary(
            lap_number=int(d.get("lap_number", -1)), start_m=int(d.get("start_m", 0)), end_m=int(d.get("end_m", 50)),
            samples=int(d.get("samples", 0)), seg_time_s=fnum(d.get("seg_time_s")), avg_speed=fnum(d.get("avg_speed")),
            min_speed=fnum(d.get("min_speed")), max_speed=fnum(d.get("max_speed")), max_brake=fnum(d.get("max_brake")),
            avg_throttle=fnum(d.get("avg_throttle")), gear_common=str(d.get("gear_common", "-")),
        )


    def set_auto_bestlap_ui(self):
        state = "AN" if self.auto_bestlap_export_enabled else "AUS"
        self.btn_auto_bestlap.setText(f"Auto-Bestlap: {state}")
        self.btn_auto_bestlap.setToolTip("F7: Auto-Bestlap AN/AUS")
        self.status.setText(f"Auto-Bestlap {state}.")

    def toggle_live_log(self):  # 0.5.9.26
        if self.live_log_enabled:
            self.stop_live_log()
        else:
            self.start_live_log()

    def start_live_log(self):  # 0.5.9.26
        try:
            CSV_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = CSV_DIR / f"live_log_{ts}.csv"
            fh = open(path, "w", newline="", encoding="utf-8")
            fieldnames = [f.name for f in _dc_fields(Sample)]
            writer = csv.writer(fh)
            writer.writerow(fieldnames)
            self.live_log_fh = fh
            self.live_log_writer = writer
            self.live_log_path = path
            self.live_log_row_count = 0
            self.live_log_enabled = True
            self.btn_live_log.setText("Live-Log: AN")
            self.log.append(f"Live-Log gestartet: {path.name} (unabhaengig vom Recording, jeder Live-Tick wird mitgeschrieben).")
        except Exception as e:
            self.live_log_enabled = False
            QMessageBox.warning(self, "Live-Log", f"Live-Log konnte nicht gestartet werden:\n{e}")

    def stop_live_log(self):  # 0.5.9.26
        self.live_log_enabled = False
        self.btn_live_log.setText("Live-Log: AUS")
        path, n = self.live_log_path, self.live_log_row_count
        try:
            if self.live_log_fh is not None:
                self.live_log_fh.flush()
                self.live_log_fh.close()
        except Exception:
            pass
        self.live_log_fh = None
        self.live_log_writer = None
        if path is not None:
            self.log.append(f"Live-Log gestoppt: {n} Zeilen in {path}")

    def write_live_log_row(self, s: Sample):  # 0.5.9.26
        if not self.live_log_enabled or self.live_log_writer is None:
            return
        try:
            self.live_log_writer.writerow(_dc_astuple(s))
            self.live_log_row_count += 1
            if self.live_log_row_count % 20 == 0:  # ~alle 2s flushen, Datenverlust bei Absturz begrenzen
                self.live_log_fh.flush()
        except Exception as e:
            self.log.append(f"Live-Log-Fehler, wird gestoppt: {e}")
            self.stop_live_log()

    def toggle_auto_bestlap_export(self):
        self.auto_bestlap_export_enabled = not self.auto_bestlap_export_enabled
        self.set_auto_bestlap_ui()
        self.log.append("Auto-Bestlap-Export " + ("aktiviert" if self.auto_bestlap_export_enabled else "deaktiviert"))
        self.refresh_dashboard()

    def set_auto_switch_ui(self):  # 0.5.9.24
        state = "AN" if self.auto_switch_recording_enabled else "AUS"
        self.btn_auto_switch.setText(f"Auto-Wechsel: {state}")
        self.btn_auto_switch.setToolTip(
            "Bei Strecken-/Fahrzeugwechsel während der Aufnahme automatisch stoppen "
            "(Report/CSV speichern) und für den neuen Kontext neu starten."
        )

    def toggle_auto_switch_recording(self):  # 0.5.9.24
        self.auto_switch_recording_enabled = not self.auto_switch_recording_enabled
        self.set_auto_switch_ui()
        self.log.append("Auto-Wechsel-Neustart " + ("aktiviert" if self.auto_switch_recording_enabled else "deaktiviert"))

    def toggle_auto_bestlap_hotkey(self):
        # F7 kann durch Stream Deck + App-Shortcut + Windows-Polling doppelt feuern.
        # Debounce verhindert AN+AUS im selben Tastendruck.
        now = datetime.now().timestamp()
        if now - getattr(self, "last_auto_hotkey_ts", 0.0) < 0.8:
            self.log.append("F7 ignoriert: Tastendruck-Doppelung verhindert.")
            return
        self.last_auto_hotkey_ts = now
        self.toggle_auto_bestlap_export()

    def snapshot_hotkey(self):
        # Auch F9 kann je nach Stream Deck Profil doppelt feuern.
        now = datetime.now().timestamp()
        if now - getattr(self, "last_snapshot_hotkey_ts", 0.0) < 0.8:
            self.log.append("F9 ignoriert: Tastendruck-Doppelung verhindert.")
            return
        self.last_snapshot_hotkey_ts = now
        self.snapshot(silent=False)

    def toggle_tire_overlay_hotkey(self):
        # F6: separates Reifen-Overlay. Debounce gegen Stream-Deck/Key-Repeat.
        now = datetime.now().timestamp()
        if now - getattr(self, "last_tire_overlay_hotkey_ts", 0.0) < 1.0:
            self.log.append("F6 ignoriert: Tastendruck-Doppelung verhindert.")
            return
        self.last_tire_overlay_hotkey_ts = now
        self.cleanup_duplicate_tire_overlays()
        self.toggle_tire_overlay()

    def setup_hotkeys(self):
        # Unter Windows nutzen wir ausschließlich den Polling-Hotkey.
        # Sonst feuern QShortcut + GetAsyncKeyState parallel und Stream Deck kann doppelt auslösen
        # oder Overlay-Fenster scheinbar doppelt öffnen.
        if sys.platform.startswith("win"):
            self.shortcut_tire_overlay = None
            self.shortcut_auto_bestlap = None
            self.shortcut_record = None
            self.shortcut_snapshot = None
            self.shortcut_overlay = None
            self.shortcut_live_coach = None
            self.shortcut_brake_coach = None
            self.log.append("App-Hotkeys unter Windows deaktiviert: nutze nur Windows-Global-Polling gegen Doppeltrigger. F6=Reifen-Overlay.")
            return

        self.shortcut_tire_overlay = QShortcut(QKeySequence("F6"), self)
        self.shortcut_tire_overlay.setContext(Qt.ApplicationShortcut)
        self.shortcut_tire_overlay.activated.connect(self.toggle_tire_overlay_hotkey)
        self.shortcut_auto_bestlap = QShortcut(QKeySequence("F7"), self)
        self.shortcut_auto_bestlap.setContext(Qt.ApplicationShortcut)
        self.shortcut_auto_bestlap.activated.connect(self.toggle_auto_bestlap_hotkey)
        self.shortcut_record = QShortcut(QKeySequence("F8"), self)
        self.shortcut_record.setContext(Qt.ApplicationShortcut)
        self.shortcut_record.activated.connect(self.toggle_recording_hotkey)
        self.shortcut_snapshot = QShortcut(QKeySequence("F9"), self)
        self.shortcut_snapshot.setContext(Qt.ApplicationShortcut)
        self.shortcut_snapshot.activated.connect(self.snapshot_hotkey)
        self.shortcut_overlay = QShortcut(QKeySequence("F10"), self)
        self.shortcut_overlay.setContext(Qt.ApplicationShortcut)
        self.shortcut_overlay.activated.connect(self.toggle_overlay_hotkey)
        self.shortcut_live_coach = QShortcut(QKeySequence("F11"), self)
        self.shortcut_live_coach.setContext(Qt.ApplicationShortcut)
        self.shortcut_live_coach.activated.connect(self.toggle_live_coach_hotkey)
        self.shortcut_brake_coach = QShortcut(QKeySequence("F12"), self)
        self.shortcut_brake_coach.setContext(Qt.ApplicationShortcut)
        self.shortcut_brake_coach.activated.connect(self.toggle_brake_coach_hotkey)
        self.log.append("App-Hotkeys aktiv: F6 Reifen-Overlay · F7 Auto-Bestlap AN/AUS · F8 Recording Start/Stop · F9 Snapshot · F10 Coach-Overlay · F11 Live-Coach · F12 Kurven-Coach")

    def toggle_recording_hotkey(self):
        # F8 kann bei Windows/Stream Deck durch Key-Repeat doppelt auslösen.
        # Kurzer Debounce verhindert direktes Start+Stop im selben Tastendruck.
        now = datetime.now().timestamp()
        if now - getattr(self, "last_record_hotkey_ts", 0.0) < 0.8:
            self.log.append("F8 ignoriert: Tastendruck-Doppelung verhindert.")
            return
        self.last_record_hotkey_ts = now
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def toggle_overlay_hotkey(self):
        # F10 kann durch App-Shortcut + Windows-Polling doppelt feuern.
        # Debounce verhindert Show+Hide im selben Tastendruck.
        now = datetime.now().timestamp()
        if now - getattr(self, "last_overlay_hotkey_ts", 0.0) < 1.0:
            self.log.append("F10 ignoriert: Tastendruck-Doppelung verhindert.")
            return
        self.last_overlay_hotkey_ts = now
        self.cleanup_duplicate_overlays()
        self.toggle_overlay()



    def toggle_live_coach_hotkey(self):
        now = datetime.now().timestamp()
        if now - getattr(self, "last_live_coach_hotkey_ts", 0.0) < 0.8:
            return
        self.last_live_coach_hotkey_ts = now
        self.set_live_coach_enabled(not self.live_coach_enabled)
        if getattr(self, "act_live_coach", None) is not None:
            self.act_live_coach.setChecked(self.live_coach_enabled)

    def set_live_coach_enabled(self, on):
        self.live_coach_enabled = bool(on)
        self.live_coach.set_enabled(self.live_coach_enabled)
        if self.live_coach_enabled and not self.tts.is_available():
            self.log.append("Live-Coach an, aber keine Sprachausgabe verfügbar – Piper/SAPI prüfen.")
        self.status.setText("Live-Coach AN – Sprachhinweise auf der Geraden (F11)."
                            if self.live_coach_enabled else "Live-Coach AUS.")

    def toggle_brake_coach_hotkey(self):
        now = datetime.now().timestamp()
        if now - getattr(self, "last_brake_coach_hotkey_ts", 0.0) < 0.8:
            return
        self.last_brake_coach_hotkey_ts = now
        self.set_brake_coach_enabled(not self.brake_coach_enabled)
        if getattr(self, "act_brake_coach", None) is not None:
            self.act_brake_coach.setChecked(self.brake_coach_enabled)

    def set_brake_coach_enabled(self, on):
        self.brake_coach_enabled = bool(on)
        self.brake_coach.set_enabled(self.brake_coach_enabled)
        if self.brake_coach_enabled:
            if not self.tts.is_available():
                self.log.append("Kurven-Coach an, aber keine Sprachausgabe – Piper/SAPI prüfen.")
            elif not self.brake_coach.has_points():
                self.log.append("Kurven-Coach an – noch keine Referenzpunkte. Fahre eine saubere Bestlap.")
            self.status.setText("Kurven-Coach AN – Bremsen/Einlenken/Gas an harten Kurven (F12).")
        else:
            self.status.setText("Kurven-Coach AUS.")

    def setup_windows_global_hotkeys(self):
        """Poll F6-F10 on Windows so Stream Deck / keyboard also work while LMU has focus.
        This avoids requiring a separate global hotkey library.
        """
        self.global_hotkey_timer = None
        if not sys.platform.startswith("win"):
            self.log.append("Globale Windows-Hotkeys nicht aktiv: nicht unter Windows erkannt.")
            return
        try:
            self._user32 = ctypes.windll.user32
            self.global_hotkey_timer = QTimer(self)
            self.global_hotkey_timer.setInterval(60)
            self.global_hotkey_timer.timeout.connect(self.poll_windows_hotkeys)
            self.global_hotkey_timer.start()
            self.log.append("Windows-Global-Hotkeys aktiv: F6/F7/F8/F9/F10 funktionieren auch wenn LMU im Fokus ist.")
        except Exception as e:
            self.log.append(f"Windows-Global-Hotkeys konnten nicht aktiviert werden: {e}")

    def _vk_down(self, vk: int) -> bool:
        try:
            return bool(self._user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            return False

    def poll_windows_hotkeys(self):
        # VK codes: F6=0x75, F7=0x76, F8=0x77, F9=0x78, F10=0x79, F11=0x7A, F12=0x7B
        mapping = {"F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B}
        for key, vk in mapping.items():
            down = self._vk_down(vk)
            was_down = self.global_hotkey_state.get(key, False)
            if down and not was_down:
                if key == "F6":
                    self.toggle_tire_overlay_hotkey()
                elif key == "F7":
                    self.toggle_auto_bestlap_hotkey()
                elif key == "F8":
                    self.toggle_recording_hotkey()
                elif key == "F9":
                    self.snapshot_hotkey()
                elif key == "F10":
                    self.toggle_overlay_hotkey()
                elif key == "F11":
                    self.toggle_live_coach_hotkey()
                elif key == "F12":
                    self.toggle_brake_coach_hotkey()
            self.global_hotkey_state[key] = down

    def _stable_timing_value(self, vals: List[float]) -> float:
        """Return the most stable official timing value from LMU scoring rows.

        LMU/rF2 updates mLastLapTime shortly after a lap rollover. On some
        frames the previous value can still be visible for one sample. Taking
        the most common rounded value avoids picking that stale one.
        """
        clean = []
        for v in vals or []:
            try:
                f = float(v)
                if 20.0 <= f <= 1800.0 and math.isfinite(f):
                    clean.append(round(f, 3))
            except Exception:
                pass
        if not clean:
            return 0.0
        counts = {}
        for v in clean:
            counts[v] = counts.get(v, 0) + 1
        # Prefer the value that appears most often; tie-breaker: later value in the list.
        best_count = max(counts.values())
        candidates = [v for v, c in counts.items() if c == best_count]
        for v in reversed(clean):
            if v in candidates:
                return float(v)
        return float(candidates[0])

    def lmu_scoring_time_for_lap_from_rows(self, rows: List[Sample], lap_number: int) -> float:
        """0.4.5.2: Official lap time per lap from LMU scoring.

        In LMU/rF2, mLastLapTime belongs to the lap that just finished.
        During lap N+1 it normally contains the official time for lap N.
        Therefore we first look at exact next-lap samples and only then use
        conservative fallbacks. This keeps Sarthe times close to the sim/SimHub
        timing without needing SimHub.
        """
        if not rows or lap_number is None or lap_number < 0:
            return 0.0
        try:
            lap_number = int(lap_number)
        except Exception:
            return 0.0

        exact_next = [float(getattr(s, "last_lap_time", 0.0)) for s in rows if int(getattr(s, "lap_number", -999)) == lap_number + 1]
        val = self._stable_timing_value(exact_next)
        if val > 0:
            return val

        exact_completed_next = [float(getattr(s, "last_lap_time", 0.0)) for s in rows if int(getattr(s, "completed_laps", -999)) == lap_number + 1]
        val = self._stable_timing_value(exact_completed_next)
        if val > 0:
            return val

        # Fallback: sometimes the finished lap is stored in rows where the current
        # telemetry lap number already advanced inconsistently. Use a narrow window.
        narrow = [float(getattr(s, "last_lap_time", 0.0)) for s in rows if lap_number <= int(getattr(s, "lap_number", -999)) <= lap_number + 2]
        val = self._stable_timing_value(narrow)
        if val > 0:
            return val

        return 0.0

    def lmu_official_lap_time_for_lap_from_rows(self, rows: List[Sample], lap_number: int) -> float:
        # Backwards-compatible wrapper: first true per-lap scoring, then no blind best-lap fallback.
        # Best-lap fallback made every lap look like the current best and confused reports/export.
        return self.lmu_scoring_time_for_lap_from_rows(rows, lap_number)

    def lmu_best_lap_from_scoring(self) -> float:
        vals = [float(getattr(s, "best_lap_time", 0.0)) for s in self.samples if 20.0 <= float(getattr(s, "best_lap_time", 0.0)) <= 1800.0]
        return min(vals) if vals else 0.0

    def timing_probe_report_lines(self) -> List[str]:
        lines = ["", "LMU-Scoring-Timing-Probe 0.4.5.4:"]
        if not self.samples:
            lines.append("Noch keine Samples vorhanden.")
            return lines
        best = self.lmu_best_lap_from_scoring()
        if best > 0:
            lines.append(f"LMU best_lap_time aus Scoring: {fmt_lap_time(best)} ({best:.3f} s)")
        else:
            lines.append("LMU best_lap_time aus Scoring: nicht verfügbar")
        last_vals = [float(getattr(s, "last_lap_time", 0.0)) for s in self.samples if 20.0 <= float(getattr(s, "last_lap_time", 0.0)) <= 1800.0]
        if last_vals:
            lines.append(f"LMU last_lap_time Werte erkannt: {len(last_vals)} Samples | min {fmt_lap_time(min(last_vals))} | max {fmt_lap_time(max(last_vals))}")
        else:
            lines.append("LMU last_lap_time Werte erkannt: keine plausiblen Werte")
        lines.append("Per-Lap-Zuordnung: mLastLapTime wird auf der Folgerunde gelesen; SimHub ist dafür nicht nötig.")
        lines.append("Lap | LMU-Scoring-Zeit | Interne Zeit | Quelle")
        if not self.lap_summaries:
            self.update_laps()
        for l in self.lap_summaries[:30]:
            official = self.lmu_scoring_time_for_lap_from_rows(self.samples, l.lap_number)
            if official > 0:
                lines.append(f"{l.lap_number} | {fmt_lap_time(official)} | {fmt_lap_time(l.duration_s)} | LMU Scoring")
            else:
                lines.append(f"{l.lap_number} | - | {fmt_lap_time(l.duration_s)} | intern/Fallback")
        return lines

    def lmu_official_lap_time_for_lap(self, lap_number: int) -> float:
        return self.lmu_official_lap_time_for_lap_from_rows(self.samples, lap_number)

    def lap_time_for_report(self, lap: LapSummary) -> float:
        if not lap:
            return 0.0
        official = self.lmu_official_lap_time_for_lap(lap.lap_number)
        if official > 0:
            return official
        return lap.duration_s

    def lap_time_for_export(self, lap: LapSummary) -> float:
        official = self.lmu_official_lap_time_for_lap(lap.lap_number)
        if official > 0:
            return official
        est = self.estimated_lap_time_from_speed(lap.lap_number)
        if est < 999998.0 and est > 0:
            return est
        return lap.duration_s

    def estimated_lap_time_from_rows(self, rows: List[Sample], lap_number: int) -> float:
        official = self.lmu_official_lap_time_for_lap_from_rows(rows, lap_number)
        if official > 0:
            return official
        segs = self.build_segment_summaries_from_rows(rows, lap_number)
        if not segs:
            return 999999.0
        return sum(s.seg_time_s for s in segs.values())

    def build_reference_payload_from_rows(self, lap: LapSummary, source_rows: List[Sample]) -> Optional[dict]:
        lap_samples = [s for s in source_rows if s.lap_number == lap.lap_number and not self.is_non_driving_sample(s)]
        if not lap_samples:
            return None
        first = lap_samples[0]
        vclass = infer_vehicle_class(first.vehicle_class, first.vehicle_name, first.vehicle_model)
        segs = self.build_segment_summaries_from_rows(lap_samples, lap.lap_number)
        if not segs:
            return None
        lap_time = self.estimated_lap_time_from_rows(lap_samples, lap.lap_number)
        meta = {
            "format": "lmu_consistency_reference_v1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "app_version": APP_VERSION,
            "auto_export": True,
            "track": first.track,
            "vehicle_class": vclass,
            "vehicle_name": first.vehicle_name,
            "vehicle_model": first.vehicle_model,
            "lap_number": lap.lap_number,
            "lap_time_s": lap_time,
            "avg_speed": lap.avg_speed,
            "fuel_used_l": lap.fuel_used_l,
            "setup_label": self.selected_setup_label(),
            "driver_hardware_profile": self.selected_hardware_profile(),
        }
        return {
            "meta": meta,
            "segments": [self.segment_to_dict(x) for x in segs.values()],
            "path": [{"pos_x": x.pos_x, "pos_z": x.pos_z, "lap_dist_m": x.lap_dist_m, "speed_kmh": x.speed_kmh} for x in lap_samples],
        }

    def build_reference_payload_for_lap(self, lap: LapSummary) -> Optional[dict]:
        return self.build_reference_payload_from_rows(lap, self.samples)

    def best_exportable_lap(self) -> Optional[LapSummary]:
        clean = [l for l in self.lap_summaries if l.is_clean]
        if not clean:
            return None
        max_cov = max((l.coverage_m for l in clean), default=0.0)
        candidates = []
        for l in clean:
            # Extra guard for auto-reference export: only full flying laps with enough data.
            if l.valid_samples < max(80, int(max(1.0, l.coverage_m) / 65.0)):
                continue
            if max_cov and l.coverage_m < max_cov * 0.93:
                continue
            if l.fuel_used_l > 0 and l.fuel_used_l < 0.75:
                continue
            ltime = self.lap_time_for_export(l)
            if ltime < 30 or l.avg_speed < 120:
                continue
            segs = self.build_segment_summaries_for_lap(l.lap_number)
            if len(segs) < 40:
                continue
            candidates.append(l)
        if not candidates:
            return None
        return min(candidates, key=lambda l: self.lap_time_for_export(l))

    def auto_bestlap_file_path(self, payload: dict, lap: LapSummary, lap_time: float) -> Path:
        meta = payload.get("meta", {})
        track = safe_filename_part(meta.get("track", "track"))
        vclass = safe_filename_part(meta.get("vehicle_class", "class"))
        car = safe_filename_part(meta.get("vehicle_model") or meta.get("vehicle_name") or "car")[:42]
        time_txt = fmt_lap_time(lap_time).replace(":", "-")
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return REFERENCE_DIR / f"reference_AUTO_{track}_{vclass}_{car}_{time_txt}_lap{lap.lap_number}_{stamp}.json"

    def activate_auto_reference_payload(self, payload: dict, path: Path, lap: LapSummary, lap_time: float, live: bool = False):
        self.auto_bestlap_export_path = str(path)
        self.auto_bestlap_lap_number = lap.lap_number
        self.auto_bestlap_time_s = lap_time
        self.external_reference = payload
        self.use_external_reference = True
        self.refresh_lap_combos()
        src = "Live-Bestlap" if live else "Auto-Bestlap"
        self.log.append(f"{src} exportiert und als Referenz aktiviert: Lap {lap.lap_number} | {fmt_lap_time(lap_time)} | {path}")
        self.refresh_dashboard()

    def auto_export_bestlap_reference(self):
        if not self.auto_bestlap_export_enabled:
            return
        lap = self.best_exportable_lap()
        if not lap:
            self.log.append("Auto-Bestlap-Export: keine geeignete saubere Runde gefunden.")
            return
        lap_time = self.lap_time_for_export(lap)
        payload = self.build_reference_payload_for_lap(lap)
        if not payload:
            self.log.append("Auto-Bestlap-Export: Referenzdaten konnten nicht erstellt werden; keine gültige komplette Runde im Live-Puffer.")
            return
        path = self.auto_bestlap_file_path(payload, lap, lap_time)
        try:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.activate_auto_reference_payload(payload, path, lap, lap_time, live=False)
        except Exception as e:
            self.log.append(f"Auto-Bestlap-Export fehlgeschlagen: {e}")
        self.refresh_dashboard()

    def export_reference_lap(self):
        if not self.reference_lap:
            QMessageBox.warning(self, "Referenz exportieren", "Keine Referenzrunde vorhanden. Erst Recording stoppen und Referenz erzeugen.")
            return
        payload = self.build_reference_payload_for_lap(self.reference_lap)
        if not payload:
            QMessageBox.warning(self, "Referenz exportieren", "Keine vollständigen Referenzdaten für diese Runde gefunden.")
            return
        meta = payload.get("meta", {})
        lap_time = fnum(meta.get("lap_time_s"))
        default = REFERENCE_DIR / f"reference_{safe_filename_part(meta.get('track','track'))}_{safe_filename_part(meta.get('vehicle_class','class'))}_{fmt_lap_time(lap_time).replace(':','-')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Referenzrunde exportieren", str(default), "Referenz (*.json)")
        if not path:
            return
        # Manual exports are marked as normal reference files.
        payload.setdefault("meta", {})["auto_export"] = False
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log.append(f"Referenz exportiert: {path}")

    def import_reference_lap(self):
        path, _ = QFileDialog.getOpenFileName(self, "Referenzrunde importieren", str(REFERENCE_DIR), "Referenz (*.json)")
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            QMessageBox.warning(self, "Referenz importieren", f"Datei konnte nicht gelesen werden:\n{e}")
            return
        meta = payload.get("meta", {})
        if meta.get("format") != "lmu_consistency_reference_v1":
            QMessageBox.warning(self, "Referenz importieren", "Keine gültige LMU-Consistency-Referenzdatei.")
            return
        cur_track, cur_class, cur_car = self.current_context()
        ref_track = meta.get("track", "")
        ref_class = meta.get("vehicle_class", "Unbekannt")
        warnings = []
        if cur_track and ref_track and cur_track != ref_track:
            warnings.append(f"Strecke anders: aktuell {cur_track} / Referenz {ref_track}")
        if cur_class and ref_class and cur_class != "Unbekannt" and ref_class != "Unbekannt" and cur_class != ref_class:
            warnings.append(f"Fahrzeugklasse anders: aktuell {cur_class} / Referenz {ref_class}")
        if warnings:
            msg = "Referenz passt möglicherweise nicht:\n" + "\n".join(warnings) + "\n\nTrotzdem laden?"
            if QMessageBox.question(self, "Referenz importieren", msg) != QMessageBox.Yes:
                return
        self.external_reference = payload
        self.use_external_reference = True
        self.log.append(f"Externe Referenz geladen und aktiviert: {self.external_reference_label()}")
        if cur_class == ref_class and cur_car and meta.get("vehicle_name") and cur_car != meta.get("vehicle_name"):
            self.log.append("Hinweis: gleiche Klasse, anderes Fahrzeug — Vergleich ist erlaubt, aber fahrzeugspezifische Unterschiede beachten.")
        self.refresh_lap_combos(); self.update_lap_compare(); self.update_heatmap(); self.update_coach_text(); self.refresh_dashboard()

    def open_export_folder(self):
        for _d in (EXPORT_DIR, REPORT_DIR, CSV_DIR, REFERENCE_DIR):
            _d.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(EXPORT_DIR)))

    def parse_ref(self, edit: QLineEdit) -> Optional[float]:
        txt = edit.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            return float(txt)
        except Exception:
            return None

    def refresh_lap_combos(self):
        if not hasattr(self, "ref_lap_combo"):
            return
        clean = [l for l in self.lap_summaries if l.is_clean]
        old_ref = "__external__" if self.use_external_reference and self.external_reference else self.manual_reference_lap
        old_cmp = self.manual_compare_lap
        self.ref_lap_combo.blockSignals(True); self.cmp_lap_combo.blockSignals(True)
        self.ref_lap_combo.clear(); self.cmp_lap_combo.clear()
        self.ref_lap_combo.addItem("Auto – beste Sessionrunde", None)
        if self.external_reference:
            self.ref_lap_combo.addItem("Importierte Referenz AKTIV/auswählbar – " + self.external_reference_label(short=True), "__external__")
        self.cmp_lap_combo.addItem("Auto – beste Vergleichsrunde", None)
        for l in clean:
            t = self.estimated_lap_time_from_speed(l.lap_number)
            label = f"Lap {l.lap_number} | {fmt_lap_time(t)}* | Avg {l.avg_speed:.1f}"
            self.ref_lap_combo.addItem("Session: " + label, l.lap_number)
            self.cmp_lap_combo.addItem(label, l.lap_number)
        def select(combo, val):
            idx = 0
            if val is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == val:
                        idx = i; break
            combo.setCurrentIndex(idx)
        select(self.ref_lap_combo, old_ref); select(self.cmp_lap_combo, old_cmp)
        self.ref_lap_combo.blockSignals(False); self.cmp_lap_combo.blockSignals(False)

    def apply_lap_selection(self):
        ref_choice = self.ref_lap_combo.currentData()
        self.use_external_reference = (ref_choice == "__external__")
        self.manual_reference_lap = None if self.use_external_reference else ref_choice
        self.manual_compare_lap = self.cmp_lap_combo.currentData()
        if self.manual_reference_lap is not None and self.manual_compare_lap is not None and self.manual_reference_lap == self.manual_compare_lap:
            QMessageBox.warning(self, "Rundenauswahl", "Referenz und Vergleich dürfen nicht dieselbe Runde sein.")
            self.manual_compare_lap = None
            self.cmp_lap_combo.setCurrentIndex(0)
        self.update_laps()
        self.update_segments()
        self.update_lap_compare()
        self.update_heatmap()
        self.update_coach_text()
        ref_log = "Import" if self.use_external_reference else (self.manual_reference_lap or "Auto")
        self.log.append(f"Rundenauswahl angewendet: Referenz={ref_log} | Vergleich={self.manual_compare_lap or 'Auto'}")
        self.refresh_dashboard()

    def lap_by_number(self, lap_number: Optional[int]) -> Optional[LapSummary]:
        if lap_number is None:
            return None
        for l in self.lap_summaries:
            if l.lap_number == lap_number and l.is_clean:
                return l
        return None

    def start_finish_warning(self) -> str:
        if not self.segment_deltas:
            return ""
        start_losses = [d for d in self.segment_deltas if d.start_m < 250 and d.delta_s > 0.10]
        if not start_losses:
            return ""
        loss = sum(d.delta_s for d in start_losses)
        spd = sum(d.speed_delta for d in start_losses) / max(1, len(start_losses))
        if loss >= 0.25 and spd < -15:
            return f"Hinweis: Start/Ziel-Bereich 0-250 m wirkt verfälscht oder stark ausgangsabhängig ({loss:+.3f} s, Speed {spd:+.1f} km/h). Für die Fahranalyse zuerst die nächste echte Brems-/Kurvenzone priorisieren."
        return ""

    def maybe_export_live_bestlap(self, rows: List[Sample], lap_number: Optional[int]):
        if not self.auto_bestlap_export_enabled or self.recording:
            return
        if not rows or lap_number is None or len(rows) < 250:
            return
        summaries = self.build_lap_summaries_from_rows(rows)
        lap = None
        for l in summaries:
            if l.lap_number == lap_number:
                lap = l
                break
        if not lap or not lap.is_clean:
            return
        if lap.valid_samples < 350 or lap.coverage_m < 2000 or lap.avg_speed < 120 or lap.fuel_used_l < 0.5:
            return
        segs = self.build_segment_summaries_from_rows(rows, lap.lap_number)
        if len(segs) < 40:
            return
        lap_time = sum(x.seg_time_s for x in segs.values())
        if self.auto_bestlap_time_s is not None and lap_time >= self.auto_bestlap_time_s - 0.001:
            return
        payload = self.build_reference_payload_from_rows(lap, rows)
        if not payload:
            return
        path = self.auto_bestlap_file_path(payload, lap, lap_time)
        try:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.activate_auto_reference_payload(payload, path, lap, lap_time, live=True)
        except Exception as e:
            self.log.append(f"Live-Bestlap-Export fehlgeschlagen: {e}")

    def sample_vehicle_signature(self, s: Sample):
        """Stabiler Schlüssel für den Recording-Lock.
        Ziel: Ein Recording darf nicht versehentlich mehrere Fahrzeuge/Klassen mischen.
        """
        track = (s.track or "").strip()
        vclass = infer_vehicle_class(s.vehicle_class, s.vehicle_name, s.vehicle_model)
        name = (s.vehicle_model or s.vehicle_name or "").strip()
        if not track or not name:
            return None
        return (track, vclass, name)

    def sample_vehicle_label(self, sig) -> str:
        if not sig:
            return "nicht gesetzt"
        return f"{sig[0]} | {sig[1]} | {sig[2]}"

    def accept_recording_sample(self, s: Sample) -> bool:
        """Schützt Reports/CSV vor Fahrzeug- oder Klassenwechseln während einer Aufnahme.
        4.4.12: Der Lock wird erst auf ein wirklich fahrendes Auto gesetzt.
        Garage-/Stand-/Menü-Samples vor dem Losfahren werden verworfen, damit nicht versehentlich
        ein falsches Fahrzeug oder KI/Replay-Slot als Sessionbasis dient.
        """
        if not self.recording:
            return True
        sig = self.sample_vehicle_signature(s)
        if sig is None:
            self.rejected_sample_count += 1
            return False
        # Vor dem ersten echten Fahr-Sample noch nicht locken.
        if self.recording_signature is None and self.is_prelock_non_driving_sample(s):
            self.rejected_sample_count += 1
            if self.rejected_sample_count in (1, 10, 50) or self.rejected_sample_count % 250 == 0:
                self.log.append(f"Warte auf erstes Fahrsample für Recording-Lock ({self.rejected_sample_count} Stand-/Pit-Samples verworfen).")
            return False
        if self.recording_signature is None:
            self.recording_signature = sig
            self.log.append(f"Recording-Fahrzeug gelockt: {self.sample_vehicle_label(sig)}")
            return True
        if sig != self.recording_signature:
            # 0.5.9.24: Strecken-/Fahrzeugwechsel während der Aufnahme. Statt die Samples
            # nur endlos zu verwerfen: nach einer stabilen Serie desselben NEUEN Signaturs
            # (Debounce gegen einzelne verrauschte/kurz falsche Frames) die laufende Session
            # automatisch stoppen (Report/CSV/Referenz werden dabei wie gewohnt gespeichert)
            # und sofort neu starten, damit sich der neue Kontext frisch einlockt.
            if self.auto_switch_recording_enabled and not self.is_prelock_non_driving_sample(s):
                if self.pending_switch_signature == sig:
                    self.pending_switch_count += 1
                else:
                    self.pending_switch_signature = sig
                    self.pending_switch_count = 1
                if self.pending_switch_count >= AUTO_SWITCH_DEBOUNCE_SAMPLES:
                    old_label = self.sample_vehicle_label(self.recording_signature)
                    new_label = self.sample_vehicle_label(sig)
                    self.pending_switch_signature = None
                    self.pending_switch_count = 0
                    self.log.append(
                        f"Automatischer Wechsel erkannt: {new_label} statt {old_label} – "
                        "aktuelle Session wird gespeichert, neue Aufnahme startet automatisch."
                    )
                    self.stop_recording()
                    self.start_recording()
                    return False  # dieses Sample gehört zur alten Session, bereits geschlossen
            self.rejected_sample_count += 1
            if self.rejected_sample_count in (1, 5, 20) or self.rejected_sample_count % 100 == 0:
                self.log.append(
                    "Sample verworfen wegen Fahrzeug-/Klassenwechsel: "
                    f"{self.sample_vehicle_label(sig)} statt {self.sample_vehicle_label(self.recording_signature)} "
                    f"({self.rejected_sample_count} verworfen)"
                )
            return False
        # Kontinuierlich passendes Signal: Wechsel-Verdacht zurücksetzen.
        self.pending_switch_signature = None
        self.pending_switch_count = 0
        # Harte Stand-/Pit-Samples nach dem Lock dürfen nicht in Auswertungen/CSV dominieren.
        # Langsame Kurven werden NICHT verworfen, nur echte Pit/Garage/0-RPM/0-Speed-Zustände.
        if self.is_hard_garage_sample(s):
            self.rejected_sample_count += 1
            return False
        return True

    def update_live_smooth_lap_clock(self, s: Sample):
        """0.5.9.26: main.mTimeIntoLap (current_lap_time) kommt aus dem LMU-Scoring-
        Block, der spuerbar seltener aktualisiert als die Telemetrie -> im
        Rundenzeiten-Overlay "AKTUELL" blieb der Wert zwischendurch kurz stehen statt
        smooth mitzulaufen ("nicht 1:1 real-time"), obwohl wir selbst mit vollen 10 Hz
        pollen. Fix: eigene Echtzeit-Uhr per time.monotonic() zwischen den Sim-Updates,
        die sich bei jedem ECHTEN neuen Sim-Wert (oder Rundenwechsel/Reset/Pause)
        selbst resynchronisiert -> bleibt exakt am Sim-Stand, laeuft dazwischen aber
        sichtbar fluessig. Rein additiv, current_lap_time selbst bleibt unveraendert
        als Fallback vorhanden.
        """
        try:
            raw = float(getattr(s, "current_lap_time", 0.0) or 0.0)
            lap = int(getattr(s, "lap_number", 0) or 0)
        except Exception:
            self.live_smooth_lap_time = None
            return
        now = time.monotonic()
        anchor_raw = self._live_clock_anchor_raw
        anchor_ts = self._live_clock_anchor_ts
        predicted = (anchor_raw + (now - anchor_ts)) if anchor_raw is not None and anchor_ts is not None else None
        resync = (
            raw <= 0.0
            or lap != self._live_clock_lap
            or predicted is None
            or abs(raw - predicted) > 0.35  # Sprung -> Boxenstopp/Reset/neuer Sim-Wert weicht ab
        )
        if resync:
            self._live_clock_anchor_raw = raw
            self._live_clock_anchor_ts = now
            self._live_clock_lap = lap
            self.live_smooth_lap_time = raw
        else:
            self.live_smooth_lap_time = predicted

    def live_tick(self):
        """Live-Abfrage für Overlay, unabhängig vom Recording.
        Liest LMU_Data, schreibt aber keine Export-/Recording-Samples.
        Dadurch funktionieren Speed/Gang/Live-Delta auch ohne Recording.
        """
        try:
            s = self.reader.read_sample()
        except Exception:
            return
        self.last_live_sample = s
        self.update_live_smooth_lap_clock(s)  # 0.5.9.26
        self.write_live_log_row(s)  # 0.5.9.26
        self.maybe_autoshow_tire_overlay(s)
        self.update_live_lap_buffer(s)
        self.compute_live_reference_delta()
        # 0.5.9.15/17: CPU/GPU-Entlastung. Bis zu 13 Overlay-Fenster sind einzeln
        # WA_TranslucentBackground + WindowStaysOnTopHint -> jedes .update() hier
        # zwingt Windows/DWM, alle sichtbaren davon neu zu kompositieren. Waehrend
        # aktiv gefahren wird bleibt das bei vollen 10 Hz (kein Verhaltensunterschied
        # im Cockpit/auf der Strecke). Steht das Auto (Menue/Stand/Box, auch mit
        # laufendem Motor) aendern sich die angezeigten Werte kaum -> dort reicht
        # 2 Hz, das reduziert die DWM-Kompositierlast dort um 80% und entlastet
        # spuerbar auch LMUs eigenes Menue. Rein additiv: refresh_overlay()/
        # paintEvent-Logik unveraendert.
        self._overlay_tick_n = getattr(self, "_overlay_tick_n", 0) + 1
        try:
            # 0.5.9.17: eigene, lockere Erkennung nur fuers Overlay-Throttling statt
            # is_hard_garage_sample (die ist fuer die Rundenanalyse gedacht und verlangt
            # zusaetzlich RPM<500 -> in Box/Garage mit laufendem Motor (Standgas oft
            # 800-1200 RPM) griff die Drosselung deshalb NICHT, PitBoss blieb dort bei
            # vollen 10 Hz. Hier zaehlt nur: bewegt sich das Auto ueberhaupt.
            _driving = not (bool(getattr(s, "in_pits", False))
                             or float(getattr(s, "speed_kmh", 0.0) or 0.0) < 2.0)
        except Exception:
            _driving = True
        _do_refresh = _driving
        if not _driving and self._overlay_tick_n % 5 == 0:
            # 0.5.9.18: Dirty-Check. Bisher wurde im Stand/Box trotz Drosselung noch
            # JEDE 5. Tick (2 Hz) blind neu gezeichnet, auch wenn sich an der Telemetrie
            # ueberhaupt nichts geaendert hat (Marcel: "durchgehend etwas ruckelig, kein
            # klares Muster"). Fingerprint = alle Sample-Felder AUSSER timestamp (der
            # aendert sich immer und wuerde die Erkennung sonst nutzlos machen). Nur bei
            # tatsaechlicher Aenderung neu zeichnen. Zwangs-Refresh alle 5s als Netz fuer
            # Anzeigen, die NICHT direkt am Sample haengen (Wetter-Trend-Modell, REST-
            # Verschleiss/Setup alle 12s im Hintergrund-Thread, Schadenmodell) -> die
            # koennen sich aendern, ohne dass sich das Sample selbst aendert.
            try:
                fp = _dc_astuple(s)[1:] if s is not None else None
            except Exception:
                fp = None
            self._idle_refresh_n = getattr(self, "_idle_refresh_n", 0) + 1
            changed = fp != getattr(self, "_last_overlay_fp", "unset")
            forced = (self._idle_refresh_n % 10 == 0)  # 10 x 500ms = alle 5s
            if changed or forced or fp is None:
                self._last_overlay_fp = fp
                _do_refresh = True
        if _do_refresh:
            self.refresh_overlay()
        self.live_coach.maybe_speak_on_straight(s)
        self.brake_coach.update(s)
        self.update_sector_times(s)  # 0.4.9.0
        self.maybe_autoshow_pit_overlay(s)  # 0.4.9.1
        self.maybe_autoshow_flag_overlay(s)  # 0.5.5.0
        self._auto_reference_from_live(s)  # 0.5.7.0: Referenz auf aktuelle Strecke
        self.brake_model.update(s)  # 0.4.9.2
        self.weather_forecast.update(s)  # 0.4.9.4
        self.damage_model.update(s)  # 0.4.9.4
        try:
            self.rest.session_type = int(getattr(s, "session_type", 0) or 0)  # 0.4.9.5
        except Exception:
            pass
        self.update_brake_status()  # 0.4.9.4

    def update_live_lap_buffer(self, s: Sample):
        if self.is_non_driving_sample(s) or s.lap_dist_m < 0 or s.speed_kmh < 1:
            return
        reset = False
        if self.live_lap_number is None or self.live_lap_number != s.lap_number:
            reset = True
        elif self.live_lap_samples and s.lap_dist_m < self.live_lap_samples[-1].lap_dist_m - 500:
            reset = True
        if reset:
            if self.live_lap_samples:
                completed = list(self.live_lap_samples)
                self.consider_live_completed_lap_as_reference(completed, self.live_lap_number)
                self.maybe_export_live_bestlap(completed, self.live_lap_number)
                self.live_coach.on_lap_completed(completed, self.live_lap_number,
                                                 self.live_delta_s, self.live_coach_line)
            self.live_lap_number = s.lap_number
            self.live_lap_samples = []
            self.live_delta_s = None
            self.live_coach_line = "Live sammelt Daten"
        self.live_lap_samples.append(s)
        if len(self.live_lap_samples) > 2000:  # 0.4.8.5: reicht auch fuer lange Runden (>90s)
            self.live_lap_samples = self.live_lap_samples[-2000:]

    def consider_live_completed_lap_as_reference(self, rows: List[Sample], lap_number: Optional[int]):
        """Während Recording/Live: abgeschlossene saubere Runde als temporäre Live-Referenz nutzen.
        Dadurch zeigt das Minimal-Overlay Delta/Coach schon während der nächsten Runde, ohne Stop.
        """
        if not rows or lap_number is None or len(rows) < 250:
            return
        try:
            summaries = self.build_lap_summaries_from_rows(rows)
            lap = next((l for l in summaries if l.lap_number == lap_number), None)
            if not lap or not lap.is_clean:
                return
            if lap.valid_samples < 350 or lap.coverage_m < 2000 or lap.avg_speed < 120:
                return
            segs = self.build_segment_summaries_from_rows(rows, lap_number)
            if len(segs) < 35:
                return
            lap_time = sum(x.seg_time_s for x in segs.values())
            if not math.isfinite(lap_time) or lap_time <= 20:
                return
            if self.live_best_reference_time_s is None or lap_time < self.live_best_reference_time_s - 0.001:
                self.live_best_reference_segments = segs
                self.live_best_reference_lap = lap_number
                self.live_best_reference_time_s = lap_time
                self.live_coach_line = f"Live-Ref Lap {lap_number}"
                self.brake_coach.set_reference_from_rows(rows)
        except Exception as e:
            try:
                self.log.append(f"Live-Referenz übersprungen: {e}")
            except Exception:
                pass

    def live_reference_segments(self) -> dict:
        if self.external_reference is not None and self.use_external_reference:
            return self.external_reference_segments()
        if self.reference_lap:
            return self.build_segment_summaries_for_lap(self.reference_lap.lap_number)
        if getattr(self, "live_best_reference_segments", None):
            return self.live_best_reference_segments
        return {}

    def compute_live_reference_delta(self):
        if not self.live_lap_samples:
            self.live_delta_s = None
            self.live_coach_line = "Live sammelt Daten"
            return
        ref_segments = self.live_reference_segments()
        if not ref_segments:
            self.live_delta_s = None
            self.live_coach_line = "Referenz importieren/Analyse"
            return
        cmp_segments = self.build_segment_summaries_from_rows(self.live_lap_samples, self.live_lap_number or -1)
        if not cmp_segments:
            self.live_delta_s = None
            self.live_coach_line = "Live sammelt Daten"
            return
        current_m = self.live_lap_samples[-1].lap_dist_m
        current_key = int(current_m // 50) * 50
        keys = sorted(k for k in (set(ref_segments) & set(cmp_segments)) if k < current_key)
        if len(keys) < 3:
            self.live_delta_s = None
            self.live_coach_line = "Live sammelt Daten"
            return
        deltas = []
        for key in keys:
            d = cmp_segments[key].seg_time_s - ref_segments[key].seg_time_s
            if abs(d) < 2.0:  # Live-Schutz gegen stehendes Auto/Reset-Ausreißer
                deltas.append((key, d, cmp_segments[key], ref_segments[key]))
        if not deltas:
            self.live_delta_s = None
            self.live_coach_line = "Live sammelt Daten"
            return
        self.live_delta_s = sum(d for _, d, _, _ in deltas)
        losses = [(k, d, c, r) for k, d, c, r in deltas if d > 0.08]
        if losses:
            k, d, c, r = max(losses, key=lambda x: x[1])
            speed_diff = c.avg_speed - r.avg_speed
            if c.avg_throttle < r.avg_throttle - 0.12:
                topic = "Gas früher"
            elif speed_diff < -5:
                topic = "mehr Mindesttempo"
            elif c.max_brake > r.max_brake + 0.08:
                topic = "Bremse lösen"
            else:
                topic = "Linie ruhiger"
            self.live_coach_line = f"{k}-{k+50} m {d:+.2f}s · {topic}"
        else:
            self.live_coach_line = "aktuell ok"

    def capture_tick(self):
        self.snapshot(silent=True)

    def snapshot(self, silent: bool = False):
        try:
            s = self.reader.read_sample()
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "LMU Shared Memory", f"Konnte LMU_Data nicht lesen:\n{e}\n\nLäuft LMU und bist du im Auto?")
            self.status.setText("LMU_Data nicht lesbar.")
            return
        if not self.accept_recording_sample(s):
            if not silent:
                self.log.append("Snapshot verworfen: anderes Fahrzeug/andere Klasse als Recording-Lock.")
            self.status.setText(f"Sample verworfen – Recording gelockt auf {self.sample_vehicle_label(self.recording_signature)}")
            return
        self.samples.append(s)
        self.add_sample_to_table(s)
        if len(self.samples) % 5 == 0 or not silent:
            self.trackmap.set_samples(self.samples)
        self.status.setText(f"Letzter Snapshot: {s.track} | {s.vehicle_name} | {s.speed_kmh:.1f} km/h | Gear {s.gear} | Fuel {s.fuel_l:.2f} L")
        self.refresh_dashboard()
        if not silent:
            self.log.append(self.sample_summary(s))
            self.compare_refs(s)

    def start_recording(self):
        if self.recording:
            self.log.append("Recording läuft bereits – Start ignoriert.")
            return
        self.samples.clear(); self.lap_summaries.clear(); self.reference_lap = None; self.compare_lap = None; self.segment_deltas = []; self.manual_reference_lap = None; self.manual_compare_lap = None; self.auto_bestlap_export_path = None; self.auto_bestlap_lap_number = None; self.auto_bestlap_time_s = None; self.live_best_reference_segments = {}; self.live_best_reference_lap = None; self.live_best_reference_time_s = None; self.recording_signature = None; self.rejected_sample_count = 0; self.pending_switch_signature = None; self.pending_switch_count = 0; self.live_summary.setRowCount(0); self.segment_table.setRowCount(0); self.zone_table.setRowCount(0); self.laps_table.setRowCount(0); self.lap_overview_table.setRowCount(0); self.compare_table.setRowCount(0); self.coach_text.clear(); self.limit_coach_text.clear() if hasattr(self, "limit_coach_text") else None;
        self.input_table.setRowCount(0) if hasattr(self, "input_table") else None; self.input_coach_text.clear() if hasattr(self, "input_coach_text") else None; self.trackmap.set_samples([]);
        self.heatmap.set_samples([]) if hasattr(self, 'heatmap') else None; self.refresh_lap_combos()
        self.recording = True; self.timer.start()
        self.snapshot(silent=True)  # 0.4.8.1: Snapshot automatisch bei Start
        self.btn_record.setText("Recording stoppen")
        self.log.append("🔴 Recording gestartet: Auto-Report/CSV werden beim Stop automatisch gespeichert.")
        self.status.setText("🔴 RECORDING AKTIV – F8 stoppt und speichert Report/CSV automatisch.")
        self.refresh_dashboard()

    def stop_recording(self):
        if not self.recording:
            self.log.append("Recording ist nicht aktiv – Stop ignoriert.")
            return
        self.recording = False; self.timer.stop()
        self.btn_record.setText("Recording starten")
        self.log.append(f"Recording gestoppt. Samples: {len(self.samples)} | verworfen wegen Fahrzeugwechsel/ungültig: {self.rejected_sample_count}")
        self.update_laps()
        self.auto_export_bestlap_reference()
        ref_samples = self.samples_for_reference_lap()
        self.trackmap.set_samples(ref_samples if ref_samples else self.samples)
        self.update_segments()
        self.update_lap_compare()
        self.update_heatmap()
        self.update_coach_text()
        self.update_input_coach()
        self.autosave_exports()
        self.status.setText("Recording gestoppt. Auto-Report/CSV gespeichert. Referenzen liegen separat in exports/references.")
        self.refresh_dashboard()

    def clear(self):
        self.samples.clear(); self.lap_summaries.clear(); self.reference_lap = None; self.compare_lap = None; self.segment_deltas = []; self.manual_reference_lap = None; self.manual_compare_lap = None; self.auto_bestlap_export_path = None; self.auto_bestlap_lap_number = None; self.auto_bestlap_time_s = None; self.live_best_reference_segments = {}; self.live_best_reference_lap = None; self.live_best_reference_time_s = None; self.live_summary.setRowCount(0); self.segment_table.setRowCount(0); self.zone_table.setRowCount(0); self.laps_table.setRowCount(0); self.lap_overview_table.setRowCount(0); self.compare_table.setRowCount(0); self.coach_text.clear(); self.limit_coach_text.clear() if hasattr(self, "limit_coach_text") else None;
        self.input_table.setRowCount(0) if hasattr(self, "input_table") else None; self.input_coach_text.clear() if hasattr(self, "input_coach_text") else None; self.trackmap.set_samples([]);
        self.heatmap.set_samples([]) if hasattr(self, 'heatmap') else None; self.refresh_lap_combos(); self.log.clear()
        self.status.setText("Gelöscht.")
        self.refresh_dashboard()

    def sample_summary(self, s: Sample) -> str:
        return (
            f"Snapshot: Track={s.track} | Player={s.player_name} | idx={s.player_idx}/{s.active_vehicles} | "
            f"Car={s.vehicle_name} | speed={s.speed_kmh:.2f} km/h | gear={s.gear} | rpm={s.rpm:.0f} | "
            f"fuel={s.fuel_l:.3f} L | thr={s.throttle:.3f} | brake={s.brake:.3f} | steer={s.steering:.5f} | "
            f"lap={s.lap_number} dist={s.lap_dist_m:.1f} m | pos=({s.pos_x:.1f},{s.pos_z:.1f})"
        )

    def compare_refs(self, s: Sample):
        refs: List[Tuple[str, Optional[float], float, str]] = [
            ("Speed", self.parse_ref(self.ref_speed), s.speed_kmh, "km/h"),
            ("Gear", self.parse_ref(self.ref_gear), float(s.gear), ""),
            ("Fuel", self.parse_ref(self.ref_fuel), s.fuel_l, "L"),
            ("RPM", self.parse_ref(self.ref_rpm), s.rpm, ""),
            ("Throttle", self.parse_ref(self.ref_throttle), s.throttle, ""),
            ("Brake", self.parse_ref(self.ref_brake), s.brake, ""),
            ("Steering", self.parse_ref(self.ref_steer), s.steering, ""),
            ("Track m", self.parse_ref(self.ref_trackm), s.lap_dist_m, "m"),
        ]
        parts = []
        for name, ref, val, unit in refs:
            if ref is not None:
                parts.append(f"{name}: LMU {val:.3f}{unit} / SimHub {ref:.3f}{unit} / Diff {val-ref:+.3f}")
        if parts:
            self.log.append("Vergleich: " + " | ".join(parts))

    def tire_rows_for_sample(self, s: Sample):
        return [
            ("VL", s.tire_fl_pressure_kpa, s.tire_fl_temp_l_c, s.tire_fl_temp_c_c, s.tire_fl_temp_r_c, s.tire_fl_carcass_c, s.tire_fl_wear_pct, s.tire_fl_flat, s.tire_fl_grip_fract),
            ("VR", s.tire_fr_pressure_kpa, s.tire_fr_temp_l_c, s.tire_fr_temp_c_c, s.tire_fr_temp_r_c, s.tire_fr_carcass_c, s.tire_fr_wear_pct, s.tire_fr_flat, s.tire_fr_grip_fract),
            ("HL", s.tire_rl_pressure_kpa, s.tire_rl_temp_l_c, s.tire_rl_temp_c_c, s.tire_rl_temp_r_c, s.tire_rl_carcass_c, s.tire_rl_wear_pct, s.tire_rl_flat, s.tire_rl_grip_fract),
            ("HR", s.tire_rr_pressure_kpa, s.tire_rr_temp_l_c, s.tire_rr_temp_c_c, s.tire_rr_temp_r_c, s.tire_rr_carcass_c, s.tire_rr_wear_pct, s.tire_rr_flat, s.tire_rr_grip_fract),
        ]

    def flatspot_status(self, flat: bool, grip_fract: float, brake: float = 0.0, speed_kmh: float = 0.0, sample: Optional[Sample] = None) -> str:
        # Echte LMU-mFlat-Meldung hat Vorrang, aber nur bei plausibler Fahrt.
        if flat and speed_kmh > 10:
            return "REIFEN PLATT"
        gf = max(0.0, float(grip_fract or 0.0))
        if brake <= 0.20 or speed_kmh <= 25:
            return "OK"
        vclass = infer_vehicle_class(getattr(sample, "vehicle_class", "") if sample else "", getattr(sample, "vehicle_name", "") if sample else "", getattr(sample, "vehicle_model", "") if sample else "")
        is_abs_car = vclass in ("GT3",)
        # GT3 wird als ABS-Fahrzeug behandelt. Hypercar/LMP/GTE werden als Non-ABS gewertet: Sliding unter Bremse = Lockup-Risiko.
        if is_abs_car:
            if gf >= 0.45:
                return "ABS!"
            if gf >= 0.22:
                return "ABS"
            return "OK"
        if gf >= 0.35:
            return "LOCK!"
        if gf >= 0.18:
            return "LOCK"
        if gf >= 0.08:
            return "leicht"
        return "OK"

    def update_tire_table(self, s: Sample):
        if not hasattr(self, "tire_table"):
            return
        rows = self.tire_rows_for_sample(s)
        self.tire_table.setRowCount(len(rows))
        notes = []
        for r, (name, pressure, tl, tc, tr, carcass, wear, flat, grip_fract) in enumerate(rows):
            avg_temp = (tl + tc + tr) / 3.0 if (tl or tc or tr) else 0.0
            spread = tr - tl
            flat_status = self.flatspot_status(flat, grip_fract, s.brake, s.speed_kmh, s)
            hint = self.tire_setup_hint(tl, tc, tr, pressure, wear)
            if hint and hint != "ok":
                notes.append(f"{name}: {hint}")
            vals = [
                name,
                f"{pressure:.1f}",
                f"{pressure/100.0:.2f}" if pressure > 0 else "-",
                f"{tl:.1f} °C",
                f"{tc:.1f} °C",
                f"{tr:.1f} °C",
                f"{carcass:.1f} °C",
                f"{wear:.1f}",
                flat_status,
                hint,
            ]
            for c, v in enumerate(vals):
                self.tire_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.tire_table.resizeColumnsToContents()
        if hasattr(self, "tire_note"):
            note_txt = " | ".join(notes[:4]) if notes else "Reifen im aktuellen Snapshot unauffällig. Für echte Analyse 3–5 Runden Stintdaten sammeln."
            self.tire_note.setText(note_txt + " Flat/ABS-Anzeige: echter mFlat-Status hat Vorrang; bei GT3 wird Sliding unter Bremse als ABS-Stress gewertet, bei Hypercar/LMP/GTE als Lockup-Risiko.")

    def add_sample_to_table(self, s: Sample):
        # 4.0.3: Live-Tab zeigt nur eine kompakte Runden-/Statusübersicht, keine Sample-Flut.
        self.live_summary.setRowCount(1)
        vals = [
            s.lap_number, f"{s.lap_dist_m:.1f} m", f"{s.speed_kmh:.1f} km/h", s.gear,
            f"{s.fuel_l:.2f} L", fmt_lap_time(s.last_lap_time), fmt_lap_time(s.best_lap_time),
            "invalid" if s.lap_invalidated else ("Pit" if s.in_pits else "ok")
        ]
        for c, v in enumerate(vals):
            self.live_summary.setItem(0, c, QTableWidgetItem(str(v)))
        if self.live_summary.columnWidth(0) < 60:
            self.live_summary.resizeColumnsToContents()
        self.update_tire_table(s)

    def samples_for_reference_lap(self) -> List[Sample]:
        if not self.reference_lap:
            return []
        return [s for s in self.samples if s.lap_number == self.reference_lap.lap_number and not self.is_non_driving_sample(s)]

    def is_hard_garage_sample(self, s: Sample) -> bool:
        return bool(s.in_pits) or (s.speed_kmh < 1.0 and s.rpm < 500 and s.gear == 0)

    def is_prelock_non_driving_sample(self, s: Sample) -> bool:
        # Für den Fahrzeug-Lock warten wir auf ein plausibles Fahrsample.
        # Dadurch lockt die Aufnahme nicht auf Stand-/Boxen-/Menü-Daten.
        return self.is_hard_garage_sample(s) or s.lap_dist_m < -20 or s.speed_kmh < 5.0

    def is_non_driving_sample(self, s: Sample) -> bool:
        # Engine/standstill/pit/garage samples should not influence lap analysis.
        return self.is_hard_garage_sample(s)

    def build_lap_summaries_from_rows(self, source_samples: List[Sample]) -> List[LapSummary]:
        by_lap = {}
        for s in source_samples:
            if s.lap_number <= 0:
                continue
            by_lap.setdefault(s.lap_number, []).append(s)
        summaries: List[LapSummary] = []
        for lap in sorted(by_lap):
            rows = by_lap[lap]
            valid = [r for r in rows if not self.is_non_driving_sample(r) and r.lap_dist_m >= 0]
            if valid:
                start_m = min(r.lap_dist_m for r in valid)
                end_m = max(r.lap_dist_m for r in valid)
                coverage = end_m - start_m
                speeds = [r.speed_kmh for r in valid]
                brakes = [r.brake for r in valid]
                thrs = [r.throttle for r in valid]
                fuel_start = max(r.fuel_l for r in valid)
                fuel_end = min(r.fuel_l for r in valid)
                fuel_used = max(0.0, fuel_start - fuel_end)
                official_lmu_time = self.lmu_official_lap_time_for_lap_from_rows(source_samples, lap)
                if official_lmu_time > 0:
                    duration = official_lmu_time
                else:
                    times = [r.current_lap_time for r in valid if r.current_lap_time >= 0]
                    duration = (max(times) - min(times)) if times else 0.0
                    # If the sim resets/duplicates time fields, fall back to timestamp span.
                    if duration < 1.0 and len(valid) > 10:
                        try:
                            dt0 = datetime.fromisoformat(valid[0].timestamp)
                            dt1 = datetime.fromisoformat(valid[-1].timestamp)
                            duration = max(0.0, (dt1 - dt0).total_seconds())
                        except Exception:
                            pass
                min_speed = min(speeds); max_speed = max(speeds); avg_speed = sum(speeds)/len(speeds)
                max_brake = max(brakes); avg_thr = sum(thrs)/len(thrs)
            else:
                start_m = end_m = coverage = duration = min_speed = max_speed = avg_speed = max_brake = avg_thr = fuel_start = fuel_end = fuel_used = official_lmu_time = 0.0
            invalidated = any(r.lap_invalidated for r in rows)
            in_pits = any(r.in_pits for r in rows)
            has_standstill = any(self.is_non_driving_sample(r) for r in rows)
            # Robust full-lap check, now dynamic for short and long circuits.
            # 3.3 used Monza-style hard limits (~5400 m), which was too strict for Silverstone National.
            session_track_m = max([r.lap_dist_m for rr in by_lap.values() for r in rr if r.lap_dist_m >= 0] or [0.0])
            if session_track_m <= 0:
                session_track_m = max(end_m, 1.0)
            start_tolerance = max(80.0, session_track_m * 0.04)
            finish_tolerance = max(90.0, session_track_m * 0.05)
            coverage_needed = max(session_track_m * 0.88, session_track_m - max(180.0, session_track_m * 0.07))
            # 0.4.5.1: Long tracks with low/variable Shared-Memory polling must not be
            # rejected just because the timer delivered fewer samples. On Sarthe, a
            # real 3:3x lap can have only ~300 usable rows.
            min_samples_needed = max(80, int(session_track_m / 50.0))
            if official_lmu_time > 0:
                min_samples_needed = max(60, int(session_track_m / 65.0))
            near_start = start_m <= start_tolerance
            near_finish = end_m >= max(0.0, session_track_m - finish_tolerance)
            is_complete = near_start and near_finish and coverage >= coverage_needed and len(valid) >= min_samples_needed
            reasons = []
            if not valid:
                reasons.append("keine Fahrdaten")
            if not is_complete:
                reasons.append("nicht komplett/Outlap")
            if invalidated:
                reasons.append("invalidiert")
            if in_pits:
                reasons.append("Pit")
            if has_standstill and not is_complete:
                reasons.append("Standphase")
            is_clean = bool(valid) and is_complete and not invalidated and not in_pits
            if is_clean:
                reasons.append("gültig")
            summaries.append(LapSummary(
                lap_number=lap, samples=len(rows), valid_samples=len(valid), start_m=start_m, end_m=end_m,
                coverage_m=coverage, duration_s=duration, min_speed=min_speed, max_speed=max_speed, avg_speed=avg_speed,
                max_brake=max_brake, avg_throttle=avg_thr, fuel_start_l=fuel_start, fuel_end_l=fuel_end,
                fuel_used_l=fuel_used, invalidated=invalidated, in_pits=in_pits, has_standstill=has_standstill,
                is_complete=is_complete, is_clean=is_clean, reason=", ".join(reasons)
            ))
        return summaries

    def build_lap_summaries(self) -> List[LapSummary]:
        return self.build_lap_summaries_from_rows(self.samples)

    def lap_samples_valid(self, lap_number: int) -> List[Sample]:
        return [s for s in self.samples if s.lap_number == lap_number and not self.is_non_driving_sample(s) and s.lap_dist_m >= 0]

    def lap_sector_overview(self, lap: LapSummary) -> Tuple[float, float, float, float, float, float, float]:
        """Stable lap overview sectors for the UI.

        LMU/rF2 exposes official timing internally, but not reliably in the telemetry rows we use here.
        4.4.5 therefore shows stable *interne Streckendrittel*: we sum our existing speed-based
        50-m segment times by lap distance. This avoids broken current_lap_time snapshots and keeps
        S1/S2/S3 consistent with the reference/coach calculations.
        """
        duration = self.lap_time_for_report(lap)
        if duration <= 0:
            duration = self.estimated_lap_time_from_speed(lap.lap_number)
        if duration >= 999998.0 or duration <= 0:
            duration = lap.duration_s
        segs = self.build_segment_summaries_for_lap(lap.lap_number)
        if not segs or duration <= 0:
            return 0.0, 0.0, 0.0, duration, lap.min_speed, lap.max_speed, lap.avg_speed
        track_len = max([l.end_m for l in self.lap_summaries if l.is_clean and l.end_m > 0] or [lap.end_m, 1.0])
        b1, b2 = track_len / 3.0, 2.0 * track_len / 3.0
        s1 = s2 = s3 = 0.0
        for key, seg in segs.items():
            mid = (seg.start_m + seg.end_m) / 2.0
            if mid < b1:
                s1 += seg.seg_time_s
            elif mid < b2:
                s2 += seg.seg_time_s
            else:
                s3 += seg.seg_time_s
        total = s1 + s2 + s3
        if total > 0 and abs(total - duration) > max(1.5, duration * 0.05):
            scale = duration / total
            s1 *= scale; s2 *= scale; s3 *= scale
        if min(s1, s2, s3) <= 0.1:
            s1 = duration / 3.0; s2 = duration / 3.0; s3 = duration / 3.0
        return s1, s2, s3, duration, lap.min_speed, lap.max_speed, lap.avg_speed

    def update_lap_overview_table(self):
        if not hasattr(self, "lap_overview_table"):
            return
        self.lap_overview_table.setRowCount(0)
        rows = []
        for lap in self.lap_summaries:
            s1, s2, s3, dur, mn, mx, avg = self.lap_sector_overview(lap)
            rows.append((lap, s1, s2, s3, dur, mn, mx, avg))
        if not rows:
            return
        clean_rows = [r for r in rows if r[0].is_clean]
        best_low = {}
        worst_low = {}
        best_high = {}
        worst_high = {}
        # Niedriger ist besser: Sektoren und Rundenzeit.
        for idx in [1,2,3,4]:
            vals = [r[idx] for r in clean_rows if r[idx] > 0]
            if vals:
                best_low[idx] = min(vals); worst_low[idx] = max(vals)
        # Höher ist besser: Min/Max/Durchschnitt Speed.
        for idx in [5,6,7]:
            vals = [r[idx] for r in clean_rows if r[idx] > 0]
            if vals:
                best_high[idx] = max(vals); worst_high[idx] = min(vals)
        for lap, s1, s2, s3, dur, mn, mx, avg in rows:
            row = self.lap_overview_table.rowCount(); self.lap_overview_table.insertRow(row)
            vals = [f"Lap #{lap.lap_number}", fmt_lap_time(s1), fmt_lap_time(s2), fmt_lap_time(s3), fmt_lap_time(dur), f"{mn:.2f}", f"{mx:.2f}", f"{avg:.2f}"]
            raw = [None, s1, s2, s3, dur, mn, mx, avg]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                if not lap.is_clean:
                    item.setBackground(QColor(120, 80, 80, 120))
                elif self.reference_lap and lap.lap_number == self.reference_lap.lap_number and c == 0:
                    item.setBackground(QColor(80, 120, 80, 160))
                    item.setText(f"Lap #{lap.lap_number} REF")
                elif c in [1,2,3,4]:
                    if c in best_low and abs(raw[c] - best_low[c]) < 0.001:
                        item.setBackground(QColor(85, 150, 95, 170))
                    elif c in worst_low and abs(raw[c] - worst_low[c]) < 0.001:
                        item.setBackground(QColor(160, 85, 85, 160))
                elif c in [5,6,7]:
                    if c in best_high and abs(raw[c] - best_high[c]) < 0.001:
                        item.setBackground(QColor(85, 150, 95, 170))
                    elif c in worst_high and abs(raw[c] - worst_high[c]) < 0.001:
                        item.setBackground(QColor(160, 85, 85, 160))
                self.lap_overview_table.setItem(row, c, item)
        self.lap_overview_table.resizeColumnsToContents()

    def update_laps(self):
        self.lap_summaries = self.build_lap_summaries()
        clean = [l for l in self.lap_summaries if l.is_clean]
        # 3.7: Auto reference can be overridden manually.
        manual_ref = self.lap_by_number(self.manual_reference_lap)
        self.reference_lap = manual_ref or (min(clean, key=lambda l: self.estimated_lap_time_from_speed(l.lap_number)) if clean else None)
        self.update_lap_overview_table()
        self.laps_table.setRowCount(0)
        for lap in self.lap_summaries:
            row = self.laps_table.rowCount(); self.laps_table.insertRow(row)
            status = "REFERENZ" if self.reference_lap and lap.lap_number == self.reference_lap.lap_number else ("gültig" if lap.is_clean else "ausgeschlossen")
            vals = [
                lap.lap_number, status, lap.reason, lap.samples, f"{lap.coverage_m:.1f}", fmt_lap_time(self.lap_time_for_report(lap)),
                f"{lap.max_speed:.1f}", f"{lap.avg_speed:.1f}", f"{lap.max_brake:.3f}",
                f"{lap.fuel_used_l:.3f}", f"{lap.start_m:.1f}", f"{lap.end_m:.1f}",
                f"stand={int(lap.has_standstill)} pit={int(lap.in_pits)}"
            ]
            for c, v in enumerate(vals):
                self.laps_table.setItem(row, c, QTableWidgetItem(str(v)))
        self.laps_table.resizeColumnsToContents()
        self.refresh_lap_combos()
        if self.reference_lap:
            mode = "manuell" if self.manual_reference_lap == self.reference_lap.lap_number else "Auto"
            self.log.append(f"Referenzrunde erkannt ({mode}): Lap {self.reference_lap.lap_number} | Avg {self.reference_lap.avg_speed:.1f} km/h | Fuel {self.reference_lap.fuel_used_l:.2f} L")
        else:
            self.log.append("Keine komplette saubere Referenzrunde erkannt. Bitte mindestens eine volle fliegende Runde aufzeichnen.")

    def update_segments(self):
        self.segment_table.setRowCount(0)
        if not self.samples:
            return
        source = self.samples_for_reference_lap() or [s for s in self.samples if not self.is_non_driving_sample(s)]
        buckets = {}
        for s in source:
            if s.lap_dist_m < 0:
                continue
            key = int(s.lap_dist_m // 50) * 50
            buckets.setdefault(key, []).append(s)
        for idx, key in enumerate(sorted(buckets)):
            rows = buckets[key]
            if len(rows) < 2:
                continue
            speeds = [r.speed_kmh for r in rows]
            brakes = [r.brake for r in rows]
            thrs = [r.throttle for r in rows]
            gears = [r.gear for r in rows if r.gear > 0]
            gear_common = max(set(gears), key=gears.count) if gears else "-"
            max_brake = max(brakes)
            min_speed = min(speeds)
            avg_speed = sum(speeds) / len(speeds)
            avg_thr = sum(thrs) / len(thrs)
            if max_brake > 0.25:
                hint = "Bremszone"
            elif avg_thr > 0.85:
                hint = "Vollgas"
            elif min_speed < 80:
                hint = "Langsame Passage"
            else:
                hint = "neutral"
            row = self.segment_table.rowCount(); self.segment_table.insertRow(row)
            vals = [row + 1, f"{key}-{key+50}", len(rows), f"{avg_speed:.1f}", f"{min_speed:.1f}", f"{max_brake:.3f}", f"{avg_thr:.3f}", gear_common, hint]
            for c, v in enumerate(vals):
                self.segment_table.setItem(row, c, QTableWidgetItem(str(v)))
        self.segment_table.resizeColumnsToContents()

    def samples_for_lap(self, lap_number: int) -> List[Sample]:
        rows = [s for s in self.samples if s.lap_number == lap_number and not self.is_non_driving_sample(s) and s.lap_dist_m >= 0 and s.speed_kmh > 1]
        rows.sort(key=lambda s: (s.lap_dist_m, s.timestamp))
        # Remove an occasional rollover sample at the end of the previous lap.
        while len(rows) > 2 and rows[0].lap_dist_m > 2000 and rows[1].lap_dist_m < 200:
            rows = rows[1:]
        return rows

    def build_segment_summaries_from_rows(self, rows: List[Sample], lap_number: int) -> dict:
        rows = [r for r in rows if not self.is_non_driving_sample(r) and r.lap_dist_m >= 0 and r.speed_kmh > 1]
        rows.sort(key=lambda s: (s.lap_dist_m, s.timestamp))
        if len(rows) < 5:
            return {}
        max_d = max(r.lap_dist_m for r in rows)
        out = {}
        # 3.5/4.1.1: Use speed-integrated segment time instead of LMU current_lap_time.
        # This also allows live segment deltas without pressing Recording.
        for key in range(0, int(max_d // 50) * 50 + 1, 50):
            start_m = float(key)
            seg_rows = [r for r in rows if start_m <= r.lap_dist_m < start_m + 50]
            if len(seg_rows) < 2:
                continue
            speeds = [r.speed_kmh for r in seg_rows if r.speed_kmh > 1]
            if not speeds:
                continue
            avg_speed = sum(speeds) / len(speeds)
            if avg_speed <= 1:
                continue
            segment_len_m = max(1.0, min(50.0, max_d - start_m))
            seg_time_s = segment_len_m / (avg_speed / 3.6)
            brakes = [r.brake for r in seg_rows]
            thrs = [r.throttle for r in seg_rows]
            gears = [r.gear for r in seg_rows if r.gear > 0]
            gear_common = str(max(set(gears), key=gears.count)) if gears else "-"
            out[key] = SegmentSummary(
                lap_number=lap_number,
                start_m=key,
                end_m=key + int(segment_len_m),
                samples=len(seg_rows),
                seg_time_s=seg_time_s,
                avg_speed=avg_speed,
                min_speed=min(speeds),
                max_speed=max(speeds),
                max_brake=max(brakes),
                avg_throttle=sum(thrs) / len(thrs),
                gear_common=gear_common,
            )
        return out

    def build_segment_summaries_for_lap(self, lap_number: int) -> dict:
        return self.build_segment_summaries_from_rows(self.samples_for_lap(lap_number), lap_number)

    def estimated_lap_time_from_speed(self, lap_number: int) -> float:
        segs = self.build_segment_summaries_for_lap(lap_number)
        if not segs:
            return 999999.0
        return sum(s.seg_time_s for s in segs.values())

    def is_plausible_compare_lap(self, lap: LapSummary, ref_segments: dict, use_external: bool = False) -> Tuple[bool, str]:
        """4.0.7: Safety filter so Auto compare never picks a partial/rolling-out/standstill lap.
        External reference comparisons are especially sensitive because a partial lap can share only the first
        few 50-m sectors and produce absurd deltas like +8 s in one zone.
        """
        if not lap or not lap.is_clean:
            return False, "Runde nicht sauber"
        cmp_segments = self.build_segment_summaries_for_lap(lap.lap_number)
        if not cmp_segments:
            return False, "keine Segmentdaten"
        if not ref_segments:
            return False, "keine Referenzsegmente"
        ref_keys = set(ref_segments.keys())
        cmp_keys = set(cmp_segments.keys())
        common = ref_keys & cmp_keys
        if not ref_keys or not common:
            return False, "keine Segment-Überlappung"
        overlap_ratio = len(common) / max(1, len(ref_keys))
        ref_max_key = max(ref_keys)
        cmp_max_key = max(cmp_keys)
        # Full-lap coverage check at segment level. This catches laps that look complete in scoring,
        # but only contain the first half of usable telemetry after the recording stopped or the car stood still.
        if overlap_ratio < 0.88 or cmp_max_key < ref_max_key * 0.88:
            return False, f"Segmentabdeckung zu klein ({overlap_ratio*100:.0f}%)"
        # Fuel/sample sanity. Normal GT3 Silverstone laps use around 1.3-1.5 L in our tests; do not hardcode that,
        # but reject obviously tiny fuel use when an external/reference comparison is active.
        if use_external and lap.fuel_used_l > 0 and lap.fuel_used_l < 0.75:
            return False, "Fuel Used zu klein / vermutlich Teilrunde"
        if lap.avg_speed < 120:
            return False, "Avg Speed zu niedrig / vermutlich Standphase"
        # Segment outlier check for automatic selection. A true 50-m sector delta above 2 s is almost always
        # stopped/slow car data, not a useful driving coach signal.
        outlier_count = 0
        for key in sorted(common):
            d = cmp_segments[key].seg_time_s - ref_segments[key].seg_time_s
            if d > 2.0:
                outlier_count += 1
        if outlier_count:
            return False, "unplausibler Sektor-Ausreißer"
        return True, "ok"

    def plausible_compare_laps(self, ref_segments: dict, use_external: bool = False) -> List[LapSummary]:
        out = []
        rejected = []
        for lap in [l for l in self.lap_summaries if l.is_clean]:
            if not use_external and self.reference_lap and lap.lap_number == self.reference_lap.lap_number:
                continue
            # 4.0.4.5.2: Wenn die externe Referenz gerade aus dieser Session automatisch exportiert wurde,
            # darf Auto-Vergleich nicht wieder exakt dieselbe Runde wählen. Sonst entsteht ein nutzloses +0.000 s.
            if use_external and self.auto_bestlap_lap_number and lap.lap_number == self.auto_bestlap_lap_number:
                rejected.append(f"Lap {lap.lap_number}: aktuelle Auto-Referenzrunde, nicht als Vergleich genutzt")
                continue
            ok, reason = self.is_plausible_compare_lap(lap, ref_segments, use_external=use_external)
            if ok:
                out.append(lap)
            else:
                rejected.append(f"Lap {lap.lap_number}: {reason}")
        if rejected:
            self.log.append("Auto-Vergleich Sicherheitsfilter: " + "; ".join(rejected[:4]) + (" ..." if len(rejected) > 4 else ""))
        return out

    def external_reference_segments(self) -> dict:
        if not self.external_reference:
            return {}
        out = {}
        for d in self.external_reference.get("segments", []):
            seg = self.dict_to_segment(d)
            out[seg.start_m] = seg
        return out

    def external_reference_samples(self) -> List[Sample]:
        if not self.external_reference:
            return []
        meta = self.external_reference.get("meta", {})
        rows = []
        for p in self.external_reference.get("path", []):
            rows.append(Sample(
                timestamp=meta.get("created_at", ""), game_version=0, track=meta.get("track", ""), player_name="Reference",
                active_vehicles=0, player_idx=-1, player_has_vehicle=False, telem_id=-1, scoring_id=-1,
                vehicle_name=meta.get("vehicle_name", ""), vehicle_model=meta.get("vehicle_model", ""), vehicle_class=meta.get("vehicle_class", ""),
                speed_kmh=fnum(p.get("speed_kmh")), gear=0, rpm=0.0, fuel_l=0.0, fuel_capacity_l=0.0,
                throttle=0.0, brake=0.0, steering=0.0, pos_x=fnum(p.get("pos_x")), pos_y=0.0, pos_z=fnum(p.get("pos_z")),
                lap_number=-1, completed_laps=0, lap_dist_m=fnum(p.get("lap_dist_m")), current_lap_time=0.0, last_lap_time=0.0,
                best_lap_time=0.0, lap_invalidated=False, in_pits=False, place=0
            ))
        return rows

    def build_lap_compare(self) -> List[SegmentDelta]:
        if not self.lap_summaries:
            self.update_laps()
        use_external = self.external_reference is not None and self.use_external_reference
        ref_segments = self.external_reference_segments() if use_external else {}
        if not use_external:
            if not self.reference_lap:
                self.compare_lap = None
                return []
            ref_segments = self.build_segment_summaries_for_lap(self.reference_lap.lap_number)
        clean = self.plausible_compare_laps(ref_segments, use_external=use_external)
        if not clean or not ref_segments:
            self.compare_lap = None
            self.log.append("Kein plausibler Vergleich möglich: Bitte eine vollständige fliegende Runde aufzeichnen oder manuell eine gültige Runde wählen.")
            return []
        manual_cmp = self.lap_by_number(self.manual_compare_lap)
        if manual_cmp and (use_external or (self.reference_lap and manual_cmp.lap_number != self.reference_lap.lap_number)):
            ok, reason = self.is_plausible_compare_lap(manual_cmp, ref_segments, use_external=use_external)
            if ok:
                self.compare_lap = manual_cmp
            else:
                self.compare_lap = min(clean, key=lambda l: self.estimated_lap_time_from_speed(l.lap_number))
                self.log.append(f"Manuelle Vergleichsrunde Lap {manual_cmp.lap_number} verworfen ({reason}); Auto nutzt Lap {self.compare_lap.lap_number}.")
        else:
            self.compare_lap = min(clean, key=lambda l: self.estimated_lap_time_from_speed(l.lap_number))
        cmp = self.build_segment_summaries_for_lap(self.compare_lap.lap_number)
        deltas: List[SegmentDelta] = []
        for key in sorted(set(ref_segments) & set(cmp)):
            r = ref_segments[key]
            c = cmp[key]
            delta = c.seg_time_s - r.seg_time_s
            speed_delta = c.avg_speed - r.avg_speed
            brake_delta = c.max_brake - r.max_brake
            throttle_delta = c.avg_throttle - r.avg_throttle
            if delta > 0.15 and c.max_brake > r.max_brake + 0.08:
                hint = "Zeitverlust: stärker/länger gebremst"
            elif delta > 0.15 and c.avg_throttle < r.avg_throttle - 0.12:
                hint = "Zeitverlust: später/weniger Gas"
            elif delta > 0.15 and c.avg_speed < r.avg_speed - 5:
                hint = "Zeitverlust: weniger Speed"
            elif delta < -0.10:
                hint = "besser als Referenz"
            elif c.max_brake > 0.25 or r.max_brake > 0.25:
                hint = "Bremszone ähnlich"
            elif c.avg_throttle > 0.85 and r.avg_throttle > 0.85:
                hint = "Vollgas ähnlich"
            else:
                hint = "neutral"
            deltas.append(SegmentDelta(
                start_m=key, end_m=key + 50,
                compare_lap=self.compare_lap.lap_number, reference_lap=(-1 if use_external else self.reference_lap.lap_number),
                cmp_time_s=c.seg_time_s, ref_time_s=r.seg_time_s, delta_s=delta,
                cmp_avg_speed=c.avg_speed, ref_avg_speed=r.avg_speed, speed_delta=speed_delta,
                cmp_max_brake=c.max_brake, ref_max_brake=r.max_brake, brake_delta=brake_delta,
                cmp_avg_throttle=c.avg_throttle, ref_avg_throttle=r.avg_throttle, throttle_delta=throttle_delta,
                hint=hint,
            ))
        return deltas

    def update_lap_compare(self):
        self.compare_table.setRowCount(0)
        self.segment_deltas = self.build_lap_compare()
        for d in self.segment_deltas:
            row = self.compare_table.rowCount(); self.compare_table.insertRow(row)
            vals = [
                row + 1, f"{d.start_m}-{d.end_m}", f"Lap {d.compare_lap}", ("Extern" if d.reference_lap < 0 else f"Lap {d.reference_lap}"),
                f"{d.delta_s:+.3f}", fmt_lap_time(d.cmp_time_s), fmt_lap_time(d.ref_time_s),
                f"{d.cmp_avg_speed:.1f}", f"{d.ref_avg_speed:.1f}", f"{d.speed_delta:+.1f}",
                f"{d.brake_delta:+.3f}", f"{d.throttle_delta:+.3f}", d.hint
            ]
            for c, v in enumerate(vals):
                self.compare_table.setItem(row, c, QTableWidgetItem(str(v)))
        self.compare_table.resizeColumnsToContents()
        if (self.reference_lap or self.external_reference) and self.compare_lap:
            total = sum(d.delta_s for d in self.segment_deltas)
            self.log.append(f"Rundenvergleich: Lap {self.compare_lap.lap_number} vs {self.reference_display_label()} | Segment-Delta gesamt {total:+.3f} s")
        elif self.reference_lap or self.external_reference:
            self.log.append("Rundenvergleich: keine gültige Vergleichsrunde vorhanden.")
        self.update_zone_table()

    def lap_compare_report_lines(self) -> List[str]:
        if not self.segment_deltas:
            self.update_lap_compare()
        lines = ["", "Lap-vs-Referenz-Vergleich 50 m:"]
        if not self.reference_lap and not self.external_reference:
            lines.append("Keine Referenzrunde vorhanden.")
            return lines
        if not self.compare_lap:
            lines.append("Keine zweite gültige Runde für Vergleich vorhanden.")
            return lines
        total = sum(d.delta_s for d in self.segment_deltas)
        losses = [d for d in self.segment_deltas if d.delta_s > 0.10]
        gains = [d for d in self.segment_deltas if d.delta_s < -0.10]
        lines.append(f"Vergleich: Lap {self.compare_lap.lap_number} gegen {self.reference_display_label()} | Segment-Delta gesamt {total:+.3f} s")
        lines.append(f"Problemzonen: {len(losses)} | bessere Zonen: {len(gains)}")
        warn = self.start_finish_warning()
        if warn:
            lines.append(warn)
        lines.append("Sektor | Meter | Delta s | Vgl Zeit [m]:ss.000* | Ref Zeit [m]:ss.000* | Vgl Avg | Ref Avg | Speed Diff | Brake Diff | Throttle Diff | Hinweis")
        for idx, d in enumerate(self.segment_deltas, 1):
            if abs(d.delta_s) >= 0.05 or "Zeitverlust" in d.hint:
                lines.append(
                    f"{idx} | {d.start_m}-{d.end_m} | {d.delta_s:+.3f} | {fmt_lap_time(d.cmp_time_s)} | {fmt_lap_time(d.ref_time_s)} | "
                    f"{d.cmp_avg_speed:.1f} | {d.ref_avg_speed:.1f} | {d.speed_delta:+.1f} | "
                    f"{d.brake_delta:+.3f} | {d.throttle_delta:+.3f} | {d.hint}"
                )
        top_losses = sorted(losses, key=lambda d: d.delta_s, reverse=True)[:8]
        lines.append("")
        lines.append("Top-Einzelsektoren:")
        if not top_losses:
            lines.append("Keine einzelnen Problemsektoren > +0.10 s erkannt.")
        for d in top_losses:
            lines.append(f"{d.start_m}-{d.end_m} m: {d.delta_s:+.3f} s | {d.hint} | Speed {d.speed_delta:+.1f} km/h | Brake {d.brake_delta:+.3f} | Gas {d.throttle_delta:+.3f}")

        grouped = self.grouped_problem_zones()
        lines.append("")
        lines.append("Zusammenhängende Problemzonen:")
        if not grouped:
            lines.append("Keine zusammenhängende Problemzone erkannt.")
        for i, (start, end, total_loss, spd, brk, thr, cause, advice) in enumerate(grouped[:8], 1):
            lines.append(f"{i}. {start}-{end} m | Summe {total_loss:+.3f} s | {cause} | Speed {spd:+.1f} km/h | Brake {brk:+.3f} | Gas {thr:+.3f}")
        return lines


    def grouped_problem_zones(self) -> List[Tuple[int, int, float, float, float, float, str, str]]:
        """Group adjacent weak losing 50-m sectors into human-readable coach zones.

        3.8 is intentionally more aggressive than 3.7: several small +0.04 to +0.09 s
        losses in the same braking/corner phase are more useful than one isolated sector.
        Returns: start, end, total_delta, avg_speed_delta, max_brake_delta, avg_throttle_delta, cause, advice
        """
        if not self.segment_deltas:
            self.segment_deltas = self.build_lap_compare()
        # Include smaller positive deltas so a whole corner phase is recognized.
        candidates = [d for d in self.segment_deltas if d.delta_s > 0.035]
        if not candidates:
            return []
        candidates = sorted(candidates, key=lambda d: d.start_m)
        groups = []
        current = [candidates[0]]
        for d in candidates[1:]:
            prev = current[-1]
            # Allow a small gap so a real corner phase stays together even if one 50-m bucket is neutral.
            if d.start_m <= prev.end_m + 100:
                current.append(d)
            else:
                groups.append(current)
                current = [d]
        groups.append(current)

        out = []
        for g in groups:
            positive = [d for d in g if d.delta_s > 0]
            if not positive:
                continue
            start = min(d.start_m for d in g)
            end = max(d.end_m for d in g)
            total = sum(max(0.0, d.delta_s) for d in g)
            # Filter tiny one-off noise, but keep multi-sector corner phases.
            if total < 0.10 and len(g) < 2:
                continue
            if total < 0.14 and len(g) < 3:
                continue
            spd = sum(d.speed_delta for d in g) / len(g)
            brk = max(d.brake_delta for d in g)
            thr = sum(d.throttle_delta for d in g) / len(g)
            max_ref_brake = max(d.ref_max_brake for d in g)
            max_cmp_brake = max(d.cmp_max_brake for d in g)
            avg_cmp_thr = sum(d.cmp_avg_throttle for d in g) / len(g)
            avg_ref_thr = sum(d.ref_avg_throttle for d in g) / len(g)
            braking_zone = max_cmp_brake > 0.20 or max_ref_brake > 0.20 or brk > 0.08

            if braking_zone and brk > 0.10 and spd < -5:
                cause = "Bremsphase kostet Zeit"
                advice = "Bremse früher und sauberer lösen; Auto in die Kurve rollen lassen statt Speed zu stark abzubauen."
            elif braking_zone and spd < -8:
                cause = "zu wenig Speed durch die Brems-/Einlenkphase"
                advice = "Bremspunkt nicht härter machen, sondern Lösepunkt und Mindesttempo stabilisieren."
            elif avg_cmp_thr < avg_ref_thr - 0.10:
                cause = "spätere oder schwächere Gasannahme"
                advice = "Auto früher gerade stellen und Gasaufbau am Ausgang früher beginnen."
            elif spd < -10:
                cause = "zu wenig Mindest-/Kurvenspeed"
                advice = "Eingang ruhiger wählen, weniger Tempo wegwerfen und sauberer durchrollen."
            elif braking_zone:
                cause = "Bremszone inkonstant"
                advice = "Bremsdruck, Lösepunkt und Einlenken reproduzierbarer treffen."
            else:
                cause = "Rhythmus-/Linienverlust"
                advice = "Linie und Lenkwinkel ruhiger halten; Referenz in diesem Bereich nachfahren."
            out.append((start, end, total, spd, brk, thr, cause, advice))
        out.sort(key=lambda x: x[2], reverse=True)
        return out

    def heatmap_report_lines(self) -> List[str]:
        lines = ["", "Trackmap-Heatmap:"]
        if (not self.reference_lap and not self.external_reference) or not self.compare_lap or not self.segment_deltas:
            lines.append("Keine Heatmap möglich: mindestens eine Referenz und eine Vergleichsrunde nötig.")
            return lines
        zones = self.grouped_problem_zones()
        losses = [d for d in self.segment_deltas if d.delta_s > 0.06]
        gains = [d for d in self.segment_deltas if d.delta_s < -0.10]
        total = sum(d.delta_s for d in self.segment_deltas)
        lines.append(f"{self.reference_display_label()} vs Vergleich Lap {self.compare_lap.lap_number} | Delta gesamt {total:+.3f} s")
        lines.append(f"Heatmap-Legende: dicke rote/orange Bereiche=Coach-Zonen ({len(zones)}), Rot/Orange=Zeitverlust ({len(losses)} Sektoren), Grün=besser ({len(gains)} Sektoren).")
        if zones:
            lines.append("Markierte Coach-Zonen auf der Map:")
            for i, z in enumerate(zones[:5], 1):
                lines.append(f"Zone {i}: {z[0]}-{z[1]} m | {z[2]:+.3f} s | {z[6]}")
        else:
            lines.append("Keine markierte Coach-Zone vorhanden.")
        return lines

    def coach_report_lines(self) -> List[str]:
        if not self.segment_deltas:
            self.segment_deltas = self.build_lap_compare()
        lines = ["", "Coach-Hinweise:"]
        if not self.reference_lap and not self.external_reference:
            lines.append("Keine Referenzrunde vorhanden. Erst eine Runde aufzeichnen oder externe Referenz importieren.")
            return lines
        if not self.compare_lap:
            lines.append("Keine Vergleichsrunde vorhanden. Für Coaching mindestens zwei saubere Runden aufzeichnen.")
            return lines
        total = sum(d.delta_s for d in self.segment_deltas)
        losses = self.grouped_problem_zones()
        lines.append(f"Vergleich Lap {self.compare_lap.lap_number} gegen {self.reference_display_label()}: Gesamt {total:+.3f} s.")
        warn = self.start_finish_warning()
        if warn:
            lines.append(warn)
            if len(losses) > 1 and losses[0][0] < 250:
                losses = losses[1:] + [losses[0]]
        if not losses:
            lines.append("Keine klaren zusammenhängenden Problemzonen erkannt. Fokus: Konstanz halten und mehr Runden sammeln.")
            return lines
        lines.append("Zone | Priorität | Bereich | Verlust | Diagnose | Handlung")
        for i, (start, end, total_loss, spd, brk, thr, cause, advice) in enumerate(losses[:5], 1):
            prio = "HOCH" if total_loss >= 0.35 else ("MITTEL" if total_loss >= 0.18 else "NIEDRIG")
            lines.append(
                f"Zone {i} | {prio} | {start}-{end} m | {total_loss:+.3f} s | "
                f"{cause}; Speed {spd:+.1f} km/h, Brake {brk:+.3f}, Gas {thr:+.3f} | {advice}"
            )
        # One concise driver summary.
        main = losses[0]
        lines.append("")
        lines.append("Kurzfazit:")
        lines.append(
            f"Der größte kumulierte Verlust liegt in Zone 1 bei {main[0]}-{main[1]} m ({main[2]:+.3f} s). "
            f"Hauptthema: {main[6]}. Nächster Run: nur diesen Bereich bewusst sauberer fahren."
        )
        lines.append("")
        lines.append("Live-Coaching-Vorbereitung:")
        lines.append("Diese Hinweise sind bewusst kurz formuliert, damit sie später als Sprachausgabe genutzt werden können.")
        return lines

    def limit_coach_assessment(self):
        """0.4.5.2: Simple Fahr-Limit-Coach.
        Labels deliberately stay human-readable and conservative:
        konservativ / sauber / am Limit / überfahren.
        This is not AI yet; it is rule-based context for the later KI-Coach.
        """
        if not self.samples:
            return "keine Daten", 0, ["Noch keine Samples. Für Limit-Coaching bitte eine saubere Session aufzeichnen."]
        reasons = []
        score = 0
        rows = self.input_coach_rows()
        if rows:
            avg_coast = sum(r["coast_pct"] for r in rows) / len(rows)
            avg_overlap = sum(r["overlap_pct"] for r in rows) / len(rows)
            total_release = sum(r["brake_release_spikes"] for r in rows)
            total_throttle = sum(r["throttle_spikes"] for r in rows)
            if avg_coast > 16:
                score -= 2; reasons.append(f"viel Rollenphase ({avg_coast:.1f}%) → eher konservativ/passiv")
            elif avg_coast > 10:
                score -= 1; reasons.append(f"etwas viel Rollenphase ({avg_coast:.1f}%)")
            if total_release > max(8, len(rows) * 4):
                score += 2; reasons.append(f"viele abrupte Bremslöse-Sprünge ({total_release}) → Auto wird wahrscheinlich überfahren")
            elif total_release > max(4, len(rows) * 2):
                score += 1; reasons.append(f"Bremslösung teilweise unruhig ({total_release})")
            if total_throttle > max(8, len(rows) * 4):
                score += 2; reasons.append(f"viele Gas-Sprünge ({total_throttle}) → Traktion/Balance am Limit")
            elif total_throttle > max(4, len(rows) * 2):
                score += 1; reasons.append(f"Gasaufbau teilweise ruppig ({total_throttle})")
            if avg_overlap > 6:
                score += 1; reasons.append(f"Gas/Bremse-Überlappung erhöht ({avg_overlap:.1f}%)")
        else:
            reasons.append("Noch keine gültigen sauberen Runden für Input-Bewertung.")

        zones = self.grouped_problem_zones() if self.segment_deltas else []
        if zones:
            main = zones[0]
            if main[2] >= 0.60:
                score += 2; reasons.append(f"großer Zeitverlust in Zone {main[0]}-{main[1]} m ({main[2]:+.3f}s)")
            elif main[2] >= 0.25:
                score += 1; reasons.append(f"relevanter Zeitverlust in Zone {main[0]}-{main[1]} m ({main[2]:+.3f}s)")
            # low speed delta with higher brake is often over-slowing, not true limit.
            if main[3] < -8 and main[4] > 0.08:
                score -= 1; reasons.append("Referenzvergleich deutet eher auf zu viel/zu lange Bremse als echtes Limit hin")
        elif self.reference_lap or self.external_reference:
            reasons.append("Referenz vorhanden, aber keine klare Problemzone erkannt.")

        if self.samples:
            flat_status = [self.flatspot_report_for_prefix(p) for p in ("tire_fl", "tire_fr", "tire_rl", "tire_rr")]
            if any("FLAT" in x or "REIFEN" in x or "LOCK!" in x or "ABS!" in x for x in flat_status):
                score += 2; reasons.append("Reifen-/Bremsstatus kritisch: " + ", ".join(flat_status))
            stats = self.tire_stats_summary() if self.samples else {}
            if stats:
                avg_temp = sum(v.get("temp_avg", 0.0) for v in stats.values()) / 4.0
                if avg_temp > 105:
                    score += 1; reasons.append(f"Reifen sehr warm ({avg_temp:.1f} °C) → Überfahren/Schonung prüfen")
                elif 70 <= avg_temp <= 100:
                    reasons.append(f"Reifenfenster wirkt brauchbar ({avg_temp:.1f} °C)")
                elif avg_temp and avg_temp < 60:
                    reasons.append(f"Reifen kalt ({avg_temp:.1f} °C) → Limit-Bewertung vorsichtig interpretieren")

        if score <= -2:
            level = "konservativ"
        elif score <= 1:
            level = "sauber"
        elif score <= 3:
            level = "am Limit"
        else:
            level = "überfahren"
        return level, score, reasons

    def limit_coach_report_lines(self, summary_only: bool = False) -> List[str]:
        level, score, reasons = self.limit_coach_assessment()
        lines = ["", "Fahr-Limit-Coach 0.4.5.4:"]
        lines.append(f"Limit-Level: {level} | Score {score:+d}")
        if level == "keine Daten":
            lines.append("Noch keine Daten. Für sinnvolle Bewertung mindestens 3–5 saubere Runden oder eine Referenzrunde nutzen.")
            return lines
        if level == "konservativ":
            lines.append("Kurzdiagnose: Du lässt wahrscheinlich noch Zeit liegen, ohne das Auto wirklich ans Limit zu bringen.")
            lines.append("Nächster Run: eine Kurve wählen, Rollenphase reduzieren und früher kontrolliert ans Gas, nicht einfach später bremsen.")
        elif level == "sauber":
            lines.append("Kurzdiagnose: Fahrweise wirkt kontrolliert. Nächster Schritt ist gezielter Vergleich einzelner Problemzonen.")
            lines.append("Nächster Run: gleiche Linie und gleiche Inputs reproduzieren, dann nur eine Zone bewusst optimieren.")
        elif level == "am Limit":
            lines.append("Kurzdiagnose: Du bist nahe am Limit, aber einzelne Inputs/Zonen kosten Stabilität oder Zeit.")
            lines.append("Nächster Run: nicht mehr Attacke, sondern Bremse lösen/Gasaufbau ruhiger machen und Exit stabilisieren.")
        else:
            lines.append("Kurzdiagnose: Du überfährst wahrscheinlich Auto/Reifen oder erzeugst zu viel Input-Unruhe.")
            lines.append("Nächster Run: 2 Runden bewusst 95% fahren, frühere Bremsruhe, weicheres Gas, keine zusätzlichen Lenkkorrekturen erzwingen.")
        if not summary_only:
            lines.append("")
            lines.append("Warum:")
            for r in reasons[:10]:
                lines.append(f"- {r}")
            lines.append("")
            lines.append("Hinweis: 0.4.5.2 ist regelbasiert. Die spätere KI-Version soll Report, Telemetrie und Settings-Screenshots gemeinsam auswerten.")
        return lines

    def update_heatmap(self):
        if not hasattr(self, 'heatmap'):
            return
        ref_samples = self.external_reference_samples() if self.external_reference else (self.samples_for_reference_lap() if self.reference_lap else [])
        cmp_samples = self.samples_for_lap(self.compare_lap.lap_number) if self.compare_lap else []
        zones = self.grouped_problem_zones() if self.segment_deltas else []
        if ref_samples and cmp_samples and self.segment_deltas:
            self.heatmap.set_heatmap(self.samples, ref_samples, cmp_samples, self.segment_deltas, zones)
            total = sum(d.delta_s for d in self.segment_deltas)
            zeroish = abs(total) < 0.001 and not zones
            self.heatmap_note.setText(
                f"{self.reference_display_label()} vs Vergleich Lap {self.compare_lap.lap_number} | "
                f"Delta gesamt {total:+.3f} s | Coach-Zonen: {len(zones)}"
                + (" | Hinweis: identische/neue Auto-Referenz, daher keine roten Zonen." if zeroish else "")
            )
        else:
            base = cmp_samples or ref_samples or self.samples
            self.heatmap.set_samples(base)
            reason = "Noch keine Heatmap möglich: Referenz und gültige Vergleichsrunde nötig."
            if ref_samples and not cmp_samples:
                reason = "Referenz vorhanden, aber noch keine gültige Vergleichsrunde für Heatmap."
            elif cmp_samples and not ref_samples:
                reason = "Vergleichsrunde vorhanden, aber keine Referenzdaten für Heatmap."
            self.heatmap_note.setText(reason)

    def update_zone_table(self):
        if not hasattr(self, "zone_table"):
            return
        self.zone_table.setRowCount(0)
        zones = self.grouped_problem_zones() if self.segment_deltas else []
        for i, (start, end, total_loss, spd, brk, thr, cause, advice) in enumerate(zones[:8], 1):
            prio = "HOCH" if total_loss >= 0.35 else ("MITTEL" if total_loss >= 0.18 else "NIEDRIG")
            row = self.zone_table.rowCount(); self.zone_table.insertRow(row)
            vals = [f"Zone {i}", f"{start}-{end} m", f"{total_loss:+.3f} s", prio, cause, advice, f"{spd:+.1f} km/h"]
            for c, v in enumerate(vals):
                self.zone_table.setItem(row, c, QTableWidgetItem(str(v)))
        self.zone_table.resizeColumnsToContents()

    def update_coach_text(self):
        if not hasattr(self, 'coach_text'):
            return
        text = "\n".join(self.coach_report_lines())
        self.coach_text.setPlainText(text)
        if hasattr(self, "limit_coach_text"):
            self.limit_coach_text.setPlainText("\n".join(self.limit_coach_report_lines()))
        self.refresh_dashboard()

    def safe_save_report_to_path(self, path) -> bool:
        try:
            self.last_report_save_error = ""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            text = self.build_report()
            if not text or len(text) < 50:
                self.last_report_save_error = "Reporttext ist leer oder zu kurz"
                self.log.append(f"Report speichern unplausibel leer: {path.resolve()}")
                return False
            path.write_text(text, encoding="utf-8")
            ok = path.exists() and path.stat().st_size > 50
            if ok:
                self.log.append(f"Report gespeichert: {path.resolve()}")
            else:
                self.last_report_save_error = "Datei wurde nicht oder leer geschrieben"
                self.log.append(f"Report speichern unplausibel leer: {path.resolve()}")
            return ok
        except Exception as e:
            self.last_report_save_error = f"{type(e).__name__}: {e}"
            self.log.append(f"Report speichern FEHLER: {self.last_report_save_error}")
            return False

    def safe_save_csv_to_path(self, path) -> bool:
        try:
            self.last_csv_save_error = ""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.write_csv(path)
            ok = path.exists() and path.stat().st_size > 50
            if ok:
                self.log.append(f"CSV gespeichert: {path.resolve()}")
            else:
                self.last_csv_save_error = "CSV wurde nicht oder leer geschrieben"
                self.log.append(f"CSV speichern unplausibel leer: {path.resolve()}")
            return ok
        except Exception as e:
            self.last_csv_save_error = f"{type(e).__name__}: {e}"
            self.log.append(f"CSV speichern FEHLER: {self.last_csv_save_error}")
            return False

    def autosave_exports(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        if not self.samples:
            self.log.append("Auto-Report/CSV übersprungen: keine Samples vorhanden.")
            return
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rp = REPORT_DIR / f"lmu_live_recorder_{stamp}.txt"
        cp = CSV_DIR / f"lmu_live_recorder_samples_{stamp}.csv"
        report_ok = self.safe_save_report_to_path(rp)
        csv_ok = self.safe_save_csv_to_path(cp)
        if report_ok and csv_ok:
            self.log.append(f"Auto-Save OK: Report + CSV gespeichert in {EXPORT_DIR.resolve()}")
        else:
            self.log.append(f"Auto-Save FEHLER: Report_ok={report_ok}, CSV_ok={csv_ok}. Bitte Logpfad prüfen: {EXPORT_DIR.resolve()}")

    def tire_grip_hint(self, avg_temp: float, wear_pct: float, pressure_kpa: float, spread: float) -> str:
        # 4.3: berechnete Schätzung. LMU liefert hier keinen direkten Grip-%-Wert.
        score = 100.0
        notes = []
        if avg_temp <= 0:
            return "keine Daten"
        if avg_temp < 65:
            score -= 28; notes.append("kalt")
        elif avg_temp > 105:
            score -= 25; notes.append("heiß")
        elif 75 <= avg_temp <= 95:
            notes.append("Temp gut")
        else:
            score -= 8; notes.append("Temp ok")
        # mWear wirkt in LMU/rF2 wie Restzustand: hoch = gut/frisch, niedrig = stärker verbraucht.
        if wear_pct <= 0:
            pass
        elif wear_pct < 55:
            score -= 25; notes.append("Wear hoch")
        elif wear_pct < 75:
            score -= 12; notes.append("Wear mittel")
        else:
            notes.append("Wear gut")
        if pressure_kpa > 0:
            if pressure_kpa < 145:
                score -= 10; notes.append("Druck niedrig")
            elif pressure_kpa > 190:
                score -= 10; notes.append("Druck hoch")
        if abs(spread) > 12:
            score -= 10; notes.append("I/O Spread")
        score = max(0, min(100, score))
        level = "Grip perfekt" if score >= 92 else ("Grip hoch" if score >= 80 else ("Grip mittel" if score >= 60 else "Grip niedrig"))
        return f"{level} · " + ", ".join(notes)

    def tire_setup_hint(self, out_t: float, mid_t: float, in_t: float, pressure_kpa: float, wear_pct: float) -> str:
        if max(out_t, mid_t, in_t, pressure_kpa) <= 0:
            return "keine Daten"
        hints = []
        spread = in_t - out_t
        avg_t = (out_t + mid_t + in_t) / 3.0 if (out_t or mid_t or in_t) else 0.0
        if avg_t < 65:
            hints.append("Reifen kalt")
        elif avg_t > 105:
            hints.append("Reifen heiß")
        if abs(spread) >= 12:
            if spread > 0:
                hints.append("innen wärmer: Sturz/Belastung prüfen")
            else:
                hints.append("außen wärmer: Untersteuer-/Sturzthema prüfen")
        if mid_t > max(out_t, in_t) + 6:
            hints.append("Mitte wärmer: Druck eher hoch")
        elif mid_t + 6 < min(out_t, in_t):
            hints.append("Mitte kühler: Druck eher niedrig")
        if pressure_kpa and pressure_kpa < 145:
            hints.append("Druck niedrig")
        elif pressure_kpa > 190:
            hints.append("Druck hoch")
        if 0 < wear_pct < 60:
            hints.append("Wear kritisch")
        return ", ".join(hints) if hints else "ok"

    def tire_stats_summary(self):
        """Aggregate tire stats for report/setup-coach. Returns dict keyed by FL/FR/RL/RR display names."""
        specs = [("VL", "tire_fl"), ("VR", "tire_fr"), ("HL", "tire_rl"), ("HR", "tire_rr")]
        def finite(vals):
            out = []
            for v in vals:
                try:
                    x = float(v)
                    if math.isfinite(x):
                        out.append(x)
                except Exception:
                    pass
            return out
        def avg(vals):
            vals = finite(vals)
            return sum(vals) / len(vals) if vals else 0.0
        data = {}
        for name, prefix in specs:
            p = [x for x in finite([getattr(s, f"{prefix}_pressure_kpa", 0.0) for s in self.samples]) if 60.0 <= x <= 350.0]
            out_t = [x for x in finite([getattr(s, f"{prefix}_temp_l_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            mid_t = [x for x in finite([getattr(s, f"{prefix}_temp_c_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            in_t = [x for x in finite([getattr(s, f"{prefix}_temp_r_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            carc = [x for x in finite([getattr(s, f"{prefix}_carcass_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            wear = [x for x in finite([getattr(s, f"{prefix}_wear_pct", 0.0) for s in self.samples]) if 0.0 < x <= 100.0]
            oa, ma, ia = avg(out_t), avg(mid_t), avg(in_t)
            pa, wa, ca = avg(p), avg(wear), avg(carc)
            temp_avg = (oa + ma + ia) / 3.0 if any([oa, ma, ia]) else 0.0
            spread = ia - oa
            data[name] = {
                "pressure": pa, "pressure_min": min(p or [0.0]), "pressure_max": max(p or [0.0]),
                "out": oa, "mid": ma, "in": ia, "temp_avg": temp_avg, "carcass": ca,
                "wear": wa, "spread": spread,
                "hint": self.tire_setup_hint(oa, ma, ia, pa, wa),
            }
        return data

    def tire_setup_coach_lines(self) -> List[str]:
        lines = ["Reifen-/Setup-Coach 4.4"]
        if not self.samples:
            lines.append("Noch keine Samples. Für echte Hinweise bitte Recording starten und 5–10 Runden fahren.")
            return lines
        stats = self.tire_stats_summary()
        if len(self.samples) < 300:
            lines.append("Hinweis: Datenbasis noch klein. Hinweise sind nur grob. Für Setup-Entscheidungen bitte 5–10 Runden am Stück fahren.")
        else:
            lines.append("Datenbasis: Stintdaten vorhanden. Hinweise aus Durchschnitt/Trend, nicht aus einer einzelnen Momentaufnahme.")

        # Global pressure and temperature balance.
        avg_press = sum(v["pressure"] for v in stats.values()) / 4.0 if stats else 0.0
        avg_temp = sum(v["temp_avg"] for v in stats.values()) / 4.0 if stats else 0.0
        lines.append("")
        lines.append(f"Gesamtbild: Druck Ø {avg_press/100.0:.2f} bar | Reifen-Temp Ø {avg_temp:.1f} °C")
        if avg_temp < 65:
            lines.append("Priorität 1: Reifen sind insgesamt kalt. Erst mit mehreren sauberen Push-Runden bewerten; falls sie kalt bleiben, Startdruck eher leicht reduzieren oder aggressiver aufwärmen.")
        elif avg_temp > 105:
            lines.append("Priorität 1: Reifen sind insgesamt heiß. Stint schonender fahren; falls dauerhaft heiß, Startdruck/Setup prüfen.")
        else:
            lines.append("Temperaturfenster: grundsätzlich brauchbar. Einzelne Reifen-Spreads sind wichtiger als der Gesamtwert.")
        if avg_press > 0:
            if avg_press < 1.45 * 100:
                lines.append("Druckbild: eher niedrig. Auf Stabilität beim Einlenken und Walken achten.")
            elif avg_press > 1.85 * 100:
                lines.append("Druckbild: eher hoch. Kontaktfläche könnte kleiner werden; Mitte-Temperaturen beobachten.")
            else:
                lines.append("Druckbild: plausibel für aktuellen Teststand. Entscheidend ist der Verlauf über den Stint.")

        lines.append("")
        lines.append("Pro Reifen:")
        for name in ["VL", "VR", "HL", "HR"]:
            v = stats.get(name, {})
            if not v:
                continue
            lines.append(f"{name}: {v['pressure']/100.0:.2f} bar | A/M/I {v['out']:.0f}/{v['mid']:.0f}/{v['in']:.0f} °C | Rest {v['wear']:.0f}% | {v['hint']}")
            sp = v.get("spread", 0.0)
            mid = v.get("mid", 0.0)
            hot_side = "innen" if sp > 8 else ("außen" if sp < -8 else "gleichmäßig")
            if hot_side == "innen":
                lines.append(f"  → Innen deutlich wärmer: Sturz/Belastung beobachten. Wenn das über viele Runden bleibt, etwas weniger negativen Sturz testen.")
            elif hot_side == "außen":
                lines.append(f"  → Außen deutlich wärmer: Reifen wird außen belastet. Einlenken/Untersteuern prüfen; ggf. Sturz/ARB/Balancing beobachten.")
            if mid > max(v.get("out", 0.0), v.get("in", 0.0)) + 6:
                lines.append("  → Mitte wärmer als Schultern: Druck tendenziell zu hoch für diesen Reifen.")
            elif mid + 6 < min(v.get("out", 0.0), v.get("in", 0.0)):
                lines.append("  → Mitte kühler als Schultern: Druck tendenziell zu niedrig für diesen Reifen.")

        # Axle balance.
        front_temp = (stats["VL"]["temp_avg"] + stats["VR"]["temp_avg"]) / 2.0
        rear_temp = (stats["HL"]["temp_avg"] + stats["HR"]["temp_avg"]) / 2.0
        front_wear = (stats["VL"]["wear"] + stats["VR"]["wear"]) / 2.0
        rear_wear = (stats["HL"]["wear"] + stats["HR"]["wear"]) / 2.0
        lines.append("")
        lines.append("Balance-Hinweis:")
        if front_temp - rear_temp > 8 or rear_wear - front_wear > 4:
            lines.append("Vorderachse stärker belastet: mögliches Untersteuern / zu viel Lenkwinkel / Front überfahren. Fahrstil und Front-Setup beobachten.")
        elif rear_temp - front_temp > 8 or front_wear - rear_wear > 4:
            lines.append("Hinterachse stärker belastet: mögliches Übersteuern / Traktionsthema. Gasannahme und Heckstabilität beobachten.")
        else:
            lines.append("Vorder-/Hinterachse wirken relativ ausgeglichen.")

        lines.append("")
        lines.append("Nächster Test: 8–10 Runden mit gleichem Fahrstil fahren. Danach prüfen wir, ob der Druck im Zielbereich landet und welche Reifen zuerst abbauen.")
        lines.append("Hinweis: Die Setup-Hinweise sind konservativ. Bitte immer nur eine Setup-Änderung auf einmal testen.")
        return lines

    def flatspot_report_for_prefix(self, prefix: str) -> str:
        if not self.samples:
            return "keine Daten"
        driving = [s for s in self.samples if not self.is_non_driving_sample(s) and getattr(s, "speed_kmh", 0.0) > 10]
        flat_seen = any(bool(getattr(s, f"{prefix}_flat", False)) for s in driving)
        if flat_seen:
            return "REIFEN PLATT"
        # Nur Bremsphasen bewerten, damit normale Kurvenslides nicht als Bremsplatte erscheinen.
        brake_rows = [s for s in driving if getattr(s, "brake", 0.0) > 0.35 and getattr(s, "speed_kmh", 0.0) > 30]
        vals = [float(getattr(s, f"{prefix}_grip_fract", 0.0) or 0.0) for s in brake_rows]
        vals = [v for v in vals if math.isfinite(v)]
        if not vals:
            return "OK"
        max_v = max(vals)
        cnt_warn = sum(1 for v in vals if v >= 0.25)
        vclasses = {infer_vehicle_class(s.vehicle_class, s.vehicle_name, s.vehicle_model) for s in driving[:200]}
        is_abs_car = bool(vclasses & {"GT3"})
        if is_abs_car:
            if max_v >= 0.45 or cnt_warn >= 8:
                return f"ABS! max {max_v:.2f}"
            if max_v >= 0.25 or cnt_warn >= 3:
                return f"ABS max {max_v:.2f}"
            return "OK"
        if max_v >= 0.45 or cnt_warn >= 8:
            return f"LOCK! max {max_v:.2f}"
        if max_v >= 0.25 or cnt_warn >= 3:
            return f"LOCK max {max_v:.2f}"
        if max_v >= 0.12:
            return f"leicht max {max_v:.2f}"
        return "OK"

    def flatspot_event_log_lines(self) -> List[str]:
        # 0.4.5.6: Ursprungssuche wird NUR durch einen bestaetigten Flatspot (echter LMU-mFlat)
        # ausgeloest. Fuer jeden Flat wird im Vorlauf das staerkste Ursachensignal gesucht:
        #   GT3/ABS   -> groesstes Lenk-Reversal (Dreher/Slide), da ABS Geradeaus-Blockaden verhindert.
        #   Nicht-GT3 -> haerteste Bremsung mit staerkster Verzoegerung (Lockup).
        # grip_fract wird nicht mehr genutzt (in echten LMU-Aufnahmen leer).
        lines = ["", "Flatspot-Event-Log 0.4.5.6:"]
        if not self.samples:
            lines.append("Keine Daten.")
            return lines
        specs = [("VL", "tire_fl"), ("VR", "tire_fr"), ("HL", "tire_rl"), ("HR", "tire_rr")]
        driving = [(i, s) for i, s in enumerate(self.samples)
                   if not self.is_non_driving_sample(s) and float(getattr(s, "speed_kmh", 0.0) or 0.0) > 10.0]
        if not driving:
            lines.append("Keine fahrenden Samples (nur Pit/Stand/Outlap).")
            return lines
        vclasses = {infer_vehicle_class(s.vehicle_class, s.vehicle_name, s.vehicle_model) for _, s in driving[:200]}
        is_abs_car = bool(vclasses & {"GT3"})
        mode = "Dreher/Slide" if is_abs_car else "Brems-Lockup"
        lines.append(f"Fahrzeugklasse: {'GT3 (ABS)' if is_abs_car else 'Nicht-ABS (Hypercar/LMP/GTE)'} -> Ursprungssuche via {mode}.")

        def g(s, a, d=0.0):
            v = getattr(s, a, d)
            try:
                v = float(v)
            except (TypeError, ValueError):
                return d
            return v if math.isfinite(v) else d

        # Bestaetigte Flatspots (mFlat, steigende Flanke); Position p im driving-Array merken.
        flats = []
        for name, prefix in specs:
            prev = False
            for p, (i, s) in enumerate(driving):
                fl = bool(getattr(s, f"{prefix}_flat", False))
                if fl and not prev:
                    flats.append((p, name, int(g(s, "lap_number")), g(s, "lap_dist_m")))
                prev = fl

        if not flats:
            lines.append("")
            lines.append("Keine bestaetigten Flatspots (LMU mFlat) in dieser Session.")
            lines.append(f"Hinweis: Ohne mFlat-Ereignis gibt es keinen Flatspot zu verorten. Die {mode}-"
                         "Ursprungssuche wird nur bei bestaetigtem Flatspot ausgeloest.")
            return lines

        LOOKBACK_M = 900.0
        def lookback_slice(p, flat_lap):
            out = []; crossed = 0; lap_prev = flat_lap; travelled = 0.0; last_dist = None
            q = p
            while q >= 0:
                i, s = driving[q]
                lap = int(g(s, "lap_number")); dist = g(s, "lap_dist_m")
                if lap != lap_prev:
                    crossed += 1
                    if crossed > 1:
                        break
                    lap_prev = lap; last_dist = None
                if last_dist is not None:
                    travelled += abs(last_dist - dist)
                last_dist = dist
                out.append(s)
                if travelled > LOOKBACK_M:
                    break
                q -= 1
            out.reverse()
            return out

        def spin_origin(sl):
            # Groesstes Lenk-Reversal ueber ein Fenster der letzten ~35 Samples; echtes
            # Reversal verlangt beide Seiten (>=+0.12 und <=-0.12). Invalidierte Runde bevorzugt.
            best = None; win = []
            for s in sl:
                win.append(s)
                if len(win) > 35:
                    win.pop(0)
                steers = [g(w, "steering") for w in win]
                smax, smin = max(steers), min(steers)
                if not (smax >= 0.12 and smin <= -0.12):
                    continue
                swing = smax - smin
                inv = any(bool(getattr(w, "lap_invalidated", False)) for w in win)
                score = swing + (0.4 if inv else 0.0)
                if best is None or score > best[0]:
                    pk = max(win, key=lambda w: abs(g(w, "steering")))
                    best = (score, pk, swing, inv)
            return best

        def lockup_origin(sl):
            best = None; win = []
            for s in sl:
                win.append(s)
                if len(win) > 15:
                    win.pop(0)
                brake = g(s, "brake"); spd = g(s, "speed_kmh")
                if brake < 0.6 or spd < 50:
                    continue
                drop = max(g(w, "speed_kmh") for w in win) - spd
                if best is None or drop > best[0]:
                    best = (drop, s, brake)
            return best

        lines.append("")
        lines.append("Bestaetigte Flatspots (LMU mFlat) & wahrscheinlicher Ursprung:")
        for p, name, lap, dist in sorted(flats, key=lambda e: e[0]):
            sl = lookback_slice(p, lap)
            vmax = max((g(x, "speed_kmh") for x in sl), default=0.0)
            vmin = min((g(x, "speed_kmh") for x in sl), default=0.0)
            maxb = max((g(x, "brake") for x in sl), default=0.0)
            lines.append(f"{name} platt ab Lap {lap}, {dist:.0f} m")
            if is_abs_car:
                org = spin_origin(sl)
                if org:
                    _, os_, swing, inv = org
                    lines.append(f"  -> Ursprung (Dreher/Slide): Lap {int(g(os_,'lap_number'))}, ~{g(os_,'lap_dist_m'):.0f} m | "
                                 f"Lenk-Swing {swing:.2f}{' | Runde invalidiert' if inv else ''} | Speed dort {g(os_,'speed_kmh'):.0f} km/h")
                    lines.append(f"     Kontext im Vorlauf: Bremse bis {maxb*100:.0f} % | Speed-Fenster {vmax:.0f}->{vmin:.0f} km/h")
                else:
                    lines.append("  -> kein klares Lenk-Reversal im Vorlauf (evtl. Kontakt/Randstein/Curbing).")
            else:
                org = lockup_origin(sl)
                if org:
                    drop, os_, brake = org
                    lines.append(f"  -> Ursprung (Lockup): Lap {int(g(os_,'lap_number'))}, ~{g(os_,'lap_dist_m'):.0f} m | "
                                 f"Bremse {brake*100:.0f} % | Verzoegerung -{drop:.0f} km/h | Speed dort {g(os_,'speed_kmh'):.0f} km/h")
                else:
                    lines.append("  -> kein klarer Lockup im Vorlauf gefunden.")

        lines.append("")
        lines.append(f"Summe: {len(flats)} bestaetigte(r) Flatspot(s). Ursprung ist eine Heuristik ohne Raddrehzahl-Sensor: "
                     "GT3/ABS ueber groesstes Lenk-Reversal (Dreher/Slide), Nicht-ABS ueber haerteste Bremsung mit staerkster Verzoegerung (Lockup).")
        return lines

    def tire_report_lines(self) -> List[str]:
        lines = ["", "Reifenanalyse 4.4:"]
        if not self.samples:
            lines.append("Keine Reifendaten vorhanden.")
            return lines
        specs = [("VL", "tire_fl"), ("VR", "tire_fr"), ("HL", "tire_rl"), ("HR", "tire_rr")]
        def avg(vals):
            vals = [float(v) for v in vals if math.isfinite(float(v))]
            return sum(vals)/len(vals) if vals else 0.0
        def finite(vals):
            return [float(v) for v in vals if math.isfinite(float(v))]
        lines.append("Reifen | Druck kPa avg/min/max | Druck bar avg | Temp außen/mitte/innen avg °C | Carcass avg °C | Wear/Rest avg % | Spread innen-außen | Flat/ABS | Hinweis")
        for name, prefix in specs:
            pressures = [x for x in finite([getattr(s, f"{prefix}_pressure_kpa", 0.0) for s in self.samples]) if 60.0 <= x <= 350.0]
            out_t = [x for x in finite([getattr(s, f"{prefix}_temp_l_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            mid_t = [x for x in finite([getattr(s, f"{prefix}_temp_c_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            in_t = [x for x in finite([getattr(s, f"{prefix}_temp_r_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            carc = [x for x in finite([getattr(s, f"{prefix}_carcass_c", 0.0) for s in self.samples]) if -20.0 <= x <= 180.0]
            wear = [x for x in finite([getattr(s, f"{prefix}_wear_pct", 0.0) for s in self.samples]) if 0.0 < x <= 100.0]
            p_avg = avg(pressures); p_min = min(pressures or [0.0]); p_max = max(pressures or [0.0])
            out_avg, mid_avg, in_avg = avg(out_t), avg(mid_t), avg(in_t)
            carc_avg, wear_avg = avg(carc), avg(wear)
            temp_avg = (out_avg + mid_avg + in_avg) / 3.0 if any([out_avg, mid_avg, in_avg]) else 0.0
            spread = in_avg - out_avg
            hint = self.tire_setup_hint(out_avg, mid_avg, in_avg, p_avg, wear_avg)
            flat_line = self.flatspot_report_for_prefix(prefix)
            lines.append(f"{name} | {p_avg:.1f}/{p_min:.1f}/{p_max:.1f} | {p_avg/100.0:.2f} | {out_avg:.1f}/{mid_avg:.1f}/{in_avg:.1f} | {carc_avg:.1f} | {wear_avg:.1f} | {spread:+.1f} | {flat_line} | {hint}")
        lines.append("")
        lines.append("Stint-Trend Reifen:")
        n = len(self.samples)
        if n >= 40:
            k = max(10, n // 5)
            first = self.samples[:k]; last = self.samples[-k:]
            for name, prefix in specs:
                def a(block, field):
                    vals = [getattr(s, field, 0.0) for s in block]
                    vals = [float(v) for v in vals if math.isfinite(float(v))]
                    if "pressure_kpa" in field:
                        vals = [v for v in vals if 60.0 <= v <= 350.0]
                    elif "wear_pct" in field:
                        vals = [v for v in vals if 0.0 < v <= 100.0]
                    elif "temp" in field:
                        vals = [v for v in vals if -20.0 <= v <= 180.0]
                    return sum(vals)/len(vals) if vals else 0.0
                p0, p1 = a(first, f"{prefix}_pressure_kpa"), a(last, f"{prefix}_pressure_kpa")
                t0 = (a(first, f"{prefix}_temp_l_c") + a(first, f"{prefix}_temp_c_c") + a(first, f"{prefix}_temp_r_c")) / 3.0
                t1 = (a(last, f"{prefix}_temp_l_c") + a(last, f"{prefix}_temp_c_c") + a(last, f"{prefix}_temp_r_c")) / 3.0
                w0, w1 = a(first, f"{prefix}_wear_pct"), a(last, f"{prefix}_wear_pct")
                lines.append(f"{name}: Druck {p0:.1f}→{p1:.1f} kPa ({p0/100.0:.2f}→{p1/100.0:.2f} bar), Temp {t0:.1f}→{t1:.1f} °C, Wear/Rest {w0:.1f}→{w1:.1f} %")
        else:
            lines.append("Zu wenig Samples für Trend. Für Stint-Trend bitte mindestens 3–5 volle Runden aufzeichnen.")
        lines.append("Hinweis: Grip-Level entfernt. Flat/ABS nutzt echten mFlat-Status, wenn LMU ihn liefert. Klassenlogik: GT3 = ABS-Stress, Hypercar/LMP/GTE = LOCK/LOCK!-Risiko.")
        lines.append("Wear/Rest wird aktuell als Restzustand interpretiert: höher = besser/frischer.")
        return lines

    def lap_report_lines(self) -> List[str]:
        if not self.lap_summaries:
            self.update_laps()
        lines = ["", "Clean-Lap-Analyse:"]
        
        ref_sel = "Importierte Referenz" if self.use_external_reference and self.external_reference else (self.manual_reference_lap or "Auto")
        lines.append(f"Auswahl: Referenz={ref_sel} | Vergleich={self.manual_compare_lap or 'Auto'}")
        official_best = self.lmu_best_lap_from_scoring()
        if official_best > 0:
            lines.append(f"LMU offizielle Bestzeit aus Scoring: {fmt_lap_time(official_best)}")
        if self.reference_lap:
            label = "Session-Referenz" if self.use_external_reference and self.external_reference else "Referenzrunde"
            lines.append(f"{label}: Lap {self.reference_lap.lap_number} | Avg Speed {self.reference_lap.avg_speed:.1f} km/h | Fuel {self.reference_lap.fuel_used_l:.3f} L")
        else:
            lines.append("Referenzrunde: keine gültige komplette Runde erkannt")
        lines.append("Lap | Status | Grund | Samples | Coverage m | Dauer [m]:ss.000 | Max Speed | Avg Speed | Max Brake | Fuel Used")
        for l in self.lap_summaries:
            status = "REFERENZ" if self.reference_lap and l.lap_number == self.reference_lap.lap_number else ("gültig" if l.is_clean else "ausgeschlossen")
            t = self.lap_time_for_report(l)
            lines.append(f"{l.lap_number} | {status} | {l.reason} | {l.samples}/{l.valid_samples} | {l.coverage_m:.1f} | {fmt_lap_time(t)} | {l.max_speed:.1f} | {l.avg_speed:.1f} | {l.max_brake:.3f} | {l.fuel_used_l:.3f}")
        return lines

    def input_metrics_for_lap(self, lap: LapSummary) -> dict:
        """Gas-/Bremsverhalten einer Runde aus vorhandenen Samples ableiten.
        Die CSV zeichnet throttle/brake pro Sample bereits auf; diese Metriken machen daraus Coaching-Signale.
        """
        rows = [s for s in self.samples if s.lap_number == lap.lap_number and not self.is_non_driving_sample(s) and s.speed_kmh > 5]
        rows.sort(key=lambda s: s.timestamp)
        if len(rows) < 20:
            return {
                "lap": lap.lap_number, "max_brake": 0.0, "avg_brake": 0.0, "hard_brakes": 0,
                "brake_release_spikes": 0, "throttle_spikes": 0, "coast_pct": 0.0, "overlap_pct": 0.0,
                "hint": "zu wenig Daten"
            }
        driven = [s for s in rows if s.speed_kmh > 30]
        driven_n = max(1, len(driven))
        brake_vals = [s.brake for s in rows if s.brake > 0.05]
        max_brake = max([s.brake for s in rows] or [0.0])
        avg_brake = sum(brake_vals)/len(brake_vals) if brake_vals else 0.0
        hard_brakes = 0
        in_hard = False
        for s in rows:
            if s.brake > 0.75 and not in_hard:
                hard_brakes += 1; in_hard = True
            elif s.brake < 0.25:
                in_hard = False
        brake_release_spikes = 0
        throttle_spikes = 0
        prev = rows[0]
        for cur in rows[1:]:
            db = cur.brake - prev.brake
            dt = cur.throttle - prev.throttle
            # abrupte Bremslösung während relevanter Bremsphase
            if prev.brake > 0.30 and cur.brake > 0.05 and db < -0.16 and cur.speed_kmh > 40:
                brake_release_spikes += 1
            # zu abrupte Gasannahme aus niedriger Teillast heraus
            if prev.throttle < 0.55 and dt > 0.22 and cur.speed_kmh > 35:
                throttle_spikes += 1
            prev = cur
        coast = sum(1 for s in driven if s.brake < 0.04 and s.throttle < 0.04)
        overlap = sum(1 for s in driven if s.brake > 0.08 and s.throttle > 0.08)
        coast_pct = 100.0 * coast / driven_n
        overlap_pct = 100.0 * overlap / driven_n
        hints = []
        if coast_pct > 14:
            hints.append("viel Rollen")
        elif coast_pct < 5:
            hints.append("direkte Inputs")
        if brake_release_spikes >= 5:
            hints.append("Bremse löst ruppig")
        elif brake_release_spikes <= 1 and max_brake > 0.5:
            hints.append("Bremslösung sauber")
        if throttle_spikes >= 6:
            hints.append("Gasannahme ruppig")
        elif throttle_spikes <= 2:
            hints.append("Gasannahme sauber")
        if overlap_pct > 4:
            hints.append("Gas/Bremse Überlappung")
        if hard_brakes >= 5 and max_brake > 0.90:
            hints.append("viele harte Bremsungen")
        if not hints:
            hints.append("unauffällig")
        return {
            "lap": lap.lap_number, "max_brake": max_brake, "avg_brake": avg_brake, "hard_brakes": hard_brakes,
            "brake_release_spikes": brake_release_spikes, "throttle_spikes": throttle_spikes,
            "coast_pct": coast_pct, "overlap_pct": overlap_pct, "hint": ", ".join(hints)
        }

    def input_coach_rows(self) -> List[dict]:
        if not self.lap_summaries:
            self.update_laps()
        rows = []
        for lap in self.lap_summaries:
            if lap.is_clean:
                rows.append(self.input_metrics_for_lap(lap))
        return rows

    def input_coach_report_lines(self, summary_only: bool = False) -> List[str]:
        rows = self.input_coach_rows()
        lines = ["", "Input-Coach 4.4.15 – Gas-/Bremsverhalten:"]
        lines.append("Throttle und Brake werden pro Sample in der CSV aufgezeichnet. Dieser Abschnitt verdichtet nur gültige, saubere Runden des gelockten Recording-Fahrzeugs.")
        if not rows:
            lines.append("Noch keine gültigen Runden für Input-Coaching erkannt.")
            return lines
        avg_coast = sum(r["coast_pct"] for r in rows)/len(rows)
        avg_overlap = sum(r["overlap_pct"] for r in rows)/len(rows)
        total_release = sum(r["brake_release_spikes"] for r in rows)
        total_throttle = sum(r["throttle_spikes"] for r in rows)
        lines.append(f"Gesamtbild: Rollen Ø {avg_coast:.1f}% | Gas/Bremse-Überlappung Ø {avg_overlap:.1f}% | Bremslöse-Sprünge {total_release} | Gas-Sprünge {total_throttle}")
        if avg_coast > 14:
            focus_line = "Coach-Fokus: Rollenphase reduzieren. Entweder sauber länger bremsen oder früher progressiv ans Gas."
        elif total_release > max(6, len(rows)*3):
            focus_line = "Coach-Fokus: Bremse ruhiger lösen. Nicht abrupt aufmachen, sondern Druck kontrolliert abbauen."
        elif total_throttle > max(6, len(rows)*3):
            focus_line = "Coach-Fokus: Gas progressiver aufbauen, besonders am Kurvenausgang."
        elif avg_overlap > 4:
            focus_line = "Coach-Fokus: Gas/Bremse-Überlappung prüfen. In GT3 mit ABS/TC nur bewusst nutzen, nicht dauerhaft mitschleppen."
        else:
            focus_line = "Coach-Fokus: Inputs wirken grundsätzlich sauber. Nächster Schritt: mit Referenzzonen koppeln."
        lines.append(focus_line)
        lines.append(self.hardware_input_hint(focus_line, rows))
        if summary_only:
            return lines
        lines.append("")
        lines.append("Lap | Max Bremse | Ø Bremse | Hartbremsungen | Bremslöse-Sprünge | Gas-Sprünge | Rollen % | Überlapp % | Hinweis")
        for r in rows:
            lines.append(f"{r['lap']} | {r['max_brake']:.3f} | {r['avg_brake']:.3f} | {r['hard_brakes']} | {r['brake_release_spikes']} | {r['throttle_spikes']} | {r['coast_pct']:.1f} | {r['overlap_pct']:.1f} | {r['hint']}")
        lines.append("")
        lines.append("Hinweis: Das ist Fahrinput-Coaching, keine Fahrzeugphysik-Wahrheit. Die Werte werden später mit Trackmap-/Problemzonen kombiniert.")
        return lines

    def update_input_coach(self):
        if not hasattr(self, "input_table"):
            return
        rows = self.input_coach_rows()
        self.input_table.setRowCount(0)
        for r in rows:
            row = self.input_table.rowCount(); self.input_table.insertRow(row)
            vals = [
                f"Lap {r['lap']}", f"{r['max_brake']:.3f}", f"{r['avg_brake']:.3f}", str(r['hard_brakes']),
                str(r['brake_release_spikes']), str(r['throttle_spikes']), f"{r['coast_pct']:.1f}", f"{r['overlap_pct']:.1f}", r['hint']
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter if c < 8 else Qt.AlignLeft | Qt.AlignVCenter)
                if c == 6 and r['coast_pct'] > 14:
                    item.setBackground(QColor(160, 100, 70, 150))
                elif c == 4 and r['brake_release_spikes'] >= 5:
                    item.setBackground(QColor(160, 100, 70, 150))
                elif c == 5 and r['throttle_spikes'] >= 6:
                    item.setBackground(QColor(160, 100, 70, 150))
                elif c == 7 and r['overlap_pct'] > 4:
                    item.setBackground(QColor(160, 100, 70, 150))
                self.input_table.setItem(row, c, item)
        self.input_table.resizeColumnsToContents()
        if hasattr(self, "input_coach_text"):
            self.input_coach_text.setPlainText("\n".join(self.input_coach_report_lines(summary_only=True)))

    def segment_report_lines(self) -> List[str]:
        lines = ["", "Interne Mini-Sektor-Analyse 50 m:"]
        lines.append("Hinweis: 50-m-Sektoren bleiben intern für Vergleich, Heatmap und Coach-Zonen. Der Report zeigt sie nicht mehr vollständig, damit die Auswertung lesbar bleibt.")
        lines.append("Für Rohdaten bitte die CSV verwenden. Sichtbar priorisiert werden Runden und Coach-Zonen.")
        return lines

    def gemini_config_load(self) -> dict:
        try:
            if GEMINI_CONFIG_PATH.exists():
                return json.loads(GEMINI_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def apply_gemini_config(self):
        cfg = self.gemini_config_load()
        self.gemini_api_key = cfg.get("api_key", "")

    def gemini_generate(self, prompt: str, system: str = None, timeout: int = 30) -> str:
        # Direkter REST-Call an die Gemini-API ueber urllib (kein SDK). Modell fest: GEMINI_MODEL.
        key = (getattr(self, "gemini_api_key", "") or "").strip()
        if not key:
            raise RuntimeError("Kein Gemini API-Key gesetzt.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-goog-api-key", key)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if getattr(self, "quota_tracker", None) is not None:
                # e.reason statt e.read(): Body bleibt fuer den aeusseren Handler lesbar
                self.quota_tracker.record(http_status=e.code, error_body=str(getattr(e, "reason", "")))
            raise
        if getattr(self, "quota_tracker", None) is not None:
            self.quota_tracker.record(usage_metadata=payload.get("usageMetadata"), http_status=200)
        cands = payload.get("candidates", [])
        if not cands:
            raise RuntimeError("Keine Antwort (evtl. Sicherheitsfilter oder Kontingent).")
        parts = cands[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or "(leere Antwort)"

    def open_gemini_window(self):
        if getattr(self, "gemini_window", None) is None:
            self.gemini_window = GeminiWindow(self)
        self.gemini_window.show()
        self.gemini_window.raise_()
        self.gemini_window.activateWindow()

    def select_fahrer_hardware_view(self):
        # Ansicht auf "Fahrer & Hardware" umschalten (ueber das Nav-Dropdown, damit es synchron bleibt).
        target = None
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Fahrer & Hardware":
                target = i
                break
        if target is None:
            return
        if hasattr(self, "nav_combo"):
            from PySide6.QtCore import Qt as _Qt
            for i in range(self.nav_combo.count()):
                if self.nav_combo.itemData(i, _Qt.UserRole) == target:
                    self.nav_combo.setCurrentIndex(i)
                    return
        self.tabs.setCurrentIndex(target)

    def build_report(self) -> str:
        lines = [
            "PitBoss – Dashboard/Referenz Report",
            f"Version: {APP_VERSION}",
            f"Zeitpunkt: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "Quelle: LMU_Data Shared Memory mit pyLMUSharedMemory-Strukturdefinitionen.",
            "SimHub wird nicht benötigt. Trackmap basiert auf pos_x/pos_z, Segmentierung auf lap_dist_m.",
            "Clean-Lap-Filter: Standphase/Pit/Outlap werden entfernt. 0.4.5.4 nutzt vereinfachte Rundenansicht, externe Referenzrunden, klassenbasierte Import-Warnungen, lesbaren Report, besser sichtbares Logo/UI, Sicherheitsfilter gegen unplausible Vergleichsrunden, Monitor-Overlay mit Live-Vergleich ohne Recording, automatischen Bestlap-Export, Live-Bestlap-Puffer, Hotkeys F6/F7/F8/F9/F10, Windows-only Polling gegen Doppeltrigger, Reifendaten, separates Reifen-Overlay mit eigenem Button und F6-Hotkey, Reifenanalyse mit Druck in kPa/bar, Innen/Mitte/Außen-Temperaturen, Spread-/Sturzhinweisen, Stint-Trend, Reifen-/Setup-Coach, manuelle Setup-Dokumentation, Rundenübersicht, Input-Coach für Gas/Bremse, Fahrzeug-Lock, Pit-/Standfilter, Reifen-Nullfilter, klassenbasierte ABS/Lockup/Flatspot-Logik, Fahrer-/Hardwareprofile per Dropdown, mehrere Buttonboxen, vollständiger Hardware-Reportblock mit Settings-Screenshot-Basis und neuen Fahr-Limit-Coach für konservativ/sauber/am Limit/überfahren und PB-Bereich aus importierter LMU-Zeitenreferenz.",
            f"Gewähltes Setup: {self.selected_setup_label()}",
            f"Fahrer-/Hardware-Profil: {self.hardware_profile_summary()}",
            f"Externe Referenz: {self.external_reference_label() if self.external_reference else 'nicht geladen'}",
            f"Auto-Bestlap-Export: {'AN' if self.auto_bestlap_export_enabled else 'AUS'} | Live-Puffer: {'AN' if self.auto_bestlap_live_mode else 'AUS'}" + (f" | Lap {self.auto_bestlap_lap_number} | {fmt_lap_time(self.auto_bestlap_time_s)} | {self.auto_bestlap_export_path}" if self.auto_bestlap_export_path else ""),
            "Hotkeys: F6 Reifen-Overlay | F7 Auto-Bestlap AN/AUS | F8 Recording Start/Stop | F9 Snapshot | F10 Coach-Overlay | Windows: nur Polling, keine parallelen App-Shortcuts",
            "Windows-Global-Hotkeys: F6/F7/F8/F9/F10 werden zusätzlich per Tastatur-Polling erkannt. 4.2.6 entkoppelt App-Shortcut und Polling gegen Doppeltrigger.",
            f"Samples: {len(self.samples)}",
            ("Aufnahmetyp: Kurzaufnahme/Snapshot" if len(self.samples) < 100 else "Aufnahmetyp: Session/Recording"),
            f"Recording-Fahrzeug-Lock: {self.sample_vehicle_label(self.recording_signature) if self.recording_signature else 'nicht aktiv/kein Lock'}",
            f"Verworfene Samples wegen Fahrzeug-/Klassenwechsel/ungültig: {self.rejected_sample_count}",
            "",
        ]
        # 4.4.25: Der vollständige Hardware-/Screenshot-Block gehört immer in den Report,
        # auch bei Snapshot/Kurzaufnahme ohne Samples. Das macht die Reports für spätere
        # KI-Auswertung und Team-Vergleiche vollständig.
        lines += self.hardware_report_lines()
        if self.samples:
            last = self.samples[-1]
            lines += [
                "Letzter Sample:",
                self.sample_summary(last),
                "",
                "Min/Max:",
                f"Speed km/h: {min(s.speed_kmh for s in self.samples):.2f} – {max(s.speed_kmh for s in self.samples):.2f}",
                f"Fuel L: {min(s.fuel_l for s in self.samples):.3f} – {max(s.fuel_l for s in self.samples):.3f}",
                f"RPM: {min(s.rpm for s in self.samples):.0f} – {max(s.rpm for s in self.samples):.0f}",
                f"Throttle: {min(s.throttle for s in self.samples):.3f} – {max(s.throttle for s in self.samples):.3f}",
                f"Brake: {min(s.brake for s in self.samples):.3f} – {max(s.brake for s in self.samples):.3f}",
                f"Steering: {min(s.steering for s in self.samples):.5f} – {max(s.steering for s in self.samples):.5f}",
                f"Track m: {min(s.lap_dist_m for s in self.samples):.1f} – {max(s.lap_dist_m for s in self.samples):.1f}",
            ]
            lines += self.tire_report_lines()
            lines += self.flatspot_event_log_lines()
            lines += ["", "Reifen-/Setup-Coach 4.4:"] + self.tire_setup_coach_lines()[1:]
            lines += self.timing_probe_report_lines()
            lines += self.personal_laptime_reference_report_lines()
            lines += self.lap_report_lines()
            lines += self.input_coach_report_lines()
            lines += self.segment_report_lines()
            lines += self.lap_compare_report_lines()
            lines += self.heatmap_report_lines()
            lines += self.limit_coach_report_lines()
            lines += self.coach_report_lines()
            lines += [
                "",
                "Samples-Auszug:",
                "Hinweis: Report zeigt nur die ersten 10 und letzten 10 Samples. Die vollständigen Daten stehen in der CSV.",
            ]
            head = self.samples[:10]
            tail = self.samples[-10:] if len(self.samples) > 20 else []
            for smp in head:
                lines.append(self.sample_summary(smp))
            if tail:
                lines.append(f"... {len(self.samples) - 20} Samples ausgelassen ...")
                for smp in tail:
                    lines.append(self.sample_summary(smp))
        return "\n".join(lines)

    def save_report(self):
        # 4.2.4: Direkt speichern statt Dateidialog. Der Dialog war auf manchen Systemen unzuverlässig.
        default = REPORT_DIR / f"lmu_live_recorder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        if self.safe_save_report_to_path(default):
            self.status.setText(f"Report gespeichert: {default}")
        else:
            QMessageBox.warning(self, "Report speichern", f"Report konnte nicht gespeichert werden. Fehler: {self.last_report_save_error or 'unbekannt'}\nZiel: {default}")

    def write_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "timestamp", "game_version", "track", "player_name", "active_vehicles", "player_idx", "player_has_vehicle",
                "telem_id", "scoring_id", "vehicle_name", "vehicle_model", "vehicle_class", "speed_kmh", "gear", "rpm",
                "fuel_l", "fuel_capacity_l", "throttle", "brake", "steering", "pos_x", "pos_y", "pos_z",
                "lap_number", "completed_laps", "lap_dist_m", "current_lap_time", "last_lap_time", "best_lap_time",
                "lap_invalidated", "in_pits", "place",
                "tire_fl_pressure_kpa", "tire_fr_pressure_kpa", "tire_rl_pressure_kpa", "tire_rr_pressure_kpa",
                "tire_fl_temp_l_c", "tire_fl_temp_c_c", "tire_fl_temp_r_c",
                "tire_fr_temp_l_c", "tire_fr_temp_c_c", "tire_fr_temp_r_c",
                "tire_rl_temp_l_c", "tire_rl_temp_c_c", "tire_rl_temp_r_c",
                "tire_rr_temp_l_c", "tire_rr_temp_c_c", "tire_rr_temp_r_c",
                "tire_fl_carcass_c", "tire_fr_carcass_c", "tire_rl_carcass_c", "tire_rr_carcass_c",
                "tire_fl_wear_pct", "tire_fr_wear_pct", "tire_rl_wear_pct", "tire_rr_wear_pct",
                "tire_fl_pressure_bar", "tire_fr_pressure_bar", "tire_rl_pressure_bar", "tire_rr_pressure_bar",
                "tire_fl_flat", "tire_fr_flat", "tire_rl_flat", "tire_rr_flat",
                "tire_fl_grip_fract", "tire_fr_grip_fract", "tire_rl_grip_fract", "tire_rr_grip_fract",
                "tire_fl_flatspot_status", "tire_fr_flatspot_status", "tire_rl_flatspot_status", "tire_rr_flatspot_status"
            ])
            for s in self.samples:
                w.writerow([
                    s.timestamp, s.game_version, s.track, s.player_name, s.active_vehicles, s.player_idx, int(s.player_has_vehicle),
                    s.telem_id, s.scoring_id, s.vehicle_name, s.vehicle_model, s.vehicle_class, f"{s.speed_kmh:.6f}", s.gear,
                    f"{s.rpm:.6f}", f"{s.fuel_l:.6f}", f"{s.fuel_capacity_l:.6f}", f"{s.throttle:.6f}",
                    f"{s.brake:.6f}", f"{s.steering:.6f}", f"{s.pos_x:.6f}", f"{s.pos_y:.6f}", f"{s.pos_z:.6f}",
                    s.lap_number, s.completed_laps, f"{s.lap_dist_m:.6f}", f"{s.current_lap_time:.6f}",
                    f"{s.last_lap_time:.6f}", f"{s.best_lap_time:.6f}", int(s.lap_invalidated), int(s.in_pits), s.place,
                    f"{s.tire_fl_pressure_kpa:.6f}", f"{s.tire_fr_pressure_kpa:.6f}", f"{s.tire_rl_pressure_kpa:.6f}", f"{s.tire_rr_pressure_kpa:.6f}",
                    f"{s.tire_fl_temp_l_c:.6f}", f"{s.tire_fl_temp_c_c:.6f}", f"{s.tire_fl_temp_r_c:.6f}",
                    f"{s.tire_fr_temp_l_c:.6f}", f"{s.tire_fr_temp_c_c:.6f}", f"{s.tire_fr_temp_r_c:.6f}",
                    f"{s.tire_rl_temp_l_c:.6f}", f"{s.tire_rl_temp_c_c:.6f}", f"{s.tire_rl_temp_r_c:.6f}",
                    f"{s.tire_rr_temp_l_c:.6f}", f"{s.tire_rr_temp_c_c:.6f}", f"{s.tire_rr_temp_r_c:.6f}",
                    f"{s.tire_fl_carcass_c:.6f}", f"{s.tire_fr_carcass_c:.6f}", f"{s.tire_rl_carcass_c:.6f}", f"{s.tire_rr_carcass_c:.6f}",
                    f"{s.tire_fl_wear_pct:.6f}", f"{s.tire_fr_wear_pct:.6f}", f"{s.tire_rl_wear_pct:.6f}", f"{s.tire_rr_wear_pct:.6f}",
                    f"{s.tire_fl_pressure_kpa/100.0:.6f}", f"{s.tire_fr_pressure_kpa/100.0:.6f}", f"{s.tire_rl_pressure_kpa/100.0:.6f}", f"{s.tire_rr_pressure_kpa/100.0:.6f}",
                    int(s.tire_fl_flat), int(s.tire_fr_flat), int(s.tire_rl_flat), int(s.tire_rr_flat),
                    f"{s.tire_fl_grip_fract:.6f}", f"{s.tire_fr_grip_fract:.6f}", f"{s.tire_rl_grip_fract:.6f}", f"{s.tire_rr_grip_fract:.6f}",
                    self.flatspot_status(s.tire_fl_flat, s.tire_fl_grip_fract, s.brake, s.speed_kmh),
                    self.flatspot_status(s.tire_fr_flat, s.tire_fr_grip_fract, s.brake, s.speed_kmh),
                    self.flatspot_status(s.tire_rl_flat, s.tire_rl_grip_fract, s.brake, s.speed_kmh),
                    self.flatspot_status(s.tire_rr_flat, s.tire_rr_grip_fract, s.brake, s.speed_kmh)
                ])
    def save_csv(self):
        # 4.2.4: Direkt speichern statt Dateidialog, passend zum Auto-Save.
        default = CSV_DIR / f"lmu_live_recorder_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if self.safe_save_csv_to_path(default):
            self.status.setText(f"CSV gespeichert: {default}")
        else:
            QMessageBox.warning(self, "CSV speichern", f"CSV konnte nicht gespeichert werden. Siehe Log. Ziel: {default}")

    def closeEvent(self, event):  # 0.5.9.26: Live-Log beim Beenden sauber schliessen
        if getattr(self, "live_log_enabled", False):
            self.stop_live_log()
        super().closeEvent(event)


def main():
    try:
        qInstallMessageHandler(qt_message_filter)
    except Exception:
        pass
    app = QApplication(sys.argv)
    # 0.4.5.2: Einige Windows/Qt-Kombinationen liefern einen Default-Font
    # mit pointSize -1. Das ist lauffähig, erzeugt aber eine CMD-Warnung.
    # Wir setzen deshalb nur bei ungültiger Größe einen sicheren Default.
    try:
        f = app.font()
        if f.pointSize() <= 0:
            f.setPointSize(10)
            app.setFont(f)
    except Exception:
        pass
    w = Main(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
