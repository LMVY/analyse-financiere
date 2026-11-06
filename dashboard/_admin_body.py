"""Parametrage : configuration des profils et ratios (accessible a tous).

PRESENTATION RAPPORT FINANCIER, ALIGNEE SUR LA PAGE ANALYSE :
- meme langage visuel que _analyse_body.py : h1 + soulignement anime,
  sous-titre, onglets soulignes, boutons et tableaux identiques ;
- double filet sous l'en-tete, bandeaux de section a filet encre
  portant leur compte, sous-sections de categorie a filet leger ;
- un seul accent, couleurs reservees au sens (ok / warn / neutre) ;
- grilles de saisie dans des conteneurs bordes : en-tete filet encre,
  filet hairline sous chaque ligne, colonnes superposees, libelles
  complets visibles ;
- tables de l'Apercu dessinees en HTML (en-tete, hairlines, chiffres
  tabulaires, colonne Part animee par categorie).

FONCTIONNEL :
- poids des profils dans une grille editable (une rangee par profil),
  validation regroupee sous la grille : nom, barre de poids, somme,
  normalisation en un clic ;
- ratios et referentiels edites ligne par ligne (case a cocher,
  champs numeriques), validation en direct : somme des poids, ordre
  Q1 <= mediane <= Q3, valeurs incompletes ;
- secteurs choisis par pastilles pleine largeur, identite du secteur
  (libelle, prefixes NAF) au-dessus des grilles de ratios ;
- notification en toast qui survit au rerun ; reinitialisation qui
  purge TOUS les widgets d'edition (retour effectif aux valeurs de
  reference).

Contrat fonctionnel inchange : cles de session new_profils /
new_ratios / new_secteurs, structure de data/config_user.yaml,
libelles metier du glossaire (src/reporting/glossaire).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import yaml

from src.visualization.colors import THEME, CATEGORIES
from src.reporting.glossaire import label_ratio, label_categorie

PROFILS_PATH = ROOT / "config" / "profils.yaml"
RATIOS_PATH = ROOT / "config" / "ratios_config.yaml"
SECTEURS_PATH = ROOT / "config" / "secteurs_config.yaml"
USER_PATH = ROOT / "data" / "config_user.yaml"

FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"

root_vars = "".join(f"--{k}:{v};" for k, v in THEME.items())

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
    :root {""" + root_vars + """}

    html, body, .stApp, [class*="css"] { font-family: """ + FONT + """; }
    .stApp { background: var(--bg); color: var(--ink); }
    #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1080px; padding-top: 2.2rem; padding-bottom: 4rem; }

    h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.015em; font-weight: 650; }
    h1 { font-size: 1.9rem; margin: 0; }
    hr { border-color: var(--line) !important; }

    /* Apparition douce du contenu */
    @keyframes apparition { from { opacity: 0; transform: translateY(6px); }
                            to { opacity: 1; transform: none; } }
    .block-container { animation: apparition .45s ease-out; }

    /* Surtitre du bandeau : petites capitales accentuees */
    .cfg-kicker { font-size: .68rem; font-weight: 700;
                  letter-spacing: .16em; text-transform: uppercase;
                  color: var(--accent); margin-bottom: .2rem; }

    .sub { color: var(--muted); font-size: .95rem; margin-top: .3rem; }

    /* Double filet d'en-tete : signature rapport financier */
    .masthead-rule { border-top: 2.5px solid var(--ink);
                     border-bottom: 1px solid var(--ink);
                     height: 4px; margin: 1rem 0 1.1rem; }

    /* Bandeaux de section : filet fort, repere de lecture majeur */
    .section-t { display: flex; justify-content: space-between;
                 align-items: baseline; gap: 1rem; flex-wrap: wrap;
                 font-size: .74rem; font-weight: 700;
                 letter-spacing: .07em; text-transform: uppercase;
                 color: var(--ink);
                 border-bottom: 2px solid var(--ink);
                 padding-bottom: .4rem; margin: 1.5rem 0 .9rem; }
    .section-t small { font-size: .74rem; font-weight: 600;
                       letter-spacing: .02em; color: var(--muted);
                       text-transform: none; }

    /* Onglets : soulignes, identiques a la page Analyse */
    [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid var(--line); }
    button[role="tab"] { padding: .55rem 0; color: var(--muted); font-weight: 500; background: transparent; }
    button[role="tab"][aria-selected="true"] { color: var(--ink); font-weight: 600; }
    [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
    [data-baseweb="tab-border"] { display: none; }

    /* Boutons : identiques a la page Analyse */
    .stButton > button, .stDownloadButton > button,
    [data-testid="stButton"] > button, [data-testid="stDownloadButton"] > button {
        border-radius: 8px; font-weight: 600; border: 1px solid var(--line);
        background: var(--paper); color: var(--ink); box-shadow: none;
        transition: border-color .15s, color .15s, background .15s; }
    .stButton > button:hover, .stDownloadButton > button:hover,
    [data-testid="stButton"] > button:hover, [data-testid="stDownloadButton"] > button:hover {
        border-color: var(--accent); color: var(--accent); }
    .stButton > button[kind="primary"] { background: var(--ink); border-color: var(--ink); color: #fff; }
    .stButton > button[kind="primary"]:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
    .stDownloadButton > button, [data-testid="stDownloadButton"] > button {
        border-color: var(--accent); color: var(--accent); font-weight: 650; }
    .stDownloadButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
        background: var(--accent); border-color: var(--accent); color: #fff; }
    button:focus-visible { outline: 2px solid var(--accent) !important;
                           outline-offset: 2px; }

    /* Popover (Reinitialiser) */
    div[data-testid="stPopoverBody"] { background: var(--paper);
                                       border: 1px solid var(--line);
                                       border-radius: 12px;
                                       padding: 1rem 1.2rem;
                                       box-shadow: 0 8px 24px rgba(15,23,42,.08); }
    [data-testid="stPopover"] > button { transition: border-color .15s, color .15s; }

    /* Selects */
    [data-baseweb="select"] > div { border-radius: 8px; background: var(--paper);
                                    border-color: var(--line); box-shadow: none; }

    /* Champs texte */
    [data-testid="stTextInput"] label { color: var(--muted);
                                        font-size: .82rem; font-weight: 500;
                                        margin-bottom: .2rem; }
    [data-testid="stTextInput"] [data-baseweb="input"] { border-radius: 8px;
                                                         background: var(--paper); }
    [data-testid="stTextInput"] [data-baseweb="input"] > div:first-child {
        border-color: var(--line); background: var(--paper); border-radius: 8px; }
    [data-testid="stTextInput"] [data-baseweb="input"]:focus-within > div:first-child {
        border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }

    /* Pastilles de statut : reservees au sens (ok / warn / neutre) */
    .cfg-pill { display: inline-flex; align-items: center; gap: .45rem;
                font-size: .78rem; font-weight: 650; border-radius: 99px;
                padding: .25rem .8rem; }
    .cfg-dot { width: .55rem; height: .55rem; border-radius: 99px;
               display: inline-block; flex: none; }

    /* Sous-section categorie : pastille couleur + libelle + compte,
       filet leger (repere de lecture secondaire) */
    .cfg-cat { display: flex; align-items: center; gap: .55rem;
               flex-wrap: wrap; border-bottom: 1px solid var(--line);
               padding-bottom: .35rem; margin: 1.15rem 0 .7rem; }
    .cfg-cat-t { font-weight: 650; font-size: .95rem; }
    .cfg-cat-note { margin-left: auto; display: inline-flex;
                    align-items: center; gap: .4rem; flex-wrap: wrap; }

    /* Barre de poids empilee : mise a jour IMMEDIATE a chaque saisie */
    .cfg-stack { display: flex; height: 10px; border-radius: 99px;
                 overflow: hidden; margin: .5rem 0 .1rem; background: var(--bg); }
    .cfg-stack i { display: block; height: 100%; }

    /* Bloc de validation : se lit comme un tableau (entete + lignes) */
    .cfg-check-head, .cfg-check { display: flex;
                                  align-items: center; gap: .8rem; }
    .cfg-check-head { font-size: .68rem; font-weight: 700;
                      letter-spacing: .06em; text-transform: uppercase;
                      color: var(--muted);
                      border-bottom: 1px solid var(--line);
                      padding-bottom: .35rem; margin-bottom: .1rem; }
    .cfg-check { padding: .45rem 0;
                 border-bottom: 1px solid var(--line); }
    .cfg-check:last-of-type { border-bottom: none; }
    .cfg-check-name, .cfg-check-head .h-name { width: 11rem; flex: none; }
    .cfg-check-name { font-weight: 650; font-size: .9rem; }
    .cfg-check-bar, .cfg-check-head .h-bar { flex: 1; min-width: 0; }
    .cfg-check-bar { display: block; }
    .cfg-check-bar .cfg-stack { margin: 0; height: 8px; }
    .cfg-check-sum, .cfg-check-head .h-sum { width: 12rem; flex: none;
                                            text-align: right;
                                            font-variant-numeric:
                                                tabular-nums; }
    .cfg-check-sum { font-weight: 650; font-size: .88rem; }
    .cfg-check-sum small { font-weight: 500; color: var(--muted); }

    /* Tables rapport (lecture seule, Apercu) : finition main */
    .cfg-table-wrap { border: 1px solid var(--line); border-radius: 12px;
                      overflow: hidden; background: var(--paper);
                      box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
                      margin-bottom: 1.1rem; }
    .cfg-table { width: 100%; border-collapse: collapse; font-size: .9rem; }
    .cfg-table th { font-size: .68rem; font-weight: 700;
                    letter-spacing: .06em; text-transform: uppercase;
                    color: var(--muted); text-align: left;
                    padding: .55rem .7rem;
                    border-bottom: 2px solid var(--ink); }
    .cfg-table td { padding: .55rem .7rem; color: #1E293B;
                    border-bottom: 1px solid #F1F5F9; }
    .cfg-table tr:last-child td { border-bottom: none; }
    .cfg-table th.num, .cfg-table td.num { text-align: right;
                                           font-variant-numeric:
                                               tabular-nums; }
    .cfg-table td.num { font-weight: 500; }
    .cfg-barcell { width: 28%; }
    .cfg-track { height: 6px; background: var(--bg); border-radius: 99px;
                 overflow: hidden; }
    .cfg-fill { height: 100%; border-radius: 99px; }

    /* Grilles de saisie (Profils, Ratios, Secteurs) : ALIGNEMENT
       TABLEAU - meme hauteur de rangee pour textes, cases et champs,
       les lignes se superposent d'une colonne a l'autre */
    [data-testid="stHorizontalBlock"]:has([data-testid="stNumberInput"]),
    [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) {
        border-bottom: 1px solid var(--line); }
    /* filets verticaux : chaque colonne des grilles est tracee
       (descendantes du conteneur borde, en-tete compris) ; la
       derniere colonne reste ouverte, le conteneur ferme a droite */
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stColumn"]:not(:last-child) {
        border-right: 1px solid var(--line); }
    .cfg-col-head { font-size: .68rem; font-weight: 700;
                    letter-spacing: .06em; text-transform: uppercase;
                    color: var(--muted);
                    border-bottom: 2px solid var(--ink);
                    padding: .1rem 0 .4rem; margin-bottom: .4rem;
                    line-height: 1.3; text-align: center;
                    /* hauteur fixe, texte cale en bas : le filet
                       d'en-tete est une ligne DROITE sur toute la
                       largeur, quels que soient les libelles */
                    height: 2.2rem; display: flex;
                    align-items: flex-end; justify-content: center; }
    .cfg-cell { font-size: .9rem; color: #1E293B;
                height: 2.6rem; display: flex;
                align-items: center; }
    .cfg-cell b { font-weight: 650; }
    .cfg-cell.r { justify-content: center;
                  font-variant-numeric: tabular-nums; }
    .cfg-cell.muted { color: var(--muted); }
    /* hauteur de rangee fixe et identique pour tout ; champs et cases
       CENTRES sous leurs en-tetes centres */
    [data-testid="stNumberInput"] { height: 2.6rem; display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    margin-bottom: 0; }
    [data-testid="stCheckbox"] { height: 2.6rem; display: flex;
                                 align-items: center;
                                 justify-content: center;
                                 margin-bottom: 0; }

    @media (max-width: 1024px) {
        .block-container { max-width: 920px; }
    }

    @media (max-width: 760px) {
        .block-container { max-width: 100%; padding: 1.2rem 1rem 3rem; }
        h1 { font-size: 1.35rem; }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important;
                                            gap: .6rem !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"] > div { width: 100% !important;
                                                  flex: none !important;
                                                  max-width: 100% !important; }
        [data-baseweb="tab-list"] { gap: 1.1rem; overflow-x: auto;
                                    -webkit-overflow-scrolling: touch;
                                    scrollbar-width: none; }
        [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        /* colonnes empilees : plus de filet vertical */
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stColumn"] {
            border-right: none; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# OUTILS
# ============================================================
def load_yaml(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False)


def _yaml_eq(a, b):
    """Comparaison legere de deux structures YAML."""
    return (yaml.dump(a, sort_keys=True, default_flow_style=False) ==
            yaml.dump(b, sort_keys=True, default_flow_style=False))


def _pill(texte: str, couleur: str):
    """Pastille de statut, reservee au sens : ok / warn / neutre."""
    return (f'<span class="cfg-pill" style="color:{couleur};'
            f'background:{couleur}1A">'
            f'<span class="cfg-dot" style="background:{couleur}"></span>'
            f'{texte}</span>')


def _fnum(v):
    """Nombre YAML -> float (None reste None) : evite l'avertissement
    NumberInput (int affiche comme int malgre le format %.2f)."""
    return None if v is None else float(v)


def _cat_header(cat: str, extra: str = ""):
    """En-tete de carte categorie : pastille couleur + libelle metier."""
    couleur = CATEGORIES.get(cat, THEME["accent"])
    libelle = label_categorie(cat) if cat != "autres" else "Autres ratios"
    return (f'<div class="cfg-cat">'
            f'<span class="cfg-dot" style="background:{couleur};'
            f'width:.7rem;height:.7rem"></span>'
            f'<span class="cfg-cat-t">{libelle}</span>'
            f'<span class="cfg-cat-note">{extra}</span></div>')


def _barre_poids(poids: dict):
    """Barre empilee LIVE : une couleur par categorie.

    Rendue a chaque affichage, elle reflete immediatement les saisies
    en cours (les widgets Streamlit declenchent un rerun).
    """
    total = sum(poids.values())
    seg = ""
    for cat, val in poids.items():
        if total <= 0 or not val:
            continue
        largeur = val / total * 100
        if largeur < 0.5:
            continue
        seg += (f'<i style="width:{largeur:.1f}%;'
                f'background:{CATEGORIES.get(cat, THEME["accent"])}"></i>')
    if not seg:
        seg = f'<i style="width:100%;background:{THEME["line"]}"></i>'
    return f'<div class="cfg-stack">{seg}</div>'


# ============================================================
# CHARGEMENT + ETAT (defaut / personnalisee / non enregistree)
# ============================================================
user_cfg = load_yaml(USER_PATH)
profils = (user_cfg.get("profils") or load_yaml(PROFILS_PATH))
ratios_cfg = (user_cfg.get("ratios") or load_yaml(RATIOS_PATH))
secteurs = (user_cfg.get("secteurs") or load_yaml(SECTEURS_PATH))
config_user_active = bool(user_cfg)

if not profils:
    st.error("Aucun profil charge depuis config/profils.yaml")
    st.stop()
if not ratios_cfg.get("categories"):
    st.error("Aucune categorie dans config/ratios_config.yaml")
    st.stop()
if not secteurs:
    st.error("Aucun secteur charge depuis config/secteurs_config.yaml")
    st.stop()

categories = list(ratios_cfg.get("categories", {}).keys())

# Modifications en cours, section par section
courant = {
    "profils": st.session_state.get("new_profils", profils),
    "ratios": st.session_state.get("new_ratios", ratios_cfg),
    "secteurs": st.session_state.get("new_secteurs", secteurs),
}
modif_sections = []
if not _yaml_eq(courant["profils"], profils):
    modif_sections.append("profils")
if not _yaml_eq(courant["ratios"], ratios_cfg):
    modif_sections.append("ratios")
if not _yaml_eq(courant["secteurs"], secteurs):
    modif_sections.append("secteurs")
modifie = bool(modif_sections)

# ============================================================
# EN-TETE + ACTIONS
# ============================================================
if modifie:
    etat_html = _pill("Modifications non enregistrees (" +
                      ", ".join(modif_sections) + ")", THEME["warn"])
elif config_user_active:
    etat_html = _pill("Configuration personnalisee active", THEME["ok"])
else:
    etat_html = _pill("Configuration par defaut", THEME["muted"])
st.markdown('<div class="cfg-kicker">FinView</div>'
            '<div style="display:flex;justify-content:space-between;'
            'align-items:flex-end;flex-wrap:wrap;gap:.6rem">'
            '<h1>Parametrage</h1>' + etat_html + '</div>'
            "<div class='sub'>Profils d'analyse, ratios actifs et "
            "referentiels sectoriels - chaque modification se voit en "
            "direct.</div>"
            '<div class="masthead-rule"></div>', unsafe_allow_html=True)

# Notification flash (survit au rerun : sauvegarde / reinitialisation)
flash = st.session_state.pop("cfg_flash", None)
if flash:
    try:
        st.toast(flash)
    except Exception:
        st.success(flash)

act1, act2 = st.columns([1, 1], gap="medium")

with act1:
    sauvegarder = st.button("Sauvegarder", type="primary",
                            use_container_width=True)

with act2:
    with st.popover("Reinitialiser", use_container_width=True):
        st.markdown("**Remettre la configuration initiale**")
        st.caption("Supprime vos modifications (profils, ratios et "
                   "referentiels sectoriels) et revient aux valeurs de "
                   "reference. Action definitive.")
        if st.button("Confirmer la reinitialisation",
                     type="primary", use_container_width=True):
            if USER_PATH.exists():
                USER_PATH.unlink()
            # purge COMPLETE : configurations en cours + tous les widgets
            # d'edition, sinon les saisies persistaient apres reset
            for cle in ("new_profils", "new_ratios", "new_secteurs",
                        "sect_choice", "cfg_flash"):
                st.session_state.pop(cle, None)
            for cle in list(st.session_state.keys()):
                if cle.startswith(("prof_", "p_", "norm_", "rat_",
                                   "sect_", "ratio_sect_ref")):
                    st.session_state.pop(cle, None)
            st.session_state["cfg_flash"] = (
                "Configuration reinitialisee aux valeurs par defaut.")
            st.rerun()

if sauvegarder:
    save_yaml(USER_PATH, courant)
    st.session_state["cfg_flash"] = (
        f"Configuration enregistree : {USER_PATH.relative_to(ROOT)}")
    st.rerun()

st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

# ============================================================
# ONGLETS
# ============================================================
tab_profils, tab_ratios, tab_secteurs, tab_apercu = st.tabs(
    ["Profils", "Ratios actifs", "Secteurs", "Apercu"])

# ------------------------------------------------------------
# PROFILS : grille editable + validation LIVE sous la grille
# ------------------------------------------------------------
with tab_profils:
    st.markdown('<div class="section-t" style="margin-top:.2rem">'
                'Poids des categories par profil'
                f'<small>{len(profils)} profils &middot; cible : somme '
                'de 1.00 par profil</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Saisissez les poids ; "Normaliser les '
                'profils invalides" ramene les sommes a 1.00.</div>',
                unsafe_allow_html=True)

    # grille de saisie : une rangee de colonnes par ligne, dans un
    # conteneur borde - libelles et valeurs toujours visibles
    proportions = [0.24] + [0.152] * len(categories)

    with st.container(border=True):
        tete = st.columns(proportions, gap="medium")
        with tete[0]:
            st.markdown('<div class="cfg-col-head">Profil</div>',
                        unsafe_allow_html=True)
        for i, cat in enumerate(categories):
            coul = CATEGORIES.get(cat, THEME["accent"])
            with tete[i + 1]:
                st.markdown(f'<div class="cfg-col-head">'
                            f'<span style="display:inline-flex;'
                            f'align-items:center;gap:.35rem">'
                            f'<span class="cfg-dot" '
                            f'style="background:{coul}"></span>'
                            f'{label_categorie(cat)}</span></div>',
                            unsafe_allow_html=True)

        # lecture retour : widget -> poids, validation regroupee
        new_profils = {}
        etats = []
        for nom, info in profils.items():
            label = info.get("label", nom)
            poids_cfg = info.get("poids_categories", {})
            ligne = st.columns(proportions, gap="medium")
            with ligne[0]:
                st.markdown(f'<div class="cfg-cell"><b>{label}</b></div>',
                            unsafe_allow_html=True)
            poids = {}
            for i, cat in enumerate(categories):
                with ligne[i + 1]:
                    poids[cat] = st.number_input(
                        f"Poids {label} - {label_categorie(cat)}",
                        min_value=0.0, max_value=1.0,
                        value=round(float(poids_cfg.get(cat, 0.0)), 2),
                        step=0.05, format="%.2f",
                        label_visibility="collapsed",
                        key=f"p_{nom}_{cat}")
            new_profils[nom] = {**info, "poids_categories": poids}
            etats.append((label, nom, poids, sum(poids.values())))

    # bloc de validation : entete + une ligne reglee par profil
    entete = ('<div class="cfg-check-head">'
              '<span class="h-name">Profil</span>'
              '<span class="h-bar">Repartition des poids</span>'
              '<span class="h-sum">Somme</span></div>')
    lignes, invalides = "", []
    for label, nom, poids, total in etats:
        ok = abs(total - 1.0) <= 0.005
        coul = THEME["ok"] if ok else THEME["warn"]
        som = (f"{total:.2f}" if ok else
               f"{total:.2f} <small>cible 1.00</small>")
        if not ok and total > 0:
            invalides.append((nom, poids, total))
        lignes += (f'<div class="cfg-check">'
                   f'<span class="cfg-check-name">{label}</span>'
                   f'<span class="cfg-check-bar">{_barre_poids(poids)}'
                   f'</span>'
                   f'<span class="cfg-check-sum" style="color:{coul}">'
                   f'{som}</span></div>')
    st.markdown(entete + lignes, unsafe_allow_html=True)

    # un seul geste : normalise tous les profils invalides
    if invalides:
        if st.button("Normaliser les profils invalides"):
            for nom, poids, total in invalides:
                for cat, v in poids.items():
                    st.session_state[f"p_{nom}_{cat}"] = round(v / total, 2)
            st.rerun()

    st.session_state["new_profils"] = new_profils

# ------------------------------------------------------------
# RATIOS : sous-sections par categorie + grilles editables LIVE
# ------------------------------------------------------------
with tab_ratios:
    n_ratios_definis = sum(len(ratios_cfg.get(cat, {}))
                           for cat in categories)
    st.markdown('<div class="section-t" style="margin-top:.2rem">'
                'Ratios actifs et poids internes'
                f'<small>{n_ratios_definis} ratios &middot; '
                f'{len(categories)} categories</small></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub">Cochez les ratios du score et ajustez '
                'leur poids dans la categorie.</div>', unsafe_allow_html=True)

    # reference sectorielle : mediane affichee EN FACE de chaque ratio,
    # depuis le referentiel en cours d'edition (mise a jour directe)
    secteurs_ref = st.session_state.get("new_secteurs", secteurs)
    codes_ref = list(secteurs_ref.keys())
    labels_ref = {c: (secteurs_ref[c].get("label") or c) for c in codes_ref}
    sec_ref = st.selectbox(
        "Secteur de reference (mediane affichee)",
        codes_ref, format_func=lambda c: labels_ref[c],
        key="ratio_sect_ref")

    new_ratios = {k: v for k, v in ratios_cfg.items()
                  if k != "categories"}
    new_categories = {}

    for cat, cat_info in ratios_cfg.get("categories", {}).items():
        actifs = cat_info.get("ratios_actifs", [])
        details = ratios_cfg.get(cat, {})
        if not details:
            continue
        ref_sect = (secteurs_ref.get(sec_ref) or {}).get("ratios") or {}

        compte = _pill(f"{len(actifs)} / {len(details)} actifs",
                       CATEGORIES.get(cat, THEME["accent"]))
        st.markdown(_cat_header(cat, extra=compte), unsafe_allow_html=True)

        # grille de saisie : une rangee par ratio, colonnes alignees
        proportions_rat = [0.09, 0.53, 0.16, 0.22]
        with st.container(border=True):
            tete = st.columns(proportions_rat, gap="medium")
            with tete[0]:
                st.markdown('<div class="cfg-col-head">Actif</div>',
                            unsafe_allow_html=True)
            with tete[1]:
                st.markdown('<div class="cfg-col-head">Ratio</div>',
                            unsafe_allow_html=True)
            with tete[2]:
                st.markdown('<div class="cfg-col-head">Poids</div>',
                            unsafe_allow_html=True)
            with tete[3]:
                st.markdown('<div class="cfg-col-head">Mediane secteur'
                            '</div>', unsafe_allow_html=True)

            sel_actifs = []
            for r in details:
                libelle = label_ratio(r)
                poids_defaut = float((details.get(r) or {})
                                     .get("poids", 0.0))
                med = (ref_sect.get(r) or {}).get("mediane")
                ligne = st.columns(proportions_rat, gap="medium")
                with ligne[0]:
                    if st.checkbox(libelle, value=r in actifs,
                                   key=f"rat_act_{cat}_{r}",
                                   label_visibility="collapsed"):
                        sel_actifs.append(r)
                with ligne[1]:
                    st.markdown(f'<div class="cfg-cell">{libelle}</div>',
                                unsafe_allow_html=True)
                with ligne[2]:
                    p = st.number_input(
                        f"Poids {libelle}", min_value=0.0, max_value=1.0,
                        value=poids_defaut, step=0.01, format="%.2f",
                        label_visibility="collapsed",
                        key=f"rat_poids_{cat}_{r}")
                with ligne[3]:
                    med_txt = (f"{med:.2f}" if med is not None
                               else "&mdash;")
                    st.markdown(f'<div class="cfg-cell r muted">'
                                f'{med_txt}</div>', unsafe_allow_html=True)
                if cat in new_ratios and r in new_ratios[cat]:
                    new_ratios[cat][r]["poids"] = float(p)

        new_categories[cat] = {"ratios_actifs": sel_actifs}

    new_ratios["categories"] = new_categories
    st.session_state["new_ratios"] = new_ratios

    n_actifs_total = sum(len(i.get("ratios_actifs", []))
                         for i in new_categories.values())
    st.caption(f"Score fonde sur {n_actifs_total} ratios actifs au total.")

# ------------------------------------------------------------
# SECTEURS : selecteur en pastilles + edition pleine largeur
# ------------------------------------------------------------
with tab_secteurs:
    new_secteurs = st.session_state.get("new_secteurs")
    if new_secteurs is None:
        new_secteurs = {code: dict(info) for code, info in secteurs.items()}

    codes_secteurs = list(secteurs.keys())

    st.markdown('<div class="section-t" style="margin-top:.2rem">'
                'Referentiels sectoriels'
                f'<small>{len(codes_secteurs)} secteurs</small></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub">Mediane et quartiles par ratio : '
                'benchmarks du scoring sectoriel. La validation (ordre '
                'Q1 <= mediane <= Q3) se fait pendant la saisie.</div>',
                unsafe_allow_html=True)

    # ---- Selecteur : pastilles pleine largeur, un secteur visible -
    if st.session_state.get("sect_choice") not in codes_secteurs:
        st.session_state["sect_choice"] = codes_secteurs[0]
    sec = st.session_state["sect_choice"]

    def _pastille(col, code):
        info = new_secteurs.get(code) or {}
        libelle = info.get("label") or code
        if col.button(libelle, key=f"sect_btn_{code}",
                      type="primary" if code == sec else "secondary",
                      use_container_width=True):
            st.session_state["sect_choice"] = code
            st.rerun()

    # rangees completes de 4, puis la derniere rangee CENTREE : les
    # pastilles restantes occupent des colonnes medianes de meme
    # largeur (1/4 de la page), le solde se repartit de part et d'autre
    PAR_LIGNE = 4
    n_complets = len(codes_secteurs) // PAR_LIGNE
    reste = len(codes_secteurs) % PAR_LIGNE

    idx = 0
    for _ in range(n_complets):
        pastilles = st.columns(PAR_LIGNE, gap="small")
        for j in range(PAR_LIGNE):
            _pastille(pastilles[j], codes_secteurs[idx])
            idx += 1

    if reste:
        if reste == 1:
            proportions, positions = [0.375, 0.25, 0.375], [1]
        elif reste == 2:
            proportions, positions = ([0.25, 0.25, 0.25, 0.25],
                                       [1, 2])
        else:
            proportions, positions = ([0.125, 0.25, 0.25, 0.25, 0.125],
                                       [1, 2, 3])
        pastilles = st.columns(proportions, gap="small")
        for pos in positions:
            _pastille(pastilles[pos], codes_secteurs[idx])
            idx += 1

    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

    # ---- Identite du secteur selectionne -------------------------
    infos = new_secteurs.get(sec) or {}
    ratios_sec = dict(infos.get("ratios") or {})
    desactives_sec = list(infos.get("ratios_desactives") or [])

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        new_label = st.text_input("Libelle du secteur",
                                  value=infos.get("label", sec),
                                  key=f"sect_label_{sec}")
    with c2:
        prefixes_txt = ", ".join(infos.get("code_naf_prefix") or [])
        new_prefixes = st.text_input(
            "Prefixes NAF (sections, separees par des virgules)",
            value=prefixes_txt, key=f"sect_naf_{sec}")

    naf = [p.strip().upper() for p in new_prefixes.split(",")
           if p.strip()]
    ligne_identite = (f"<b>{len(ratios_sec)}</b> ratios definis"
                      f" &middot; <b>{len(desactives_sec)}</b> desactives"
                      + (f" &middot; NAF : {', '.join(naf)}"
                         if naf else ""))
    st.markdown(f'<div class="sub" style="margin:.1rem 0 .3rem">'
                f'{ligne_identite}</div>', unsafe_allow_html=True)

    # ratios regroupes par categorie (meme ordre et memes couleurs
    # que l'onglet Ratios actifs), complete par ceux du referentiel
    ordre_config = [r for cat in categories
                    for r in ratios_cfg.get(cat, {})]
    union = {r for s in secteurs.values()
             for r in (s.get("ratios") or {})}
    tous_ratios = list(dict.fromkeys(ordre_config + sorted(union)))
    groupes = [(cat, [r for r in ratios_cfg.get(cat, {})
                       if r in tous_ratios])
               for cat in categories]
    connus = {r for _, rs in groupes for r in rs}
    hors_config = [r for r in tous_ratios if r not in connus]
    if hors_config:
        groupes.append(("autres", hors_config))

    # validation LIVE en une passe (pas un avertissement par ligne)
    problemes = []
    new_ratios_sec, new_desactives = {}, []
    for cat, rs in groupes:
        if not rs:
            continue
        couleur = CATEGORIES.get(cat, THEME["accent"])
        n_desact_g = sum(1 for r in rs if r in desactives_sec)
        compte = _pill(f"{len(rs)} ratios", couleur)
        if n_desact_g:
            compte += _pill(f"{n_desact_g} desactives", THEME["muted"])
        st.markdown(_cat_header(cat, extra=compte),
                    unsafe_allow_html=True)

        # grille de saisie : une rangee par ratio, colonnes alignees
        proportions_sect = [0.4, 0.14, 0.12, 0.12, 0.22]
        with st.container(border=True):
            tete = st.columns(proportions_sect, gap="medium")
            with tete[0]:
                st.markdown('<div class="cfg-col-head">Ratio</div>',
                            unsafe_allow_html=True)
            for j, t in enumerate(("Mediane", "Q1", "Q3")):
                with tete[j + 1]:
                    st.markdown(f'<div class="cfg-col-head">{t}</div>',
                                unsafe_allow_html=True)
            with tete[4]:
                st.markdown('<div class="cfg-col-head">Desactive</div>',
                            unsafe_allow_html=True)

            for r in rs:
                libelle = label_ratio(r)
                ref = ratios_sec.get(r) or {}
                ligne = st.columns(proportions_sect, gap="medium")
                with ligne[0]:
                    st.markdown(f'<div class="cfg-cell">{libelle}</div>',
                                unsafe_allow_html=True)
                with ligne[1]:
                    med = st.number_input(
                        f"Mediane {libelle}", value=_fnum(ref.get("mediane")),
                        format="%.2f", label_visibility="collapsed",
                        key=f"sect_med_{sec}_{r}")
                with ligne[2]:
                    q1v = st.number_input(
                        f"Q1 {libelle}", value=_fnum(ref.get("q1")),
                        format="%.2f", label_visibility="collapsed",
                        key=f"sect_q1_{sec}_{r}")
                with ligne[3]:
                    q3v = st.number_input(
                        f"Q3 {libelle}", value=_fnum(ref.get("q3")),
                        format="%.2f", label_visibility="collapsed",
                        key=f"sect_q3_{sec}_{r}")
                with ligne[4]:
                    des = st.checkbox(
                        f"Desactive {libelle}", value=r in desactives_sec,
                        label_visibility="collapsed",
                        key=f"sect_des_{sec}_{r}")

                if des:
                    new_desactives.append(r)
                if med is None and q1v is None and q3v is None:
                    continue
                if med is None or q1v is None or q3v is None:
                    problemes.append(f"{libelle} : valeurs incompletes")
                elif not (q1v <= med <= q3v):
                    problemes.append(
                        f"{libelle} : ordre attendu Q1 <= mediane <= Q3")
                else:
                    # conserve les champs annexes du referentiel
                    # (source), ne remplace que les bornes
                    new_ratios_sec[r] = {**ratios_sec.get(r, {}),
                                         "mediane": float(med),
                                         "q1": float(q1v),
                                         "q3": float(q3v)}

    if problemes:
        st.markdown(_pill(f"{len(problemes)} ligne(s) a corriger",
                         THEME["warn"]) +
                    '<div class="sub" style="margin-top:.5rem">'
                    + "<br>".join(problemes) + '</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(_pill("Referentiel coherent - Q1 <= mediane <= Q3 "
                         "partout", THEME["ok"]), unsafe_allow_html=True)

    st.caption("Sources : Banque de France - fascicules de resultats "
               "sectoriels 2024, base FIBEN ; industrie : fascicule "
               "division 28 (machines), donnees 2023. Delais de "
               "reglement : references BdF en TTC, calculs en HT.")

    new_secteurs[sec] = {
        "label": new_label, "code_naf_prefix": naf,
        "ratios": new_ratios_sec, "ratios_desactives": new_desactives,
    }
    st.session_state["new_secteurs"] = new_secteurs

# ------------------------------------------------------------
# APERCU : configuration effective, en tables
# ------------------------------------------------------------
with tab_apercu:
    profils_eff = st.session_state.get("new_profils", profils)
    ratios_eff = st.session_state.get("new_ratios", ratios_cfg)
    secteurs_eff = st.session_state.get("new_secteurs", secteurs)
    n_actifs_eff = sum(len(i.get("ratios_actifs", []))
                       for i in (ratios_eff.get("categories") or {}).values())

    st.markdown('<div class="section-t" style="margin-top:.2rem">'
                'Apercu de la configuration effective'
                f'<small>{len(profils_eff)} profils &middot; '
                f'{n_actifs_eff} ratios actifs &middot; '
                f'{len(secteurs_eff)} referentiels</small></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub">Ce qui sera applique a la prochaine '
                'analyse si vous sauvegardez maintenant.</div>',
                unsafe_allow_html=True)

    # Profils : meme gabarit que la validation de l'onglet Profils
    st.markdown('<div class="section-t">Profils</div>', unsafe_allow_html=True)
    lignes_profils = ('<div class="cfg-check-head">'
                      '<span class="h-name">Profil</span>'
                      '<span class="h-bar">Repartition des poids</span>'
                      '<span class="h-sum">Somme</span></div>')
    for nom, info in profils_eff.items():
        poids = info.get("poids_categories", {})
        total = sum(poids.values())
        ok = abs(total - 1.0) <= 0.005
        couleur = THEME["ok"] if ok else THEME["warn"]
        lignes_profils += (f'<div class="cfg-check">'
                           f'<span class="cfg-check-name">'
                           f'{info.get("label", nom)}</span>'
                           f'<span class="cfg-check-bar">'
                           f'{_barre_poids(poids)}</span>'
                           f'<span class="cfg-check-sum" '
                           f'style="color:{couleur}">{total:.2f}</span>'
                           f'</div>')
    st.markdown(lignes_profils, unsafe_allow_html=True)

    # Ratios actifs par categorie : table rapport, finition main
    n_definis_eff = sum(len(ratios_eff.get(cat, {}))
                        for cat in (ratios_eff.get("categories") or {}))
    st.markdown('<div class="section-t">Ratios actifs par categorie'
                f'<small>{n_definis_eff} ratios definis</small></div>',
                unsafe_allow_html=True)
    corps_t = ""
    for cat, info in (ratios_eff.get("categories") or {}).items():
        actifs = info.get("ratios_actifs", [])
        total_cat = len(ratios_eff.get(cat, {}))
        pct = (len(actifs) / total_cat * 100) if total_cat else 0.0
        coul = CATEGORIES.get(cat, THEME["accent"])
        barre = (f'<div class="cfg-track"><div class="cfg-fill" '
                 f'style="width:{max(0.0, min(100.0, pct)):.0f}%;'
                 f'background:{coul}"></div></div>')
        corps_t += (f'<tr><td><span class="cfg-dot" '
                    f'style="background:{coul};margin-right:.5rem"></span>'
                    f'{label_categorie(cat)}</td>'
                    f'<td class="num">{len(actifs)}</td>'
                    f'<td class="num">{total_cat}</td>'
                    f'<td class="cfg-barcell">{barre}</td></tr>')
    st.markdown('<div class="cfg-table-wrap"><table class="cfg-table">'
                '<thead><tr><th>Categorie</th>'
                '<th class="num">Actifs</th>'
                '<th class="num">Definis</th><th>Part</th></tr></thead>'
                f'<tbody>{corps_t}</tbody></table></div>',
                unsafe_allow_html=True)

    # Referentiels sectoriels : table rapport
    st.markdown('<div class="section-t">Referentiels sectoriels'
                f'<small>{len(secteurs_eff)} secteurs</small></div>',
                unsafe_allow_html=True)
    corps_s = ""
    for code, info in secteurs_eff.items():
        n_definis = len(info.get("ratios") or {})
        n_desact = len(info.get("ratios_desactives") or [])
        corps_s += (f'<tr><td>{info.get("label", code)}</td>'
                    f'<td class="num">{n_definis}</td>'
                    f'<td class="num">{n_desact}</td></tr>')
    st.markdown('<div class="cfg-table-wrap"><table class="cfg-table">'
                '<thead><tr><th>Referentiel</th>'
                '<th class="num">Ratios definis</th>'
                '<th class="num">Desactives</th></tr></thead>'
                f'<tbody>{corps_s}</tbody></table></div>',
                unsafe_allow_html=True)
    st.caption("Le scoring sectoriel compare chaque ratio a la "
               "distribution Q1 / mediane / Q3 de son secteur ; il "
               "prime sur les grilles standard des que le secteur de "
               "l'entreprise est connu.")
