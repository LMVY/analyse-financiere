"""Styles du dashboard FinView : source unique du CSS.

Une fonction d'injection par page, appelee au debut du rendu :
injecter_base (theme, typographie, navigation), injecter_analyse
et injecter_parametrage. Couleurs : src.visualization.colors.
"""
import streamlit as st

from src.visualization.colors import THEME

T = dict(THEME)
FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"
root_vars = "".join(f"--{k}:{v};" for k, v in T.items())


# ============================================================
# BASE : variables de theme, typographie, navigation en haut a droite
# ============================================================
def injecter_base():
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


# ============================================================
# PAGE ANALYSE : composants maison, KPI, tableaux, controles, hero
# ============================================================
def injecter_analyse():
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
# PAGE PARAMETRAGE
# ============================================================
def injecter_parametrage():
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
