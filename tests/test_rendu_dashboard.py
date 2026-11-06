import sys, copy, warnings
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import streamlit as st

from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios
from src.analysis.validator import Validator
from src.analysis.historique import calculer_historique
from src.scoring.score import Scorer, load_config, load_profils
from src.scoring.alerts import detect_alerts

DATA = {
    "actif": {"total_actif": 1000.0, "actif_immobilise": 600.0, "total_stocks": 100.0,
              "total_creances": 150.0, "disponibilites": 50.0,
              "valeurs_mobilieres_placement": 20.0},
    "passif": {"total_capitaux_propres": 400.0, "dettes_financieres": 300.0,
               "dettes_fournisseurs": 100.0, "dettes_fiscales_sociales": 80.0,
               "autres_dettes": 20.0, "total_dettes": 500.0,
               "total_passif": 1000.0, "resultat_exercice": 60.0},
    "compte_resultat": {"chiffre_affaires": 1200.0, "achats_matieres": 400.0,
                        "autres_achats_charges_externes": 200.0, "impots_taxes": 20.0,
                        "salaires_traitements": 200.0, "charges_sociales": 80.0,
                        "dotations_amortissements_immob": 50.0,
                        "resultat_exploitation": 70.0, "interets_charges_assimilees": 25.0,
                        "resultat_net": 60.0},
}
agg = Agregats(copy.deepcopy(DATA)).compute_all()
ratios_f = filter_ratios(Ratios(agg).compute_all(), 3)
res = Scorer(ratios_f, profil="moyen_terme").compute_all()
res["methode"] = "standard"
res["secteur_code"] = None
res["secteur_label"] = None
validation = Validator(agg, ratios_f, DATA).validate_all()
alertes = detect_alerts(agg, ratios_f)

st.session_state["analyse_faite"] = True
st.session_state["nom_entreprise"] = "TEST SCI"
st.session_state["naf_auto"] = None
st.session_state["secteur_auto_label"] = None
st.session_state["secteur_auto_code"] = None
st.session_state["config_yaml"] = load_config()
st.session_state["profils_dispo"] = load_profils()
st.session_state["result"] = res
st.session_state["agregats"] = agg
st.session_state["ratios"] = ratios_f
st.session_state["validation"] = validation
st.session_state["alertes"] = alertes
st.session_state["bilans_data"] = [copy.deepcopy(DATA) for _ in range(3)]
st.session_state["exercices"] = [{"path": None, "nom": str(a), "type": "docai", "annee": a}
                                 for a in (2024, 2023, 2022)]
st.session_state["ratios_par_annee"] = {"2024": ratios_f, "2023": ratios_f, "2022": ratios_f}
st.session_state["historique"] = calculer_historique({"2024": ratios_f, "2023": ratios_f})
st.session_state["files_sig"] = "test"
st.session_state["controles"] = []
st.session_state.pop("pdf_bytes", None)

from dashboard import page_analyse, page_parametrage

try:
    page_analyse.afficher()
    print("RENDU COMPLET DE LA PAGE ANALYSE : OK, aucune exception")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("ECHEC RENDU :", type(e).__name__, e)
    sys.exit(1)

# ============================================================
# Page Parametrage : rendu sans exception (mode autonome)
# ============================================================
try:
    page_parametrage.afficher()
    print("RENDU COMPLET DE LA PAGE PARAMETRAGE : OK, aucune exception")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("ECHEC RENDU PARAMETRAGE :", type(e).__name__, e)
    sys.exit(1)

# ============================================================
# Scenario du bug reel : premier rendu apres analyse, "result" absent
# (l'en-tete s'execute avant la section Resultats) - la page doit
# rendre sans exception (garde + pre-calcul a l'import).
# ============================================================
st.session_state.pop("result", None)
st.session_state.pop("pdf_cache", None)
try:
    page_analyse.afficher()
    print("RENDU SANS 'result' PRE-CALCULE (garde en-tete) : OK, aucune exception")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("ECHEC (result absent) :", type(e).__name__, e)
    sys.exit(1)
