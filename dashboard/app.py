"""Dashboard Streamlit - Analyse financiere."""
import sys
from pathlib import Path

# Ajouter la racine du projet au PYTHONPATH
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import tempfile

from src.extraction.bilan_parser import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.multi_year import MultiYearData, GrowthCalculator
from src.scoring.score import Scorer, PROFILS


st.set_page_config(
    page_title="Analyse Financiere",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Analyse Financiere d'Entreprise")
st.markdown("Deposez 2 a 5 bilans et 2 a 5 comptes de resultat pour obtenir une analyse complete.")


# ============================================================
# ETAT DE LA SESSION
# ============================================================
if "data_n" not in st.session_state:
    st.session_state.data_n = None
if "agregats" not in st.session_state:
    st.session_state.agregats = None
if "ratios" not in st.session_state:
    st.session_state.ratios = None
if "analyse_faite" not in st.session_state:
    st.session_state.analyse_faite = False


# ============================================================
# SECTION 1 : UPLOAD DES PDFs
# ============================================================
st.header("1. Chargement des documents")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Bilan (2 a 5 PDFs)")
    bilans = st.file_uploader(
        "Deposez les bilans (N, N-1, ...)",
        type=["pdf"],
        accept_multiple_files=True,
        key="bilans",
    )

with col2:
    st.subheader("Compte de resultat (2 a 5 PDFs)")
    comptes = st.file_uploader(
        "Deposez les comptes de resultat (N, N-1, ...)",
        type=["pdf"],
        accept_multiple_files=True,
        key="comptes",
    )

# Verification
if bilans and comptes:
    if len(bilans) < 2:
        st.warning(f"⚠️ Il faut au moins 2 bilans (vous en avez {len(bilans)})")
    elif len(comptes) < 2:
        st.warning(f"⚠️ Il faut au moins 2 comptes de resultat (vous en avez {len(comptes)})")
    else:
        st.success(f"✅ {len(bilans)} bilans + {len(comptes)} comptes de resultat charges")

        if st.button("🚀 Lancer l'analyse", type="primary"):
            with st.spinner("Analyse en cours... (peut prendre 2-3 minutes)"):
                progress = st.progress(0)
                status = st.empty()

                # Sauvegarder les fichiers uploades dans /tmp
                tmpdir = Path(tempfile.mkdtemp())

                # Parser chaque bilan
                bilans_data = []
                for i, pdf in enumerate(sorted(bilans, key=lambda f: f.name, reverse=True)):
                    status.text(f"Parsing bilan {i+1}/{len(bilans)} : {pdf.name}")
                    pdf_path = tmpdir / f"bilan_{i}.pdf"
                    pdf_path.write_bytes(pdf.read())
                    parser = BilanParser(str(pdf_path))
                    data = parser.parse_simple(force_ocr=False)
                    bilans_data.append({"annee": f"N-{i}" if i > 0 else "N", "data": data})
                    progress.progress((i + 1) / (len(bilans) + len(comptes)))

                # Parser chaque compte de resultat
                for i, pdf in enumerate(sorted(comptes, key=lambda f: f.name, reverse=True)):
                    status.text(f"Parsing CR {i+1}/{len(comptes)} : {pdf.name}")
                    pdf_path = tmpdir / f"cr_{i}.pdf"
                    pdf_path.write_bytes(pdf.read())
                    parser = BilanParser(str(pdf_path))
                    data = parser.parse_simple(force_ocr=False)
                    # Fusionner avec le bilan correspondant
                    if i < len(bilans_data):
                        bilans_data[i]["data"]["compte_resultat"] = data.get("compte_resultat", {})
                    progress.progress((len(bilans) + i + 1) / (len(bilans) + len(comptes)))

                # Calculer les agregats sur le dernier exercice
                data_n = bilans_data[0]["data"]
                st.session_state.data_n = data_n

                agg = Agregats(data_n)
                agregats = agg.compute_all()
                st.session_state.agregats = agregats

                # Calculer les ratios
                r = Ratios(agregats)
                ratios = r.compute_all()
                st.session_state.ratios = ratios

                st.session_state.analyse_faite = True
                status.text("✅ Analyse terminee")
                progress.progress(1.0)
                st.rerun()
else:
    st.info("Deposez au moins 2 bilans et 2 comptes de resultat pour lancer l'analyse.")


# ============================================================
# SECTION 2 : RESULTATS (si analyse faite)
# ============================================================
if st.session_state.analyse_faite and st.session_state.ratios:

    ratios = st.session_state.ratios
    agregats = st.session_state.agregats

    st.markdown("---")

    # --- AGREGATS CLES ---
    st.header("2. Agregats cles")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Chiffre d'affaires", f"{agregats.get('chiffre_affaires', 0):,.0f} €")
    col2.metric("EBITDA", f"{agregats.get('ebitda', 0):,.0f} €")
    col3.metric("Resultat net", f"{agregats.get('resultat_net', 0):,.0f} €")
    col4.metric("Capitaux propres", f"{agregats.get('capitaux_propres', 0):,.0f} €")

    # --- ANALYSE PAR DEFAUT ---
    st.header("3. Analyse par defaut")

    scorer_default = Scorer(ratios, profil="moyen_terme")
    result_default = scorer_default.compute_all()
    rec_default = scorer_default.get_recommandation(result_default["score_global"])

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Score global", f"{result_default['score_global']}/100")
        st.info(f"**{rec_default}**")

    with col2:
        st.subheader("Scores par categorie")
        scores_cat = result_default["scores_categories"]
        for cat, score in scores_cat.items():
            if score is not None:
                st.progress(min(score / 100, 1.0), text=f"{cat} : {score}/100")

    # --- AJUSTEMENT DES PONDERATIONS ---
    st.markdown("---")
    st.header("4. Ajustement des ponderations")
    st.markdown("Modifiez les poids pour recalculer le score en temps reel.")

    profil_choisi = st.selectbox(
        "Profil predefini",
        options=list(PROFILS.keys()),
        format_func=lambda x: PROFILS[x]["label"],
        index=2,
    )

    poids_defaut = PROFILS[profil_choisi]["poids"]

    st.subheader("Ponderations personnalisees")
    poids_custom = {}
    cols = st.columns(4)
    for i, (cat, poids) in enumerate(poids_defaut.items()):
        with cols[i % 4]:
            poids_custom[cat] = st.slider(
                cat.replace("_", " ").title(),
                0.0, 1.0, float(poids), 0.05,
                key=f"slider_{cat}",
            )

    total = sum(poids_custom.values())
    if abs(total - 1.0) > 0.01:
        st.warning(f"⚠️ Total des poids : {total:.2f} (doit etre egal a 1.00)")
    else:
        st.success(f"✅ Total des poids : {total:.2f}")

    # --- SCORE PERSONNALISE ---
    if abs(total - 1.0) <= 0.01:
        st.markdown("---")
        st.header("5. Score personnalise")

        scorer_custom = Scorer(ratios, profil=profil_choisi, poids_custom=poids_custom)
        result_custom = scorer_custom.compute_all()
        rec_custom = scorer_custom.get_recommandation(result_custom["score_global"])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Score par defaut", f"{result_default['score_global']}/100")
        with col2:
            delta = result_custom["score_global"] - result_default["score_global"]
            st.metric("Score personnalise", f"{result_custom['score_global']}/100", delta=f"{delta:+.1f}")

        st.info(f"**{rec_custom}**")
