"""Admin : configuration des profils et ratios (refonte).

Meme theme visuel que la page Analyse. Organise en :
- Etat de la configuration (defaut ou utilisateur) ;
- Actions : sauvegarder, reinitialiser (confirmation), exporter ;
- Onglets Profils / Ratios / Apercu.
"""
import sys
import io
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import yaml

from src.visualization.colors import THEME

PROFILS_PATH = ROOT / "config" / "profils.yaml"
RATIOS_PATH = ROOT / "config" / "ratios_config.yaml"
USER_PATH = ROOT / "data" / "config_user.yaml"

FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
    html, body, .stApp, [class*="css"] { font-family: """ + FONT + """; }
    .stApp { background: #""" + THEME["bg"].lstrip("#") + """; color: #""" + THEME["ink"].lstrip("#") + """; }
    #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1080px; padding-top: 2.2rem; padding-bottom: 4rem; }
    h1 { font-size: 1.7rem; margin: 0; letter-spacing: -0.015em; }
    hr { border-color: #""" + THEME["line"].lstrip("#") + """ !important; }

    [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid #""" + THEME["line"].lstrip("#") + """; }
    button[role="tab"] { padding: .6rem 0; color: #""" + THEME["muted"].lstrip("#") + """; font-weight: 500; background: transparent; }
    button[role="tab"][aria-selected="true"] { color: #""" + THEME["ink"].lstrip("#") + """; font-weight: 600; }
    [data-baseweb="tab-highlight"] { background: #""" + THEME["accent"].lstrip("#") + """; height: 2px; }
    [data-baseweb="tab-border"] { display: none; }

    .stButton > button { border-radius: 8px; font-weight: 600; border: 1px solid #""" + THEME["line"].lstrip("#") + """;
                          background: #FFFFFF; color: #""" + THEME["ink"].lstrip("#") + """; box-shadow: none; }
    .stButton > button:hover { border-color: #""" + THEME["accent"].lstrip("#") + """; color: #""" + THEME["accent"].lstrip("#") + """; }
    .stButton > button[kind="primary"] { background: #""" + THEME["ink"].lstrip("#") + """; border-color: #""" + THEME["ink"].lstrip("#") + """; color: #fff; }

    .adm-card { background: #FFFFFF; border: 1px solid #""" + THEME["line"].lstrip("#") + """;
                border-radius: 12px; padding: 1.1rem 1.4rem; margin-bottom: 1rem; }
    .adm-title { font-size: 1.05rem; font-weight: 650; margin-bottom: .3rem; }
    .adm-sub { color: #""" + THEME["muted"].lstrip("#") + """; font-size: .88rem; }
    .adm-kv { display: flex; gap: .6rem; font-size: .85rem; color: #""" + THEME["muted"].lstrip("#") + """;
              font-variant-numeric: tabular-nums; }
    .adm-kv b { color: #""" + THEME["ink"].lstrip("#") + """; }
</style>
""", unsafe_allow_html=True)


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


# ============================================================
# EN-TETE + ETAT DE LA CONFIGURATION
# ============================================================
st.markdown("<h1>Configuration</h1>", unsafe_allow_html=True)
st.markdown('<div class="adm-sub">Profils d\'analyse, ratios actifs et '
            'sauvegarde de la configuration.</div>', unsafe_allow_html=True)
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

user_cfg = load_yaml(USER_PATH)
config_user_active = bool(user_cfg)

if config_user_active:
    profils = user_cfg.get("profils") or load_yaml(PROFILS_PATH)
    ratios_cfg = user_cfg.get("ratios") or load_yaml(RATIOS_PATH)
    source_html = f"""
    <div class="adm-card">
      <div class="adm-title" style="color:{THEME['accent']}">Configuration personnalisee active</div>
      <div class="adm-sub">Vos modifications sont appliquees aux analyses.</div>
    </div>"""
else:
    profils = load_yaml(PROFILS_PATH)
    ratios_cfg = load_yaml(RATIOS_PATH)
    source_html = f"""
    <div class="adm-card">
      <div class="adm-title" style="color:{THEME['muted']}">Configuration par defaut active</div>
      <div class="adm-sub">Aucune modification utilisateur enregistree :
          les valeurs de reference sont utilisees.</div>
    </div>"""
st.markdown(source_html, unsafe_allow_html=True)

if not profils:
    st.error("Aucun profil charge depuis config/profils.yaml")
    st.stop()
if not ratios_cfg.get("categories"):
    st.error("Aucune categorie dans config/ratios_config.yaml")
    st.stop()

# ============================================================
# ACTIONS
# ============================================================
act1, act2, act3 = st.columns([1, 1, 1], gap="medium")

with act1:
    sauvegarder = st.button("Sauvegarder mes modifications",
                            type="primary", use_container_width=True)

with act2:
    with st.popover("Reinitialiser la configuration",
                   use_container_width=True):
        st.markdown("**Remettre la configuration initiale**")
        st.caption("Supprime vos modifications (profils et ratios) et "
                   "revient aux valeurs de reference. Action definitive.")
        if st.button("Confirmer la reinitialisation",
                     type="primary", use_container_width=True):
            if USER_PATH.exists():
                USER_PATH.unlink()
            for cle in ("new_profils", "new_ratios"):
                st.session_state.pop(cle, None)
            st.success("Configuration reinitialisee aux valeurs par defaut.")
            st.rerun()

with act3:
    exporter = st.button("Exporter la configuration (YAML)",
                         use_container_width=True)

if sauvegarder:
    new_config = {
        "profils": st.session_state.get("new_profils", profils),
        "ratios": st.session_state.get("new_ratios", ratios_cfg),
    }
    save_yaml(USER_PATH, new_config)
    st.success(f"Sauvegarde enregistree : {USER_PATH}")
    st.rerun()

if exporter:
    export_cfg = {
        "profils": st.session_state.get("new_profils", profils),
        "ratios": st.session_state.get("new_ratios", ratios_cfg),
    }
    buf = io.BytesIO()
    buf.write(yaml.dump(export_cfg, default_flow_style=False,
                        allow_unicode=True, sort_keys=False).encode("utf-8"))
    st.download_button("Telecharger le fichier", data=buf.getvalue(),
                      file_name="config_user.yaml", mime="text/yaml")

st.divider()

# ============================================================
# ONGLETS
# ============================================================
tab_profils, tab_ratios, tab_apercu = st.tabs(
    ["Profils d'analyse", "Ratios actifs", "Apercu de la configuration"])

# ------------------------------------------------------------
# PROFILS
# ------------------------------------------------------------
with tab_profils:
    st.markdown('<div class="adm-title">Poids des categories par profil</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="adm-sub">La somme des 6 categories doit faire '
                '1.00. Les poids determinent la contribution de chaque '
                'categorie au score global.</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    categories = list(ratios_cfg.get("categories", {}).keys())
    new_profils = {}

    for profil_nom, profil_info in profils.items():
        label = profil_info.get("label", profil_nom)
        with st.expander(f"{label}", expanded=(profil_nom == "moyen_terme")):
            st.caption(profil_info.get("description", ""))
            poids = profil_info.get("poids_categories", {})
            new_poids = {}

            cols = st.columns(3)
            for i, cat in enumerate(categories):
                with cols[i % 3]:
                    cat_label = cat.replace("_", " ").title()
                    val = float(poids.get(cat, 0.0))
                    new_poids[cat] = st.slider(
                        cat_label, 0.0, 1.0, val, 0.01,
                        key=f"p_{profil_nom}_{cat}",
                    )

            total = sum(new_poids.values())
            if abs(total - 1.0) > 0.01:
                st.warning(f"Somme = {total:.2f} (doit etre 1.00). "
                           "Ajustez les curseurs ou normalisez.")
                if st.button("Normaliser automatiquement",
                             key=f"norm_{profil_nom}"):
                    facteur = total if total > 0 else 1
                    for k in new_poids:
                        new_poids[k] = round(new_poids[k] / facteur, 2)
                    st.rerun()
            else:
                st.success(f"Somme = {total:.2f}")

            new_profils[profil_nom] = {**profil_info,
                                       "poids_categories": new_poids}

    st.session_state["new_profils"] = new_profils

# ------------------------------------------------------------
# RATIOS
# ------------------------------------------------------------
with tab_ratios:
    st.markdown('<div class="adm-title">Ratios actifs et poids internes</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="adm-sub">Cochez les ratios a utiliser dans le '
                'score et ajustez leur poids relatif dans la '
                'categorie.</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    categories_dict = ratios_cfg.get("categories", {})
    new_categories = {}

    for cat, cat_info in categories_dict.items():
        ratios_actifs = cat_info.get("ratios_actifs", [])
        ratios_details = ratios_cfg.get(cat, {})

        titre = (f"{cat.replace('_', ' ').title()} "
                 f"({len(ratios_actifs)} actifs / {len(ratios_details)} total)")
        with st.expander(titre, expanded=False):
            if not ratios_details:
                st.warning(f"Aucun ratio defini pour '{cat}'")
                continue

            selected = []
            for ratio in ratios_details:
                c1, c2 = st.columns([1, 3])
                with c1:
                    actif = ratio in ratios_actifs
                    new_actif = st.checkbox(ratio, value=actif,
                                            key=f"act_{cat}_{ratio}")
                with c2:
                    if new_actif:
                        val = float(ratios_details[ratio].get("poids", 0.0))
                        ratios_cfg[cat][ratio]["poids"] = st.slider(
                            "Poids relatif", 0.0, 1.0, val, 0.01,
                            key=f"pds_{cat}_{ratio}")
                        selected.append(ratio)

            new_categories[cat] = {"ratios_actifs": selected}

    ratios_cfg["categories"] = new_categories
    st.session_state["new_ratios"] = ratios_cfg

# ------------------------------------------------------------
# APERCU
# ------------------------------------------------------------
with tab_apercu:
    st.markdown('<div class="adm-title">Apercu de la configuration effective</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="adm-sub">Ce qui sera applique a la prochaine '
                'analyse (modifications en cours incluses).</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    profils_eff = st.session_state.get("new_profils", profils)
    ratios_eff = st.session_state.get("new_ratios", ratios_cfg)

    gauche, droite = st.columns(2, gap="large")
    with gauche:
        st.markdown('<div class="adm-title">Profils</div>', unsafe_allow_html=True)
        for nom, info in profils_eff.items():
            poids = info.get("poids_categories", {})
            total = sum(poids.values())
            st.markdown(
                f"<div class='adm-kv'><b>{info.get('label', nom)}</b> "
                f"&middot; somme des poids = {total:.2f}</div>",
                unsafe_allow_html=True)
        st.caption("Somme attendue : 1.00 par profil.")

    with droite:
        st.markdown('<div class="adm-title">Ratios actifs par categorie</div>',
                    unsafe_allow_html=True)
        for cat, info in (ratios_eff.get("categories") or {}).items():
            actifs = info.get("ratios_actifs", [])
            st.markdown(
                f"<div class='adm-kv'>{cat.replace('_', ' ').title()} : "
                f"<b>{len(actifs)}</b> actifs</div>",
                unsafe_allow_html=True)

    st.divider()
    st.markdown(
        f"<div class='adm-sub'>Fichiers : profils et seuils de reference dans "
        f"<b>config/</b> &middot; votre configuration dans "
        f"<b>{USER_PATH.relative_to(ROOT)}</b> "
        f"({'presente' if USER_PATH.exists() else 'absente'}).</div>",
        unsafe_allow_html=True)
