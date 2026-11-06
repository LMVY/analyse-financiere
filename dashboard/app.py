"""Dashboard Streamlit - Launcher avec navigation par onglets."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st


st.set_page_config(
    page_title="FinView",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Configuration locale (.env) : chargee avant la lecture des cles.
import os
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

# Cle Mistral : sur Streamlit Cloud, elle vit dans Settings > Secrets ;
# on la reprend dans l'environnement si le .env local ne l'a pas fournie.
try:
    if not os.environ.get("MISTRAL_API_KEY"):
        os.environ["MISTRAL_API_KEY"] = st.secrets["MISTRAL_API_KEY"]
except Exception:
    pass


def _secret(nom):
    """Valeur depuis l'environnement ou les secrets Streamlit."""
    try:
        return os.environ.get(nom) or st.secrets.get(nom)
    except Exception:
        return os.environ.get(nom)


# Acces protege : si APP_PASSWORD est definie (env ou secrets),
# l'app exige le mot de passe ; sinon elle reste ouverte.
# Indispensable des que le port est expose (0.0.0.0 ou tunnel).
_mdp = _secret("APP_PASSWORD")
if _mdp and not st.session_state.get("acces_ok"):
    st.markdown("<h1 style='margin-bottom:.2rem'>FinView</h1>"
                "<p style='color:#64748b'>Acces protege par mot de passe</p>",
                unsafe_allow_html=True)
    with st.form("acces"):
        saisie = st.text_input("Mot de passe", type="password")
        ouvrir = st.form_submit_button("Ouvrir FinView")
    if ouvrir:
        if saisie == _mdp:
            st.session_state.acces_ok = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()


# Navigation : boutons radio horizontaux en haut du contenu.
# Aucune restriction d'acces : Analyse et Parametrage sont ouverts a tous.
page = st.radio(
    "Navigation",
    ["Analyse", "Paramétrage"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_page",
)

# Styles globaux puis rendu de la page selectionnee.
from dashboard.styles import injecter_base  # noqa: E402
from dashboard.page_analyse import afficher as afficher_analyse  # noqa: E402
from dashboard.page_parametrage import afficher as afficher_parametrage  # noqa: E402

injecter_base()
if page == "Analyse":
    afficher_analyse()
else:
    afficher_parametrage()
