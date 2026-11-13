"""
Rapport École du Sabbat — app locale (Streamlit).

Fandefasana:
    streamlit run app.py

Ny rafitra:
    app.py          → pejy (UI), kajy, ary ny famonjena PDF/PowerPoint
    auth.py         → fidirana (PBKDF2, tsy misy password en clair)
    storage.py      → angona (cache), «backup», ary famerenana
    manage_users.py → fitaovana mpitantana ny mpampiana (command line)
    assets/app.css  → ny endrika (couleurs, boutons, cartes)
    data/           → sabata.csv, classes.json, users.json
    backups/        → «backup» automatika (daty sy ora ao amin'ny anarana)
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.util import Inches, Pt  # noqa: E402
from streamlit import column_config  # noqa: E402

import auth  # noqa: E402
import storage  # noqa: E402
from storage import ASA_FITORINA, FIELDS  # noqa: E402

# ============================== konfig ==============================
BASE_DIR = Path(__file__).resolve().parent
LOGO = BASE_DIR / "logo.png.jpg"
CSS_FILE = BASE_DIR / "assets" / "app.css"
APP_NAME = "Rapport École du Sabbat"
APP_SUBTITLE = "Gestion et suivi des rapports hebdomadaires"
APP_VERSION = "2.1"

NAVY = "#0B2545"
GOLD = "#C28A2B"
STEEL = "#2F6F6B"

SHORT = {"mambra_tonga": "Membres tonga", "tonga_tsy_tara": "Tsy tara", "tonga_tara": "Tara",
         "tsy_tara_%": "Tsy tara %", "mpamangy": "Mpamangy", "isan_tonga": "Isan'ny tonga",
         "asa_soa": "Asa soa", "fampianarana_baiboly": "Baiboly", "boky_trakta": "Boky/trakta",
         "seminera": "Seminera", "ala_sarona": "Ala Sarona", "ala_sarona_vita": "Nahavita",
         "batisa": "Batisa", "fanatitra_mission": "Fanatitra", "asa_fitorina": "ASA FITORINA"}
COLS = ["tonga_tsy_tara", "tonga_tara", "mambra_tonga", "tsy_tara_%", "mpamangy", "isan_tonga", "asa_soa",
        "fampianarana_baiboly", "boky_trakta", "seminera", "ala_sarona", "ala_sarona_vita", "batisa",
        "asa_fitorina", "fanatitra_mission"]
TOP_TSY = ["tonga_tsy_tara", "tonga_tara", "mambra_tonga", "tsy_tara_%"]
TOP_ASA = ASA_FITORINA + ["asa_fitorina"]

st.set_page_config(
    page_title=APP_NAME,
    page_icon=str(LOGO) if LOGO.exists() else "📖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================== endrika =============================
def inject_css() -> None:
    """Mampiditra ny CSS-n'ny app (couleurs, boutons, cartes)."""
    try:
        css = CSS_FILE.read_text(encoding="utf-8")
    except OSError:
        return
    st.html(f"<style>{css}</style>")


def page_header(title: str, subtitle: str, icon: str) -> None:
    """Lohateny ny pejy (sadro sy karatra manify)."""
    with st.container(key="page_header"):
        st.title(title, icon=icon)
        st.caption(subtitle)


def show_logo(width: int = 140) -> bool:
    """Mampiseho ny logo; raha tsy misy dia manome fallback (tsy mitsy)."""
    if LOGO.exists():
        st.image(str(LOGO), width=width, alt="Logo ny Rapport École du Sabbat")
        return True
    st.markdown(":material/menu_book:")
    st.caption("Logo tsy hita — ampidiro ny `logo.png.jpg` ao amin'ny dossier.")
    return False


def kpi_card(label: str, value, delta: str | None = None, key: str = "kpi",
             icon: str | None = None) -> None:
    """Karte «KPI» (chiffre clé) amin'ny fomba mahafinaritra."""
    with st.container(key=key):
        st.metric(label, value, delta=delta, icon=icon, border=False)


def note(text: str, icon: str = ":material/info:", key: str = "note_box") -> None:
    """Kotra fanamarihana (hatsipika gavana)."""
    with st.container(key=key):
        st.markdown(f"{icon} {text}")


def podium(rank: int, classe: str, valeur: str, suffixe: str = "") -> None:
    """Karatra podium (Top 3) — 1 = or, 2 = argent, 3 = bronze."""
    medaille = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "•")
    with st.container(key=f"podium_{rank}"):
        st.html(f"<div style='font-size:1.9rem;line-height:1'>{medaille}</div>")
        st.metric(classe, f"{valeur}{suffixe}", border=False)


def role_badge(role: str) -> None:
    """Badge ny rol ny mpampiana."""
    couleur = {"admin": "orange", "editeur": "blue", "lecteur": "gray"}.get(role, "gray")
    icone = {"admin": ":material/admin_panel_settings:", "editeur": ":material/edit:",
             "lecteur": ":material/visibility:"}.get(role, ":material/person:")
    st.badge(auth.role_label(role), icon=icone, color=couleur)


# ============================== kajy ===============================
def calc(d):
    """Kajy ny Derived: mambra_tonga, isan_tonga, asa_fitorina, tsy_tara_%."""
    d = d.copy()
    for k in FIELDS:
        d[k] = pd.to_numeric(d[k], errors="coerce").fillna(0) if k in d.columns else 0
    d["mambra_tonga"] = d.tonga_tsy_tara + d.tonga_tara
    d["isan_tonga"] = d.mambra_tonga + d.mpamangy
    d["asa_fitorina"] = d[ASA_FITORINA].sum(axis=1)
    d["tsy_tara_%"] = (100 * d.tonga_tsy_tara / d.mambra_tonga.replace(0, np.nan)).round(1)
    return d


def sivana(d, de=None, ha=None):
    """Sivana ny angona araka ny daty."""
    d = calc(d)
    if "daty" not in d.columns:
        return d
    if de:
        d = d[d.daty >= str(de)]
    if ha:
        d = d[d.daty <= str(ha)]
    return d


def fitambarana(d, de=None, ha=None):
    """Fitambarana ny classe rehetra (misy andalana TOTALY)."""
    d = sivana(d, de, ha)
    g = d.groupby("classe")[list(FIELDS) + ["mambra_tonga", "isan_tonga", "asa_fitorina"]].sum()
    g["tsy_tara_%"] = (100 * g.tonga_tsy_tara / g.mambra_tonga.replace(0, np.nan)).round(1)
    g.loc["TOTALY"] = g.sum(numeric_only=True)
    g.loc["TOTALY", "tsy_tara_%"] = round(100 * g.loc["TOTALY", "tonga_tsy_tara"] / max(g.loc["TOTALY", "mambra_tonga"], 1), 1)
    return g[COLS]


def tatitra_classe(d, classe, de=None, ha=None):
    """Tatitra isaky ny classe (isan'ny daty + TOTALY)."""
    x = sivana(d, de, ha)
    x = x[x.classe == classe].sort_values("daty")
    if x.empty:
        return None
    t = x.set_index("daty")[COLS]
    tot = t.drop(columns="tsy_tara_%").sum()
    tot["tsy_tara_%"] = round(100 * tot.tonga_tsy_tara / max(tot.mambra_tonga, 1), 1)
    t.loc["TOTALY"] = tot[COLS]
    return t


def top3(d, col, de=None, ha=None, cols=None):
    """Top 3 ny classe araka ny kolona voalaza."""
    g = fitambarana(d, de, ha).drop("TOTALY", errors="ignore")
    t = g.sort_values(col, ascending=False).head(3)[cols or [col]].copy()
    t.insert(0, "Laharana", range(1, len(t) + 1))
    return t


def sary_top3(d, de=None, ha=None):
    """Sary misy 3 panel: tsy tara %, asa fitorina, fanatitra."""
    g = fitambarana(d, de, ha).drop("TOTALY", errors="ignore")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    for a, (col, ttl, clr, suf) in zip(ax, [("tsy_tara_%", "Top 3 Tonga tsy tara (%)", NAVY, " %"),
                                            ("asa_fitorina", "Top 3 Asa fitorina", GOLD, ""),
                                            ("fanatitra_mission", "Top 3 Fanatitra", STEEL, "")]):
        s = g[col].sort_values(ascending=False).head(3)
        a.bar(s.index, s.values, color=clr)
        a.set_title(ttl, color=NAVY, fontweight="bold")
        for i, v in enumerate(s.values):
            a.text(i, v, f"{v:,.0f}{suf}", ha="center", va="bottom", fontsize=9, fontweight="bold")
        a.tick_params(axis="x", rotation=20)
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", alpha=.25)
    plt.tight_layout()
    return fig


# ============================ famonjena ============================
def _f(v):
    """Format ny isa ho an'ny tabele/rapport."""
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        return f"{v:,.1f}" if (isinstance(v, (float, np.floating)) and v != int(v)) else f"{int(v):,}"
    return "" if pd.isna(v) else str(v)


def rapport_pages(d, cls, de=None, ha=None):
    """Lisitry ny pejy ao amin'ny rapport: (lohateny, DataFrame na sary)."""
    g = fitambarana(d, de, ha)
    P = []
    P.append(("Rapport totaly — classe rehetra",
              g[["tonga_tsy_tara", "tonga_tara", "mambra_tonga", "tsy_tara_%", "mpamangy",
                 "isan_tonga", "asa_soa", "asa_fitorina", "fanatitra_mission"]].rename(columns=SHORT).rename_axis("Classe")))
    fig = sary_top3(d, de, ha)
    png = Path(tempfile.gettempdir()) / "_top3.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)
    P.append(("Top 3", str(png)))
    P.append(("Top 3 — Tonga tsy tara (%)", top3(d, "tsy_tara_%", de, ha, TOP_TSY).rename(columns=SHORT)))
    P.append(("Top 3 — Asa fitorina (fitambaran'ny asa 6)", top3(d, "asa_fitorina", de, ha, TOP_ASA).rename(columns=SHORT)))
    P.append(("Top 3 — Fanatitra ho an'ny asa maneran-tany", top3(d, "fanatitra_mission", de, ha).rename(columns=SHORT)))
    for c, info in cls.items():
        t = tatitra_classe(d, c, de, ha)
        if t is not None:
            P.append((f"{c} — {info.get('mpampianatra', '')}", t.rename(columns=SHORT).rename_axis("Daty")))
    return P


def _pdf_table(pdf, d, titre):
    """Taby ho an'ny PDF (matplotlib)."""
    d = d.reset_index()
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    ax.axis("off")
    ax.set_title(titre, fontsize=20, loc="left", color=NAVY, pad=20)
    cells = [[_f(v) for v in r] for r in d.values]
    h = min(0.075 * (len(cells) + 1), 0.9)
    t = ax.table(cellText=cells, colLabels=[str(c) for c in d.columns], bbox=[0, 1 - h, 1, h], cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(8 if d.shape[1] > 10 else 11)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color="white", weight="bold", fontsize=(6.5 if d.shape[1] > 10 else 10))
        elif str(d.iloc[r - 1, 0]) == "TOTALY":
            cell.set_facecolor("#F3E9D2")
            cell.set_text_props(weight="bold")
    pdf.savefig(fig)
    plt.close(fig)


def make_pdf(P, lohateny, per):
    """Manoratra ny rapport PDF (16:9) — mamerina ny bytes."""
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(13.33, 7.5))
        fig.patch.set_facecolor(NAVY)
        fig.text(.5, .55, lohateny, ha="center", color="white", fontsize=36, weight="bold")
        fig.text(.5, .45, per, ha="center", color="#E3BC6B", fontsize=18)
        pdf.savefig(fig)
        plt.close(fig)
        for titre, x in P:
            if isinstance(x, str):
                fig, ax = plt.subplots(figsize=(13.33, 7.5))
                ax.axis("off")
                ax.set_title(titre, fontsize=20, loc="left", color=NAVY)
                ax.imshow(plt.imread(x))
                pdf.savefig(fig)
                plt.close(fig)
            else:
                _pdf_table(pdf, x, titre)
    return buf.getvalue()


def make_pptx(P, lohateny, per):
    """Manoratra ny rapport PowerPoint (16:9) — mamerina ny bytes."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = lohateny
    s.placeholders[1].text = per
    for titre, x in P:
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = titre
        s.shapes.title.text_frame.paragraphs[0].font.size = Pt(28)
        if isinstance(x, str):
            s.shapes.add_picture(x, Inches(0.5), Inches(1.7), width=Inches(12.3))
            continue
        d = x.reset_index()
        n, m = d.shape[0] + 1, d.shape[1]
        t = s.shapes.add_table(n, m, Inches(0.3), Inches(1.5), Inches(12.7), Inches(0.38 * n)).table
        for j, c in enumerate(d.columns):
            t.cell(0, j).text = str(c)
        for i, r in enumerate(d.values):
            for j, v in enumerate(r):
                t.cell(i + 1, j).text = _f(v)
        for row in t.rows:
            for cell in row.cells:
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(10 if m > 10 else 13)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ============================ fidirana =============================
def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def is_authenticated() -> bool:
    return bool(current_user())


def can_write() -> bool:
    u = current_user()
    return bool(u) and auth.can_write(u.get("role", "lecteur"))


def is_admin() -> bool:
    u = current_user()
    return bool(u) and auth.can_admin(u.get("role", "lecteur"))


def render_login_form() -> None:
    """Fomba fidirana (mpampiana + password)."""
    with st.form("login_form", border=False):
        st.text_input("Anaran'ny mpampiana", placeholder="admin", key="login_user")
        st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Hiditra", type="primary", icon=":material/login:",
                                          width="stretch", key="btn_login")
    if submitted:
        ok, msg = auth.authenticate(st.session_state.get("login_user", ""),
                                    st.session_state.get("login_password", ""))
        if ok:
            rec = auth.get_user(st.session_state.get("login_user", ""))
            st.session_state["auth_user"] = {
                "username": st.session_state.get("login_user", "").strip(),
                "role": (rec or {}).get("role", "lecteur"),
                "login_at": auth.stamp(),
            }
            st.rerun()
        st.error(msg, icon=":material/error:")


def render_first_run_setup() -> None:
    """Fanombohana voalohany: famorona ny mpampianatra administrateur."""
    st.info("Fanombohana voalohany: amboary ny mpampianatra administrateur. "
            "Ny code fanombohana dia hita ao amin'ny terminal-n'ny serveur "
            "(rehefa nanomboka ny Streamlit).", icon=":material/key:")
    with st.form("setup_form", border=False):
        st.text_input("Code fanombohana", key="setup_code")
        st.text_input("Anaran'ny administrateur", key="setup_user")
        st.text_input("Password", type="password", key="setup_pwd")
        st.text_input("Hamerina ny password", type="password", key="setup_pwd2")
        submitted = st.form_submit_button("Hamorona ny administrateur", type="primary",
                                          icon=":material/person_add:", width="stretch")
    if submitted:
        ok, msg = auth.first_run_setup(st.session_state.get("setup_code", ""),
                                       st.session_state.get("setup_user", ""),
                                       st.session_state.get("setup_pwd", ""),
                                       st.session_state.get("setup_pwd2", ""))
        if ok:
            st.success(msg, icon=":material/check_circle:")
            st.rerun()
        st.error(msg, icon=":material/error:")


def render_login() -> None:
    """Pejy fidirana (azy no jerena raha tsy voasoratra ny mpampiana)."""
    left, mid, right = st.columns([1, 1.5, 1])
    with mid:
        with st.container(border=True, key="login_card"):
            with st.container(key="login_brand"):
                c1, c2, c3 = st.columns([1, 1.7, 1])
                with c2:
                    show_logo(132)
                st.title(APP_NAME)
                st.markdown(f"<p style='text-align:center;margin:0'>{APP_SUBTITLE}</p>",
                            unsafe_allow_html=True)
            with st.container(key="login_body"):
                if auth.setup_code_needed():
                    render_first_run_setup()
                else:
                    render_login_form()
                with st.container(key="login_foot"):
                    st.caption(f"Version {APP_VERSION} · ny angona dia ao amin'ny PC-mpanomefa")
    st.markdown("")
    st.caption("Raha tsy mety ny fidirana, mifandraisa amin'ny mpitantana ny app.")


# ============================== sidebar ============================
def render_sidebar(page_objs) -> None:
    """Logo + anarana + menu + mpampiana + fivoahana."""
    with st.sidebar:
        with st.container(key="sidebar_brand"):
            c1, c2, c3 = st.columns([1, 2.4, 1])
            with c2:
                show_logo(92)
            st.markdown(f"**{APP_NAME}**")
            st.caption("Rapport hebdomadaire — Suivi des classes")
        with st.container(key="nav_menu"):
            for p in page_objs:
                st.page_link(p, label=p.title, width="stretch")
        cls = storage.read_classes()
        df = storage.read_df()
        st.caption(f"🏫 Classe: {len(cls)}/10 · 📅 Andalana: {len(df)}")
        u = current_user() or {}
        with st.container(key="user_card"):
            st.markdown(f"**🔑 {u.get('username', '')}**")
            role_badge(u.get("role", "lecteur"))
        if st.button("Fivoahana", icon=":material/logout:", width="stretch", key="btn_logout"):
            for k in ("auth_user", "login_user", "login_password", "pdf", "pptx"):
                st.session_state.pop(k, None)
            st.rerun()
        st.caption("☰ → Settings → Appearance : fomba maizina.")


# ============================== pejy ===============================
def sivana_daty(key: str):
    """Sivana daty (de → ha)."""
    c1, c2 = st.columns(2)
    de = c1.date_input("Daty fiandohana", value=None, key=key + "a")
    ha = c2.date_input("Daty farany", value=None, key=key + "b")
    return (str(de) if de else None), (str(ha) if ha else None)


def page_classe() -> None:
    """🏫 Classe — fanampiana/fafana ny classe."""
    page_header("🏫 Classe", "Ampio ny classe, ny mpampianatra ary ny isa voasoratra (hatramin'ny 10).",
                ":material/school:")
    cls = storage.read_classes()
    df = storage.read_df()
    total_mambra = sum(int(v.get("mambra", 0) or 0) for v in cls.values())

    k1, k2, k3, k4 = st.columns(4)
    k1.container(key="kpi_1").metric("Classe voasoratra", f"{len(cls)}/10", icon=":material/school:")
    k2.container(key="kpi_2").metric("Membre voasoratra", total_mambra, icon=":material/groups:")
    k3.container(key="kpi_3").metric("Andalana rehetra", len(df), icon=":material/event_note:")
    k4.container(key="kpi_4").metric("Sabata farany", (df["daty"].max() if len(df) else "—"),
                                      icon=":material/calendar_month:")

    if can_write():
        with st.container(border=True):
            st.markdown("**➕ Ampio ny classe vaovao**")
            with st.form("fc", clear_on_submit=True):
                a, b, c = st.columns(3)
                nom = a.text_input("Anaran'ny classe")
                mon = b.text_input("Mpampianatra")
                eff = c.number_input("Isa voasoratra", 0, step=1)
                if st.form_submit_button("Ampio ny classe", type="primary", icon=":material/add:",
                                         key="btn_add"):
                    if not nom.strip():
                        st.error("Soraty ny anarana.")
                    elif nom.strip() in cls:
                        st.error("Efa misy io classe io.")
                    elif len(cls) >= 10:
                        st.error("Classe 10 no betsaka indrindra.")
                    else:
                        cls[nom.strip()] = {"mpampianatra": mon, "mambra": int(eff)}
                        storage.save_classes(cls, tag="avao_ampiana_classe")
                        st.rerun()
    else:
        note("Tsy mahazo manova ny angona ianao (rol: mpamaky).", ":material/lock:")

    if cls:
        st.markdown("**📋 Ny classe rehetra**")
        st.dataframe(
            pd.DataFrame(cls).T.rename(columns={"mpampianatra": "Mpampianatra",
                                                 "mambra": "Isa voasoratra"}),
            column_config={
                "Mpampianatra": column_config.TextColumn("Mpampianatra", width="medium"),
                "Isa voasoratra": column_config.NumberColumn("Isa voasoratra", format="%d"),
            },
            width="stretch", hide_index=True)
        if can_write():
            with st.expander("🗑️ Fafao ny classe (miaraka amin'ny angony)"):
                del_c = st.selectbox("Safidio ny classe", [""] + list(cls), key="del_classe")
                if del_c and st.button("Fafao ny classe", icon=":material/delete:", key="btn_delete"):
                    storage.backup_now("avao_fafana_classe")
                    storage.save_df(df[df.classe != del_c], backup=False)
                    storage.save_classes({k: v for k, v in cls.items() if k != del_c}, backup=False)
                    st.rerun()


def page_fampidirana() -> None:
    """📝 Fampidirana Sabata — fidirana ny angona isaky ny Sabata."""
    page_header("📝 Fampidirana Sabata", "Ampidiro ny angona isaky ny Sabata isaky ny classe.",
                ":material/assignment:")
    cls = storage.read_classes()
    df = storage.read_df()
    if not cls:
        st.warning("Ampio classe aloha.", icon=":material/warning:")
        return
    if not can_write():
        note("Tsy mahazo manova ny angona ianao (rol: mpamaky).", ":material/lock:")
        return

    with st.container(border=True):
        with st.form("fs"):
            a, b = st.columns(2)
            daty = a.date_input("Daty ny Sabata", value=pd.Timestamp.today().date())
            classe = b.selectbox("Classe", list(cls))
            vals, cols = {}, st.columns(3)
            for i, (k, lab) in enumerate(FIELDS.items()):
                vals[k] = (cols[i % 3].number_input(lab, 0.0, step=100.0, key=k) if k == "fanatitra_mission"
                           else cols[i % 3].number_input(lab, 0, step=1, key=k))
            st.markdown("---")
            if st.form_submit_button("Tahirizo ny angona", type="primary", icon=":material/save:",
                                     width="stretch", key="btn_save"):
                row = {"daty": str(daty), "classe": classe, **vals}
                df = df[~((df.daty == row["daty"]) & (df.classe == classe))]
                storage.save_df(pd.concat([df, pd.DataFrame([row])], ignore_index=True),
                                tag="avao_fampidirana")
                st.success(f"✅ Voatahiry: {classe} · {daty} (raha efa misy, nosoloina)",
                           icon=":material/check_circle:")

    if not df.empty:
        st.markdown("**🕘 Ny andalana farany**")
        recent = calc(df).sort_values("daty").tail(8).iloc[::-1]
        st.dataframe(recent[["daty", "classe", "tonga_tsy_tara", "tonga_tara", "mpamangy",
                             "asa_fitorina", "fanatitra_mission"]]
                     .rename(columns={"daty": "Daty", "classe": "Classe",
                                      "tonga_tsy_tara": "Tsy tara", "tonga_tara": "Tara",
                                      "mpamangy": "Mpamangy", "asa_fitorina": "Asa fitorina",
                                      "fanatitra_mission": "Fanatitra"}),
                     column_config={"Fanatitra": column_config.NumberColumn("Fanatitra", format="%.0f")},
                     width="stretch", hide_index=True)


def page_rapport_classe() -> None:
    """📄 Rapport classe — tatitra isaky ny classe."""
    page_header("📄 Rapport classe", "Tatitra isaky ny classe, amin'ny sivana daty.",
                ":material/description:")
    cls = storage.read_classes()
    df = storage.read_df()
    if df.empty:
        st.info("Tsy mbola misy angona.", icon=":material/info:")
        return
    if not cls:
        st.info("Tsy misy classe voarakitra.")
        return
    c = st.selectbox("Classe", list(cls), key="rc_classe")
    de, ha = sivana_daty("rc")
    t = tatitra_classe(df, c, de, ha)
    if t is None:
        st.info("Tsy misy angona.", icon=":material/info:")
        return

    tot = t.loc["TOTALY"] if "TOTALY" in t.index else t.sum(numeric_only=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.container(key="kpi_1").metric("Tsy tara", int(tot["tonga_tsy_tara"]), icon=":material/group_off:")
    k2.container(key="kpi_2").metric("Tsy tara %", f"{tot['tsy_tara_%']}%", icon=":material/percent:")
    k3.container(key="kpi_3").metric("Asa fitorina", int(tot["asa_fitorina"]),
                                      icon=":material/volunteer_activism:")
    k4.container(key="kpi_4").metric("Fanatitra", f"{tot['fanatitra_mission']:,.0f}",
                                      icon=":material/savings:")

    st.dataframe(
        t.rename(columns=SHORT),
        column_config={
            "Tsy tara %": column_config.ProgressColumn("Tsy tara %", format="%.1f%%",
                                                        min_value=0, max_value=100),
            "Fanatitra": column_config.NumberColumn("Fanatitra", format="%.0f"),
        },
        width="stretch")


def page_totaly_top3() -> None:
    """📊 Totaly & Top 3 — fitambarana ny classe rehetra."""
    page_header("📊 Totaly & Top 3", "Fitambarana ny classe rehetra sy ny Top 3.",
                ":material/leaderboard:")
    df = storage.read_df()
    if df.empty:
        st.info("Tsy mbola misy angona.", icon=":material/info:")
        return
    de, ha = sivana_daty("tt")
    g = fitambarana(df, de, ha)
    tot = g.loc["TOTALY"]

    k1, k2, k3, k4 = st.columns(4)
    k1.container(key="kpi_1").metric("Tonga tonga", int(tot["mambra_tonga"]), icon=":material/groups:")
    k2.container(key="kpi_2").metric("Tsy tara %", f"{tot['tsy_tara_%']}%", icon=":material/percent:")
    k3.container(key="kpi_3").metric("Asa fitorina", int(tot["asa_fitorina"]),
                                      icon=":material/volunteer_activism:")
    k4.container(key="kpi_4").metric("Fanatitra", f"{tot['fanatitra_mission']:,.0f}",
                                      icon=":material/savings:")

    best = g.drop("TOTALY", errors="ignore").sort_values("tsy_tara_%", ascending=False).head(3)
    if not best.empty:
        st.markdown("**🏆 Podium — tsy tara ny tsaran'ny tonga (%)**")
        p1, p2, p3 = st.columns(3)
        for i, (col, cl) in enumerate(zip((p1, p2, p3), best.index)):
            with col:
                podium(i + 1, str(cl), f"{best.loc[cl, 'tsy_tara_%']}", " %")

    st.markdown("**📋 Fitambarana ny classe rehetra**")
    st.dataframe(
        g.rename(columns=SHORT),
        column_config={
            "Tsy tara %": column_config.ProgressColumn("Tsy tara %", format="%.1f%%",
                                                        min_value=0, max_value=100),
            "Fanatitra": column_config.NumberColumn("Fanatitra", format="%.0f"),
        },
        width="stretch")

    st.markdown("**🏆 Top 3**")
    a, b = st.columns(2)
    with a:
        st.markdown("*Tonga tsy tara (%)*")
        st.dataframe(top3(df, "tsy_tara_%", de, ha, TOP_TSY).rename(columns=SHORT), hide_index=True)
    with b:
        st.markdown("*Fanatitra*")
        st.dataframe(top3(df, "fanatitra_mission", de, ha).rename(columns=SHORT), hide_index=True)
    st.markdown("*Asa fitorina* (fitambaran'ny asa 6)")
    st.dataframe(top3(df, "asa_fitorina", de, ha, TOP_ASA).rename(columns=SHORT), width="stretch",
                 hide_index=True)
    fig = sary_top3(df, de, ha)
    st.pyplot(fig)
    plt.close(fig)


def page_fanondranana() -> None:
    """📤 Fanondranana — PDF na PowerPoint."""
    page_header("📤 Fanondranana", "Alamino ny rapport ary alaina amin'ny format PDF na PowerPoint (16:9).",
                ":material/download:")
    df = storage.read_df()
    cls = storage.read_classes()
    if df.empty:
        st.info("Tsy mbola misy angona.", icon=":material/info:")
        return
    with st.container(border=True):
        lohateny = st.text_input("Lohateny", "Rapport École du Sabbat", key="export_title")
        de, ha = sivana_daty("ex")
        st.caption(f"Periody: {de or df.daty.min()} → {ha or df.daty.max()}")
        st.markdown("**📑 Pejy ao amin'ny rapport**")
        st.markdown("- Pejy fandraisana ankapobeny (classe rehetra)\n"
                    "- Sary Top 3 (tsy tara %, asa fitorina, fanatitra)\n"
                    "- Top 3 isaky ny kolona\n"
                    "- Tatitra isaky ny classe (isan'ny daty + TOTALY)")
        if st.button("Alamino ny rapport", type="primary", icon=":material/build:",
                     width="stretch", key="btn_export"):
            with st.spinner("Manao ny rapport..."):
                P = rapport_pages(df, cls, de, ha)
                per = f"{de or df.daty.min()} → {ha or df.daty.max()}"
                st.session_state["pdf"] = make_pdf(P, lohateny, per)
                st.session_state["pptx"] = make_pptx(P, lohateny, per)
    if "pdf" in st.session_state:
        st.markdown("**⬇️ Alaina ny rapport**")
        a, b = st.columns(2)
        a.download_button("⬇️ PDF", st.session_state["pdf"], "Rapport_Ecole_du_Sabbat.pdf",
                          "application/pdf", width="stretch", key="dl_pdf")
        b.download_button("⬇️ PowerPoint", st.session_state["pptx"], "Rapport_Ecole_du_Sabbat.pptx",
                          "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                          width="stretch", key="dl_pptx")
    else:
        note("Tsindrio «Alamino ny rapport» aloha vao hisy ny bouton-download.", ":material/info:")


def page_angona() -> None:
    """🗂️ Angona — fanovana/fafana ny angona + CSV."""
    page_header("🗂️ Angona (sora-baventy)", "Ovay ny angona eto, na alaina amin'ny CSV.",
                ":material/storage:")
    df = storage.read_df()

    if can_write():
        st.markdown("**✏️ Fanovana ny angona**")
        ed = st.data_editor(df, num_rows="dynamic", width="stretch", key="angona_editor",
                            column_config={"fanatitra_mission": column_config.NumberColumn(
                                "Fanatitra", format="%.0f")})
        if st.button("Tahirizo ny fanovana", type="primary", icon=":material/save:",
                     width="stretch", key="btn_save"):
            storage.save_df(ed, tag="avao_fanovana")
            st.success("Voatahiry.", icon=":material/check_circle:")
            st.rerun()
    else:
        st.dataframe(df, width="stretch")
        note("Tsy mahazo manova ny angona ianao (rol: mpamaky).", ":material/lock:")

    st.markdown("**⬇️ Export / import**")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ CSV (Excel)", df.to_csv(index=False).encode("utf-8-sig"),
                           "sabata.csv", "text/csv", width="stretch", key="dl_csv")
    if can_write():
        with st.expander("📥 Ampidiro ny angona avy amin'ny CSV"):
            up = st.file_uploader("Safidio ny rakitra CSV", type=["csv"], key="csv_upload")
            if up is not None:
                try:
                    new = pd.read_csv(up)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Tsy azo vakiana ny CSV: {e}")
                else:
                    missing = [c for c in storage.CSV_COLUMNS if c not in new.columns]
                    st.dataframe(new.head(10), width="stretch")
                    st.caption(f"{len(new)} andalana · {len(new.columns)} kolona"
                               + (f" · kolona tsy hita: {', '.join(missing)}" if missing else ""))
                    if st.button("Soloina ny angona amin'ity CSV ity", icon=":material/upload:",
                                 key="btn_import"):
                        storage.backup_now("avao_import")
                        for c in storage.CSV_COLUMNS:
                            if c not in new.columns:
                                new[c] = 0
                        storage.save_df(new[storage.CSV_COLUMNS], backup=False)
                        st.success("Voatahiry ny angona vaovao.", icon=":material/check_circle:")
                        st.rerun()


def page_administration() -> None:
    """🛠️ Administration — sauvegardes, utilisateurs, système."""
    page_header("🛠️ Administration", "Sauvegardes, mpampiana ary momba ny app.",
                ":material/admin_panel_settings:")

    tabs = st.tabs(["💾 Sauvegardes", "🔑 Mon mot de passe", "👥 Utilisateurs", "🖥️ Système"])
    with tabs[0]:
        st.markdown("**💾 Sauvegardes automatiques**")
        backups = storage.list_backups()
        last_week = storage.last_weekly_backup_date()
        st.caption(f"📁 Folder: `{storage.BACKUP_DIR}` · "
                   f"🗓️ Derrière sauvegarde hebdomadaire: {last_week or 'tsy mbola natao'}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sauvegarde manuelle", type="primary", icon=":material/save:",
                         key="btn_backup"):
                folder = storage.backup_now("manuel")
                if folder:
                    st.success(f"Voatahiry ny backup: {folder.name}", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.warning("Tsy misy angona voatahiry mbola.", icon=":material/warning:")
        with c2:
            st.download_button("⬇️ Télécharger toutes les sauvegardes", storage.backup_zip_bytes(),
                               "sauvegardes_ecole_du_sabbat.zip", "application/zip",
                               key="dl_all_backups", width="stretch")
        if backups:
            rows = [{"Nom": b["name"], "Créé le": b["created"], "Type": b["tag"],
                     "Fichiers": ", ".join(b["files"]), "Taille (Ko)": round(b["size"] / 1024, 1)}
                    for b in backups]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            sel = st.selectbox("Safidio ny sauvegarde", [b["name"] for b in backups],
                               key="backup_select")
            c3, c4 = st.columns(2)
            with c3:
                st.download_button("⬇️ Ala ny backup nofidiana", storage.backup_zip_bytes([sel]),
                                   f"{sel}.zip", "application/zip", key="dl_one_backup",
                                   width="stretch")
            with c4:
                confirm = st.checkbox("⚠️ Azoko ny manapaka ny angona ankehitriny vao averina",
                                      key="restore_confirm")
                if st.button("Restorer ny sauvegarde", type="secondary", icon=":material/restore:",
                             disabled=not confirm, width="stretch", key="btn_restore"):
                    ok, msg = storage.restore_backup(sel)
                    if ok:
                        st.success(msg, icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.error(msg, icon=":material/error:")
        else:
            st.info("Mbola tsy misy sauvegarde.", icon=":material/info:")

    with tabs[1]:
        st.markdown("**🔑 Ovay ny password-nao**")
        u = current_user() or {}
        with st.form("pwd_form", border=False):
            old = st.text_input("Password ankehitriny", type="password", key="pwd_old")
            new = st.text_input("Password vaovao", type="password", key="pwd_new")
            new2 = st.text_input("Hamerina ny password vaovao", type="password", key="pwd_new2")
            if st.form_submit_button("Ovay ny password", type="primary", icon=":material/key:"):
                if new != new2:
                    st.error("Tsy mitovy ny password roa.", icon=":material/error:")
                elif not auth.verify_password(old, auth.get_user(u.get("username", ""))):
                    st.error("Tsy mety ny password ankehitriny.", icon=":material/error:")
                else:
                    ok, msg = auth.set_password(u.get("username", ""), new)
                    (st.success if ok else st.error)(msg,
                                                     icon=":material/check_circle:" if ok else ":material/error:")
        note("Ampiasaina hy 10 litera farafiny, misy isa sy litera lehibe. "
             "Aza mampizara ny password amin'ny rehetra.", ":material/shield:",
             key="note_box_pwd")

    with tabs[2]:
        if not is_admin():
            note("Ny fitantanana ny mpampiana dia natao ho an'ny administrateur ihany.", ":material/lock:")
        else:
            users = auth.list_users()
            st.dataframe(pd.DataFrame([
                {"Utilisateur": u, "Rôle": auth.role_label(r.get("role", "")),
                 "Créé le": r.get("created", ""), "Dernière connexion": r.get("last_login", "") or "—",
                 "Mot de passe changé": r.get("password_changed", "") or "—"}
                for u, r in users.items()]), width="stretch", hide_index=True)
            with st.expander("➕ Mpampiana vaovao", icon=":material/person_add:"):
                with st.form("add_user", border=False):
                    nu = st.text_input("Anaran'ny mpampiana", key="new_user")
                    np1 = st.text_input("Password", type="password", key="new_pwd")
                    np2 = st.text_input("Hamerina ny password", type="password", key="new_pwd2")
                    role = st.selectbox("Rol", list(auth.ROLES), key="new_role")
                    if st.form_submit_button("Hamorona", type="primary"):
                        if np1 != np2:
                            st.error("Tsy mitovy ny password roa.", icon=":material/error:")
                        else:
                            ok, msg = auth.create_user(nu, np1, role)
                            (st.success if ok else st.error)(
                                msg, icon=":material/check_circle:" if ok else ":material/error:")
            with st.expander("🔁 Ovay ny password", icon=":material/key:"):
                with st.form("reset_pwd", border=False):
                    target = st.selectbox("Mpampiana", list(users) if users else ["—"])
                    rp1 = st.text_input("Password vaovao", type="password", key="reset_pwd1")
                    rp2 = st.text_input("Hamerina ny password", type="password", key="reset_pwd2")
                    if st.form_submit_button("Ovay"):
                        if rp1 != rp2:
                            st.error("Tsy mitovy ny password roa.", icon=":material/error:")
                        else:
                            ok, msg = auth.set_password(target, rp1)
                            (st.success if ok else st.error)(
                                msg, icon=":material/check_circle:" if ok else ":material/error:")
            with st.expander("🗑️ Fafao ny mpampiana", icon=":material/delete:"):
                with st.form("del_user", border=False):
                    target2 = st.selectbox("Mpampiana", list(users) if users else ["—"], key="del_user_sel")
                    if st.form_submit_button("Fafao"):
                        ok, msg = auth.delete_user(target2)
                        (st.success if ok else st.error)(
                            msg, icon=":material/check_circle:" if ok else ":material/error:")

    with tabs[3]:
        st.markdown("**🖥️ Mombamomba ny app**")
        df = storage.read_df()
        st.dataframe(pd.DataFrame([
            {"Élément": "Version", "Valeur": str(APP_VERSION)},
            {"Élément": "Streamlit", "Valeur": str(st.__version__)},
            {"Élément": "Angona (sabata.csv)", "Valeur": f"{len(df)} andalana · {storage.F_DATA}"},
            {"Élément": "Classes (classes.json)",
             "Valeur": f"{len(storage.read_classes())} classe · {storage.F_CLS}"},
            {"Élément": "Mpampiana", "Valeur": str(len(auth.list_users()))},
            {"Élément": "Sauvegardes", "Valeur": f"{len(storage.list_backups())} · {storage.BACKUP_DIR}"},
            {"Élément": "Logo", "Valeur": str(LOGO) if LOGO.exists() else "tsy hita"},
        ]), width="stretch", hide_index=True)
        note("Ny angona dia voatahiry ao amin'ny PC-mpanomefa (server) — "
             "tsy misy mila internet na kaonty en ligne.", ":material/server:",
             key="note_box_system")


# ============================ fidirana + nav ========================
def build_pages():
    """Mamorona ny pejy rehetra (st.Page) — misy URL manokana isaky ny iray."""
    return [
        st.Page(page_classe, title="🏫 Classe", url_path="classe",
                help="Ampio ny classe, ny mpampianatra sy ny isa voasoratra (hatramin'ny 10)."),
        st.Page(page_fampidirana, title="📝 Fampidirana Sabata", url_path="fampidirana",
                help="Ampidiro ny angona isaky ny Sabata isaky ny classe."),
        st.Page(page_rapport_classe, title="📄 Rapport classe", url_path="rapport-classe",
                help="Tatitra isaky ny classe, amin'ny sivana daty."),
        st.Page(page_totaly_top3, title="📊 Totaly & Top 3", url_path="totaly-top3",
                help="Fitambarana ny classe rehetra sy ny Top 3 (tsy tara, asa fitorina, fanatitra)."),
        st.Page(page_fanondranana, title="📤 Fanondranana", url_path="fanondranana",
                help="Alamino ny rapport ary alaina amin'ny format PDF na PowerPoint."),
        st.Page(page_angona, title="🗂️ Angona", url_path="angona",
                help="Ovay, fafana na alaina ny angona amin'ny CSV."),
        st.Page(page_administration, title="🛠️ Administration", url_path="administration",
                help="Sauvegardes, mpampiana, ary ny momba ny app."),
    ]


def main() -> None:
    """Fomba lehibe: fidirana aloha, dia ny app."""
    inject_css()
    # «Backup» isam-bolana rehefa manomboka ny app (tsy mifangaro ny tehatro)
    try:
        storage.weekly_backup_if_needed()
    except OSError:
        pass
    # Code fanombohana (raha mbola tsy misy mpampiana) — hita ao amin'ny terminal
    try:
        code = auth.ensure_setup_code()
    except OSError:
        code = None
    if code:
        print("=" * 66, flush=True)
        print("  RAPPORT ÉCOLE DU SABBAT — CODE FANOMBOHANA (raha mbola tsy misy mpampiana):",
              flush=True)
        print(f"      {code}", flush=True)
        print("  Ampidiro ity ao amin'ny pejy fidirana ny app mba hamorona ny administrateur.",
              flush=True)
        print(f"  (Na jerena ao amin'ny rakitra: {auth.SETUP_TXT})", flush=True)
        print("=" * 66, flush=True)

    page_objs = build_pages()
    page = st.navigation(page_objs, position="hidden")

    if not is_authenticated():
        render_login()
        st.stop()

    render_sidebar(page_objs)
    page.run()


if __name__ == "__main__":
    main()
