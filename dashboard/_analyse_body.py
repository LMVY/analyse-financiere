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
from src.visualization.colors import THEME, CATEGORIES

T = dict(THEME)
FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"


def hex_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def score_color(s):
    if s is None:
        return T["muted"]
    return T["ok"] if s >= 70 else T["warn"] if s >= 40 else T["bad"]


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

    /* Onglets */
    [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid var(--line); }
    button[role="tab"] { padding: .6rem 0; color: var(--muted); font-weight: 500; background: transparent; }
    button[role="tab"][aria-selected="true"] { color: var(--ink); font-weight: 600; }
    [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
    [data-baseweb="tab-border"] { display: none; }

    /* Boutons */
    .stButton > button, .stDownloadButton > button {
        border-radius: 8px; font-weight: 600; border: 1px solid var(--line);
        background: var(--paper); color: var(--ink); box-shadow: none;
    }
    .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--accent); color: var(--accent); }
    .stButton > button[kind="primary"] { background: var(--ink); border-color: var(--ink); color: #fff; }
    .stButton > button[kind="primary"]:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
    button:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

    /* Uploader */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--paper); border: 1px dashed #C5CBD6; border-radius: 12px; padding: 2rem;
    }
    [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--accent); }

    [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 10px; background: var(--paper); }

    /* Composants maison */
    .sub { color: var(--muted); font-size: .95rem; margin-top: .25rem; }
    .ring-wrap { display: flex; align-items: center; gap: 1.75rem; }
    .verdict { font-size: 1.35rem; font-weight: 650; letter-spacing: -.01em; }
    .verdict-sub { color: var(--muted); margin-top: .35rem; max-width: 26ch; line-height: 1.45; }
    .meta { color: var(--muted); font-size: .85rem; margin-top: .35rem; }
    .meta b { color: var(--ink); }

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

    @media (max-width: 760px) {
        .row { grid-template-columns: 1fr 3.5rem; }
        .row .track { grid-column: 1 / -1; order: 3; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. IMPORTS MÉTIER
# ============================================================
from src.extraction.mistral_docai import DocumentAIExtractor, SECTIONS
from src.extraction.controle_extraction import scorer_extraction
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.scoring.score import Scorer, PROFILS, load_config, load_profils
from src.analysis.validator import Validator
from src.analysis.filter_ratios import filter_ratios
from src.analysis.historique import calculer_historique
from src.scoring.sector_scorer import SectorScorer, detect_secteur, load_secteurs
from src.visualization.charts import (
    evolution_multi_annees, benchmark_sectoriel, comparaison_n_n1,
)
from src.reporting.pdf_report import generate_pdf_report
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


def kpi(name, value, delta):
    d = ""
    if delta is not None:
        c = T["ok"] if delta >= 0 else T["bad"]
        arrow = "▲" if delta >= 0 else "▼"
        d = f'<div class="kpi-d" style="color:{c}">{arrow} {abs(delta):.1f} % vs N-1</div>'
    return f'<div class="kpi"><div class="kpi-l">{name}</div><div class="kpi-v">{fmt_eur(value)}</div>{d}</div>'


def score_ring(score, size=168):
    r, sw = 70, 12
    circ = 2 * 3.14159265 * r
    dash = circ * max(0, min(100, score)) / 100
    col = score_color(score)
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 180 180" role="img" aria-label="Score {score:.0f} sur 100">
      <circle cx="90" cy="90" r="{r}" fill="none" stroke="{T['line']}" stroke-width="{sw}"/>
      <circle cx="90" cy="90" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"
              stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 90 90)"/>
      <text x="90" y="94" text-anchor="middle" font-family="{FONT}" font-size="46" font-weight="700"
            fill="{T['ink']}">{score:.0f}</text>
      <text x="90" y="118" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{T['muted']}">sur 100</text>
    </svg>"""


def category_rows(scores):
    html = ""
    for cat, s in scores.items():
        if s is None:
            continue
        html += (f'<div class="row"><div class="row-l">{label(cat)}</div>'
                 f'<div class="track"><div class="fill" style="width:{max(0, min(100, s))}%;background:{score_color(s)}"></div></div>'
                 f'<div class="row-v">{s:.0f}</div></div>')
    return html


def base_layout(fig, height=340):
    grid = T["line"]
    fig.update_layout(
        height=height, margin=dict(l=16, r=16, t=16, b=16),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["muted"], size=12),
        legend=dict(orientation="h", y=-0.15, font=dict(color=T["ink"])),
    )
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid, linecolor=grid)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid, linecolor=grid)
    return fig


def radar_chart(scores):
    items = [(label(k), v) for k, v in scores.items() if v is not None]
    if not items:
        return None
    theta = [i[0] for i in items] + [items[0][0]]
    r = [i[1] for i in items] + [items[0][1]]
    fig = go.Figure(go.Scatterpolar(
        r=r, theta=theta, fill="toself", name="Score",
        line=dict(color=T["accent"], width=2), fillcolor=hex_rgba(T["accent"], 0.14),
    ))
    base_layout(fig, 340)
    fig.update_layout(showlegend=False, margin=dict(l=48, r=48, t=24, b=24), polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor=T["line"], linecolor=T["line"],
                        tickfont=dict(size=10, color=T["muted"]), tickvals=[25, 50, 75, 100]),
        angularaxis=dict(gridcolor=T["line"], linecolor=T["line"], tickfont=dict(color=T["ink"], size=12)),
    ))
    return fig


def contribution_chart(scores, poids, cible=60):
    """Contribution au score - version simplifiee."""
    cats = [k for k, v in scores.items() if v is not None]
    if not cats:
        return None

    w = {k: (poids or {}).get(k, 1) for k in cats}
    tot = sum(w.values()) or 1
    contrib = {k: scores[k] * w[k] / tot for k in cats}

    order = list(reversed(cats))

    labels = [k.replace("_", " ").capitalize() for k in order]
    vals = [contrib[k] for k in order]
    couleurs = [
        "#1F9D6B" if scores[k] >= 70 else "#D98E04" if scores[k] >= 40 else "#D64545"
        for k in order
    ]

    fig = go.Figure()
    fig.add_bar(
        y=labels, x=vals, orientation="h",
        marker=dict(color=couleurs),
        text=[f"{v:.1f}" for v in vals],
        textposition="outside",
    )
    fig.update_layout(
        height=340,
        margin=dict(l=16, r=16, t=16, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["muted"], size=12),
        showlegend=False,
        xaxis=dict(gridcolor=T["line"], title="Points de score"),
        yaxis=dict(showgrid=False),
    )
    return fig




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


# ============================================================
# 4. EN-TETE
# ============================================================
h_left, h_opts, h_pdf = st.columns([6, 1.3, 1.7], vertical_alignment="center")
with h_left:
    st.markdown("<h1>Analyse financiere</h1>", unsafe_allow_html=True)
    if st.session_state.analyse_faite:
        nom = st.session_state.get("nom_entreprise", "")
        naf_auto = st.session_state.get("naf_auto")
        secteur_label = st.session_state.get("secteur_auto_label")
        meta = nom
        if naf_auto:
            meta += f" &middot; Code NAF : <b>{naf_auto}</b>"
        if secteur_label:
            meta += f" &middot; <b>Secteur auto-detecte</b> : {secteur_label}"
        st.markdown(f"<div class='sub'>{meta}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='sub'>Deposez une liasse fiscale ou un bilan pour obtenir un score detaille.</div>",
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

with h_pdf:
    if st.session_state.analyse_faite:
        if st.button("Exporter en PDF", type="primary", use_container_width=True):
            try:
                bilans = st.session_state.get("bilans_data", [])
                agg_n1 = (Agregats(bilans[1]).compute_all()
                          if len(bilans) >= 2 else None)
                st.session_state.pdf_bytes = generate_pdf_report(
                    result=st.session_state.result,
                    agregats=st.session_state.agregats,
                    agregats_n1=agg_n1,
                    validation=st.session_state.validation,
                    alertes=st.session_state.alertes,
                    company_name=st.session_state.get("nom_entreprise") or "Entreprise analysee",
                    secteur_label=st.session_state.result.get("secteur_label"),
                )
            except Exception as e:
                st.session_state.pdf_bytes = None
                st.error(f"L'export a echoue : {e}")

if st.session_state.get("pdf_bytes"):
    st.download_button("Telecharger le rapport", data=st.session_state.pdf_bytes,
                       file_name="Rapport_Financier.pdf", mime="application/pdf")

st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)


# ============================================================
# 5. IMPORT
# ============================================================
zone = st.expander("Remplacer les documents") if st.session_state.analyse_faite else st.container()
with zone:
    fichiers = st.file_uploader(
        "Documents comptables (PDF natif ou scanne, JPG, PNG)",
        type=["pdf", "jpg", "jpeg", "png"],
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

            try:
                extractor = DocumentAIExtractor()
            except ValueError as e:
                st.error(str(e))
                st.stop()

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
                if Path(p).suffix.lower() not in (".pdf", ".jpg", ".jpeg", ".png"):
                    erreurs.append(f"{f.name} : format ignore (Document AI lit PDF, JPG, PNG)")
                    continue

                st.write(f"Extraction Document AI : {f.name}")
                try:
                    annotation = extractor.extraire(p)
                    data_f = extractor.vers_format_standard(annotation)
                except Exception as e:
                    erreurs.append(f"{f.name} : {e}")
                    continue

                data_n, data_n1 = scinder_exercices(data_f)
                controles.append((f.name, scorer_extraction(data_n, "mistral_docai")))
                extraits.append((f.name, data_n, data_n1, _annee_fichier(f.name),
                                 annotation.get("meta") or {}))

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
                st.error("Aucun document exploitable apres extraction Document AI.")
                status.update(label="Echec de l'extraction", state="error")
                st.stop()

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
                        "croissance_resultat_net": calculer_croissance(agg_n.get("resultat_net"), agg_n1.get("resultat_net")),
                        "croissance_ebitda": calculer_croissance(agg_n.get("ebitda"), agg_n1.get("ebitda")),
                        "croissance_capitaux_propres": calculer_croissance(agg_n.get("capitaux_propres"), agg_n1.get("capitaux_propres")),
                    }
                ratios_f = filter_ratios(ratios, len(exercices))
                st.session_state.validation = Validator(agg_n, ratios_f, data_n).validate_all()
                st.session_state.agregats = agg_n
                st.session_state.ratios = ratios_f
                st.session_state.alertes = detect_alerts(agg_n, ratios_f)
                st.session_state.bilans_data = bilans_data
                st.session_state.exercices = exercices
                st.session_state.ratios_par_annee = ratios_par_annee
                st.session_state.historique = historique

                # Identification de l'entreprise : meta du document le plus recent
                meta_recent = extraits[0][4] if extraits else {}
                st.session_state.nom_entreprise = (
                    meta_recent.get("raison_sociale")
                    or Path(fichiers_tri[0][0].name).stem
                )
                naf = meta_recent.get("code_naf")
                st.session_state.naf_auto = naf
                st.session_state.secteur_auto_code = detect_secteur(naf) if naf else None
                st.session_state.secteur_auto_label = (
                    load_secteurs()[st.session_state.secteur_auto_code]["label"]
                    if st.session_state.secteur_auto_code else None
                )

                st.session_state.pdf_bytes = None
                st.session_state.analyse_faite = True
                st.session_state.files_sig = files_sig
            status.update(label="Analyse terminee", state="complete")
            st.rerun()


# ============================================================
# 6. RESULTATS
# ============================================================
if st.session_state.analyse_faite:
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

    methode = "standard"
    res = None

    if secteur_code:
        try:
            _sector = SectorScorer(st.session_state.ratios, secteur=secteur_code)
            res = _sector.compute_scores_by_category(st.session_state.config_yaml)
            if res.get("score_global", 0) > 0:
                methode = "sectorielle"
            else:
                res = None
        except Exception:
            res = None

    if res is None:
        try:
            res = Scorer(st.session_state.ratios, profil=profil).compute_all()
        except Exception:
            profil = "moyen_terme"
            res = Scorer(st.session_state.ratios, profil=profil).compute_all()
        methode = "standard"

    res["methode"] = methode
    res["secteur_code"] = secteur_code
    res["secteur_label"] = secteur_label
    st.session_state.result = res

    agg = st.session_state.agregats
    score = res.get("score_global", 0) or 0
    cats = res.get("scores_categories", {})
    alertes = st.session_state.alertes
    val = st.session_state.validation
    stats = val["stats"]

    d = {"ca": None, "ebitda": None, "rn": None, "cp": None}
    if len(st.session_state.bilans_data) >= 2:
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

    left, right = st.columns([5, 7], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            f'<div class="ring-wrap">{score_ring(score)}<div>'
            f'<div class="verdict" style="color:{score_color(score)}">{verdict(score)}</div>'
            f'<div class="verdict-sub">{resume}</div>'
            f'<div class="meta">{("Score sectoriel - " + secteur_label) if methode == "sectorielle" and secteur_label else "Score standard (seuils fixes)"}</div>'
            f'</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            '<div class="kpi-grid">'
            + kpi("Chiffre d'affaires", agg.get("chiffre_affaires"), d["ca"])
            + kpi("EBITDA", agg.get("ebitda"), d["ebitda"])
            + kpi("Resultat net", agg.get("resultat_net"), d["rn"])
            + kpi("Capitaux propres", agg.get("capitaux_propres"), d["cp"])
            + "</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    if secteur_code:
        tab_syn, tab_rat, tab_sect, tab_ctl = st.tabs(["Synthese", "Ratios", "Secteur", "Controles"])
    else:
        tab_syn, tab_rat, tab_ctl = st.tabs(["Synthese", "Ratios", "Controles"])
        tab_sect = None

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
        fig_contrib = contribution_chart(cats, poids)
        if fig_contrib:
            st.plotly_chart(fig_contrib, use_container_width=True, config={"displayModeBar": False})

        if len(st.session_state.get("bilans_data", [])) >= 2:
            st.markdown('<div class="section-t">Comparaison des agregats N vs N-1 (EUR)</div>',
                        unsafe_allow_html=True)
            try:
                agg_n1_cmp = Agregats(st.session_state.bilans_data[1]).compute_all()
                fig_cmp = comparaison_n_n1(agg, agg_n1_cmp)
                if fig_cmp:
                    st.plotly_chart(fig_cmp, use_container_width=True,
                                    config={"displayModeBar": False})
            except Exception as e:
                st.warning(f"Comparaison indisponible : {e}")

            st.markdown('<div class="section-t">Evolution des indicateurs sur les exercices disponibles (EUR)</div>',
                        unsafe_allow_html=True)
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
                ]
                for row in range(2):
                    col_g, col_d = st.columns(2, gap="medium")
                    for col, (code_evo, label_evo) in zip(
                            (col_g, col_d), indicateurs_evo[row * 2:row * 2 + 2]):
                        with col:
                            fig_evo = evolution_multi_annees(agregats_par_annee, code_evo, label_evo)
                            if fig_evo:
                                fig_evo = base_layout(fig_evo, 300)
                                st.plotly_chart(fig_evo, use_container_width=True,
                                                config={"displayModeBar": False})
            except Exception as e:
                st.warning(f"Evolution indisponible : {e}")

    with tab_rat:
        details = res.get("details", {})
        historique = st.session_state.get("historique", {})

        rows = []
        for nom, det in details.items():
            h = historique.get(nom, {})
            val_n = det.get("valeur")
            val_moy = h.get("moyenne")
            tendance = h.get("tendance", "-")
            type_r = h.get("type", "flux")

            if type_r == "stock":
                val_moy = val_n
                tendance = "-"

            rows.append({
                "Ratio": nom,
                "Categorie": label(det.get("categorie", "autre")),
                "Type": type_r,
                "Valeur N": round(val_n, 2) if val_n is not None else None,
                "Moyenne": round(val_moy, 2) if val_moy is not None else None,
                "Tendance": tendance,
                "Score": det.get("score", 0),
                "Poids": det.get("poids", 0),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                choix = st.selectbox("Categorie", ["Toutes"] + sorted(df["Categorie"].unique()))
            with col_f2:
                filtre_type = st.selectbox("Type", ["Tous", "flux", "stock"])
            if choix != "Toutes":
                df = df[df["Categorie"] == choix]
            if filtre_type != "Tous":
                df = df[df["Type"] == filtre_type]

        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Valeur N": st.column_config.NumberColumn("Valeur N", format="%.2f"),
                "Moyenne": st.column_config.NumberColumn("Moyenne", format="%.2f"),
                "Tendance": st.column_config.TextColumn("Tend.", width="small"),
                "Score": st.column_config.ProgressColumn("Score", format="%.0f", min_value=0, max_value=100),
                "Poids": st.column_config.NumberColumn("Poids", format="%.2f"),
            },
        )

    if tab_sect is not None:
        with tab_sect:
            st.markdown(f'<div class="section-t">Reference : {secteur_label}</div>', unsafe_allow_html=True)
            try:
                fig_bench = benchmark_sectoriel(st.session_state.ratios, secteur_code, secteurs_dispo)
                if fig_bench:
                    fig_bench = base_layout(fig_bench, 400)
                    st.plotly_chart(fig_bench, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.info("Pas assez de ratios comparables pour ce secteur.")
            except Exception as e:
                st.warning(f"Benchmark sectoriel indisponible : {e}")

    with tab_ctl:
        c1, c2 = st.columns(2, gap="large")
        with c1:
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
        with c2:
            st.markdown('<div class="section-t">Audit comptable</div>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="stat"><b>{stats["succes"]}/{stats["total"]}</b><span>Controles reussis</span></span>'
                f'<span class="stat"><b>{stats["avertissements"]}</b><span>Avertissements</span></span>'
                f'<span class="stat"><b>{stats["erreurs"]}</b><span>Erreurs</span></span>',
                unsafe_allow_html=True)
            with st.expander("Detail des controles"):
                for item in val["rapport"]:
                    st.write(f"- **{item['test']}** : {item['message']}")
