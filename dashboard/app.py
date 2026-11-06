"""Dashboard Streamlit - Launcher avec navigation par onglets."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.visualization.colors import THEME  # noqa: E402

FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"

st.set_page_config(
    page_title="FinView",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
    :root {
        --bg: #""" + THEME["bg"].lstrip("#") + """;
        --paper: #""" + THEME["paper"].lstrip("#") + """;
        --ink: #""" + THEME["ink"].lstrip("#") + """;
        --muted: #""" + THEME["muted"].lstrip("#") + """;
        --line: #""" + THEME["line"].lstrip("#") + """;
        --accent: #""" + THEME["accent"].lstrip("#") + """;
    }
    html, body, .stApp, [class*="css"] { font-family: """ + FONT + """; }

    /* En-tete d'application : la navigation flotte en HAUT A DROITE,
       sur la meme ligne visuelle que le titre de page (h1, a gauche).
       Plus d'empilement navigation / barre / titre. */
    .stApp .block-container { padding-top: 1.35rem !important; position: relative; }
    [data-testid="stHorizontalRadio"] {
        position: absolute; top: 1rem; right: 1.6rem; z-index: 5;
        box-shadow: 0 1px 2px rgba(15, 23, 42, .05);
    }

    /* Navigation : radio horizontal en pastilles segmentees,
       icones vectorielles modernes (suivent la couleur du libelle) */
    [data-testid="stHorizontalRadio"] { gap: .25rem; background: var(--paper); border: 1px solid var(--line);
                                        border-radius: 10px; padding: .25rem; width: fit-content;
                                        flex-wrap: wrap; }
    [data-testid="stHorizontalRadio"] > label { background: transparent; border-radius: 8px;
                                                padding: .35rem 1.1rem; cursor: pointer; }
    [data-testid="stHorizontalRadio"] > label > div:first-child { display: none; }
    [data-testid="stHorizontalRadio"] > label > div:last-child { padding: 0; font-size: .92rem;
                                                                 font-weight: 600; color: var(--muted);
                                                                 display: inline-flex; align-items: center;
                                                                 gap: .45rem; }
    [data-testid="stHorizontalRadio"] > label:hover > div:last-child { color: var(--ink); }
    [data-testid="stHorizontalRadio"] > label:has(input:checked) { background: var(--ink); }
    [data-testid="stHorizontalRadio"] > label:has(input:checked) > div:last-child { color: #fff; }

    [data-testid="stHorizontalRadio"] > label:nth-of-type(1) > div:last-child::before,
    [data-testid="stHorizontalRadio"] > label:nth-of-type(2) > div:last-child::before {
        content: ""; width: 1.05em; height: 1.05em; display: inline-block;
        background: currentColor; flex: none;
        -webkit-mask-position: center; -webkit-mask-repeat: no-repeat;
        -webkit-mask-size: contain; mask-position: center;
        mask-repeat: no-repeat; mask-size: contain;
    }
    [data-testid="stHorizontalRadio"] > label:nth-of-type(1) > div:last-child::before {
        -webkit-mask-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 3v16a2 2 0 0 0 2 2h16'/%3E%3Cpath d='m7 14 3-3 3 3 5-6'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 3v16a2 2 0 0 0 2 2h16'/%3E%3Cpath d='m7 14 3-3 3 3 5-6'/%3E%3C/svg%3E");
    }
    [data-testid="stHorizontalRadio"] > label:nth-of-type(2) > div:last-child::before {
        -webkit-mask-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='21' y1='4' x2='14' y2='4'/%3E%3Cline x1='10' y1='4' x2='3' y2='4'/%3E%3Cline x1='21' y1='12' x2='12' y2='12'/%3E%3Cline x1='8' y1='12' x2='3' y2='12'/%3E%3Cline x1='21' y1='20' x2='16' y2='20'/%3E%3Cline x1='12' y1='20' x2='3' y2='20'/%3E%3Cline x1='14' y1='2' x2='14' y2='6'/%3E%3Cline x1='8' y1='10' x2='8' y2='14'/%3E%3Cline x1='16' y1='18' x2='16' y2='22'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='21' y1='4' x2='14' y2='4'/%3E%3Cline x1='10' y1='4' x2='3' y2='4'/%3E%3Cline x1='21' y1='12' x2='12' y2='12'/%3E%3Cline x1='8' y1='12' x2='3' y2='12'/%3E%3Cline x1='21' y1='20' x2='16' y2='20'/%3E%3Cline x1='12' y1='20' x2='3' y2='20'/%3E%3Cline x1='14' y1='2' x2='14' y2='6'/%3E%3Cline x1='8' y1='10' x2='8' y2='14'/%3E%3Cline x1='16' y1='18' x2='16' y2='22'/%3E%3C/svg%3E");
    }

    /* Responsive : sur petit ecran la navigation redevient statique
       et se place au-dessus du titre (pas de chevauchement) */
    @media (max-width: 900px) {
        .block-container { max-width: 100%; padding: 1.1rem 1rem 3rem; }
        [data-testid="stHorizontalRadio"] { position: static; width: 100%; margin-bottom: .7rem; }
        [data-testid="stHorizontalRadio"] > label { flex: 1; text-align: center; }
    }
</style>
""", unsafe_allow_html=True)

# Navigation : boutons radio horizontaux en haut du contenu.
# Aucune restriction d'acces : Analyse et Parametrage sont ouverts a tous.
page = st.radio(
    "Navigation",
    ["Analyse", "Paramétrage"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_page",
)

# Executer le body correspondant
HERE = Path(__file__).parent
if page == "Analyse":
    body_path = HERE / "_analyse_body.py"
else:
    body_path = HERE / "_admin_body.py"

code = body_path.read_text(encoding="utf-8")
exec(compile(code, str(body_path), "exec"))
