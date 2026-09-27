"""Dashboard Streamlit - Analyse financiere."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import tempfile
import pandas as pd

from src.extraction.bilan_parser import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.scoring.score import Scorer, PROFILS
from src.analysis.validator import Validator
from src.analysis.filter_ratios import filter_ratios, get_ratios_desactives


st.set_page_config(
    page_title="Analyse Financiere",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Analyse Financiere d'Entreprise")
st.markdown("Deposez 2 a 5 bilans + 2 a 5 comptes de resultat pour obtenir une analyse complete.")


# ============================================================
# ETAT DE LA SESSION
# ============================================================
if "result" not in st.session_state:
    st.session_state.result = None
if "ratios" not in st.session_state:
    st.session_state.ratios = None
if "agregats" not in st.session_state:
    st.session_state.agregats = None
if "analyse_faite" not in st.session_state:
    st.session_state.analyse_faite = False


# ============================================================
# SECTION 1 : UPLOAD
# ============================================================
st.header("1. Chargement des documents")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Bilan (2 a 5 PDFs)")
    bilans = st.file_uploader(
        "Deposez les bilans (N, N-1, ...)",
        type=["pdf"], accept_multiple_files=True, key="bilans",
    )

with col2:
    st.subheader("Compte de resultat (2 a 5 PDFs)")
    comptes = st.file_uploader(
        "Deposez les comptes de resultat (N, N-1, ...)",
        type=["pdf"], accept_multiple_files=True, key="comptes",
    )

if bilans and comptes:
    if len(bilans) < 2:
        st.warning(f"⚠️ Il faut au moins 2 bilans (vous en avez {len(bilans)})")
    elif len(comptes) < 2:
        st.warning(f"⚠️ Il faut au moins 2 comptes de resultat (vous en avez {len(comptes)})")
    else:
        st.success(f"✅ {len(bilans)} bilans + {len(comptes)} comptes de resultat charges")

        if st.button("🚀 Lancer l'analyse", type="primary"):
            with st.spinner("Analyse en cours..."):
                progress = st.progress(0)
                status = st.empty()
                tmpdir = Path(tempfile.mkdtemp())

                # Parser les bilans (tries par nom desc)
                bilans_tries = sorted(bilans, key=lambda f: f.name, reverse=True)
                comptes_tries = sorted(comptes, key=lambda f: f.name, reverse=True)

                bilans_data = []
                for i, pdf in enumerate(bilans_tries):
                    status.text(f"Parsing bilan {i+1}/{len(bilans_tries)} : {pdf.name}")
                    p = tmpdir / f"bilan_{i}.pdf"
                    p.write_bytes(pdf.read())
                    parser = BilanParser(str(p))
                    data = parser.parse_simple(force_ocr=False)
                    bilans_data.append(data)
                    progress.progress((i + 1) / (len(bilans_tries) + len(comptes_tries)))

                # Parser les CR et fusionner
                for i, pdf in enumerate(comptes_tries):
                    status.text(f"Parsing CR {i+1}/{len(comptes_tries)} : {pdf.name}")
                    p = tmpdir / f"cr_{i}.pdf"
                    p.write_bytes(pdf.read())
                    parser = BilanParser(str(p))
                    data = parser.parse_simple(force_ocr=False)
                    if i < len(bilans_data):
                        bilans_data[i]["compte_resultat"] = data.get("compte_resultat", {})
                    progress.progress((len(bilans_tries) + i + 1) / (len(bilans_tries) + len(comptes_tries)))

                # Agregats N
                data_n = bilans_data[0]
                agg_n = Agregats(data_n)
                agregats_n = agg_n.compute_all()

                # Ratios N
                r = Ratios(agregats_n)
                ratios = r.compute_all()

                # Croissance N vs N-1
                if len(bilans_data) >= 2:
                    data_n1 = bilans_data[1]
                    agg_n1 = Agregats(data_n1)
                    agregats_n1 = agg_n1.compute_all()

                    def _growth(v_n, v_n1):
                        if v_n1 and v_n1 != 0 and v_n is not None:
                            return (v_n - v_n1) / abs(v_n1) * 100
                        return None

                    ratios["croissance"] = {
                        "croissance_ca": _growth(agregats_n.get("chiffre_affaires", 0), agregats_n1.get("chiffre_affaires", 0)),
                        "croissance_resultat_net": _growth(agregats_n.get("resultat_net", 0), agregats_n1.get("resultat_net", 0)),
                        "croissance_ebitda": _growth(agregats_n.get("ebitda", 0), agregats_n1.get("ebitda", 0)),
                        "croissance_capitaux_propres": _growth(agregats_n.get("capitaux_propres", 0), agregats_n1.get("capitaux_propres", 0)),
                    }
                else:
                    ratios["croissance"] = {}

                # Filtrer les ratios selon le nombre d'exercices
                nb_exercices = len(bilans_data)
                ratios_filtres = filter_ratios(ratios, nb_exercices)

                # Validation
                validator = Validator(agregats_n, ratios_filtres, data_n)
                validation = validator.validate_all()

                # Scorer sur les ratios filtres
                scorer = Scorer(ratios_filtres, profil="moyen_terme")
                result = scorer.compute_all()

                st.session_state.result = result
                st.session_state.ratios = ratios_filtres
                st.session_state.agregats = agregats_n
                st.session_state.validation = validation
                st.session_state.nb_exercices = nb_exercices
                st.session_state.analyse_faite = True

                status.text("✅ Analyse terminee")
                progress.progress(1.0)
                st.rerun()
else:
    st.info("Deposez au moins 2 bilans et 2 comptes de resultat pour lancer l'analyse.")


# ============================================================
# SECTION 2 : RESULTATS
# ============================================================
if st.session_state.analyse_faite and st.session_state.result:

    result = st.session_state.result
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

    # --- SCORE GLOBAL ---
    st.header("3. Score global")
    col1, col2 = st.columns([1, 3])

    with col1:
        score = result["score_global"]
        st.metric("Score global", f"{score}/100")

        if score >= 75:
            st.success("✅ Risque faible")
        elif score >= 60:
            st.info("ℹ️ Risque modere")
        elif score >= 45:
            st.warning("⚠️ Risque eleve")
        else:
            st.error("🚨 Risque critique")

    with col2:
        st.subheader("Scores par categorie")
        for cat, sc in result["scores_categories"].items():
            if sc is not None:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.progress(min(sc / 100, 1.0), text=f"{cat.replace('_', ' ').title()}")
                with col_b:
                    st.write(f"**{sc:.1f}/100**")
            else:
                st.write(f"{cat.replace('_', ' ').title()} : N/A")

    # --- RAPPORT DE VALIDATION ---
    st.markdown("---")
    st.header("4. Rapport de validation")

    if "validation" in st.session_state and st.session_state.validation:
        validation = st.session_state.validation
        stats = validation["stats"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tests reussis", f"{stats['succes']}/{stats['total']}")
        col2.metric("Avertissements", stats['avertissements'])
        col3.metric("Erreurs", stats['erreurs'])
        col4.metric("Exercices", st.session_state.get("nb_exercices", 0))

        if stats["erreurs"] == 0 and stats["avertissements"] == 0:
            st.success("✅ Toutes les verifications sont passees")
        elif stats["erreurs"] == 0:
            st.warning(f"⚠️ {stats['avertissements']} avertissement(s)")
        else:
            st.error(f"🚨 {stats['erreurs']} erreur(s) detectee(s)")

        with st.expander("Voir le detail des 18 tests"):
            for item in validation["rapport"]:
                sym = {"OK": "✅", "WARN": "⚠️", "ERREUR": "🚨"}[item["niveau"]]
                st.write(f"{sym} **{item['test']}** : {item['message']}")
                if item["details"]:
                    st.caption(f"    {item['details']}")

    # --- RATIOS DESACTIVES ---
    if "nb_exercices" in st.session_state:
        nb = st.session_state.nb_exercices
        desactives = get_ratios_desactives(nb)
        if desactives:
            with st.expander(f"ℹ️ Ratios desactives ({nb} exercice(s))"):
                for cat, info in desactives.items():
                    if info.get("ratios"):
                        st.write(f"**{cat}** : {info['raison']}")
                        for r in info["ratios"]:
                            st.write(f"  - {r}")

    # --- DETAILS DES RATIOS ---
    st.markdown("---")
    st.header("5. Detail des ratios par categorie")

    details = result.get("details", {})

    # Grouper par categorie
    par_cat = {}
    for nom, det in details.items():
        cat = det.get("categorie", "autre")
        if cat not in par_cat:
            par_cat[cat] = []
        par_cat[cat].append((nom, det))

    for cat in ["liquidite", "endettement", "rentabilite", "structure_financiere",
                "croissance", "gestion_activite", "tresorerie", "risque_solvabilite"]:

        if cat not in par_cat:
            continue

        score_cat = result["scores_categories"].get(cat)
        titre = cat.replace("_", " ").title()

        with st.expander(f"**{titre}** — Score : {score_cat:.1f}/100" if score_cat else f"**{titre}**"):

            data_table = []
            for nom, det in sorted(par_cat[cat], key=lambda x: -x[1].get("poids", 0)):
                data_table.append({
                    "Ratio": nom,
                    "Valeur": det.get("valeur"),
                    "Score": det.get("score"),
                    "Poids": f"{det.get('poids', 0):.2f}",
                    "Cible": det.get("cible", ""),
                    "Source": det.get("source", ""),
                })

            df = pd.DataFrame(data_table)
            st.dataframe(df, use_container_width=True)

    # --- AJUSTEMENT DES PONDERATIONS ---
    st.markdown("---")
    st.header("6. Ajustement des ponderations")
    st.markdown("Modifiez les poids des categories pour recalculer le score en temps reel.")

    profil = st.selectbox(
        "Profil predefini",
        options=list(PROFILS.keys()),
        format_func=lambda x: PROFILS[x]["label"],
        index=2,
    )

    poids_defaut = PROFILS[profil]["poids"]

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
    if total > 0:
        poids_normalises = {c: p / total for c, p in poids_custom.items()}
        st.info(f"Total : {total:.2f} → normalise automatiquement a 1.00")

        scorer_custom = Scorer(ratios, profil=profil, poids_custom=poids_normalises)
        result_custom = scorer_custom.compute_all()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score par defaut", f"{result['score_global']}/100")
        with col2:
            delta = result_custom["score_global"] - result["score_global"]
            st.metric("Score personnalise", f"{result_custom['score_global']}/100", delta=f"{delta:+.1f}")
        with col3:
            st.metric("Ecart", f"{delta:+.2f}")
