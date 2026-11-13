"""
Auth — module d'authentification ho an'ny "Rapport École du Sabbat".

Ny fitahirizana ny momba ny mpampiasa dia ao amin'ny `data/users.json`.
Password dia tsy voatahiry amin'ny tenantsaina mihitsy: voahash PBKDF2-HMAC-SHA256
(salt miaraka amin'ny mpampiasa, 600 000 iterations) ary ny verification dia
constant-time (hmac.compare_digest).

Fampiharana:
    - `python manage_users.py add admin`        (mamporofo mpampianatra)
    - `python manage_users.py passwd admin`     (ovao ny password)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- konfig ===
BASE_DIR = Path(__file__).resolve().parent
# Azo ovaina amin'ny variable d'environnement (ampiasaina amin'ny teste)
DATA_DIR = Path(os.environ.get("RAPPORT_DATA_DIR") or (BASE_DIR / "data"))
USERS_FILE = DATA_DIR / "users.json"
SETUP_FILE = DATA_DIR / "setup_code.json"
SETUP_TXT = DATA_DIR / "setup_code.txt"          # ho an'ny mpitantana (amaiziny)
ATTEMPTS_FILE = DATA_DIR / "login_attempts.json"

ALGO = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000          # OWASP: PBKDF2-HMAC-SHA256
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
MAX_ATTEMPTS = 5                      # fanandramana aorian'ny fanadramana
BASE_LOCK_SECONDS = 60                # mialoha kely
MAX_LOCK_SECONDS = 15 * 60

ROLES = ("admin", "editeur", "lecteur")
ROLE_LABELS = {
    "admin": "Mpitantana (administrateur)",
    "editeur": "Mpampiasa (pe afaka manova angona)",
    "lecteur": "Mpamaky (fijery fotsiny)",
}
# iza no afaka manao ny asa manampy/fafana angona sy mpitantana ny mpampiasa
ROLES_CAN_WRITE = ("admin", "editeur")
ROLES_CAN_ADMIN = ("admin",)


# ------------------------------------------------------------------ utils ===
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    """Ny fotoana ankehitriny (String) — azo ampiasaina avy any amin'ny app."""
    return _stamp()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ----------------------------------------------------------------- hashing ===
def hash_password(password: str, salt: bytes | None = None,
                  iterations: int = DEFAULT_ITERATIONS) -> dict:
    """Mamerina ny{'salt','hash','iterations'} ho an'ny password."""
    if not isinstance(password, str) or not password:
        raise ValueError("Tsy maintsy manana ny password ny string.")
    salt = salt or secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {
        "algo": ALGO,
        "iterations": int(iterations),
        "salt": salt.hex(),
        "hash": dk.hex(),
    }


def verify_password(password: str, record: dict | None) -> bool:
    """Fanamarinana ny password amin'ny fomba constant-time."""
    if not record or not isinstance(record, dict):
        return False
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
        iterations = int(record.get("iterations", DEFAULT_ITERATIONS))
    except (KeyError, ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)


def password_strength(password: str) -> tuple[bool, str]:
    """Mamerina (maty, hafatra) — fanamarinana ny hery ny password."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Ny password dia tokony manana ny {MIN_PASSWORD_LENGTH} hery farafiny."
    if len(password) >= 12 and any(c.isdigit() for c in password) and \
            any(c.isupper() for c in password) and any(not c.isalnum() for c in password):
        return True, "Password mahery vao."
    if len(password) >= MIN_PASSWORD_LENGTH:
        return True, "Password azo ampiasaina (alaina sady lava kely)."
    return False, "Password tsy ampy."


# ------------------------------------------------------------------ users ===
def load_users() -> dict:
    """Mamerina ny dikan'ny mpampiasa: {username: {salt, hash, role, ...}}."""
    data = _read_json(USERS_FILE, {})
    if not isinstance(data, dict):
        return {}
    return data.get("users", {}) if isinstance(data.get("users", {}), dict) else {}


def save_users(users: dict) -> None:
    _write_json(USERS_FILE, {"users": users, "updated": _stamp()})


def users_configured() -> bool:
    """Misy mpampiana voaforona ve (raha tsia dia mila fanombohana)?"""
    return bool(load_users())


def list_users() -> dict:
    return load_users()


def user_exists(username: str) -> bool:
    return username.strip().lower() in load_users()


def create_user(username: str, password: str, role: str = "admin") -> tuple[bool, str]:
    """Mamporoko mpampisa vaovao. Mamerina (ok, hafatra)."""
    username = (username or "").strip()
    if not username:
        return False, "Soraty ny anaran'ny mpampiana."
    if len(username) < 3:
        return False, "Ny anaran'ny mpampiana dia tokony manana ny litera 3 farafiny."
    if any(ch.isspace() for ch in username):
        return False, "Aza ampiasaina ny toerana ao amin'ny anaran'ny mpampiana."
    if role not in ROLES:
        return False, f"Tsy fantatra ny rol: {role}"
    ok, msg = password_strength(password)
    if not ok:
        return False, msg
    users = load_users()
    if username.lower() in {u.lower() for u in users}:
        return False, f"Efa misy ny mpampiana «{username}»."
    users[username] = {
        **hash_password(password),
        "role": role,
        "created": _stamp(),
        "last_login": "",
    }
    save_users(users)
    return True, f"Voaforona ny mpampiana «{username}» ({ROLE_LABELS.get(role, role)})."


def set_password(username: str, password: str, *, role: str | None = None) -> tuple[bool, str]:
    """Ovay ny password (na ny rol) ny mpampiana."""
    users = load_users()
    key = next((u for u in users if u.lower() == (username or "").strip().lower()), None)
    if key is None:
        return False, f"Tsy misy ny mpampiana «{username}»."
    ok, msg = password_strength(password)
    if not ok:
        return False, msg
    rec = users[key]
    users[key] = {**rec, **hash_password(password), "password_changed": _stamp()}
    if role:
        if role not in ROLES:
            return False, f"Tsy fantatra ny rol: {role}"
        users[key]["role"] = role
    save_users(users)
    return True, f"Voaova ny password ny «{key}»."


def delete_user(username: str) -> tuple[bool, str]:
    users = load_users()
    key = next((u for u in users if u.lower() == (username or "").strip().lower()), None)
    if key is None:
        return False, f"Tsy misy ny mpampiana «{username}»."
    if len(users) <= 1:
        return False, "Tsy azo fafana ny mpampiana farany (tsy maintsy misy mihitsy)."
    del users[key]
    save_users(users)
    return True, f"Voafafa ny mpampiana «{key}»."


def get_user(username: str) -> dict | None:
    users = load_users()
    key = next((u for u in users if u.lower() == (username or "").strip().lower()), None)
    return users[key] if key else None


def set_role(username: str, role: str) -> tuple[bool, str]:
    """Ovay ny rol ny mpampiana (tsy miova ny password)."""
    if role not in ROLES:
        return False, f"Tsy fantatra ny rol: {role}"
    users = load_users()
    key = next((u for u in users if u.lower() == (username or "").strip().lower()), None)
    if key is None:
        return False, f"Tsy misy ny mpampiana «{username}»."
    users[key]["role"] = role
    save_users(users)
    return True, f"Voaova ny rol ny «{key}» → {ROLE_LABELS.get(role, role)}."


# ------------------------------------------------- fanandramana ny fidirana ===
def _attempts_state() -> dict:
    data = _read_json(ATTEMPTS_FILE, {})
    return data if isinstance(data, dict) else {}


def _save_attempts(state: dict) -> None:
    _write_json(ATTEMPTS_FILE, state)


def lock_seconds_remaining(username: str) -> int:
    """Misy fanatrehana (sekONDS) ve ny mpampiana — 0 raha tsy voahidy."""
    state = _attempts_state()
    rec = state.get((username or "").lower())
    if not rec:
        return 0
    remaining = float(rec.get("locked_until", 0)) - time.time()
    return int(remaining) if remaining > 0 else 0


def _register_failure(username: str) -> int:
    state = _attempts_state()
    key = (username or "").lower()
    rec = state.get(key, {"fails": 0, "lock_seconds": BASE_LOCK_SECONDS})
    rec["fails"] = int(rec.get("fails", 0)) + 1
    rec["last_try"] = _stamp()
    if rec["fails"] >= MAX_ATTEMPTS:
        lock = min(int(rec.get("lock_seconds", BASE_LOCK_SECONDS)) * 2, MAX_LOCK_SECONDS)
        rec["lock_seconds"] = lock
        rec["locked_until"] = time.time() + lock
        rec["fails"] = 0
    state[key] = rec
    _save_attempts(state)
    return int(rec.get("fails", 0))


def _clear_failures(username: str) -> None:
    state = _attempts_state()
    state.pop((username or "").lower(), None)
    _save_attempts(state)


def authenticate(username: str, password: str) -> tuple[bool, str]:
    """
    Fanamarinana ny fidirana. Mamerina (ok, hafatra).

    Tsy manavany ny hafatra na dia tsy misy ny mpampiana aza (mba tsy ho
    hita ny lisitry ny mpampiana).
    """
    username = (username or "").strip()
    if not username or not password:
        return False, "Soraty ny anaran'ny mpampiana sy ny password."

    remaining = lock_seconds_remaining(username)
    if remaining > 0:
        return False, (f"Voahidy ny fidirana noho ny fanandramana betsaka. "
                       f"Andraso ny {remaining} segondra kely aorian'ny fanandramana farany.")

    rec = get_user(username)
    if rec is None:
        # Hash «dummy» mba hanahana ny fotoana mitovy (tsy hitahiana ny anarana)
        hash_password(password or "x", salt=b"\x00" * SALT_BYTES)
        _register_failure(username)
        return False, "Anarana mpampiana na password tsy mety."

    if not verify_password(password, rec):
        _register_failure(username)
        return False, "Anarana mpampiana na password tsy mety."

    _clear_failures(username)
    users = load_users()
    key = next(u for u in users if u.lower() == username.lower())
    users[key]["last_login"] = _stamp()
    save_users(users)
    return True, "Tongasoa!"


# ----------------------------------------------- code fanombohana (1 indray) ===
def setup_code_needed() -> bool:
    """Mila code fanombohana ve (mpbola tsy misy mpampiana)?"""
    if users_configured():
        return False
    return bool(_read_json(SETUP_FILE, {}).get("code_hash"))


def ensure_setup_code() -> str | None:
    """
    Mamorona code fanombohana indray (raha mbola tsy misy mpampiana) ary
    manoratra azy ao amin'ny terminal-n'ny serveur. Mamerina ny code
    (String) na None raha efa misy mpampiana.
    """
    if users_configured():
        return None
    data = _read_json(SETUP_FILE, {})
    if data.get("code_hash"):
        return None
    code = "-".join(secrets.token_hex(2).upper() for _ in range(4))  # e.g. 1A2B-3C4D-5E6F-7A8B
    rec = hash_password(code)
    _write_json(SETUP_FILE, {
        "code_hash": rec["hash"],
        "salt": rec["salt"],
        "iterations": rec["iterations"],
        "created": _stamp(),
    })
    try:                                   # ho an'ny mpitantana (azo jerena ao amin'ny PC)
        SETUP_TXT.write_text(f"{code}\n", encoding="utf-8")
    except OSError:
        pass
    return code


def verify_setup_code(code: str) -> bool:
    data = _read_json(SETUP_FILE, {})
    if not data.get("code_hash"):
        return False
    rec = {"algo": ALGO, "iterations": data.get("iterations", DEFAULT_ITERATIONS),
           "salt": data["salt"], "hash": data["code_hash"]}
    return verify_password((code or "").strip().upper(), rec)


def clear_setup_code() -> None:
    for p in (SETUP_FILE, SETUP_TXT):
        try:
            p.unlink()
        except OSError:
            pass


def first_run_setup(code: str, username: str, password: str,
                    password2: str) -> tuple[bool, str]:
    """Fanombohana farany: manao ny mpampianatra voalohany amin'ny code."""
    if users_configured():
        return False, "Efa misy mpampiana. Tsy mila fanombohana intsony."
    if not verify_setup_code(code):
        return False, "Tsy mety ny code fanombohana (jereo ny terminal-n'ny serveur)."
    if password != password2:
        return False, "Tsy mitovy ny password roa."
    ok, msg = create_user(username, password, role="admin")
    if not ok:
        return False, msg
    clear_setup_code()
    return True, f"Voaforona ny mpampianatra administrateur «{username.strip()}»."


# ------------------------------------------------------------------ rôles ===
def can_write(role: str) -> bool:
    return role in ROLES_CAN_WRITE


def can_admin(role: str) -> bool:
    return role in ROLES_CAN_ADMIN


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)
