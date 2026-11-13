# Rapport École du Sabbat

Application locale (Python + Streamlit) ny **École du Sabbat** — rapport hebdomadaire
isaky ny classe, fitambarana, Top 3, ary export PDF / PowerPoint.

Ny app dia miasa **eto an-tanànana ao amin'ny PC-mpanomefa** (server local) : ny angona
dia voatahiry ao amin'ny PC-n'ny serveur, tsy misy mila internet na kaonty en ligne.
Ny mpampiasa hafa ao amin'ny Wi-Fi dia afaka miditra amin'ny alalan'ny adiresy IP-n'ny
serveur, nefa **tsy maintsy manao fidirana**.

---

## 1. voto

| Zavatra | Anjara |
|---|---|
| Fomba fidirana | `auth.py` — PBKDF2-HMAC-SHA256 (600 000 iterations), tsy misy password en clair |
| Angona + backup | `storage.py` — cache `@st.cache_data`, «backup» automatika, restauration |
| Pejy + rapport | `app.py` — 7 pejy, kajy, PDF/PowerPoint |
| Fitaovana admin | `manage_users.py` — mamorona/ovay/fafana ny mpampiana (command line) |
| Logo | `logo.png.jpg` |
| Angona | `data/sabata.csv`, `data/classes.json`, `data/users.json` |
| Sauvegardes | `backups/` |

---

## 2. Installation

### 2.1 Python

Apetraho Python 3.10+ (https://www.python.org/downloads/) ary azafady
**"Add Python to PATH"** rehefa mametraka.

### 2.2 Environnement virtuel (venv)

Ao amin'ny PowerShell na CMD, ao amin'ny dossier-n'ny app:

```bat
cd /d "D:\Projet App Ecole du sabbat\Rapport ecole du sabbta"

python -m venv venv
venv\Scripts\activate
```

### 2.3 Dependances

```bat
pip install -r requirements.txt
```

### 2.4 fandefasana

```bat
venv\Scripts\streamlit run app.py
```

Ampidiro ao amin'ny navigateur: **http://localhost:8501**

> Rehefa miova ny `app.py`, dia miova avy hatrany ny app (Streamlit dia mametraka
> ny rakitra manao hot-reload). **Fa rehefa miova ny `auth.py` na ny `storage.py`,
> tokony manohana ny server** (Ctrl+C, avy efa avereno).

---

## 3. Voalohany fandefasana — famoronana ny administrateur

Mbola tsy misy mpampiana rehefa manomboka ny app voalohany:

1. Ao amin'ny **terminal-n'ny serveur** dia hiseho ny *code fanombohana*, ohatra:

   ```
   ==============================================================
     RAPPORT ÉCOLE DU SABBAT — CODE FANOMBOHANA:
         890B-B080-FB68-C660
   ==============================================================
   ```

   Ilay code dia hita koa amin'ny rakitra `data/setup_code.txt`.

2. Ao amin'ny navigateur, ampidiro ny code, ny anaran'ny administrateur ary ny
   password **ampihiditrao manokana** (azo alaina amin'ny ny anaranao, ohatra
   `TANANAn'iAMBONY-2026!`).

3. Rehefa vita ny famoronana, ny code dia fafana (tsy azo ampiasaina intsony).

> ⚠️ **Aza manao ny code ho sandan'ny rehetra**: izy dia mety ho hita ao amin'ny
> terminal-n'ny server. Raha misy olona hafa afaka miditra amin'ny PC-n'ny serveur,
> ampio ny administrateur voalohany aloha.

### 3.1 Mpampiana hafa (raha ilaina)

Ao amin'ny **pejy "🛠️ Administration" → "👥 Utilisateurs"** (na amin'ny terminal) :

```bat
venv\Scripts\python manage_users.py add mpampianatra1 --role editeur
```

Ity ny_roles_azo_atao_:

| Rol | Tomany |
|---|---|
| `admin` | Mpitantana: manao ny zava-drehetra (manampy mpampiana, restaura backup…) |
| `editeur` | Mpampiasa: amampy classe, ampidiro ny angona, manova ny angona |
| `lecteur` | Mpamaky: mijery ny rapport fotsiny (tsy afaka manova angona) |

### 3.2 Ovana ny password (secure)

**Amin'ny ny app** (pejy Administration → "🔑 Mon mot de passe"), na amin'ny terminal:

```bat
venv\Scripts\python manage_users.py passwd admin
```

Ny password **tsy voatahiry en clair**: voatahiry ny `salt` + ny hash PBKDF2 ao amin'ny
`data/users.json`. Rehefa ovaina ny password, ny session rehetra mbola velona dia
tsy mifanapaka ny session (miditra indray).

### 3.3 Fivoahana

Ny bouton **"Fivoahana"** ao amin'ny sisiny dia mamafa ny session.
Rehefa mamerina ny pejy (F5 / Ctrl+R) dia session vaovao no misy → **mila miditra indray**.

---

## 4. Ny pejy (menu)

| Pejy | Inona no atao |
|---|---|
| 🏫 Classe | Manampy classe (hatramin'ny 10), mpampianatra, isa voasoratra; mamafa classe (miaraka amin'ny angony) |
| 📝 Fampidirana Sabata | Ampidiro ny angona isaky ny Sabata isaky ny classe (11 isa) |
| 📄 Rapport classe | Tatitra isaky ny classe + sivana daty |
| 📊 Totaly & Top 3 | Fitambarana ny classe rehetra + Top 3 (tsy tara %, asa fitorina, fanatitra) + sary |
| 📤 Fanondranana | Export **PDF** sy **PowerPoint** (16:9) |
| 🗂️ Angona | Manova/mamama ny angona, download CSV, import CSV |
| 🛠️ Administration | Sauvegardes, mpampiana, momba ny app |

Ny kajy (tsy miova):

- `Membres tonga` = tonga tsy tara + tonga tara
- `Isan'ny tonga` = membres tonga + mpamangy
- `ASA FITORINA` = Baiboly + Boky/trakta + Seminera + Ala Sarona + Nahavita + Batisa
- `Tsy tara %` = tonga tsy tara ÷ (tsy tara + tara) × 100

---

## 5. Angona

| Rakitra | voto |
|---|---|
| `data/sabata.csv` | Angona isaky ny Sabata (daty, classe, asa…) |
| `data/classes.json` | Classe, mpampianatra, isa voasoratra |
| `data/users.json` | Mpampiana + hash ny password (tsy misy password en clair) |
| `data/login_attempts.json` | Fanandramana ny fidirana (lockout) |
| `data/setup_code.json` / `.txt` | Code fanombohana (efa voafafa rehefa vita) |
| `data/sad.db`, `data/secret.key` | Rakitra taloha (tsy ampiasaina ny app 2.0) — azo fafana raha tsy ilaina |

Ny angona dia **tsy mifindra** rehefa miankina amin'ny mpampiasa ny app: ny PC-n'ny
serveur no mametraka ny rakitra.

### 5.1 Cache

`storage.load_df()` sy `storage.load_classes()` dia `@st.cache_data`. Ny «mtime» ny
rakitra no ampiasaina ho clé, ka ** miova avy hatrany ny cache** rehefa miova ny
rakitra. Mba feno aza, dia atontay ny cache (`load_df.clear()`) **rehefa manoratra**
(ampiditra angona, ampio classe, fafao classe, restaura backup).

---

## 6. Sauvegardes («backup»)

### 6.1 Ahoana no mitranga

| Fotoana | Inona |
|---|---|
| Rehefa manomboka ny app | «Backup» isam-bolana raha tsy nisy tao an-toerana 7 andro (ohatra: `backup_20261113_073333_hebdomadaire/`) |
| Talohan'ny fanovana zava-dehibe | «Backup» alohan'ny fampidirana angona, fampidirana classe, fanafana classe, na import CSV |
| Manually | Bouton «💾 Sauvegarde manuelle» ao amin'ny pejy Administration |

Isaky ny backup dia misy folder misy daty sy ora ao amin'ny anarany, misy
`sabata.csv`, `classes.json` ary `manifest.json` ao anatiny.

> Ny backup **tsy fafana mihitsy** mba ho an'ny app (ary ny mpampiana mihitsy no
> afaka mamafa, amin'ny alalan'ny fitaovana).

### 6.2 Fitantanana (pejy Administration → "💾 Sauvegardes")

- **Jereo** ny lisitry ny backup rehetra (daty, karazana,_SIZE_).
- **Alaina** ny backup iray (ZIP) na ny backup rehetra.
- **Restaura** ny backup: tsy maintsy manamarika ny fitaratra *"Azoko ny manapaka ny
  angona ankehitriny vao averina"* aloha. Ny angona ankehitriny dia voatahiry
  (backup "avao_restauration") alohan'ny averina — ka azo averina koa.

### 6.3 Copie grefy (recommandé)

Kopia ny dossier `data/` sy `backups/` amin'ny USB na Google Drive **isaky ny herinandro**.

---

## 7. Fampiasaina amin'ny réseau local (LAN)

### 7.1 fandefasana ho an'ny LAN

```bat
venv\Scripts\streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Ao amin'ny terminal dia hiseho ny "Network URL", ohatra `http://192.168.1.15:8501`.
Izay no hidirany ny mpampiasa hafa amin'ny telefa na ny PC.

> ⚠️ `--server.address 0.0.0.0` dia manao ny app ho rehetra amin'ny interface rehetra.
> Raha tsy ilaina ny LAN, aza asio — alefa ao amin'ny `localhost` fotsiny.

### 7.2 Parefa Windows (Windows Firewall)

Orazo ny parefa ho an'ny **réseau privé** ihany (tsy "public"):

```powershell
New-NetFirewallRule -DisplayName "Streamlit - Ecole du Sabbat" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8501 `
  -Profile Private -RemoteAddress LocalSubnet
```

- `-Profile Private` : tsy misokatra amin'ny café na ny Wi-Fi mivantana.
- `-RemoteAddress LocalSubnet` : ny olona ao amin'ny tranokarena ihany.

Tohana ny parefa ny mpiaraka amin'ny ny PC:

```powershell
Get-NetFirewallRule -DisplayName "Streamlit - Ecole du Sabbat"
Set-NetFirewallRule -DisplayName "Streamlit - Ecole du Sabbat" -Enabled True
```

Hanadio ny rakitra: `Remove-NetFirewallRule -DisplayName "Streamlit - Ecole du Sabbat"`.

### 7.3 Fiarovana amin'ny fomba ankapobeny

- **Password mahery** ny administrateur; aza mampizara azy.
- Aza manao *port forwarding* (tsy tokony ho renivohitra amin'ny internet).
- Aza mitady ny app amin'ny Wi-Fi mivantana (café) — ampiasao ny *VPN* raha ilaina.
- Ny angona dia ao amin'ny PC-n'ny serveur: ny mpampiana dia tsy mahita ny
  rakitra `data/` (tsy misy *static file serving* amin'ny dossier `data/`).
- Vakiana ny journal-n'ny Windows Defender raha misy olona tsy fantatra.
- Manàna «backup» isam-bolana automatika + kopia grefy.

> **Fanamarihana:** ny fidirana dia mifototra amin'ny `st.session_state` (araka ny
> fangatahanao). Noho izany, ny rechargement-n'ny pejy dia tsy mitohy ny session →
> **mila miditra indray**. Raha ilaina ny fidirana mandrakizay, dia ny
> `st.login()` (OpenID Connect) no mety — fa mila internet sy mpizara identity.

---

## 8. Fanamarinana ny app

```bat
venv\Scripts\python test_app.py
```

Ny teste dia miasa amin'ny **angona tampon** (copie ao amin'ny dossier
`RAPPORT_DATA_DIR`) — ny angona velona dia tsy miova. Voamarina:

- ny app dia manomboka ary mampiseho ny pejy fidirana (tsy misy dashboard raha tsy
  voasoratra ny mpampiana);
- fidirana: password tsy mety → hafatra d'iditra, password mety → miditra,
  fivoahana → miverina amin'ny pejy fidirana;
- ny pejy 7 rehetra dia miasa;
- ny kajy (mambra_tonga, isan_tonga, asa_fitorina, tsy tara %) dia mitovy amin'ny
  version tehatro;
- famoronana/fanofana/fafana ny angona, ary ny cache dia mava avy hatrany;
- backup + restauration;
- export PDF + PowerPoint;
- hashing PBKDF2 sy ny lockout rehefa betsaka ny fanadramana.

---

## 9. Fanontaniana matetika

**Tsy mahita ny angona aorian'ny ny namadika ny classe.**
Hidiova ve ny pejy (`st.rerun()`) — ny classe vaovao dia tokony hiseho avy hatrany.
Raha mbola tsy hita: jereo ny anarana (misy litera lehibe) sy ny daty.

**Tsy afaka miditra.**
Jereo: ny anaran'ny mpampiana, ny password, ary ny terminal-n'ny serveur (raha
voahidy ny fidirana noho ny fanadramana: andraso 60 segondra kely, mihameno).

**Very ny angona.**
Pejy Administration → "💾 Sauvegardes" → restaura ny backup. Ny backup rehetra
dia ao amin'ny `backups/`.

**Tsy mba mitondra ny «backup» isam-bolana.**
Jereo `backups/.last_weekly.json` — raha tsy misy na outdated dia manomboka ny
server indray ny app.

**Ny app dia miresaka amin'ny internet.**
Tsy izany no izy — esory ny `--server.address 0.0.0.0` ary esory ny
`[browser] gatherUsageStats = false` amin'ny `.streamlit/config.toml` (efa atao).

---

## 10. Fomba fanentanana ny rafitra

```
app.py             Page principale : konfig, fidirana, sidebar, navigation, 7 pejy
auth.py            Hash PBKDF2, mpampiana, lockout, code fanombohana
storage.py         Sabata.csv/classes.json, cache @st.cache_data, backup, restauration
manage_users.py    CLI : list / add / passwd / role / delete / setup-code
logo.png.jpg       Logo ny app (sidebar + pejy fidirana)
data/              Angona (sabata.csv, classes.json, users.json…)
backups/           Backup automatika (daty sy ora ao amin'ny anarana)
test_app.py        Fanamarinana (AppTest)
LISEZ_MOI.txt      Fanamarihana fohy ho an'ny mpampiasa
```
