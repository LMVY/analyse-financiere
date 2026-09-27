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
from src.scoring.score import Scorer, PROFILS, load_config
from src.analysis.validator import Validator
from src.analysis.filter_ratios import filter_ratios, get_ratios_desactives
from src.scoring.sector_scorer import SectorScorer, detect_secteur, load_secteurs
from src.extraction.doc_detector import build_exercices, detect_doc_type, detect_annee
from src.extraction.doc_detector import build_exercices, detect_doc_type, detect_annee


st.set_page_config(
    page_title="Analyse Financiere",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Analyse Financiere d'Entreprise")


# ============================================================
# SESSION
# ============================================================
if "result" not in st.session_state:
    st.session_state.result = None
if "ratios" not in st.session_state:
    st.session_state.ratios = None
if "agregats" not in st.session_state:
    st.session_state.agregats = None
if "validation" not in st.session_state:
    st.session_state.validation = None
if "nb_exercices" not in st.session_state:
    st.session_state.nb_exercices = 0
if "analyse_faite" not in st.session_state:
    st.session_state.analyse_faite = False
if "config_yaml" not in st.session_state:
    st.session_state.config_yaml = load_config()


# ============================================================
# 1. UPLOAD
# ============================================================
st.header("1. Chargement des documents")
st.markdown("Deposez **tous les PDFs** (bilans + comptes de resultat, 2 a 5 exercices).")
st.markdown("L'outil detecte automatiquement le type de document et l'annee.")

pdfs = st.file_uploader(
    "Deposez tous les PDFs ici",
    type=["pdf"],
    accept_multiple_files=True,
    key="pdfs",
)

# Selecteur de secteur (optionnel)
st.markdown("### Secteur d'activite (optionnel)")
st.markdown("Selectionnez le secteur pour comparer aux references INSEE / Banque de France.")

secteurs_dispo = load_secteurs()
options_secteurs = ["Aucun (seuils fixes)"] + [info["label"] for info in secteurs_dispo.values()]
secteur_selectionne = st.selectbox("Secteur", options_secteurs, index=0)

# Code NAF personnalise
code_naf = st.text_input("Code NAF/APE (ex: C25.99Z, F41.20A, 6201Z)", "")

# Determiner le secteur
secteur_code = None
if secteur_selectionne != "Aucun (seuils fixes)":
    for code, info in secteurs_dispo.items():
        if info["label"] == secteur_selectionne:
            secteur_code = code
            break
elif code_naf:
    secteur_code = detect_secteur(code_naf)

if secteur_code:
    st.info(f"📊 Secteur : **{secteurs_dispo[secteur_code]['label']}**")

if pdfs and len(pdfs) >= 2:
    st.success(f"✅ {len(pdfs)} PDFs charges")

    if st.button("🚀 Lancer l'analyse", type="primary"):
        with st.spinner("Analyse en cours..."):
            progress = st.progress(0)
            status = st.empty()
            tmpdir = Path(tempfile.mkdtemp())

            # Sauvegarder tous les PDFs dans tmp
            paths = []
            for i, pdf in enumerate(pdfs):
                p = tmpdir / pdf.name
                p.write_bytes(pdf.read())
                paths.append(str(p))

            # Classer automatiquement
            status.text("Classification des documents...")
            exercices = build_exercices(paths)

            if not exercices:
                st.error("❌ Aucun exercice detecte")
                st.stop()

            st.info(f"📊 {len(exercices)} exercice(s) detecte(s) : {', '.join(ex['annee'] for ex in exercices)}")
            progress.progress(0.2)

            # Parser chaque exercice
            bilans_data = []
            for i, ex in enumerate(exercices):
                status.text(f"Parsing exercice {ex['annee']}...")

                data = {"actif": {}, "passif": {}, "compte_resultat": {}}

                # Parser le bilan (ou mixte)
                bilan_path = ex.get("bilan")
                if bilan_path:
                    parser = BilanParser(bilan_path)
                    d = parser.parse_simple(force_ocr=False)
                    data["actif"] = d.get("actif", {})
                    data["passif"] = d.get("passif", {})

                # Parser le CR (ou mixte)
                cr_path = ex.get("compte_resultat")
                if cr_path:
                    parser = BilanParser(cr_path)
                    d = parser.parse_simple(force_ocr=False)
                    data["compte_resultat"] = d.get("compte_resultat", {})

                bilans_data.append(data)
                progress.progress(0.2 + (i + 1) / len(exercices) * 0.6)

            # Agregats N
            data_n = bilans_data[0]
            agg_n = Agregats(data_n)
            agregats_n = agg_n.compute_all()
            r = Ratios(agregats_n)
            ratios = r.compute_all()

            # Croissance
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

            nb_exercices = len(exercices)
            ratios_filtres = filter_ratios(ratios, nb_exercices)

            validator = Validator(agregats_n, ratios_filtres, data_n)
            validation = validator.validate_all()

            scorer = Scorer(ratios_filtres, profil="moyen_terme")
            result = scorer.compute_all()

            st.session_state.result = result
            st.session_state.ratios = ratios_filtres
            st.session_state.agregats = agregats_n
            st.session_state.validation = validation
            st.session_state.nb_exercices = nb_exercices
            st.session_state.analyse_faite = True
            st.session_state.secteur_code = secteur_code

            status.text("✅ Analyse terminee")
            progress.progress(1.0)
            st.rerun()
else:
    st.info("Deposez au moins 2 PDFs (bilans + comptes de resultat).")


# ============================================================
# 2. RESULTATS
# ============================================================
if st.session_state.analyse_faite and st.session_state.result:

    result = st.session_state.result
    ratios = st.session_state.ratios
    agregats = st.session_state.agregats
    config = st.session_state.config_yaml
    nb_ex = st.session_state.nb_exercices

    st.markdown("---")

    # 2. AGREGATS CLES
    st.header("2. Agregats cles")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA", f"{agregats.get('chiffre_affaires', 0):,.0f} €")
    c2.metric("EBITDA", f"{agregats.get('ebitda', 0):,.0f} €")
    c3.metric("Resultat net", f"{agregats.get('resultat_net', 0):,.0f} €")
    c4.metric("Capitaux propres", f"{agregats.get('capitaux_propres', 0):,.0f} €")

    # 2b. SCORING SECTORIEL (si secteur selectionne)
    secteur_code = st.session_state.get("secteur_code")
    if secteur_code:
        secteurs = load_secteurs()
        info_secteur = secteurs.get(secteur_code, {})
        st.markdown("---")
        st.header("2b. Comparaison sectorielle")
        st.markdown(f"**Secteur : {info_secteur.get('label', '?')}**")

        # Ratios desactives du secteur
        desactives_secteur = info_secteur.get("ratios_desactives", [])
        if desactives_secteur:
            st.warning(f"⚠️ Ratios non pertinents pour ce secteur : {', '.join(desactives_secteur)}")

        # Scoring sectoriel
        sector_scorer = SectorScorer(ratios, secteur=secteur_code)
        sector_scores = sector_scorer.compute_sector_scores(config)

        if sector_scores:
            # Tableau comparatif
            comp_data = []
            for nom, info in sector_scores.items():
                ref = info.get("ref_secteur") or {}
                comp_data.append({
                    "Ratio": nom,
                    "Valeur": round(info["valeur"], 2),
                    "Score sectoriel": info["score"],
                    "Mediane secteur": ref.get("mediane", "?"),
                    "Q1": ref.get("q1", "?"),
                    "Q3": ref.get("q3", "?"),
                })

            df_comp = pd.DataFrame(comp_data)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            # Score sectoriel global
            score_sect = sum(s["score"] * s["poids"] for s in sector_scores.values()) / sum(s["poids"] for s in sector_scores.values())
            st.metric("Score sectoriel global", f"{score_sect:.1f}/100")

    # 3. SCORE GLOBAL
    st.header("3. Score global")
    c1, c2 = st.columns([1, 3])
    with c1:
        sc = result["score_global"]
        st.metric("Score global", f"{sc}/100")
        if sc >= 75: st.success("✅ Risque faible")
        elif sc >= 60: st.info("ℹ️ Risque modere")
        elif sc >= 45: st.warning("⚠️ Risque eleve")
        else: st.error("🚨 Risque critique")
    with c2:
        for cat, s in result["scores_categories"].items():
            if s is not None:
                a, b = st.columns([3, 1])
                with a: st.progress(min(s / 100, 1.0), text=f"{cat.replace('_', ' ').title()}")
                with b: st.write(f"**{s:.1f}/100**")

    # 4. VALIDATION
    st.markdown("---")
    st.header("4. Rapport de validation")
    if st.session_state.validation:
        val = st.session_state.validation
        stats = val["stats"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reussis", f"{stats['succes']}/{stats['total']}")
        c2.metric("Avertissements", stats['avertissements'])
        c3.metric("Erreurs", stats['erreurs'])
        c4.metric("Exercices", nb_ex)

        with st.expander("Voir les 18 tests"):
            for item in val["rapport"]:
                sym = {"OK": "✅", "WARN": "⚠️", "ERREUR": "🚨"}[item["niveau"]]
                st.write(f"{sym} **{item['test']}** : {item['message']}")
                if item["details"]:
                    st.caption(f"    {item['details']}")

    # 5. DETAIL DES RATIOS (interactif)
    st.markdown("---")
    st.header("5. Detail des ratios par categorie")
    st.markdown("💡 **Cliquez sur les en-tetes pour trier. Utilisez la recherche pour filtrer.**")

    details = result.get("details", {})
    par_cat = {}
    for nom, det in details.items():
        cat = det.get("categorie", "autre")
        par_cat.setdefault(cat, []).append((nom, det))

    for cat in ["liquidite", "endettement", "rentabilite", "structure_financiere",
                "croissance", "gestion_activite", "tresorerie", "risque_solvabilite"]:
        if cat not in par_cat:
            continue
        score_cat = result["scores_categories"].get(cat)
        titre = cat.replace("_", " ").title()

        with st.expander(f"**{titre}** — Score : {score_cat:.1f}/100" if score_cat else f"**{titre}**", expanded=True):
            data_table = []
            for nom, det in sorted(par_cat[cat], key=lambda x: -x[1].get("poids", 0)):
                data_table.append({
                    "Ratio": nom,
                    "Valeur": round(det.get("valeur", 0), 2) if det.get("valeur") is not None else 0,
                    "Score": det.get("score", 0),
                    "Poids": det.get("poids", 0),
                    "Cible": det.get("cible", ""),
                    "Source": det.get("source", ""),
                })

            df = pd.DataFrame(data_table)

            # Barre de recherche
            search = st.text_input(f"🔍 Rechercher dans {titre}", key=f"search_{cat}", label_visibility="collapsed")
            if search:
                df = df[df["Ratio"].str.contains(search, case=False)]

            # Tableau interactif avec tri natif
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score",
                        help="Score du ratio (0-100)",
                        format="%.1f",
                        min_value=0,
                        max_value=100,
                    ),
                    "Poids": st.column_config.NumberColumn("Poids", format="%.2f"),
                    "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f"),
                },
            )

            # Export CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"📥 Export CSV ({titre})",
                csv,
                file_name=f"ratios_{cat}.csv",
                mime="text/csv",
                key=f"csv_{cat}",
            )

    # 6. AJUSTEMENT AVANCE
    st.markdown("---")
    st.header("6. Ajustement avance")
    st.markdown("Ajustez les **poids des categories** ET les **poids des ratios** pour recalculer le score en temps reel.")

    # 6a. Profil predefini
    profil = st.selectbox("Profil predefini", options=list(PROFILS.keys()),
                          format_func=lambda x: PROFILS[x]["label"], index=2)

    # 6b. Poids des categories
    with st.expander("🎯 Poids des categories", expanded=True):
        poids_defaut = PROFILS[profil]["poids"]
        poids_custom = {}
        cols = st.columns(4)
        for i, (cat, poids) in enumerate(poids_defaut.items()):
            with cols[i % 4]:
                poids_custom[cat] = st.slider(
                    cat.replace("_", " ").title(),
                    0.0, 1.0, float(poids), 0.05,
                    key=f"cat_{cat}",
                )

    # 6c. Poids des ratios individuels
    with st.expander("🔧 Poids des ratios (avance)", expanded=False):
        st.markdown("Modifiez le poids de chaque ratio dans sa categorie.")
        poids_ratios_custom = {}
        for cat in ["liquidite", "endettement", "rentabilite", "structure_financiere",
                    "croissance", "gestion_activite", "tresorerie", "risque_solvabilite"]:
            if cat not in config:
                continue
            st.markdown(f"**{cat.replace('_', ' ').title()}**")
            cols = st.columns(3)
            for i, (nom_ratio, cfg_ratio) in enumerate(config[cat].items()):
                with cols[i % 3]:
                    val_defaut = cfg_ratio.get("poids", 0.0)
                    poids_ratios_custom[nom_ratio] = st.slider(
                        nom_ratio,
                        0.0, 1.0, float(val_defaut), 0.05,
                        key=f"rat_{nom_ratio}",
                    )

    # 6d. Recalcul
    total_cat = sum(poids_custom.values())
    if total_cat > 0:
        poids_cat_norm = {c: p / total_cat for c, p in poids_custom.items()}

        # Normaliser les poids des ratios par categorie
        config_custom = {}
        for cat, cfg_cat in config.items():
            if cat == "agregats":
                continue
            config_custom[cat] = {}
            total_poids_ratio = 0.0
            for nom_ratio, cfg_ratio in cfg_cat.items():
                p = poids_ratios_custom.get(nom_ratio, cfg_ratio.get("poids", 0))
                config_custom[cat][nom_ratio] = {**cfg_ratio, "poids": p}
                total_poids_ratio += p
            # Normaliser
            if total_poids_ratio > 0:
                for nom_ratio in config_custom[cat]:
                    config_custom[cat][nom_ratio]["poids"] /= total_poids_ratio

        # Scorer personnalise
        scorer_custom = Scorer(ratios, profil=profil, poids_custom=poids_cat_norm)
        scorer_custom.config = config_custom
        result_custom = scorer_custom.compute_all()

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Score par defaut", f"{result['score_global']}/100")
        with c2:
            delta = result_custom["score_global"] - result["score_global"]
            st.metric("Score personnalise", f"{result_custom['score_global']}/100", delta=f"{delta:+.1f}")
        with c3: st.metric("Ecart", f"{delta:+.2f}")

        # Comparaison des scores par categorie
        st.subheader("Comparaison par categorie")
        comp_data = []
        for cat in result["scores_categories"]:
            s_def = result["scores_categories"].get(cat)
            s_cus = result_custom["scores_categories"].get(cat)
            if s_def is not None and s_cus is not None:
                comp_data.append({"Categorie": cat, "Defaut": s_def, "Personnalise": s_cus, "Ecart": s_cus - s_def})

        if comp_data:
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Total des poids des categories = 0")
