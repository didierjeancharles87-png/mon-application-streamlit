"""
test_app.py — fanamarinana ny "Rapport École du Sabbat".

Fandefasana:
    python test_app.py          # mandeha ny teste rehetra
    python test_app.py -v       # misy antsipiriany raha misy lesoka

Ny teste dia miasa amin'ny angona KOPIANY (dossier tampon) — ny angona
velona ao amin'ny `data/` dia tsy miova.

Voamarina:
    - ny app dia manomboka ary mampiseho ny pejy fidirana (tsy misy dashboard
      raha tsy voasoratra ny mpampiana)
    - fidirana: password tsy mety, password mety, fivoahana
    - ny pejy 7 rehetra dia miasa
    - famoronana / fanovana / fafana ny angona (cache dia mava)
    - backup + restauration
    - export PDF + PowerPoint
    - hashing PBKDF2, fanandramana ny fidirana
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent

# --- Angona tampon: ny teste dia tsy mikasika ny angona velona -----------
TMP = Path(tempfile.mkdtemp(prefix="rapport_test_"))
shutil.copytree(BASE / "data", TMP / "data", dirs_exist_ok=True)
os.environ["RAPPORT_DATA_DIR"] = str(TMP / "data")
os.environ["RAPPORT_BACKUP_DIR"] = str(TMP / "backups")

sys.path.insert(0, str(BASE))

import auth  # noqa: E402
import storage  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = BASE / "app.py"
TEST_USER = "admin_test"
TEST_PWD = "MotDePasse2026!"
ADMIN_SESSION = {"username": TEST_USER, "role": "admin", "login_at": ""}

# Mpampiana test (ao amin'ny angona tampon ihany)
_ok, _msg = auth.create_user(TEST_USER, TEST_PWD, role="admin")
if not _ok:
    print(f"⚠️  {_msg}")


# --------------------------------------------------------------- helpers ---
def new_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=120).run()


def run_page(fn: str, authed: bool = True) -> AppTest:
    """Mandeha ny pejy iray (function) — misy exception ve?"""
    code = f"import sys; sys.path.insert(0, {str(BASE)!r}); import app; app.{fn}()"
    at = AppTest.from_string(code, default_timeout=120)
    if authed:
        at.session_state["auth_user"] = dict(ADMIN_SESSION)
    at.run()
    return at


def button_by_label(at: AppTest, label: str):
    for b in at.button:
        if label.lower() in (b.label or "").lower():
            return b
    raise AssertionError(f"Tsy hita ny bouton «{label}»: {[b.label for b in at.button]}")


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def login(at: AppTest, user: str = TEST_USER, pwd: str = TEST_PWD) -> AppTest:
    """Manao ny fidirana amin'ny alalan'ny pejy fidirana."""
    at.text_input(key="login_user").set_value(user)
    at.text_input(key="login_password").set_value(pwd)
    at.form_submit_button[0].click().run()
    return at


# ---------------------------------------------------------------- tests ---
def test_app_mandeha():
    at = new_app()
    check(not at.exception, f"Exception: {[e.value for e in at.exception]}")
    check(at.title, "Tsy misy lohateny (pejy fidirana).")
    check("Rapport École du Sabbat" in at.title[0].value, "Tsy misy ny anaran'ny app.")
    check(not at.dataframe, "Misy tabelle mihintsy tsy voasoratra ny mpampiana!")
    check(not getattr(at.sidebar, "page_link", []), "Misy menu raha tsy voasoratra ny mpampiana!")
    check(at.text_input(key="login_user"), "Tsy misy ny toerana anaran'ny mpampiana.")
    check(at.image, "Tsy misy ny logo ao amin'ny pejy fidirana.")


def test_login_password_tsy_mety():
    at = new_app()
    at.text_input(key="login_user").set_value(TEST_USER)
    at.text_input(key="login_password").set_value("password-tsy-mety")
    at.form_submit_button[0].click().run()
    check(not at.exception, f"Exception: {[e.value for e in at.exception]}")
    check(at.error, "Tsy misy hafatra d'iditra diso.")
    check(not at.session_state.get("auth_user"), "Niditra nefa diso ny password!")


def test_login_mety_ary_fivoahana():
    at = new_app()
    at = login(at)
    check(not at.exception, f"Exception: {[e.value for e in at.exception]}")
    check(at.session_state.get("auth_user"), "Tsy voasoratra ny mpampiana.")
    check(at.session_state["auth_user"]["username"] == TEST_USER, "Diso ny anaran'ny mpampiana.")
    check(at.sidebar.page_link, "Tsy misy menu rehefa voasoratra.")
    at.sidebar.button[0].click().run()
    check(not at.exception, f"Exception rehefa fivoahana: {[e.value for e in at.exception]}")
    check(not at.session_state.get("auth_user"), "Mbola voasoratra ny mpampiana aorian'ny fivoahana.")
    check(not at.dataframe, "Misy angona aorian'ny fivoahana!")


def test_pejy_rehetra_miasa():
    at = new_app()
    at = login(at)
    check(not at.exception, f"Exception: {[e.value for e in at.exception]}")
    for fn in ("page_classe", "page_fampidirana", "page_rapport_classe", "page_totaly_top3",
               "page_fanondranana", "page_angona", "page_administration"):
        p = run_page(fn)
        check(not p.exception, f"Exception ao amin'ny {fn}: {[e.value for e in p.exception]}")
        check(p.title, f"Tsy misy lohateny ny pejy {fn}.")


def test_kajy_voatahiry():
    """Ny kajy dia mitovy amin'ny app taloha (tsy miova ny logika)."""
    import pandas as pd
    d = pd.DataFrame([{"daty": "2026-11-08", "classe": "Classe 1", "tonga_tsy_tara": 10,
                        "tonga_tara": 5, "mpamangy": 2, "asa_soa": 1, "fampianarana_baiboly": 2,
                        "boky_trakta": 3, "seminera": 1, "ala_sarona": 1, "ala_sarona_vita": 1,
                        "batisa": 1, "fanatitra_mission": 100.0}])
    import app
    c = app.calc(d).iloc[0]
    check(c.mambra_tonga == 15, "mambra_tonga diso.")
    check(c.isan_tonga == 17, "isan_tonga diso.")
    check(c.asa_fitorina == 9, "asa_fitorina diso.")
    check(abs(c["tsy_tara_%"] - 66.7) < 0.1, "tsy_tara_% diso.")
    g = app.fitambarana(d)
    check(g.loc["TOTALY", "tonga_tsy_tara"] == 10, "TOTALY diso.")


def test_fampidirana_ary_fafana_classe():
    p = run_page("page_classe")
    check(p.text_input, "Tsy misy ny formulaire fampidirana ny classe.")
    p.text_input[0].set_value("Classe Test")
    p.text_input[1].set_value("Mpampianatra Test")
    p.form_submit_button[0].click().run()
    check(not p.exception, f"Exception: {[e.value for e in p.exception]}")
    check("Classe Test" in storage.read_classes(), "Tsy voatahiry ny classe vaovao.")
    check(storage.list_backups(), "Tsy nisy backup talohan'ny fanovana!")

    p2 = run_page("page_classe")
    p2.selectbox[0].select("Classe Test").run()
    button_by_label(p2, "Fafao").click().run()
    check(not p2.exception, f"Exception rehefa fafana: {[e.value for e in p2.exception]}")
    check("Classe Test" not in storage.read_classes(), "Tsy voafafa ny classe.")


def test_cache_mava_ao_amin_ny_fampidirana():
    p = run_page("page_fampidirana")
    check(not p.exception, f"Exception: {[e.value for e in p.exception]}")
    n_before = len(storage.read_df())
    p.number_input[0].set_value(7)
    p.form_submit_button[0].click().run()
    check(not p.exception, f"Exception: {[e.value for e in p.exception]}")
    check(p.success, "Tsy nisy hafatra fahombiazana.")
    df = storage.read_df()
    check(len(df) == n_before + 1, "Tsy mitovy ny isa ny andalana (cache mbola tsy mava!).")
    check(int(df.iloc[-1]["tonga_tsy_tara"]) == 7, "Tsy voatahiry ny isa voampiditra.")


def test_backup_ary_restauration():
    folder = storage.backup_now("test")
    check(folder and folder.exists(), "Tsy nisy backup.")
    check((folder / "sabata.csv").exists(), "Tsy misy sabata.csv ao amin'ny backup.")
    check((folder / "classes.json").exists(), "Tsy misy classes.json ao amin'ny backup.")
    check(any(b["name"] == folder.name for b in storage.list_backups()),
          "Tsy hita ao amin'ny lisitry ny backup.")
    check(len(storage.backup_zip_bytes()) > 100, "Tsy misy ZIP.")

    # Manova ny angona dia averina amin'ny backup
    df = storage.read_df()
    storage.save_df(df, tag="test_modif", backup=False)
    ok, msg = storage.restore_backup(folder.name)
    check(ok, f"Tsy voaresta: {msg}")
    check(len(storage.read_df()) == len(df), "Tsy mitovy ny isa aorian'ny restauration.")
    check(storage.list_backups(), "Tsy nisy backup 'avao_restauration'.")


def test_export_pdf_pptx():
    p = run_page("page_fanondranana")
    check(not p.exception, f"Exception: {[e.value for e in p.exception]}")
    button_by_label(p, "Alamino").click().run()
    check(not p.exception, f"Exception rehefa alamina: {[e.value for e in p.exception]}")
    check(p.session_state.get("pdf"), "Tsy misy PDF.")
    check(p.session_state.get("pptx"), "Tsy misy PowerPoint.")
    check(len(p.session_state["pdf"]) > 1000, "PDF loatra malemy.")
    check(len(p.session_state["pptx"]) > 1000, "PPTX loatra malemy.")


def test_auth_module():
    rec = auth.hash_password(TEST_PWD)
    check(TEST_PWD not in str(rec), "Misy ny password en clair ao amin'ny hash!")
    check(auth.verify_password(TEST_PWD, rec), "Tsy mety ny verification.")
    check(not auth.verify_password("hafa", rec), "Mety ny password hafa!")
    ok, msg = auth.authenticate(TEST_USER, "hatsapana")
    check(not ok, "Niditra ny password diso!")
    ok, msg = auth.set_password(TEST_USER, "PasswordVaovao2026!")
    check(ok, msg)
    check(auth.authenticate(TEST_USER, "PasswordVaovao2026!")[0], "Tsy mety ny password vaovao.")
    check(not auth.authenticate(TEST_USER, TEST_PWD)[0], "Mbola mety ny password taloha!")
    auth.set_password(TEST_USER, TEST_PWD)
    # Mpampiana tsy misy: hafatra mitovy (tsy hitahiana ny anarana)
    ok, msg = auth.authenticate("tsy-misy", "whatever")
    check(not ok and "tsy mety" in msg.lower(), "Hafatra hafahafa: " + msg)


def test_fanandramana_fidirana():
    """Rehefa betsaka ny fanadramana dia voahidy ny fidirana."""
    user = "admin_lock"
    auth.create_user(user, "MotDePasse2026!")
    for _ in range(5):
        auth.authenticate(user, "diso")
    remaining = auth.lock_seconds_remaining(user)
    check(remaining > 0, "Tsy voahidy ny fidirana aorian'ny 5 fanadramana.")
    ok, msg = auth.authenticate(user, "MotDePasse2026!")
    check(not ok, "Niditra na dia voahidy aza!")
    check("voahidy" in msg.lower(), "Hafatra hafahafa: " + msg)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"✅ {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"❌ {name}: {e}")
            if "-v" in sys.argv:
                traceback.print_exc()
    print("-" * 60)
    print(f"{len(tests) - failed}/{len(tests)} ny teste dia nety.")
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
