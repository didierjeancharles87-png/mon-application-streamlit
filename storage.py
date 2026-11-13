"""
Storage — fitahirizana ny angona, cache, ary ny «backup» ho an'ny
"Rapport École du Sabbat".

Fandrafana:
    data/sabata.csv    → ny angona isaky ny Sabata (isaky ny daty × classe)
    data/classes.json  → ny classe, mpampianatra sy isa voasoratra
    backups/           → ny «backup» automatika (daty sy ora ao amin'ny anaran'ny folder)

Ny cache (`st.cache_data`) dia voamarina amin'ny «mtime» ny rakitra:
raha miova ny rakitra dia miova ny cache avy hatrany, ka ny angona vaovao
dia hitranga avy hatrany. Mba feno aza, dia atontay ny cache ihany ko
(`invalidate_cache()`) rehefa manoratra.
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------- konfig ===
BASE_DIR = Path(__file__).resolve().parent
# Azo ovaina amin'ny variable d'environnement (ampiasaina amin'ny teste)
DATA_DIR = Path(os.environ.get("RAPPORT_DATA_DIR") or (BASE_DIR / "data"))
F_DATA = DATA_DIR / "sabata.csv"
F_CLS = DATA_DIR / "classes.json"
BACKUP_DIR = Path(os.environ.get("RAPPORT_BACKUP_DIR") or (BASE_DIR / "backups"))
WEEKLY_MARKER = BACKUP_DIR / ".last_weekly.json"

# Ny tsalaha (schema) — mitovy amin'ny app.py taloha
FIELDS = {
    "tonga_tsy_tara": "Membres tonga TSY TARA",
    "tonga_tara": "Membres tonga TARA",
    "mpamangy": "Mpamangy",
    "asa_soa": "Asa soa natao",
    "fampianarana_baiboly": "Fampianarana Baiboly natao",
    "boky_trakta": "Boky na trakta nozaraina",
    "seminera": "Seminera na Kaonferansa natao",
    "ala_sarona": "Fampianarana Baiboly an-taratasy ALA SARONA",
    "ala_sarona_vita": "Nahavita fampianarana an-taratasy",
    "batisa": "Batisa vokatry ny Tarika Miasa",
    "fanatitra_mission": "Fanatitra ho an'ny asa maneran-tany",
}
ASA_FITORINA = ["fampianarana_baiboly", "boky_trakta", "seminera",
                "ala_sarona", "ala_sarona_vita", "batisa"]

CSV_COLUMNS = ["daty", "classe"] + list(FIELDS)


# ------------------------------------------------------------------ cache ===
def _stamp(path: Path) -> float:
    """Ny «mtime» ny rakitra — ampiasaina ho «clé» amin'ny cache."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def load_df(path: str, stamp: float = 0.0) -> pd.DataFrame:
    """
    Mamaky ny `sabata.csv`. Cached (`@st.cache_data`).

    Ny «stamp» (mtime ny rakitra) dia ampiasaina ho argumenty: raha miova ny
    rakitra dia miova ny cache avy hatrany — tsy misy angona mihintsy.
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame(columns=CSV_COLUMNS)
    try:
        return pd.read_csv(p)
    except (pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame(columns=CSV_COLUMNS)


@st.cache_data(show_spinner=False)
def load_classes(path: str, stamp: float = 0.0) -> dict:
    """Mamaky ny `classes.json`. Cached (`@st.cache_data`)."""
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def invalidate_cache() -> None:
    """Mamafa ny cache rehetra — ampiasaina rehefa miova ny angona."""
    load_df.clear()
    load_classes.clear()


def read_df() -> pd.DataFrame:
    """Mamaky ny angona (tsy mihintsy ny cache raha efa miova ny rakitra)."""
    return load_df(str(F_DATA), _stamp(F_DATA))


def read_classes() -> dict:
    return load_classes(str(F_CLS), _stamp(F_CLS))


# ------------------------------------------------------------------ writes ===
def save_df(df: pd.DataFrame, *, backup: bool = True, tag: str = "avao_fanovana") -> None:
    """Vonona ny `sabata.csv` (amin'ny backup aloha) dia mamafa ny cache."""
    if backup:
        backup_now(tag)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(F_DATA, index=False)
    invalidate_cache()


def save_classes(classes: dict, *, backup: bool = True, tag: str = "avao_fanovana") -> None:
    """Vonona ny `classes.json` (amin'ny backup aloha) dia mamafa ny cache."""
    if backup:
        backup_now(tag)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    F_CLS.write_text(json.dumps(classes, ensure_ascii=False, indent=1), encoding="utf-8")
    invalidate_cache()


# ---------------------------------------------------------------- backups ===
def _safe_tag(tag: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "_" for c in (tag or "backup").strip().lower()]
    return ("".join(keep) or "backup")[:40]


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def backup_now(tag: str = "manual") -> Path | None:
    """
    Mamorona «backup» misy daty sy ora ao amin'ny `backups/`.

    Tsy mbola ovay ny rakitra taloha raha tsy misy ny «sabata.csv».
    Mamerina ny folder-ny backup (Path) na None raha tsy nisy nafona.
    """
    ensure_backup_dir()
    if not F_DATA.exists() and not F_CLS.exists():
        return None
    now = datetime.now(timezone.utc).astimezone()
    base = f"backup_{now.strftime('%Y%m%d_%H%M%S')}_{_safe_tag(tag)}"
    folder = BACKUP_DIR / base
    n = 2
    while folder.exists():                       # tsy hovana ny backup tehatro
        folder = BACKUP_DIR / f"{base}_{n}"
        n += 1
    folder.mkdir(parents=True)
    manifest = {"created": now.isoformat(timespec="seconds"), "tag": _safe_tag(tag), "files": {}}
    for src, name in ((F_DATA, "sabata.csv"), (F_CLS, "classes.json")):
        if src.exists() and src.stat().st_size > 0:
            shutil.copy2(src, folder / name)
            manifest["files"][name] = {"size": src.stat().st_size,
                                       "modified": datetime.fromtimestamp(
                                           src.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")}
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return folder


def list_backups() -> list[dict]:
    """Mamerina ny lisitry ny backup (vaovao aloha)."""
    if not BACKUP_DIR.exists():
        return []
    out = []
    for folder in sorted(BACKUP_DIR.glob("backup_*"), reverse=True):
        if not folder.is_dir():
            continue
        manifest = {}
        mpath = folder / "manifest.json"
        if mpath.exists():
            try:
                manifest = json.loads(mpath.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
        files = [f.name for f in folder.iterdir() if f.is_file() and f.name != "manifest.json"]
        out.append({
            "name": folder.name,
            "path": folder,
            "created": manifest.get("created", ""),
            "tag": manifest.get("tag", ""),
            "files": files,
            "size": sum((folder / f).stat().st_size for f in files),
        })
    return out


def backup_zip_bytes(names: list[str] | None = None) -> bytes:
    """Manoratra ny backup rehetra (na ny voalohany) ao amin'ny ZIP azo alaina."""
    buf = BytesIO()
    folders = [b["path"] for b in list_backups() if names is None or b["name"] in names]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in folders:
            for f in folder.iterdir():
                if f.is_file():
                    z.write(f, arcname=f"{folder.name}/{f.name}")
    return buf.getvalue()


def restore_backup(name: str) -> tuple[bool, str]:
    """
    Mametraka ny backup indray. Misy «backup» aloha ny angona ankehitriny
    (mba azo averina), avy e dia ampiditra ny rakitra.
    """
    folder = BACKUP_DIR / name
    if not folder.is_dir():
        return False, f"Tsy misy ny backup «{name}»."
    src_data, src_cls = folder / "sabata.csv", folder / "classes.json"
    if not src_data.exists() and not src_cls.exists():
        return False, "Tsy misy angona ao amin'ity backup ity."
    backup_now("avao_restauration")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if src_data.exists():
        shutil.copy2(src_data, F_DATA)
    if src_cls.exists():
        shutil.copy2(src_cls, F_CLS)
    invalidate_cache()
    return True, f"Voaresta ny angona avy amin'ny backup «{name}»."


def weekly_backup_if_needed(interval_days: int = 7) -> Path | None:
    """
    Manao «backup» iray isam-bolana (raha mbola tsy natao ny 7 andro farany).
    Ampiasaina rehefa manomboka ny app.
    """
    ensure_backup_dir()
    marker = {}
    if WEEKLY_MARKER.exists():
        try:
            marker = json.loads(WEEKLY_MARKER.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            marker = {}
    last = marker.get("date")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if datetime.now(timezone.utc) - last_dt < timedelta(days=interval_days):
                return None
        except ValueError:
            pass
    folder = backup_now("hebdomadaire")
    WEEKLY_MARKER.write_text(json.dumps({"date": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    return folder


def last_weekly_backup_date() -> str:
    if not WEEKLY_MARKER.exists():
        return ""
    try:
        return json.loads(WEEKLY_MARKER.read_text(encoding="utf-8")).get("date", "")
    except (OSError, json.JSONDecodeError):
        return ""
