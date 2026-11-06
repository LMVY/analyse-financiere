"""
Dashboard Streamlit - Analyse financière (v2)
Direction : rapport de gestion clair, aéré, un seul accent, couleurs de statut réservées au sens.
"""
import sys
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent if Path(__file__).parent.parent.exists() else Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# 1. THÈME
# ============================================================
# 1. THÈME (source unique : src/visualization/colors.py)
# ============================================================
from src.visualization.colors import THEME, CATEGORIES, tint_hex, get_score_gradient


def score_color(s):
    """Couleur CONTINUE d'un score : rouge (0) -> ambre (40) -> vert (70+).

    Plus fin que 3 niveaux : les barres 'Score par categorie', l'anneau
    et le verdict suivent le degradé, harmonises avec le PDF.
    """
    return get_score_gradient(s)

T = dict(THEME)
FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"


def hex_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def verdict(s):
    if s >= 70:
        return "Situation solide"
    if s >= 40:
        return "Situation à surveiller"
    return "Situation fragile"



root_vars = "".join(f"--{k}:{v};" for k, v in T.items())
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
    :root {""" + root_vars + """}

    html, body, .stApp, [class*="css"] { font-family: """ + FONT + """; }
    .stApp { background: var(--bg); color: var(--ink); }
    #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }

    h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.015em; font-weight: 650; }
    h1 { font-size: 1.7rem; margin: 0; }
    hr { border-color: var(--line) !important; }

    /* Presentation dynamique : apparition douce + soulignement anime */
    @keyframes apparition { from { opacity: 0; transform: translateY(6px); }
                            to { opacity: 1; transform: none; } }
    .block-container { animation: apparition .45s ease-out; }
    @keyframes trace { from { width: 0; } to { width: 4.5rem; } }
    h1 { position: relative; display: inline-block; padding-bottom: .35rem; }
    h1::after { content: ""; position: absolute; left: 0; bottom: 0;
                height: 3px; width: 4.5rem; border-radius: 99px;
                background: linear-gradient(90deg, var(--accent), var(--bg));
                animation: trace .8s ease-out .15s both; }

    /* Onglets */
    [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid var(--line); }
    button[role="tab"] { padding: .6rem 0; color: var(--muted); font-weight: 500; background: transparent; }
    button[role="tab"][aria-selected="true"] { color: var(--ink); font-weight: 600; }
    [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
    [data-baseweb="tab-border"] { display: none; }

    /* Boutons */
    .stButton > button, .stDownloadButton > button,
    [data-testid="stButton"] > button, [data-testid="stDownloadButton"] > button {
        border-radius: 8px; font-weight: 600; border: 1px solid var(--line);
        background: var(--paper); color: var(--ink); box-shadow: none;
    }
    .stButton > button:hover, .stDownloadButton > button:hover,
    [data-testid="stButton"] > button:hover, [data-testid="stDownloadButton"] > button:hover {
        border-color: var(--accent); color: var(--accent);
    }
    .stButton > button[kind="primary"] { background: var(--ink); border-color: var(--ink); color: #fff; }
    .stButton > button[kind="primary"]:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
    /* Telechargement du rapport : bouton accent visible, survol qui
       ECLAIRCIT - jamais le bleu fonce par defaut de Streamlit */
    .stDownloadButton > button, [data-testid="stDownloadButton"] > button {
        border-color: var(--accent); color: var(--accent); font-weight: 650;
    }
    .stDownloadButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
        background: var(--accent); border-color: var(--accent); color: #fff;
    }
    .stDownloadButton > button[kind="primary"],
    [data-testid="stDownloadButton"] > button[kind="primary"] {
        background: var(--accent); border-color: var(--accent); color: #fff;
    }
    .stDownloadButton > button[kind="primary"]:hover,
    [data-testid="stDownloadButton"] > button[kind="primary"]:hover {
        background: #6366F1; border-color: #6366F1; color: #fff;
    }
    button:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

    /* Uploader */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--paper); border: 1px dashed #C5CBD6; border-radius: 12px; padding: 2rem;
    }
    [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--accent); }

    /* Textes natifs (anglais) de la zone de dépôt : masques et
       remplaces par du francais */
    [data-testid="stFileUploaderInstructions"],
    [data-testid="stFileUploaderDropzone"] > div > small,
    [data-testid="stFileUploaderDropzone"] > div:not(:has(button)) {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"]::before {
        content: "Glissez-déposez vos fichiers ici \\A Limite 200 Mo par fichier • PDF, JPG, JPEG, PNG, XLSX, XLSM";
        white-space: pre-line;
        display: block; width: 100%;
        text-align: center; color: var(--muted); font-size: .88rem;
        margin-bottom: .8rem;
    }

    /* Bouton "Parcourir les fichiers" : meme style que le bouton
       "T\00e9l\00e9charger le PDF" - accent au repos, rempli en accent
       au survol, retour visuel au clic (focus) */
    [data-testid="stFileUploaderDropzone"] button {
        background: var(--paper) !important;
        border: 1px solid var(--accent) !important;
        border-radius: 8px; color: var(--accent); font-weight: 650;
        box-shadow: none !important;
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: var(--accent) !important;
        border-color: var(--accent) !important; color: #fff !important;
    }
    [data-testid="stFileUploaderDropzone"] button:focus:not(:hover) {
        background: var(--paper) !important; color: var(--accent);
    }
    /* libelle francais du bouton natif (masque + reinjecte) */
    [data-testid="stFileUploaderDropzone"] button span,
    [data-testid="stFileUploaderDropzone"] button p {
        font-size: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] button span::after,
    [data-testid="stFileUploaderDropzone"] button p::after {
        content: "Parcourir les fichiers";
        font-size: .84rem !important; font-weight: 650;
    }

    [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 10px; background: var(--paper); }

    /* Composants maison */
    .sub { color: var(--muted); font-size: .95rem; margin-top: .25rem; }
    .ring-wrap { display: flex; align-items: center; gap: 2.1rem; }
    .verdict { font-size: 1.5rem; font-weight: 650; letter-spacing: -.01em; }
    .verdict-sub { color: var(--muted); margin-top: .4rem; max-width: 30ch; line-height: 1.45; }
    .meta { color: var(--muted); font-size: .85rem; margin-top: .35rem; }
    .meta b { color: var(--ink); }

    .rd-hs { font-variant-numeric: tabular-nums; }

    .rt-wrap { background: var(--paper); border: 1px solid var(--line);
               border-radius: 10px; overflow-x: auto; margin-bottom: 1rem; }
    .rt-cat { display: flex; justify-content: space-between; align-items: baseline;
               padding: .55rem .95rem .45rem; font-weight: 650; font-size: .92rem; }
    /* Tableau des ratios : largeurs de colonnes en pourcentages
       (colgroup partage) - les scores /100 demarrent au meme point
       partout ; min-width garantit que les valeurs ne sont jamais
       ecrasees (defilement horizontal sur petit ecran) */
    table.rt { width: 100%; min-width: 700px; border-collapse: collapse;
               font-size: .84rem; table-layout: fixed; }
    table.rt th { text-align: right; padding: .38rem .95rem;
                  color: var(--muted); font-weight: 600; font-size: .74rem;
                  text-transform: uppercase; letter-spacing: .04em;
                  border-bottom: 1px solid var(--line); }
    table.rt th:first-child { text-align: left; }
    table.rt td { padding: .36rem .95rem; text-align: right;
                  border-bottom: 1px solid var(--line);
                  font-variant-numeric: tabular-nums; white-space: nowrap; }
    table.rt td:first-child { text-align: left; white-space: normal; }
    /* largeurs fixes : les valeurs tres longues ne debordent jamais
       sur la colonne voisine (rognage propre) */
    table.rt td:not(:first-child) { overflow: hidden; text-overflow: ellipsis; }
    table.rt tbody tr:last-child td { border-bottom: none; }
    table.rt tbody tr:hover td { background: var(--bg); }
    .rt-tag { color: var(--muted); font-size: .68rem; border: 1px solid var(--line);
              border-radius: 99px; padding: 0 .4rem; margin-left: .45rem;
              text-transform: uppercase; letter-spacing: .04em; }
    .rt-bar { display: inline-block; width: 48px; height: 7px; border-radius: 99px;
              background: var(--line); vertical-align: middle; margin-right: .5rem;
              overflow: hidden; }
    .rt-bar i { display: block; height: 100%; border-radius: 99px; }
    .rt-sc { font-weight: 700; font-variant-numeric: tabular-nums; }

    /* Controles de coherence : cartes par categorie de test */
    .ctl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem 1.2rem; }
    .ctl-wrap { background: var(--paper); border: 1px solid var(--line);
                border-radius: 10px; overflow: hidden; }
    .ctl-cat { display: flex; justify-content: space-between; align-items: baseline;
               padding: .55rem .95rem .45rem; font-weight: 650; font-size: .92rem;
               border-bottom: 1px solid var(--line); }
    .ctl-sum { font-size: .74rem; font-weight: 600; text-transform: uppercase;
               letter-spacing: .04em; }
    .ctl-row { display: flex; gap: .6rem; padding: .45rem .95rem;
               border-bottom: 1px solid var(--line); align-items: flex-start;
               font-size: .85rem; }
    .ctl-row:nth-child(even) { background: var(--bg); }
    .ctl-row:last-child { border-bottom: none; }
    .ctl-badge { flex: none; font-size: .66rem; font-weight: 700; text-transform: uppercase;
                 letter-spacing: .04em; border-radius: 99px; padding: .14rem .55rem;
                 margin-top: .1rem; }
    .ctl-t { font-weight: 600; color: var(--ink); }
    .ctl-m { color: var(--muted); font-size: .79rem; margin-top: .1rem; line-height: 1.4; }

    .kpi-grid { display: grid; grid-template-columns: 1fr 1fr; background: var(--paper);
                border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
    .kpi { padding: 1.25rem 1.5rem; }
    .kpi:nth-child(odd) { border-right: 1px solid var(--line); }
    .kpi:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
    .kpi-l { color: var(--muted); font-size: .85rem; font-weight: 500; }
    .kpi-v { font-size: 1.65rem; font-weight: 700; letter-spacing: -.02em;
             font-variant-numeric: tabular-nums; margin-top: .2rem; }
    .kpi-d { font-size: .8rem; font-weight: 600; margin-top: .15rem; font-variant-numeric: tabular-nums; }

    .row { display: grid; grid-template-columns: 11rem 1fr 3.5rem; align-items: center; gap: 1rem;
           padding: .8rem 0; border-bottom: 1px solid var(--line); }
    .row:last-child { border-bottom: none; }
    .row-l { font-weight: 500; }
    .row-v { text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }
    .track { height: 6px; background: var(--line); border-radius: 99px; overflow: hidden; }
    .fill { height: 100%; border-radius: 99px; }

    .alert { display: flex; gap: .8rem; align-items: flex-start; padding: .85rem 0;
             border-bottom: 1px solid var(--line); line-height: 1.45; }
    .alert:last-child { border-bottom: none; }
    .dot { width: 8px; height: 8px; border-radius: 99px; margin-top: .5rem; flex: none; }
    .alert-lvl { color: var(--muted); font-size: .8rem; font-weight: 600; }

    .stat { display: inline-block; margin-right: 2.5rem; }
    .stat b { display: block; font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .stat span { color: var(--muted); font-size: .85rem; }
    .section-t { font-size: 1.05rem; font-weight: 650; margin: 1.75rem 0 .5rem; }

    /* Responsive : tablette */
    @media (max-width: 1024px) {
        .steps { grid-template-columns: 1fr; max-width: 620px; }
        .block-container { max-width: 920px; }
    }

    /* Responsive : mobile - les colonnes Streamlit s'empilent */
    @media (max-width: 760px) {
        .block-container { max-width: 100%; padding: 1.2rem 1rem 3rem; }
        h1 { font-size: 1.35rem; }
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important; gap: .6rem !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"] > div {
            width: 100% !important; flex: none !important; max-width: 100% !important; }
        [data-baseweb="tab-list"] { gap: 1.1rem; overflow-x: auto;
                                    -webkit-overflow-scrolling: touch; scrollbar-width: none; }
        [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .hero { padding: 1.4rem .5rem 1rem; }
        .hero-t { font-size: 1.3rem; }
        .ring-wrap { flex-wrap: wrap; gap: 1.4rem; justify-content: center; }
        .verdict { font-size: 1.3rem; }
        .kpi { padding: 1rem 1.1rem; }
        .kpi-v { font-size: 1.4rem; }
        .stat { margin-right: 1.4rem; display: inline-block; margin-bottom: .4rem; }
        .stat b { font-size: 1.3rem; }
        .row { grid-template-columns: 1fr 3.5rem; }
        .row .track { grid-column: 1 / -1; order: 3; }
        .ctl-grid { grid-template-columns: 1fr; }
        .section-t { font-size: 1rem; }
        [data-testid="stPlotlyChart"] { padding: .6rem .4rem .25rem; }
    }

    /* Responsive : tres petits ecrans - KPI en colonne unique */
    @media (max-width: 480px) {
        .kpi-grid { grid-template-columns: 1fr; }
        .kpi:nth-child(odd) { border-right: none; }
        .kpi:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
        .kpi:last-child { border-bottom: none; }
    }

    /* Titres de section : tiret accent */
    .section-t::before { content: ""; display: inline-block; width: 1rem; height: .45rem;
                         border-radius: 99px; background: var(--accent); margin-right: .55rem;
                         vertical-align: .12em; }

    /* Etat initial : accueil + etapes */
    .hero { text-align: center; padding: 2.4rem 1rem 1.4rem; }
    .hero-t { font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; color: var(--ink); }
    .hero-s { color: var(--muted); margin: .5rem auto 0; max-width: 60ch; font-size: .95rem; line-height: 1.5; }
    .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;
             margin: 1.7rem auto 0; max-width: 960px; }
    .step { background: var(--paper); border: 1px solid var(--line); border-radius: 14px;
            padding: 1.15rem 1.25rem; text-align: left; }
    .step b { display: block; font-size: .95rem; font-weight: 650; margin-bottom: .3rem; }
    .step .step-s { color: var(--muted); font-size: .85rem; line-height: 1.45; }
    .step-n { display: inline-flex; width: 1.65rem; height: 1.65rem; align-items: center;
              justify-content: center; border-radius: 99px; background: var(--accent);
              color: #fff; font-size: .8rem; font-weight: 700; margin-bottom: .65rem; }

    /* Graphiques en cartes : RIEN ne doit deborder de la carte au
       survol (carte de survol plotly comprise) */
    [data-testid="stPlotlyChart"] { background: var(--paper); border: 1px solid var(--line);
                                    border-radius: 14px; padding: .9rem .9rem .35rem;
                                    overflow: hidden; }
    [data-testid="stPlotlyChart"] .js-plotly-plot { overflow: hidden; }
    [data-testid="stPlotlyChart"] .plotly .modebar { opacity: 0; transition: opacity .2s; }
    [data-testid="stPlotlyChart"]:hover .plotly .modebar { opacity: .6; }

    /* Tableaux (dataframe) */
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px;
                                  overflow: hidden; background: var(--paper); }
    [data-testid="stDataFrame"] [class*="dgc-header-cell"] {
        background: var(--bg); color: var(--muted); font-size: .72rem; font-weight: 650;
        letter-spacing: .05em; text-transform: uppercase; border-bottom: 1px solid var(--line);
        border-right: 1px solid var(--line); }
    [data-testid="stDataFrame"] [class*="dgc-cell"] { font-size: .88rem;
        border-right: 1px solid rgba(226,232,240,.55); }
    [data-testid="stDataFrame"] [class*="dgc-number-cell"] { font-variant-numeric: tabular-nums; }

    /* Badges (methode de score) */
    .badge { display: inline-flex; align-items: center; gap: .35rem; padding: .2rem .75rem;
             border-radius: 99px; font-size: .78rem; font-weight: 600;
             background: rgba(79,70,229,.08); color: var(--accent);
             border: 1px solid rgba(79,70,229,.18); margin-bottom: .55rem; margin-right: .4rem; }
    .badge.neutre { background: var(--bg); color: var(--muted); border-color: var(--line); }

    /* Lignes de categories : pastille + survol */
    .row-l { display: flex; align-items: center; gap: .5rem; }
    .cat-dot { width: 9px; height: 9px; border-radius: 99px; flex: none; }
    .row { transition: background .15s; border-radius: 8px; }
    .row:hover { background: rgba(79,70,229,.03); }
    .kpi { transition: background .15s; }
    .kpi:hover { background: rgba(79,70,229,.03); }

    /* Selects (filtres, options) */
    [data-baseweb="select"] > div { border-radius: 8px; background: var(--paper);
                                    border-color: var(--line); box-shadow: none; }

    /* Popover (Options) */
    div[data-testid="stPopoverBody"] { background: var(--paper); border: 1px solid var(--line);
                                       border-radius: 12px; padding: 1rem 1.2rem;
                                       box-shadow: 0 8px 24px rgba(15,23,42,.08); }
    [data-testid="stPopover"] > button { transition: border-color .15s, color .15s; }

    /* Zone de depot */
    [data-testid="stFileUploaderDropzone"] { transition: border-color .15s; }
    [data-testid="stFileUploaderDropzone"] > button {
        border: none; background: var(--bg); color: var(--ink);
        font-weight: 600; border-radius: 8px; padding: .45rem 1rem; }
    [data-testid="stFileUploaderDropzone"] > button:hover { color: var(--accent); }
    [data-testid="stFileUploaderDropzone"] span[data-testid="stFileUploaderDropzoneCaption"] {
        color: var(--muted); font-size: .8rem; }

    /* Variations KPI en pastilles discretement teintees */
    .kpi-d { display: inline-block; padding: .14rem .55rem; border-radius: 99px;
             background: color-mix(in srgb, currentColor 9%, transparent); font-weight: 650; }

    /* Transitions des boutons */
    .stButton > button, .stDownloadButton > button { transition: border-color .15s, color .15s, background .15s; }

    /* Ligne separee du detail des ratios */
    .stDataFrame { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. IMPORTS MÉTIER
# ============================================================
from src.extraction.mistral_docai import SECTIONS
from src.extraction.service import ExtractionService
from src.extraction.excel_parser import detecter_documents
from src.extraction.controle_extraction import scorer_extraction
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.scoring.score import Scorer, PROFILS, load_config, load_profils
from src.scoring.modes import (
    MODE_TENDANCE, MODE_MOYENNE, LABELS_MODES,
    ratios_moyens, ajustement_tendance,
)
from src.analysis.validator import Validator
from src.analysis.filter_ratios import filter_ratios, MIN_EXERCICES_ANALYSE, MAX_EXERCICES_ANALYSE
from src.analysis.historique import calculer_historique
from src.scoring.sector_scorer import SectorScorer, detect_secteur, load_secteurs
from src.visualization.charts import (
    evolution_indicateurs_unifie, comparaison_n_n1,
)
from src.reporting.pdf_report import generate_pdf_report
from src.reporting.glossaire import GLOSSAIRE, label_ratio
from src.scoring.alerts import detect_alerts


# ============================================================
# 3. HELPERS
# ============================================================
def calculer_croissance(v_n, v_n1):
    if v_n1 and v_n1 != 0 and v_n is not None:
        return (v_n - v_n1) / abs(v_n1) * 100
    return None


def scinder_exercices(data: dict) -> tuple:
    """Data standard Document AI (poste + poste_n1) -> (dict exercice N, dict exercice N-1)."""
    n, n1 = {}, {}
    for sec in SECTIONS:
        n[sec] = {k: v for k, v in data.get(sec, {}).items() if not k.endswith("_n1")}
        n1[sec] = {k[:-3]: v for k, v in data.get(sec, {}).items() if k.endswith("_n1")}
    return n, n1


def fusionner_exercice(par_annee: dict, cle, data: dict):
    """Ajoute un exercice ; complete les postes manquants si l'exercice existe deja."""
    if cle not in par_annee:
        par_annee[cle] = data
        return True
    for sec in SECTIONS:
        for k, v in data.get(sec, {}).items():
            par_annee[cle].setdefault(sec, {})
            par_annee[cle][sec].setdefault(k, v)
    return False


def fmt_eur(v):
    return f"{(v or 0):,.0f} €".replace(",", "\u202f")


def label(cat):
    return cat.replace("_", " ").capitalize()


def kpi(name, value, delta, suffix="vs N-1"):
    d = ""
    if delta is not None:
        c = T["ok"] if delta >= 0 else T["bad"]
        arrow = "▲" if delta >= 0 else "▼"
        d = f'<div class="kpi-d" style="color:{c}">{arrow} {abs(delta):.1f} % {suffix}</div>'
    return f'<div class="kpi"><div class="kpi-l">{name}</div><div class="kpi-v">{fmt_eur(value)}</div>{d}</div>'


def score_ring(score, size=260):
    """Anneau du score global : rempli jusqu'au score, reste VIDE.

    La portion 0 -> score est remplie avec LA couleur du score sur
    l'echelle degrade (vert a 100, nuance tous les 5 % jusqu'au
    rouge fonce a 0) ; le reste de l'anneau reste vide (piste
    discrete). Une seule couronne lisse, aucun trait de separation.
    Demarre a midi (comme une montre) et suit le sens horaire.
    """
    import math
    s = max(0.0, min(100.0, float(score))) if score is not None else 0.0
    r, sw = 82, 14
    cx, cy = 100, 100
    circ = 2 * math.pi * r
    dash = f"{circ * s / 100.0:.2f} {circ:.2f}"
    col = get_score_gradient(s)
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 200 200" role="img" aria-label="Score {score:.0f} sur 100">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{T['line']}" stroke-width="{sw}"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-dasharray="{dash}" transform="rotate(-90 {cx} {cy})"/>
      <text x="100" y="104" text-anchor="middle" font-family="{FONT}" fill="{T['ink']}">
        <tspan font-size="62" font-weight="700">{score:.0f}</tspan><tspan font-size="21" fill="{T['muted']}"> /100</tspan>
      </text>
      <text x="100" y="130" text-anchor="middle" font-family="{FONT}" font-size="14.5" fill="{T['muted']}">score global</text>
    </svg>"""


def category_rows(scores):
    html = ""
    for cat, s in scores.items():
        if s is None:
            continue
        dot = CATEGORIES.get(cat, T["accent"])
        col = score_color(s)
        html += (f'<div class="row"><div class="row-l"><span class="cat-dot" style="background:{dot}"></span>{label(cat)}</div>'
                 f'<div class="track"><div class="fill" style="width:{max(0, min(100, s))}%;background:{col}"></div></div>'
                 f'<div class="row-v" style="color:{col};font-weight:650">{s:.0f}</div></div>')
    return html


def base_layout(fig, height=340):
    """Habillage commun aligne sur charts.py : sobre, sans cadre."""
    grid = T["line"]
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["muted"], size=11.5),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"])),
    )
    fig.update_xaxes(showline=False, tickfont=dict(size=11))
    fig.update_yaxes(showline=False, tickfont=dict(size=11))
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid)
    return fig


def radar_chart(scores):
    items = [(label(k), v) for k, v in scores.items() if v is not None]
    if not items:
        return None
    theta = [i[0] for i in items] + [items[0][0]]
    r = [i[1] for i in items] + [items[0][1]]
    fig = go.Figure(go.Scatterpolar(
        r=r, theta=theta, fill="toself", name="Score",
        line=dict(color=T["accent"], width=2),
        fillcolor=hex_rgba(T["accent"], 0.12),
        marker=dict(size=5, color=T["accent"],
                    line=dict(width=1.5, color="#FFFFFF")),
        hovertemplate="<b>%{theta}</b> : %{r:.0f}/100<extra></extra>",
    ))
    base_layout(fig, 340)
    # Marges elargies : les libelles de categories les plus longs
    # ("risque solvabilite", "gestion activite") doivent rester
    # entiers dans la demi-colonne, rien ne depasse du conteneur
    fig.update_layout(showlegend=False, margin=dict(l=64, r=64, t=28, b=28), polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor=T["line"], linecolor=T["line"],
                        tickfont=dict(size=10, color=T["muted"]), tickvals=[25, 50, 75, 100]),
        angularaxis=dict(gridcolor=T["line"], linecolor=T["line"], tickfont=dict(color=T["ink"], size=12)),
    ))
    return fig




def contribution_chart(scores, poids, details=None, cible=60, medianes=None):
    """Ce qui construit le score : treemap des contributions, ratio par ratio.

    Refait pour la lisibilite :
    - le texte des tuiles ne deborde JAMAIS (uniformtext masque un
      libelle qui ne tient pas dans sa tuile) : les grands ratios
      gardent leur nom francais complet, les petits restent vides ;
    - le SURVOL dit tout : nom complet, categorie, valeur, mediane du
      secteur, score, poids et contribution en points et en % du
      score global - une carte blanche lisible, lignes courtes.
    """
    if not scores:
        return None
    details = details or {}
    medianes = medianes or {}

    cats = {c: s for c, s in scores.items() if s is not None}
    if not cats:
        return None
    total_poids_cats = sum((poids or {}).get(c, 1) for c in cats) or 1

    # ---- 1er passage : contributions par categorie et par ratio ----
    par_cat = {}       # cat -> [(libelle, contrib, score_ratio, survol)]
    for cat, cat_score in cats.items():
        poids_cat = (poids or {}).get(cat, 1)
        rat = {nom: det for nom, det in details.items()
               if det.get("categorie") == cat and det.get("score") is not None}
        if not rat:
            continue
        somme_poids_r = sum(d.get("poids", 0) for d in rat.values()) or 1
        tuiles = []
        for nom, det in rat.items():
            score_r = det.get("score") or 0
            poids_r = det.get("poids") or 0
            contrib = (score_r * poids_r / somme_poids_r
                       * poids_cat / total_poids_cats)
            val = det.get("valeur")
            val_txt = (f"{val:,.2f}".replace(",", " ")
                       if isinstance(val, (int, float)) else "n/d")
            survol = (f"<b>{label_ratio(nom)}</b><br>"
                      f"{label(cat)}<br>"
                      f"Valeur : {val_txt}<br>")
            med = medianes.get(nom)
            if med is not None:
                survol += f"Mediane du secteur : {med:,.2f}".replace(",", " ")
                survol += "<br>"
            survol += (f"Score du ratio : {score_r:.0f} / 100<br>"
                       f"Poids : {poids_r:.2f} dans la categorie "
                       f"({poids_cat / total_poids_cats * 100:.0f} % du profil)<br>"
                       f"Contribution : +{contrib:.1f} pts")
            tuiles.append((label_ratio(nom), contrib, score_r, survol))
        par_cat[cat] = tuiles

    if not par_cat:
        return None

    # ---- 2e passage : noeuds, valeurs EXPLICITES (jamais None) ----
    ids, labels, parents, values, couleurs, textes, survols = \
        [], [], [], [], [], [], []

    def _texte_tuille(contrib, nom, seuil_complet=1.5, seuil_nom=0.6):
        """Texte d'une tuile selon sa place : complet, nom seul, rien.

        Les libelles qui ne tiennent pas dans leur tuile sont masques
        par uniformtext (mode=hide) : aucun chevauchement, le detail
        complet reste au survol.
        """
        if contrib >= seuil_complet:
            return f"{nom}<br>+{contrib:.1f}"
        if contrib >= seuil_nom:
            return nom
        return ""

    for cat in sorted(par_cat,
                      key=lambda c: sum(t[1] for t in par_cat[c]),
                      reverse=True):
        tuiles = sorted(par_cat[cat], key=lambda t: t[1], reverse=True)
        contrib_cat = sum(t[1] for t in tuiles)
        cat_id = f"cat-{cat}"
        col_cat = CATEGORIES.get(cat, T["accent"])
        ids.append(cat_id)
        labels.append(label(cat))
        parents.append("racine")
        values.append(contrib_cat)          # valeur explicite, jamais None
        couleurs.append(tint_hex(col_cat, 0.16))
        textes.append(f"{label(cat)}<br>+{contrib_cat:.1f}")
        survols.append(f"<b>{label(cat)}</b><br>"
                       f"Score : {cats[cat]:.0f} / 100<br>"
                       f"{len(tuiles)} ratios evalues<br>"
                       f"Poids du profil : "
                       f"{(poids or {}).get(cat, 1) / total_poids_cats * 100:.0f} %")
        for nom, contrib, score_r, survol in tuiles:
            ids.append(f"{cat_id}-{nom}")
            labels.append(nom)
            parents.append(cat_id)
            values.append(contrib)
            couleurs.append(tint_hex(col_cat, 0.30 + 0.70 * score_r / 100))
            textes.append(_texte_tuille(contrib, nom))
            survols.append(survol)

    if not any(values):
        return None
    # score global = somme des contributions des CATEGORIES (values
    # contient aussi les tuiles : ne pas doubler le compte)
    score_global = sum(v for p, v in zip(parents, values) if p == "racine")
    n_ratios = sum(len(t) for t in par_cat.values())

    # racine : le score global obtenu, valeur explicite
    ids.insert(0, "racine")
    labels.insert(0, f"Score global {score_global:.0f} / 100")
    parents.insert(0, "")
    values.insert(0, score_global)
    couleurs.insert(0, "#FFFFFF")
    textes.insert(0, f"Score global {score_global:.0f} / 100")
    survols.insert(0, (f"<b>Score global</b><br>{score_global:.1f} / 100<br>"
                      f"{n_ratios} ratios evalues - {len(par_cat)} categories"))

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="remainder",
        marker=dict(colors=couleurs,
                    line=dict(color="#FFFFFF", width=2)),
        text=textes,
        textposition="top left",
        tiling=dict(pad=4),
        pathbar=dict(visible=False),
        customdata=survols,
        hovertemplate="%{customdata}<extra></extra>",
        # carte de survol : fond blanc, bord fin, texte encre, lisible
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"]),
                        align="left"),
        insidetextfont=dict(size=11.5, color=T["ink"]),
    ))
    fig.update_layout(
        height=460,
        margin=dict(l=4, r=4, t=10, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["ink"]),
        # un libelle qui ne tient pas dans sa tuile est MASQUE (jamais
        # de texte qui deborde ou se chevauche) ; le detail complet
        # reste disponible au survol
        uniformtext=dict(minsize=9, mode="hide"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"]),
                        align="left"),
    )
    return fig


def _score_cell_html(sc):
    """Cellule Score /100 : mini-barre + chiffre colore.

    Rendu unique partage par la synthese et l'onglet Ratios : les
    scores s'affichent exactement de la meme facon partout.
    """
    if sc is None:
        return f'<span style="color:{T["muted"]}">n/d</span>'
    col = get_score_gradient(sc)
    return (f'<span class="rt-bar"><i style="width:'
            f'{max(0.0, min(100.0, sc)):.0f}%;background:{col}"></i></span>'
            f'<span class="rt-sc" style="color:{col}">{sc:.0f}</span>')


# Colonnes du tableau des ratios : grille PARTAGEE par tous les
# tableaux -> chaque colonne demarre au meme point partout (valeurs,
# moyennes, medianes du secteur et scores /100 parfaitement
# alignes). Largeurs en POURCENTAGES : les colonnes gardent leur
# place quel que soit la largeur disponible et les valeurs
# s'affichent en entier (la premiere colonne absorbe le reste ;
# min-width + defilement horizontal en CSS pour les ecrans etroits).
_RT_COLGROUP = (
    '<colgroup><col><col style="width:12%">'
    '<col style="width:12%"><col style="width:12%">'
    '<col style="width:7%"><col style="width:14%">'
    '<col style="width:10%"></colgroup>')


def _rt_thead(valeur_label="Valeur N"):
    """En-tete du tableau des ratios ; le libelle de la colonne valeur
    depend de la base du score (exercice N ou moyenne des exercices)."""
    return ('<thead><tr><th>Ratio</th>'
            f'<th>{valeur_label}</th><th>Moyenne</th>'
            '<th>M&eacute;d. secteur</th><th>Tend.</th>'
            '<th>Score /100</th><th>Poids</th></tr></thead>')

# Categories de controles du validateur : numero du controle -> famille.
# Numerotation SEQUENTIELLE : l'ordre d'execution = l'ordre des numeros
# (1-6 base, 7-18 comptable, 19-22 economique, 23-32 complementaires,
#  33-36 enrichissement, 37-39 sectoriel).
_CATEGORIE_CONTROLE = {
    1: "Structure du bilan", 23: "Structure du bilan",
    24: "Structure du bilan", 25: "Structure du bilan",
    26: "Structure du bilan", 29: "Structure du bilan",
    32: "Structure du bilan",
    2: "Soldes intermediaires et resultats", 3: "Soldes intermediaires et resultats",
    5: "Soldes intermediaires et resultats", 13: "Soldes intermediaires et resultats",
    14: "Soldes intermediaires et resultats", 15: "Soldes intermediaires et resultats",
    19: "Soldes intermediaires et resultats", 27: "Soldes intermediaires et resultats",
    28: "Soldes intermediaires et resultats",
    4: "Equilibres financiers", 7: "Equilibres financiers",
    8: "Equilibres financiers", 9: "Equilibres financiers",
    10: "Equilibres financiers", 11: "Equilibres financiers",
    12: "Equilibres financiers", 31: "Equilibres financiers",
    35: "Equilibres financiers", 36: "Equilibres financiers",
    6: "Plausibilite des donnees", 16: "Plausibilite des donnees",
    17: "Plausibilite des donnees", 18: "Plausibilite des donnees",
    20: "Plausibilite des donnees", 21: "Plausibilite des donnees",
    22: "Plausibilite des donnees", 30: "Plausibilite des donnees",
    33: "Plausibilite des donnees", 34: "Plausibilite des donnees",
    37: "Reference sectorielle", 38: "Reference sectorielle",
    39: "Reference sectorielle",
}
_ORDRE_CATEGORIES = ["Structure du bilan",
                     "Soldes intermediaires et resultats",
                     "Equilibres financiers",
                     "Plausibilite des donnees",
                     "Reference sectorielle"]


def _rt_val(v):
    if v is None:
        return "n/d"
    return f"{v:,.2f}".replace(",", " ")


def _rt_ligne(nom, det, h, med_sect=None):
    """Ligne du tableau des ratios : rendu UNIQUE partage.

    Utilise par la synthese et l'onglet Ratios : une ligne pour un
    ratio donnee est representee exactement pareil partout.
    med_sect : mediane du secteur (reference de comparaison), None si
    aucune reference sectorielle n'existe pour ce ratio.
    """
    det = det or {}
    h = h or {}
    sc = det.get("score")
    val_n = det.get("valeur")
    if val_n is None:
        val_n = h.get("N")
    val_moy = h.get("moyenne")
    med_txt = "—" if med_sect is None else _rt_val(med_sect)
    tendance = h.get("tendance", "-")
    if h.get("type") == "stock":
        tendance = "-"
    # Libelle francais + formule en info-bulle (titre de la cellule)
    libelle = label_ratio(nom)
    formule = (GLOSSAIRE.get(nom) or ("", ""))[0]
    tooltip = (f' title="{formule}"' if formule else "")
    type_r = h.get("type", "flux")
    t_s = str(tendance)
    if t_s in ("↗", "hausse", "▲"):
        t_col, t_txt = T["ok"], "↗"
    elif t_s in ("↘", "baisse", "▼"):
        t_col, t_txt = T["bad"], "↘"
    else:
        t_col, t_txt = T["muted"], "—"
    return (f'<tr><td><b{tooltip}>{libelle}</b><span class="rt-tag">{type_r}</span></td>'
            f'<td>{_rt_val(val_n)}</td><td>{_rt_val(val_moy)}</td>'
            f'<td>{med_txt}</td>'
            f'<td style="color:{t_col}">{t_txt}</td>'
            f'<td>{_score_cell_html(sc)}</td>'
            f'<td>{(det.get("poids") or 0):.2f}</td></tr>')


def ratios_table_html(details, historique=None, cats_scores=None,
                      filtre_cat="Toutes", filtre_type="Tous",
                      medianes=None, valeur_label="Valeur N"):
    """Tableau detaille des ratios, presente en cartes par categorie.

    Harmonise avec le design de la page : une carte par categorie
    (couleur habituelle + score de la categorie), lignes classees de
    la meilleure note a la moins bonne, score en mini-barre + chiffre
    colores par le degrade continu vert (100) -> rouge fonce (0),
    tendance en fleche coloree, valeurs alignees a droite.

    medianes : {nom_ratio: mediane du secteur} - la colonne "Med.
    secteur" donne la reference de comparaison sectorielle (la
    mediane, pas la moyenne : elle n'est pas deplacee par les valeurs
    extremes). Absente si aucun secteur n'est detecte ou si le ratio
    n'a pas de reference sectorielle.
    """
    historique = historique or {}
    by_cat = {}
    for nom, det in (details or {}).items():
        cat = det.get("categorie", "autre")
        if filtre_cat != "Toutes" and label(cat) != filtre_cat:
            continue
        h = historique.get(nom, {})
        if filtre_type != "Tous" and h.get("type", "flux") != filtre_type:
            continue
        by_cat.setdefault(cat, []).append((nom, det, h))
    if not by_cat:
        return ""

    blocs = []
    # Ordre des categories : score decroissant, meme ordre que la
    # synthese et que le PDF (les non notees passent en fin)
    for cat in sorted(by_cat,
                      key=lambda c: ((cats_scores or {}).get(c)
                                     if (cats_scores or {}).get(c) is not None
                                     else -1), reverse=True):
        # Ratios notes d'abord (score decroissant), non notes (n/d) en fin
        lignes = sorted(by_cat[cat],
                        key=lambda t: (t[1].get("score") is None,
                                       -(t[1].get("score") or 0)))
        col_cat = CATEGORIES.get(cat, T["accent"])
        rows_html = ""
        for nom, det, h in lignes:
            rows_html += _rt_ligne(nom, det, h, (medianes or {}).get(nom))
        sc_cat = (cats_scores or {}).get(cat)
        sc_cat_txt = f"{sc_cat:.0f} /100" if sc_cat is not None else ""
        sc_cat_col = get_score_gradient(sc_cat) if sc_cat is not None else T["muted"]
        blocs.append(
            '<div class="rt-wrap">'
            f'<div class="rt-cat" style="border-left:4px solid {col_cat}">'
            f'<span>{label(cat)}</span>'
            f'<span class="rd-hs" style="color:{sc_cat_col}">{sc_cat_txt}</span></div>'
            f'<table class="rt">{_RT_COLGROUP}{_rt_thead(valeur_label)}'
            f'<tbody>{rows_html}</tbody></table></div>')
    return "".join(blocs)




# ============================================================
# 3. ETAT / SESSION
# ============================================================
if "analyse_faite" not in st.session_state:
    st.session_state.analyse_faite = False
try:
    st.session_state.config_yaml = load_config()
except Exception:
    st.session_state.config_yaml = {"poids_categories": {}}
try:
    st.session_state.profils_dispo = load_profils()
except Exception:
    st.session_state.profils_dispo = PROFILS

PROFILS_EFFECTIFS = st.session_state.get("profils_dispo", PROFILS)

profil = "moyen_terme"


def _score_resultat(profil_courant="moyen_terme"):
    """Calcule le score courant (sectoriel si secteur connu, sinon standard).

    Lecture pure de session_state : appele a la fin de l'import (pour
    que l'en-tete dispose du resultat des le premier rendu suivant
    l'analyse) puis a chaque rendu de la section Resultats, ou les
    options de secteur et de profil de l'utilisateur s'appliquent.
    """
    secteurs_dispo = {}
    try:
        secteurs_dispo = load_secteurs()
    except Exception:
        pass

    secteur_sel = st.session_state.get("secteur_sel", "Detection automatique")
    code_naf = st.session_state.get("naf_input", "")
    secteur_code = None
    secteur_label = None

    if secteur_sel and secteur_sel != "Detection automatique":
        for code, info in secteurs_dispo.items():
            if info.get("label") == secteur_sel:
                secteur_code = code
                secteur_label = info["label"]
                break
    elif code_naf:
        secteur_code = detect_secteur(code_naf)
        if secteur_code:
            secteur_label = secteurs_dispo.get(secteur_code, {}).get("label")
    elif st.session_state.get("secteur_auto_code"):
        secteur_code = st.session_state["secteur_auto_code"]
        secteur_label = secteurs_dispo.get(secteur_code, {}).get("label")

    # Base du score (Options) : exercice N + ajustement de tendance
    # (defaut) ou moyenne des exercices. Le meme moteur et la meme
    # configuration : seul le jeu de valeurs change.
    base_sel = st.session_state.get("score_base_sel",
                                    LABELS_MODES[MODE_TENDANCE])
    mode = (MODE_MOYENNE if base_sel == LABELS_MODES[MODE_MOYENNE]
            else MODE_TENDANCE)
    ratios_base = st.session_state.ratios
    if mode == MODE_MOYENNE:
        ratios_base = ratios_moyens(
            st.session_state.ratios,
            st.session_state.get("historique") or {})

    methode = "standard"
    res = None

    if secteur_code:
        try:
            _sector = SectorScorer(ratios_base, secteur=secteur_code)
            # Concordance avec le scoring standard : le score sectoriel
            # utilise les poids de categories du profil d'analyse configure
            _poids_profil = ((PROFILS_EFFECTIFS.get(profil_courant) or {})
                             .get("poids_categories")) or {}
            res = _sector.compute_scores_by_category(
                st.session_state.config_yaml,
                poids_categories=_poids_profil)
            if res.get("score_global", 0) > 0:
                methode = "sectorielle"
            else:
                res = None
        except Exception:
            res = None

    if res is None:
        try:
            res = Scorer(ratios_base, profil=profil_courant).compute_all()
        except Exception:
            res = Scorer(ratios_base,
                         profil="moyen_terme").compute_all()
        methode = "standard"

    # Mode tendance : ajustement borne par la trajectoire des ratios
    # (N vs moyenne des exercices), scores recalculent avec les poids
    # du profil - meme pondereage que le scoring standard.
    if mode == MODE_TENDANCE:
        _poids_tend = ((PROFILS_EFFECTIFS.get(profil_courant) or {})
                       .get("poids_categories")) or {}
        res = ajustement_tendance(
            res, st.session_state.get("historique") or {},
            st.session_state.config_yaml, _poids_tend)
    res["base_scoring"] = mode

    res["methode"] = methode
    res["secteur_code"] = secteur_code
    res["secteur_label"] = secteur_label
    return res


# ============================================================
# 4. EN-TETE
# ============================================================
h_left, h_opts, h_pdf = st.columns([5.2, 1.3, 2.5], vertical_alignment="center")
with h_left:
    st.markdown("<h1>FinView</h1>", unsafe_allow_html=True)
    if st.session_state.analyse_faite:
        nom = st.session_state.get("nom_entreprise", "")
        secteur_label = st.session_state.get("secteur_auto_label")
        meta = nom
        if secteur_label:
            meta += f" &middot; Secteur : <b>{secteur_label}</b>"
        st.markdown(f"<div class='sub'>{meta}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='sub'>Deposez les documents d'au moins trois exercices complets (huit maximum) pour obtenir un score detaille.</div>",
                    unsafe_allow_html=True)

with h_opts:
    with st.popover("Options", use_container_width=True):
        try:
            secteurs = load_secteurs()
            opts = ["Detection automatique"] + [i["label"] for i in secteurs.values()]
        except Exception:
            opts = ["Detection automatique"]
        st.selectbox("Secteur", opts, key="secteur_sel")
        st.text_input("Code NAF / APE", placeholder="Ex : 41.20A", key="naf_input")
        if st.session_state.get("naf_auto"):
            st.caption(f"Détecté dans le document : {st.session_state.naf_auto}"
                       + (f" ({st.session_state.secteur_auto_label})"
                          if st.session_state.get("secteur_auto_label") else ""))
        if st.session_state.analyse_faite:
            try:
                keys = list(PROFILS_EFFECTIFS.keys())
                idx = keys.index("moyen_terme") if "moyen_terme" in keys else 0
                profil = st.selectbox("Profil d'analyse", keys, index=idx,
                                      format_func=lambda x: PROFILS_EFFECTIFS[x].get("label", x))
            except Exception:
                profil = "moyen_terme"
            st.selectbox("Base du score",
                         list(LABELS_MODES.values()),
                         index=0, key="score_base_sel",
                         help="Dernière année + tendance : le score porte sur "
                              "l'exercice N, ajusté par la trajectoire des ratios "
                              "(N comparé à la moyenne des exercices, ±5 pts par "
                              "catégorie). Moyenne des exercices : le score porte "
                              "sur la valeur moyenne de chaque ratio.")

with h_pdf:
    # Garde : au premier rendu qui suit l'analyse, "result" n'existe pas
    # encore (il est calcule plus bas, section Resultats) - aucun
    # bouton ce tour-ci, sans faire planter la page.
    if st.session_state.analyse_faite and st.session_state.get("result") is not None:
        # Telechargement en un clic : le PDF est calcule une seule fois
        # par configuration (signature des donnees + profil), puis cache
        import hashlib
        import json as _json

        try:
            _poids_pdf = ((PROFILS_EFFECTIFS.get(profil) or {})
                          .get("poids_categories")) or {}
        except Exception:
            _poids_pdf = {}

        # Medianes du secteur detecte (alignement PDF/dashboard : la
        # colonne "Med. secteur" existe dans les deux)
        _medianes_pdf = {}
        _code_sect_pdf = ((st.session_state.result or {}).get("secteur_code"))
        if _code_sect_pdf:
            try:
                from src.scoring.sector_scorer import load_secteurs as _ls
                _cfg_sect_pdf = (_ls().get(_code_sect_pdf) or {})
                _medianes_pdf = {
                    n: (r or {}).get("mediane")
                    for n, r in (_cfg_sect_pdf.get("ratios") or {}).items()
                }
            except Exception:
                _medianes_pdf = {}

        # Integralite des ratios configures : le tableau de detail du
        # PDF affiche toutes les lignes comme le dashboard (n/d si non note)
        _config_ratios_pdf = {}
        try:
            _cy = st.session_state.get("config_yaml") or {}
            for _cat, _info in (_cy.get("categories") or {}).items():
                for _nom in (_info.get("ratios_actifs") or []):
                    _config_ratios_pdf[_nom] = {
                        "categorie": _cat,
                        "poids": ((_cy.get(_cat) or {}).get(_nom) or {}).get("poids", 0),
                    }
        except Exception:
            _config_ratios_pdf = {}

        # agregats par exercice : base de comparaison du mode moyenne
        # (indicateurs cles du PDF) et element de la signature du cache
        _bilans_ch = st.session_state.get("bilans_data", [])
        _exs_ch = st.session_state.get("exercices", [])
        _agg_ex_charge = {}
        for _i, _bd in enumerate(_bilans_ch):
            try:
                _an = (str(_exs_ch[_i].get("annee", f"N-{_i}"))
                       if _i < len(_exs_ch) else f"N-{_i}")
                _agg_ex_charge[_an] = Agregats(_bd).compute_all()
            except Exception:
                pass

        _charge = {
            "result": st.session_state.result,
            "agregats": st.session_state.agregats,
            "validation": st.session_state.validation,
            "alertes": st.session_state.alertes,
            "nom": st.session_state.get("nom_entreprise"),
            "secteur": (st.session_state.result or {}).get("secteur_label"),
            "n_bilans": len(st.session_state.get("bilans_data", [])),
            "poids": _poids_pdf,
            # moyennes multi-exercices affichees dans le detail des
            # ratios : une donnee qui change doit invalider le cache
            "historique": st.session_state.get("historique", {}),
            # medianes du secteur (colonne "Med. secteur" du PDF)
            "medianes_secteur": _medianes_pdf,
            # integralite des ratios configures au detail
            "config_ratios": _config_ratios_pdf,
            # agregats par exercice : comparaison du mode moyenne
            "agregats_exercices": _agg_ex_charge,
            # toute modification du code du rapport invalide le PDF en
            # cache : on ne doit jamais re-servir un rapport obsolete
            "rapport_mtime": max(
                int(Path(str(ROOT / "src" / "reporting" / f)).stat().st_mtime)
                for f in ("pdf_report.py", "synthese.py", "charts_pdf.py",
                          "glossaire.py")),
        }
        _sig = hashlib.sha256(
            _json.dumps(_charge, sort_keys=True, default=str,
                        ensure_ascii=False).encode()).hexdigest()[:16]

        _cache = st.session_state.get("pdf_cache") or {}
        if _cache.get("sig") != _sig:
            try:
                _bilans = st.session_state.get("bilans_data", [])
                _agg_n1 = (Agregats(_bilans[1]).compute_all()
                           if len(_bilans) >= 2 else None)
                _cache = {"sig": _sig, "bytes": generate_pdf_report(
                    result=st.session_state.result,
                    agregats=st.session_state.agregats,
                    agregats_n1=_agg_n1,
                    validation=st.session_state.validation,
                    alertes=st.session_state.alertes,
                    company_name=(st.session_state.get("nom_entreprise")
                                  or "Entreprise analysee"),
                    secteur_label=(st.session_state.result or {}).get("secteur_label"),
                    poids_categories=_poids_pdf,
                    historique=st.session_state.get("historique", {}),
                    medianes_secteur=_medianes_pdf,
                    config_ratios=_config_ratios_pdf,
                    agregats_exercices=_agg_ex_charge,
                )}
                st.session_state.pdf_cache = _cache
            except Exception as e:
                st.error(f"L'export a echoue : {e}")
                _cache = {"sig": _sig, "bytes": None}
                st.session_state.pdf_cache = _cache
        if _cache.get("bytes"):
            # pas de type="primary" : le style primaire de Streamlit
            # rend un indigo qui FONCE au survol - on style le bouton
            # nous-memes (accent, survol qui eclaircit)
            st.download_button(
                "Télécharger le PDF", data=_cache["bytes"],
                file_name="Rapport_Financier.pdf", mime="application/pdf",
                use_container_width=True)

st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)


# ============================================================
# 5. IMPORT
# ============================================================
zone = st.expander("Remplacer les documents") if st.session_state.analyse_faite else st.container()
with zone:
    if not st.session_state.analyse_faite:
        st.markdown("""
<div class="hero">
  <div class="hero-t">Analysez la sante financiere d'une entreprise</div>
  <div class="hero-s">Deposez trois exercices complets minimum, huit maximum (bilan et compte de resultat, PDF, image ou Excel) : extraction, ratios et score sont calcules automatiquement.</div>
  <div class="steps">
    <div class="step">
      <span class="step-n">1</span>
      <b>Deposez vos documents</b>
      <span class="step-s">Liasse fiscale, bilan et compte de resultat, PDF natif ou scanne, JPG, PNG ou Excel (.xlsx). Trois exercices complets minimum, huit maximum : un exercice = bilan (actif + passif) + compte de resultat.</span>
    </div>
    <div class="step">
      <span class="step-n">2</span>
      <b>Extraction automatique</b>
      <span class="step-s">Postes normalises au PCG, controles de coherence comptable et detection du secteur via le code NAF.</span>
    </div>
    <div class="step">
      <span class="step-n">3</span>
      <b>Score et vigilances</b>
      <span class="step-s">Scoring sectoriel, ratios detailles, points de vigilance et rapport PDF exportable.</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    fichiers = st.file_uploader(
        "Documents comptables (PDF, JPG, PNG ou Excel .xlsx)",
        type=["pdf", "jpg", "jpeg", "png", "xlsx", "xlsm"],
        accept_multiple_files=True, key="docs",
        label_visibility="visible" if not st.session_state.analyse_faite else "collapsed",
    )

if fichiers:
    files_sig = "|".join(sorted(f.name for f in fichiers))
    if st.session_state.get("files_sig") != files_sig:
        with st.status("Analyse des documents en cours...", expanded=True) as status:
            tmpdir = Path(tempfile.mkdtemp())
            paths = []
            for f in fichiers:
                p = tmpdir / f.name
                p.write_bytes(f.read())
                paths.append(str(p))

            service = ExtractionService()

            def _annee_fichier(nom):
                m = re.search(r"(20\d{2})", nom)
                return int(m.group(1)) if m else None

            # Du plus recent au plus ancien (annee dans le nom de fichier)
            fichiers_tri = sorted(zip(fichiers, paths),
                                  key=lambda x: _annee_fichier(x[0].name) or 0,
                                  reverse=True)

            extraits = []      # (nom, data_n, data_n1, annee, meta)
            controles = []
            erreurs = []

            for f, p in fichiers_tri:
                st.write(f"Extraction : {f.name}")
                try:
                    extrait = service.extraire(p)
                except Exception as e:
                    erreurs.append(f"{f.name} : {e}")
                    continue

                data_n, data_n1 = scinder_exercices(extrait.data)
                controles.append((f.name, scorer_extraction(data_n, extrait.source)))
                annee = _annee_fichier(f.name) or extrait.meta.get("annee_n")
                extraits.append((f.name, data_n, data_n1, annee, extrait.meta))

            # Fusion par exercice : les donnees N (directes) priment sur les N-1
            par_annee = {}
            for direct in (True, False):
                for nom, data_n, data_n1, annee, meta in extraits:
                    if direct:
                        cle = annee if annee else "N"
                        data = data_n
                    else:
                        cle = (annee - 1) if annee else "N-1"
                        data = data_n1
                    fusionner_exercice(par_annee, cle, data)

            # Annees numeriques du plus recent au plus ancien, puis libelles (N, N-1)
            cles = (sorted([c for c in par_annee if isinstance(c, int)], reverse=True)
                    + [c for c in par_annee if not isinstance(c, int)])
            bilans_data = [par_annee[c] for c in cles]
            exercices = [{"path": None, "nom": str(c), "type": "docai", "annee": c}
                         for c in cles]

            if controles:
                non_ok = [(n, c) for n, c in controles if c.statut != "ok"]
                for n, c in non_ok:
                    msg = c.problemes[0] if c.problemes else c.statut
                    st.warning(f"**{n}** — {c.statut} ({c.score}/100) : {msg}")
                st.session_state.controles = controles

            for e in erreurs:
                st.error(e)

            if extraits and any(a is None for _, _, _, a, _ in extraits):
                st.info("Annee non detectee dans le nom d'un fichier : "
                        "ajoutez l'annee au nom pour un historique fiable.")

            if not bilans_data:
                st.error("Aucun document exploitable apres extraction.")
                status.update(label="Echec de l'extraction", state="error")
                st.stop()

            # Porte avant analyse : de MIN_EXERCICES_ANALYSE a
            # MAX_EXERCICES_ANALYSE exercices fiscaux complets.
            # Un exercice complet = bilan (actif ET passif) + compte de
            # resultat. Les exercices incomplets (ou trop anciens) sont
            # ecartes ; sous trois complets, l'analyse est bloquee.
            def _libelle_exercice(i):
                if i < len(exercices):
                    return str(exercices[i].get("annee", f"N-{i}"))
                return f"N-{i}"

            def _manques(det):
                manq = []
                if not det["bilan"]:
                    manq.append("le bilan (actif et passif)")
                if not det["compte_resultat"]:
                    manq.append("le compte de resultat")
                return manq

            complets = []   # indices des exercices complets, du plus recent
            ecarts = []     # (libelle, raison)
            for i, bd in enumerate(bilans_data):
                det = detecter_documents(bd)
                if det["complet"]:
                    complets.append(i)
                else:
                    manq = _manques(det)
                    ecarts.append((_libelle_exercice(i),
                                   " et ".join(manq) + " manquant"
                                   + ("s" if len(manq) > 1 else "")))

            if len(complets) < MIN_EXERCICES_ANALYSE:
                st.error(f"Analyse impossible : il faut au minimum "
                         f"{MIN_EXERCICES_ANALYSE} exercices complets. "
                         "Un exercice complet = un bilan (actif et passif) "
                         "+ un compte de resultat.")
                for lib, raison in ecarts:
                    st.markdown(f"- **{lib}** : {raison}")
                st.info("Deposez les documents (PDF, image ou Excel) d'au "
                        f"moins {MIN_EXERCICES_ANALYSE} exercices complets "
                        f"(maximum {MAX_EXERCICES_ANALYSE}).")
                status.update(label="Exercices insuffisants", state="error")
                st.stop()

            # Maximum : seuls les exercices les plus recents sont analyses
            if len(complets) > MAX_EXERCICES_ANALYSE:
                for i in complets[MAX_EXERCICES_ANALYSE:]:
                    ecarts.append((_libelle_exercice(i),
                                   f"au-dela des {MAX_EXERCICES_ANALYSE} "
                                   "exercices les plus recents"))
                complets = complets[:MAX_EXERCICES_ANALYSE]

            if ecarts:
                resumes = ", ".join(f"{lib} ({raison})" for lib, raison in ecarts)
                st.info(f"Exercice(s) ecarte(s) : {resumes}. L'analyse porte "
                        f"sur les {len(complets)} exercices les plus recents.")
                bilans_data = [bilans_data[i] for i in complets]
                exercices = [exercices[i] for i in complets]

            if bilans_data:
                data_n = bilans_data[0]
                agg_n = Agregats(data_n).compute_all()
                ratios = Ratios(agg_n).compute_all()

                ratios_par_annee = {}
                for i, bd in enumerate(bilans_data):
                    try:
                        annee = str(exercices[i].get("annee", f"N-{i}")) if i < len(exercices) else f"N-{i}"
                        agg_i = Agregats(bd).compute_all()
                        ratios_par_annee[annee] = Ratios(agg_i).compute_all()
                    except Exception:
                        pass

                historique = calculer_historique(ratios_par_annee)

                if len(bilans_data) >= 2:
                    agg_n1 = Agregats(bilans_data[1]).compute_all()
                    ratios["croissance"] = {
                        "croissance_ca": calculer_croissance(agg_n.get("chiffre_affaires"), agg_n1.get("chiffre_affaires")),
                        "croissance_va": calculer_croissance(agg_n.get("valeur_ajoutee"), agg_n1.get("valeur_ajoutee")),
                    }
                ratios_f = filter_ratios(ratios, len(exercices))

                # Identification de l'entreprise : meta du document le plus recent
                meta_recent = extraits[0][4] if extraits else {}
                st.session_state.nom_entreprise = (
                    meta_recent.get("raison_sociale")
                    or Path(fichiers_tri[0][0].name).stem
                )
                naf = meta_recent.get("code_naf")
                st.session_state.naf_auto = naf
                st.session_state.secteur_auto_code = detect_secteur(naf) if naf else None
                try:
                    secteurs_cfg_val = load_secteurs()
                except Exception:
                    secteurs_cfg_val = {}
                st.session_state.secteur_auto_label = (
                    secteurs_cfg_val[st.session_state.secteur_auto_code]["label"]
                    if st.session_state.secteur_auto_code else None
                )

                # Controles de coherence, sectoriels si le secteur est connu
                st.session_state.validation = Validator(
                    agg_n, ratios_f, data_n,
                    data_n1=(bilans_data[1] if len(bilans_data) > 1 else None),
                    secteur_code=st.session_state.secteur_auto_code,
                    secteurs_config=secteurs_cfg_val).validate_all()
                st.session_state.agregats = agg_n
                st.session_state.ratios = ratios_f
                # agregats N-1 pour les alertes de variation (baisse CP...)
                _agg_n1_al = (Agregats(bilans_data[1]).compute_all()
                              if len(bilans_data) > 1 else None)
                st.session_state.alertes = detect_alerts(agg_n, ratios_f,
                                                        agregats_n1=_agg_n1_al)
                st.session_state.bilans_data = bilans_data
                st.session_state.exercices = exercices
                st.session_state.ratios_par_annee = ratios_par_annee
                st.session_state.historique = historique

                st.session_state.pop("pdf_cache", None)
                st.session_state.pop("pdf_bytes", None)
                # Le score est pre-calcule ici : l'en-tete (cache PDF,
                # resume) en a besoin des le premier rendu suivant le
                # rerun, avant que la section Resultats ne s'execute.
                st.session_state.result = _score_resultat()
                st.session_state.analyse_faite = True
                st.session_state.files_sig = files_sig
            status.update(label="Analyse terminee", state="complete")
            st.rerun()


# ============================================================
# 6. RESULTATS
# ============================================================
if st.session_state.analyse_faite:
    res = _score_resultat(profil)
    methode = res.get("methode", "standard")
    secteur_code = res.get("secteur_code")
    secteur_label = res.get("secteur_label")
    st.session_state.result = res

    # referentiels sectoriels (benchmark de l'onglet Secteur)
    secteurs_dispo = {}
    try:
        secteurs_dispo = load_secteurs()
    except Exception:
        pass

    agg = st.session_state.agregats
    score = res.get("score_global", 0) or 0
    cats = res.get("scores_categories", {})
    alertes = st.session_state.alertes
    val = st.session_state.validation
    stats = val["stats"]

    # KPI : valeurs et variations selon la base du score.
    # - mode derniere annee + tendance : valeurs de N, variation N vs N-1 ;
    # - mode moyenne : VALEURS MOYENNES des exercices, variation qui
    #   situe N par rapport a cette moyenne.
    _codes_kpi = {"ca": "chiffre_affaires", "ebitda": "ebitda",
                  "rn": "resultat_net", "cp": "capitaux_propres"}
    kpi_vals = {k: agg.get(code) for k, code in _codes_kpi.items()}
    d = {k: None for k in _codes_kpi}
    kpi_suffix = "vs N-1"
    if res.get("base_scoring") == MODE_MOYENNE:
        _moy_kpi = {}
        for code in _codes_kpi.values():
            _vals = []
            for bd in st.session_state.get("bilans_data", []):
                try:
                    v = Agregats(bd).compute_all().get(code)
                except Exception:
                    v = None
                if v:
                    _vals.append(v)
            if _vals:
                _moy_kpi[code] = sum(_vals) / len(_vals)
        kpi_vals = {k: _moy_kpi.get(code, agg.get(code))
                    for k, code in _codes_kpi.items()}
        d = {k: calculer_croissance(agg.get(code), _moy_kpi.get(code))
             for k, code in _codes_kpi.items()}
        kpi_suffix = "vs moyenne"
    elif len(st.session_state.bilans_data) >= 2:
        n1 = Agregats(st.session_state.bilans_data[1]).compute_all()
        d = {
            "ca": calculer_croissance(agg.get("chiffre_affaires"), n1.get("chiffre_affaires")),
            "ebitda": calculer_croissance(agg.get("ebitda"), n1.get("ebitda")),
            "rn": calculer_croissance(agg.get("resultat_net"), n1.get("resultat_net")),
            "cp": calculer_croissance(agg.get("capitaux_propres"), n1.get("capitaux_propres")),
        }

    n_crit = sum(1 for a in alertes if a.get("niveau") == "critique")
    n_warn = sum(1 for a in alertes if a.get("niveau") == "warning")
    resume = (f"{n_crit} alerte{'s' if n_crit > 1 else ''} critique{'s' if n_crit > 1 else ''} "
              f"et {n_warn} point{'s' if n_warn > 1 else ''} d'attention." if alertes
              else "Aucun point de vigilance detecte.")

    left, right = st.columns([6, 7], gap="large", vertical_alignment="center")
    with left:
        if methode == "sectorielle" and secteur_label:
            badge = (f'<span class="badge">Score sectoriel &middot; '
                     f'{secteur_label}</span>')
        else:
            badge = ('<span class="badge neutre">Score standard &middot; '
                     'seuils fixes</span>')
        _base = res.get("base_scoring")
        if _base == MODE_MOYENNE:
            badge_base = ('<span class="badge neutre">Base : moyenne '
                          'des exercices</span>')
        else:
            badge_base = ('<span class="badge neutre">Base : exercice N '
                          '+ tendance</span>')
        st.markdown(
            f'<div class="ring-wrap">{score_ring(score)}<div>'
            f'{badge}{badge_base}'
            f'<div class="verdict" style="color:{score_color(score)}">{verdict(score)}</div>'
            f'<div class="verdict-sub">{resume}</div>'
            f'</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            '<div class="kpi-grid">'
            + kpi("Chiffre d'affaires", kpi_vals["ca"], d["ca"], kpi_suffix)
            + kpi("EBITDA", kpi_vals["ebitda"], d["ebitda"], kpi_suffix)
            + kpi("Resultat net", kpi_vals["rn"], d["rn"], kpi_suffix)
            + kpi("Capitaux propres", kpi_vals["cp"], d["cp"], kpi_suffix)
            + "</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    tab_syn, tab_rat, tab_ctl = st.tabs(["Synthese", "Ratios", "Controles"])

    with tab_syn:
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            st.markdown('<div class="section-t">Score par categorie</div>', unsafe_allow_html=True)
            st.markdown(category_rows(cats), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="section-t">Profil de risque</div>', unsafe_allow_html=True)
            fig_radar = radar_chart(cats)
            if fig_radar:
                st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="section-t">Ce qui construit le score</div>', unsafe_allow_html=True)
        try:
            poids = PROFILS_EFFECTIFS[profil].get("poids_categories") or PROFILS_EFFECTIFS[profil].get("poids", {})
        except Exception:
            poids = {}
        # medianes du secteur : enrichissent le survol du treemap
        _medianes_syn = {}
        if secteur_code:
            _cfg_sect_syn = (secteurs_dispo.get(secteur_code) or {})
            _medianes_syn = {
                n: (r or {}).get("mediane")
                for n, r in (_cfg_sect_syn.get("ratios") or {}).items()
            }
        fig_contrib = contribution_chart(cats, poids, res.get("details", {}),
                                         medianes=_medianes_syn)
        if fig_contrib:
            st.plotly_chart(fig_contrib, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='sub'>Chaque tuile est un ratio : sa surface est "
                "proportionnelle a sa contribution au score global (score du "
                "ratio x poids dans la categorie x poids de la categorie dans "
                "le profil). Chaque categorie garde sa couleur habituelle ; "
                "l'intensite de la tuile traduit le niveau du ratio (pale = "
                "faible, soutenue = solide). Survolez pour le detail.</div>",
                unsafe_allow_html=True)
        else:
            st.info("Aucun ratio score a representer pour ce profil : "
                    "verifiez les ratios actifs dans le Parametrage.")

        if len(st.session_state.get("bilans_data", [])) >= 2:
            st.markdown('<div class="section-t">Comparaison des agregats : '
                        'N, N-1 et moyenne des exercices (EUR)</div>',
                        unsafe_allow_html=True)
            try:
                agg_n1_cmp = Agregats(st.session_state.bilans_data[1]).compute_all()
                # agregats par exercice (calcules pour les courbes) ->
                # troisieme serie : moyenne de tous les exercices
                _exs_cmp = st.session_state.get("exercices", [])
                _agg_par_ex = {}
                for _i, _bd in enumerate(st.session_state.bilans_data):
                    try:
                        _an = (str(_exs_cmp[_i].get("annee", f"N-{_i}"))
                               if _i < len(_exs_cmp) else f"N-{_i}")
                        _agg_par_ex[_an] = Agregats(_bd).compute_all()
                    except Exception:
                        pass
                fig_cmp = comparaison_n_n1(agg, agg_n1_cmp,
                                           agregats_exercices=_agg_par_ex)
                if fig_cmp:
                    st.plotly_chart(fig_cmp, use_container_width=True,
                                    config={"displayModeBar": False})
                    st.markdown(
                        "<div class='sub'>La moyenne couvre tous les "
                        "exercices disponibles (N et N-1 inclus), jusqu'a "
                        "huit.</div>", unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Comparaison indisponible : {e}")

            try:
                agregats_par_annee = {}
                _exs = st.session_state.get("exercices", [])
                for i, bd in enumerate(st.session_state.bilans_data):
                    try:
                        annee = str(_exs[i].get("annee", f"N-{i}")) if i < len(_exs) else f"N-{i}"
                        agregats_par_annee[annee] = Agregats(bd).compute_all()
                    except Exception:
                        pass

                indicateurs_evo = [
                    ("chiffre_affaires", "Chiffre d'affaires"),
                    ("ebitda", "EBITDA"),
                    ("resultat_net", "Resultat net"),
                    ("capitaux_propres", "Capitaux propres"),
                    ("total_dettes", "Total dettes"),
                    ("tresorerie", "Tresorerie"),
                ]
                # UN SEUL graphique : une couleur par indicateur, survol
                # unifie, legende cliquable, boutons Valeurs / Base 100
                fig_evo = evolution_indicateurs_unifie(
                    agregats_par_annee, indicateurs_evo)
                if fig_evo:
                    st.plotly_chart(fig_evo, use_container_width=True,
                                    config={"displayModeBar": False})
                    st.markdown(
                        "<div class='sub'>Une couleur par indicateur. "
                        "Survolez un exercice : toutes les valeurs "
                        "s'affichent ensemble ; cliquez un indicateur "
                        "dans la legende pour l'isoler ; basculez en "
                        "base 100 pour comparer des montants d'echelles "
                        "differentes.</div>",
                        unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Evolution indisponible : {e}")

    with tab_rat:
        details = res.get("details", {})
        historique = st.session_state.get("historique", {})

        # Medianes du secteur detecte : reference de comparaison de
        # chaque ratio (colonne "Med. secteur")
        medianes_sect = {}
        if secteur_code:
            try:
                _cfg_sect = (secteurs_dispo.get(secteur_code) or {})
                medianes_sect = {
                    n: (r or {}).get("mediane")
                    for n, r in (_cfg_sect.get("ratios") or {}).items()
                }
            except Exception:
                medianes_sect = {}

        if details:
            # TOUJOURS toutes les lignes configures : la vue affiche l'integralite des
            # ratios configures ; ceux non notes sur les donnees (ou
            # desactives par le secteur) apparaissent en n/d au lieu
            # de disparaitre - calcule = config = affiche
            cfg_y = st.session_state.get("config_yaml") or {}
            details_tous = dict(details)
            for cat_cfg, info_cfg in (cfg_y.get("categories") or {}).items():
                cfg_cat = cfg_y.get(cat_cfg) or {}
                for nom in (info_cfg.get("ratios_actifs") or []):
                    if nom in details_tous or nom not in cfg_cat:
                        continue
                    details_tous[nom] = {
                        "score": None, "valeur": None,
                        "poids": (cfg_cat.get(nom) or {}).get("poids", 0),
                        "categorie": cat_cfg,
                    }
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                _cats_rat = sorted({label(det.get("categorie", "autre"))
                                    for det in details_tous.values()})
                choix = st.selectbox("Categorie", ["Toutes"] + _cats_rat)
            with col_f2:
                filtre_type = st.selectbox("Type", ["Tous", "flux", "stock"])
            _html_tbl = ratios_table_html(details_tous, historique,
                                          cats_scores=cats,
                                          filtre_cat=choix,
                                          filtre_type=filtre_type,
                                          medianes=medianes_sect,
                                          valeur_label=(
                                              "Valeur (moy.)"
                                              if res.get("base_scoring") == MODE_MOYENNE
                                              else "Valeur N"))
            if _html_tbl:
                st.markdown(_html_tbl, unsafe_allow_html=True)
            else:
                st.info("Aucun ratio score pour ces filtres.")
        else:
            st.info("Aucun ratio score pour ce profil : verifiez les "
                    "ratios actifs dans le Parametrage.")

    with tab_ctl:
        # 1. Fiabilite des donnees : bandeau de compteurs en tete
        st.markdown('<div class="section-t">Fiabilit&eacute; des donn&eacute;es</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<span class="stat"><b style="color:{T["ok"]}">{stats["succes"]}/{stats["total"]}</b><span>Controles reussis</span></span>'
            f'<span class="stat"><b style="color:{T["warn"]}">{stats["avertissements"]}</b><span>Vigilances</span></span>'
            f'<span class="stat"><b style="color:{T["bad"]}">{stats["erreurs"]}</b><span>Incoherences</span></span>',
            unsafe_allow_html=True)

        if stats.get("erreurs"):
            st.markdown(
                f'<div class="alert"><span class="dot" style="background:{T["bad"]}"></span>'
                '<div><div class="alert-lvl">Incoherences detectees</div>'
                f'{stats["erreurs"]} controle(s) en erreur : les valeurs '
                'concernees sont identifiees ci-dessous et doivent etre '
                'verifiees avant d\'exploiter le rapport.</div></div>',
                unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # 2. Points de vigilance : alertes en pleine largeur
        st.markdown('<div class="section-t">Points de vigilance</div>', unsafe_allow_html=True)
        if not alertes:
            st.markdown(f'<div class="alert"><span class="dot" style="background:{T["ok"]}"></span>'
                        'Aucun risque critique identifie.</div>', unsafe_allow_html=True)
        else:
            lv = {"critique": (T["bad"], "Critique"), "warning": (T["warn"], "Attention")}
            html = ""
            for a in alertes:
                col, name = lv.get(a.get("niveau"), (T["accent"], "Information"))
                html += (f'<div class="alert"><span class="dot" style="background:{col}"></span>'
                         f'<div><div class="alert-lvl">{name}</div>{a["message"]}</div></div>')
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # --- controles regroupes par CATEGORIE DE TEST, PLEINE LARGEUR
        #     (hors des deux colonnes du haut : rien ne s'entasse d'un cote) ---
        niveaux_ctl = {
            "OK": (T["ok"], "Reussi"),
            "WARN": (T["warn"], "Vigilance"),
            "ERREUR": (T["bad"], "Incoherence"),
        }
        groupes = {}
        for item in val["rapport"]:
            m = re.match(r"(\d+)\.", item.get("test", ""))
            num = int(m.group(1)) if m else 999
            cat = _CATEGORIE_CONTROLE.get(num, "Autres controles")
            groupes.setdefault(cat, []).append(item)

        def _tint_ctl(hexc):
            return (f"color:{hexc};background:{hexc}1A")

        html_ctl = ""
        for cat in [c for c in _ORDRE_CATEGORIES if c in groupes] + \
                   [c for c in groupes if c not in _ORDRE_CATEGORIES]:
            items = groupes[cat]
            n_ok = sum(1 for i in items if i.get("niveau") == "OK")
            n_warn = sum(1 for i in items if i.get("niveau") == "WARN")
            n_err = sum(1 for i in items if i.get("niveau") == "ERREUR")
            if n_err:
                sum_col, sum_txt = T["bad"], f"{n_err} incoherence{'s' if n_err > 1 else ''}"
            elif n_warn:
                sum_col, sum_txt = T["warn"], f"{n_warn} vigilance{'s' if n_warn > 1 else ''}"
            else:
                sum_col, sum_txt = T["ok"], "tous reussis"
            html_ctl += (f'<div class="ctl-wrap">'
                         f'<div class="ctl-cat"><span>{cat}</span>'
                         f'<span class="ctl-sum" style="color:{sum_col}">{sum_txt}</span></div>')
            for item in items:
                col, badge = niveaux_ctl.get(item.get("niveau"),
                                             (T["muted"], "Info"))
                det = item.get("details") or ""
                det_html = f'<div class="ctl-m">{det}</div>' if det else ""
                html_ctl += (f'<div class="ctl-row">'
                             f'<span class="ctl-badge" style="{_tint_ctl(col)}">{badge}</span>'
                             f'<div><div class="ctl-t">{item["test"]}</div>'
                             f'<div class="ctl-m">{item.get("message", "")}</div>'
                             f'{det_html}</div></div>')
            html_ctl += "</div>"
        if html_ctl:
            st.markdown('<div class="section-t">Controles par categorie de test</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="ctl-grid">{html_ctl}</div>',
                        unsafe_allow_html=True)
