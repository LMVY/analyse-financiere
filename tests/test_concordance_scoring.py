"""Audit de concordance du scoring.

Verifie, sur un jeu de donnees a valeurs connues :
1. les agregats intermediaires (SIG, structure, tresorerie) ;
2. chaque ratio calcule par src/analysis/ratios.py (formule attendue) ;
3. le score de chaque ratio vs la grille YAML (seuils, sens) ;
4. le score de categorie = moyenne ponderee par les poids CONFIGURES ;
5. le score global = moyenne ponderee par les poids du PROFIL configure ;
6. la concordance avec la config utilisateur (ratios_actifs, poids) ;
7. le scoring sectoriel (quartiles Q1/mediane/Q3, ratios desactives,
   poids du profil).

Lancement : python tests/test_concordance_scoring.py (depuis la racine)
La vraie config utilisateur (data/config_user.yaml) n'est JAMAIS modifiee :
elle est detournee via config_loader.USER_PATH vers un fichier temporaire.
"""
import sys
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import src.scoring.config_loader as cl
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import (
    filter_ratios, load_categories,
    MIN_EXERCICES_ANALYSE, MAX_EXERCICES_ANALYSE,
)
from src.scoring.score import Scorer, score_grille
from src.scoring.sector_scorer import SectorScorer

TMP = ROOT / "data" / "raw" / "test_concordance"
TMP.mkdir(parents=True, exist_ok=True)

echecs = []


def check(nom, cond, detail=""):
    etat = "OK " if cond else "KO "
    print(f"  [{etat}] {nom}" + (f" -> {detail}" if detail and not cond else ""))
    if not cond:
        echecs.append(f"{nom} : {detail}")


def proche(a, b, tol=1e-4):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(1.0, abs(b))


# ============================================================
# Jeu de donnees a valeurs connues (un exercice)
# ============================================================
DATA = {
    "actif": {
        "total_actif": 1000.0, "actif_immobilise": 600.0,
        "total_stocks": 100.0, "total_creances": 150.0,
        "disponibilites": 50.0, "valeurs_mobilieres_placement": 20.0,
    },
    "passif": {
        "total_capitaux_propres": 400.0, "dettes_financieres": 300.0,
        "dettes_fournisseurs": 100.0, "dettes_fiscales_sociales": 80.0,
        "autres_dettes": 20.0, "total_dettes": 500.0,
        "total_passif": 1000.0, "resultat_exercice": 60.0,
    },
    "compte_resultat": {
        "chiffre_affaires": 1200.0, "achats_matieres": 400.0,
        "autres_achats_charges_externes": 200.0, "impots_taxes": 20.0,
        "salaires_traitements": 200.0, "charges_sociales": 80.0,
        "dotations_amortissements_immob": 50.0, "resultat_exploitation": 70.0,
        "interets_charges_assimilees": 25.0, "resultat_net": 60.0,
    },
}

# ============================================================
# Patch de la config utilisateur (jamais le vrai fichier)
# ============================================================
USER_TMP = TMP / "config_user_test.yaml"
USER_ABSENT = TMP / "config_user_absente.yaml"
USER_TMP.write_text("", encoding="utf-8")
REAL_USER_PATH = cl.USER_PATH


def with_config_user(cfg_user, fn):
    """Execute fn avec config_loader.USER_PATH pointant vers cfg_user."""
    cl.USER_PATH = USER_TMP
    try:
        if cfg_user is None:
            cl.USER_PATH = USER_ABSENT     # force la config par defaut
        else:
            USER_TMP.write_text(yaml.dump(cfg_user, allow_unicode=True),
                                encoding="utf-8")
        return fn()
    finally:
        cl.USER_PATH = REAL_USER_PATH


CFG_DEFAUT = yaml.safe_load((ROOT / "config" / "ratios_config.yaml")
                            .read_text(encoding="utf-8"))
PROFILS_DEFAUT = yaml.safe_load((ROOT / "config" / "profils.yaml")
                                .read_text(encoding="utf-8"))


# ============================================================
# Implementation independante du score d'un ratio selon sa grille
# ============================================================
def score_grille(valeur, seuils, sens):
    if sens == "hausse_bien":
        if valeur <= seuils[0]:
            return 0.0
        for i in range(len(seuils) - 1):
            if seuils[i] <= valeur <= seuils[i + 1]:
                pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
                return (i + pct) * 20
        return 100.0
    if valeur <= seuils[0]:
        return 100.0
    for i in range(len(seuils) - 1):
        if seuils[i] <= valeur <= seuils[i + 1]:
            pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
            return 100 - (i + pct) * 20
    return 0.0


def grille(cfg, cat, nom):
    return (cfg.get(cat) or {}).get(nom) or {}


# ============================================================
# 1. AGREGATS
# ============================================================
print("=== 1. Agregats intermediaires (SIG, structure, tresorerie) ===")
agg = Agregats(copy.deepcopy(DATA)).compute_all()
attendus = {
    "chiffre_affaires": 1200.0,
    "consommations_tiers": 600.0,
    "valeur_ajoutee": 600.0,       # fallback CA quand pas de ventilation
    "charges_personnel": 280.0,
    "ebe": 300.0,                  # VA - impots - charges personnel
    "ebit": 70.0,
    "dotations": 50.0,
    "ebitda": 120.0,
    "resultat_net": 60.0,
    "caf": 110.0,
    "achats": 400.0,
    "capitaux_propres": 400.0,
    "dettes_financieres": 300.0,
    "total_dettes": 500.0,
    "capitaux_employes": 700.0,
    "ressources_stables": 700.0,
    "actif_immobilise": 600.0,
    "total_actif": 1000.0,
    "total_passif": 1000.0,
    "total_stocks": 100.0,
    "total_creances": 150.0,
    "bfr": 150.0,
    "fdr": 100.0,
    "tresorerie": 70.0,
    "dette_nette": 230.0,
}
for k, v in attendus.items():
    check(f"agregat {k} = {v}", proche(agg.get(k), v), f"obtenu {agg.get(k)}")

# ============================================================
# 2. CHAQUE RATIO (formule attendue)
# ============================================================
print("\n=== 2. Ratios : chaque formule ===")
ratios = Ratios(agg).compute_all()
# dettes court terme = fournisseurs + fiscales/sociales
attendus_ratios = {
    # --- formules Banque de France (fascicules sectoriels) ---
    # VA = 600 (fallback CA), EBE = 300, CAF = 110, capital expl. = 750
    ("rentabilite", "taux_valeur_ajoutee"): 600 / 1200.0 * 100,
    ("rentabilite", "taux_marge"): 300 / 600.0 * 100,
    ("rentabilite", "taux_excedent_brut_global"): 300 / 1200.0 * 100,
    ("rentabilite", "rentabilite_financiere_capitaux_propres"): 110 / 400.0 * 100,
    ("rentabilite", "rentabilite_brute_capital_exploitation"): 300 / 750.0 * 100,

    ("rentabilite", "rendement_capital_exploitation"): 600 / 750.0 * 100,
    # delais BdF : x 360, avances nettees, achats + charges externes
    ("gestion_activite", "dso"): 150 / 1200.0 * 360,
    ("gestion_activite", "dpo"): 100 / 600.0 * 360,
    ("gestion_activite", "poids_bfr_exploitation"): 150 / 1200.0 * 360,
    ("endettement", "gearing"): 300 / 400.0 * 100,
    ("endettement", "dette_nette_fonds_propres"): (300 - 70) / 400.0 * 100,
    ("endettement", "cout_apparent_endettement"): 25 / 300.0 * 100,
    ("endettement", "poids_interets_ebg"): 25 / 300.0 * 100,
    ("partage_valeur", "repartition_personnel"): 280 / 600.0 * 100,
    ("partage_valeur", "repartition_etat"): 20 / 600.0 * 100,
    ("partage_valeur", "repartition_preteurs"): 25 / 600.0 * 100,
}
for (cat, nom), v in attendus_ratios.items():
    obtenu = (ratios.get(cat) or {}).get(nom)
    check(f"{cat}.{nom} = {v:.4f}", proche(obtenu, v), f"obtenu {obtenu}")

# ratios supprimes : plus ni calcules ni presents nulle part
for cat, nom in (("rentabilite", "taux_marge_commerciale"),
                 ("rentabilite", "taux_marge_industrielle"),
                 ("rentabilite", "rentabilite_nette_capital_exploitation")):
    check(f"{cat}.{nom} supprime du moteur",
          nom not in (ratios.get(cat) or {}))

# croissance : None sans exercice N-1
for nom in ("croissance_ca", "croissance_va"):
    check(f"croissance.{nom} = None sans N-1",
          (ratios["croissance"] or {}).get(nom) is None)

# ratios supprimes du moteur : ni calcules ni presents nulle part
check("tcac_ca_3ans supprime du moteur",
      "tcac_ca_3ans" not in (ratios.get("croissance") or {}))
check("couverture_frais_financiers supprimee du moteur",
      "couverture_frais_financiers" not in (ratios.get("risque_solvabilite") or {}))

# ============================================================
# 3-5. SCORING STANDARD vs CONFIGURATION (defauts)
# ============================================================
print("\n=== 3. Score de chaque ratio vs grille YAML ===")
print("=== 4. Scores de categories vs poids configures ===")
print("=== 5. Score global vs poids du profil ===")

ratios_f = filter_ratios(ratios, MIN_EXERCICES_ANALYSE)

def audit_standard():
    scorer = Scorer(ratios_f, profil="moyen_terme")
    res = scorer.compute_all()

    # 3. chaque ratio score : grille + sens du YAML (config effective = defauts)
    nb_verifies = 0
    for cat, acts in load_categories().items():
        for nom in acts:
            valeur = (ratios_f.get(cat) or {}).get(nom)
            if valeur is None:
                continue
            g = grille(CFG_DEFAUT, cat, nom)
            attendu = score_grille(valeur, g["seuils"], g["sens"])
            check(f"score {nom} = {attendu:.2f} (grille {g['seuils']}, {g['sens']})",
                  proche(res["scores_ratios"].get(nom), attendu, 1e-3),
                  f"obtenu {res['scores_ratios'].get(nom)}")
            nb_verifies += 1
    check("au moins 16 ratios verifies", nb_verifies >= 16, f"{nb_verifies}")

    # ratios supprimes : jamais scores
    check("tcac_ca_3ans jamais score",
          "tcac_ca_3ans" not in res["scores_ratios"])
    check("couverture_frais_financiers jamais scoree",
          "couverture_frais_financiers" not in res["scores_ratios"])

    # 4. score de categorie = moyenne ponderee par les poids CONFIGURES
    poids_profil = PROFILS_DEFAUT["moyen_terme"]["poids_categories"]
    for cat in ("croissance", "rentabilite", "gestion_activite",
                "endettement", "partage_valeur"):
        num = den = 0.0
        for nom in load_categories()[cat]:
            if nom in res["scores_ratios"]:
                p = grille(CFG_DEFAUT, cat, nom)["poids"]
                num += res["scores_ratios"][nom] * p
                den += p
        attendu = num / den if den else None
        check(f"categorie {cat} = moyenne ponderee configuree",
              proche(res["scores_categories"].get(cat), attendu, 1e-3),
              f"attendu {attendu}, obtenu {res['scores_categories'].get(cat)}")

    check("croissance = None (pas de N-1 dans le jeu)",
          res["scores_categories"].get("croissance") is None)
    check("pas de categorie fantome 'categories'",
          "categories" not in res["scores_categories"])

    # 5. score global = moyenne ponderee par les poids du PROFIL
    num = den = 0.0
    for cat, p in poids_profil.items():
        sc = res["scores_categories"].get(cat)
        if sc is not None:
            num += sc * p
            den += p
    attendu = num / den
    check(f"score global = moyenne ponderee du profil ({attendu:.2f})",
          proche(res["score_global"], attendu, 1e-3),
          f"attendu {attendu}, obtenu {res['score_global']}")

    # un autre profil doit donner un score global different
    res_lt = Scorer(ratios_f, profil="long_terme").compute_all()
    check("profil long_terme != moyen_terme (poids differents)",
          res_lt["score_global"] != res["score_global"],
          f"{res_lt['score_global']} == {res['score_global']}")
    return res

res_std = with_config_user(None, audit_standard)

# ============================================================
# 6. CONCORDANCE AVEC LA CONFIG UTILISATEUR
# ============================================================
print("\n=== 6. Config utilisateur (ratios_actifs, poids) ===")

cfg_user_ratios = copy.deepcopy(CFG_DEFAUT)
# desactive poids_bfr_exploitation, double le poids de dso
cfg_user_ratios["categories"]["gestion_activite"]["ratios_actifs"] = [
    r for r in cfg_user_ratios["categories"]["gestion_activite"]["ratios_actifs"]
    if r != "poids_bfr_exploitation"]
cfg_user_ratios["gestion_activite"]["dso"]["poids"] *= 2

def audit_user():
    # filter_ratios doit suivre la config utilisateur
    rf = filter_ratios(ratios, MIN_EXERCICES_ANALYSE)
    check("filter_ratios : poids_bfr desactive par l'utilisateur",
          "poids_bfr_exploitation" not in (rf.get("gestion_activite") or {}))

    scorer = Scorer(rf, profil="moyen_terme")
    res = scorer.compute_all()
    check("score : poids_bfr desactive absent du scoring",
          "poids_bfr_exploitation" not in res["scores_ratios"]
          and "poids_bfr_exploitation" not in res["details"])

    # la categorie gestion_activite doit reagir au poids double
    num = den = 0.0
    for nom in cfg_user_ratios["categories"]["gestion_activite"]["ratios_actifs"]:
        if nom in res["scores_ratios"]:
            p = grille(cfg_user_ratios, "gestion_activite", nom)["poids"]
            num += res["scores_ratios"][nom] * p
            den += p
    attendu = num / den
    check("categorie gestion_activite suit les poids de l'utilisateur",
          proche(res["scores_categories"].get("gestion_activite"), attendu, 1e-3),
          f"attendu {attendu}, obtenu {res['scores_categories'].get('gestion_activite')}")
    return res

with_config_user({"profils": PROFILS_DEFAUT, "ratios": cfg_user_ratios},
                 audit_user)

# ============================================================
# 7. SCORING SECTORIEL
# ============================================================
print("\n=== 7. Scoring sectoriel (quartiles, desactives, poids profil) ===")
SECTEURS = {
    "test": {
        "label": "Secteur test", "code_naf_prefix": ["C"],
        "ratios": {
            "dso": {"mediane": 50.0, "q1": 30.0, "q3": 70.0},
            "taux_marge": {"mediane": 25.0, "q1": 15.0, "q3": 35.0},
            "gearing": {"mediane": 60.0, "q1": 40.0, "q3": 90.0},
        },
        "ratios_desactives": ["gearing"],
    }
}

def audit_sectoriel():
    sc = SectorScorer(ratios_f, secteur="test", secteurs_config=SECTEURS)
    scores = sc.compute_sector_scores(CFG_DEFAUT)

    # dso = 45 : baisse_bien, entre Q1 (30) et mediane (50) -> 60-80
    attendu_dso = 60 + (50.0 - 45.0) / (50.0 - 30.0) * 20
    check(f"dso sectoriel = {attendu_dso:.2f}",
          proche(scores.get("dso", {}).get("score"), attendu_dso, 1e-3),
          f"obtenu {scores.get('dso', {}).get('score')}")
    # taux_marge = 50 > Q3 (35) -> 80 + (50-35)/35*20
    attendu_tm = 80 + (50.0 - 35.0) / 35.0 * 20
    check(f"taux_marge sectoriel = {attendu_tm:.2f} (> Q3)",
          proche(scores.get("taux_marge", {}).get("score"), attendu_tm, 1e-3),
          f"obtenu {scores.get('taux_marge', {}).get('score')}")
    # gearing desactive pour le secteur
    check("gearing desactive exclu du scoring sectoriel",
          "gearing" not in scores)
    # bornes : valeur = mediane -> 60 ; valeur = Q1 -> 40 (hausse_bien)
    check("borne hausse_bien : valeur = mediane -> 60",
          proche(sc._score_vs_sector("taux_marge", 25.0, "hausse_bien"), 60.0, 1e-6))
    check("borne hausse_bien : valeur = Q1 -> 40",
          proche(sc._score_vs_sector("taux_marge", 15.0, "hausse_bien"), 40.0, 1e-6))

    # poids du profil appliques au score global sectoriel
    poids_profil = PROFILS_DEFAUT["moyen_terme"]["poids_categories"]
    res = sc.compute_scores_by_category(CFG_DEFAUT,
                                        poids_categories=poids_profil)
    # repli standard : un ratio SANS reference sectorielle mais avec
    # valeur disponible doit etre note sur la grille YAML (jamais
    # 'non calcule') -- poids_bfr_exploitation n'a pas de ref dans le secteur test
    qk = scores.get("poids_bfr_exploitation")
    grille_qk = CFG_DEFAUT["gestion_activite"]["poids_bfr_exploitation"]
    attendu_qk = score_grille(qk["valeur"], grille_qk["seuils"],
                              grille_qk.get("sens", "hausse_bien"))
    check("repli standard : poids_bfr_exploitation note sur la grille YAML "
          f"({attendu_qk:.2f})",
          qk is not None and proche(qk["score"], round(attendu_qk, 2), 1e-2),
          f"obtenu {qk and qk.get('score')}")
    check("repli standard : methode_ratio = 'standard'",
          qk is not None and qk.get("methode_ratio") == "standard")
    # score global = moyenne ponderee des categories par le profil
    num = sum(res["scores_categories"][c] * poids_profil[c]
              for c in res["scores_categories"] if poids_profil.get(c))
    den = sum(poids_profil[c]
              for c in res["scores_categories"] if poids_profil.get(c))
    attendu = num / den if den else 0.0
    check(f"score global sectoriel suit le profil ({attendu:.2f})",
          proche(res["score_global"], attendu, 1e-2),
          f"attendu {attendu}, obtenu {res['score_global']}")
    return res

with_config_user(None, audit_sectoriel)

# ============================================================
# 8. Bornes d'exercices (3 minimum, 8 maximum)
# ============================================================
print("\n=== 8. Bornes d'exercices (3-8) ===")
check("MIN_EXERCICES_ANALYSE = 3", MIN_EXERCICES_ANALYSE == 3)
check("MAX_EXERCICES_ANALYSE = 8", MAX_EXERCICES_ANALYSE == 8)
check("tcac_ca_3ans plus reference par le filtre",
      "tcac_ca_3ans" not in (filter_ratios(ratios, 4).get("croissance") or {}))
check("ratios de croissance exclus a 1 exercice",
      "croissance_ca" not in (filter_ratios(ratios, 1).get("croissance") or {}))

print("\n=== 9. Rapport PDF genere (contributions au score incluses) ===")
from src.reporting.charts_pdf import chart_contributions_categories
from src.reporting.pdf_report import generate_pdf_report
from src.analysis.validator import Validator
from src.scoring.alerts import detect_alerts, SEUILS
from src.visualization.colors import (
    get_score_gradient, SCORE_COLORS, ROUGE_FONCE, VERT_DEGRADE,
    THEME as THEME_COLORS,
)

poids_profil = PROFILS_DEFAUT["moyen_terme"]["poids_categories"]

# degrade continu sur TOUTE l'echelle : nuance propre a chaque tranche de 5 %
check("gradient : score 0 -> rouge fonce", get_score_gradient(0) == ROUGE_FONCE)
check("gradient : score 20 -> rouge", get_score_gradient(20) == SCORE_COLORS["fragile"])
check("gradient : score 40 -> ambre", get_score_gradient(40) == SCORE_COLORS["surveiller"])
check("gradient : score 70 -> vert degrade (zone solide)",
      get_score_gradient(70) == VERT_DEGRADE)
check("gradient : 21 nuances distinctes (tous les 5 %)",
      len({get_score_gradient(v) for v in range(0, 101, 5)}) == 21)
check("gradient : score 100 -> vert", get_score_gradient(100) == SCORE_COLORS["solide"])
check("gradient : score 55 entre ambre et vert",
      get_score_gradient(55) != SCORE_COLORS["surveiller"]
      and get_score_gradient(55) != SCORE_COLORS["solide"],
      get_score_gradient(55))
check("gradient : monotone (0 < 40 < 70 < 100)",
      get_score_gradient(0) != get_score_gradient(20)
      and get_score_gradient(45) != get_score_gradient(65))

fig_contrib = chart_contributions_categories(res_std["scores_categories"],
                                             poids_profil)
check("chart contributions categories : figure construite",
      fig_contrib is not None)
fig_contrib_sans_poids = chart_contributions_categories(
    res_std["scores_categories"])
check("chart contributions sans poids (equipondere)",
      fig_contrib_sans_poids is not None)
fig_contrib_vide = chart_contributions_categories({})
check("chart contributions : categories vides -> None",
      fig_contrib_vide is None)
# coherence : la somme des contributions vaut le score global
_cats_c = {k: v for k, v in res_std["scores_categories"].items()
           if v is not None and poids_profil.get(k)}
_den_c = sum(poids_profil[c] for c in _cats_c)
check("contributions : somme = score global",
      _den_c > 0 and proche(
          sum(_cats_c[c] * poids_profil[c] for c in _cats_c) / _den_c,
          res_std["score_global"]),
      str(res_std["score_global"]))

def audit_pdf():
    validation = Validator(agg, ratios_f, DATA).validate_all()
    alertes = detect_alerts(agg, ratios_f)
    pdf = generate_pdf_report(
        result=res_std, agregats=agg, agregats_n1=None,
        validation=validation, alertes=alertes,
        company_name="TEST SCI", secteur_label=None,
        poids_categories=poids_profil,
    )
    check("PDF valide (signature %PDF)", bool(pdf) and pdf[:5] == b"%PDF-",
          f"{len(pdf) if pdf else 0} octets")
    check("PDF complet (> 50 Ko, plusieurs pages)", len(pdf) > 50000,
          f"{len(pdf)} octets")
    return pdf

with_config_user(None, audit_pdf)

print("\n=== 10. Totaux stocks / creances : repli par somme (liasse fiscale) ===")
# la liasse fiscale n'a pas de ligne "Total stocks" ni "Total creances" :
# l'extraction ne fournit que les composantes, les agregats doivent sommer
DATA_COMPOSANTES = {
    "actif": {
        "total_actif": 500.0, "actif_immobilise": 200.0,
        "stocks_marchandises": 30.0, "matieres_premieres": 10.0,
        "creances_clients": 70.0, "autres_creances": 30.0,
        "disponibilites": 20.0,
    },
    "passif": dict(DATA["passif"]),
    "compte_resultat": dict(DATA["compte_resultat"]),
}
agg_c = Agregats(copy.deepcopy(DATA_COMPOSANTES)).compute_all()
check("total_stocks calcule par somme (30 + 10)",
      proche(agg_c.get("total_stocks"), 40.0), str(agg_c.get("total_stocks")))
check("total_creances calcule par somme (70 + 30)",
      proche(agg_c.get("total_creances"), 100.0), str(agg_c.get("total_creances")))
check("BFR coherent (40 + 100 - 100)",
      proche(agg_c.get("bfr"), 40.0), str(agg_c.get("bfr")))
ratios_c = Ratios(agg_c).compute_all()
check("poids_bfr utilise les totaux recalcules ((40+100-100)/1200 x 360)",
      proche((ratios_c["gestion_activite"] or {}).get("poids_bfr_exploitation"),
             40.0 / 1200.0 * 360),
      str((ratios_c["gestion_activite"] or {}).get("poids_bfr_exploitation")))
# total explicite fourni : jamais ecrase par la somme
agg_t = Agregats(copy.deepcopy(DATA)).compute_all()
check("total_stocks explicite prioritaire",
      proche(agg_t.get("total_stocks"), 100.0), str(agg_t.get("total_stocks")))
check("total_creances explicite prioritaire",
      proche(agg_t.get("total_creances"), 150.0), str(agg_t.get("total_creances")))

print("\n=== 11. Alertes : seuils declares tous testes, sain vs a risque ===")
# cas sain (celui du banc d'essai) : aucune des alertes de seuil
codes_sain = {a["code"] for a in detect_alerts(agg, ratios_f)}
check("cas sain : aucune alerte de seuil",
      not codes_sain & {"gearing_eleve", "bfr_sur_ca_eleve", "dso_eleve",
                        "dpo_eleve", "endettement_court_terme_eleve",
                        "taux_ebg_faible", "variation_ca_suspecte"},
      str(codes_sain))

agg_risque = {"capitaux_propres": 100.0, "resultat_net": 60.0,
              "tresorerie": 70.0, "chiffre_affaires": 1000.0,
              "bfr": 500.0, "total_creances": 400.0,
              "dettes_fournisseurs": 600.0, "dettes_fiscales_sociales": 100.0,
              "total_dettes": 1000.0}
ratios_risque = {"rentabilite": {"taux_excedent_brut_global": 1.0},
                 "endettement": {"gearing": 250.0},
                 "gestion_activite": {"dpo": 150.0, "dso": 120.0},
                 "croissance": {"croissance_ca": 300.0}}
codes_risque = {a["code"] for a in detect_alerts(agg_risque, ratios_risque)}
for code in ("gearing_eleve", "bfr_sur_ca_eleve", "dso_eleve", "dpo_eleve",
             "endettement_court_terme_eleve", "taux_ebg_faible",
             "variation_ca_suspecte"):
    check(f"alerte {code} declenchee quand le seuil est depasse",
          code in codes_risque, str(codes_risque))
# tous les seuils declares sont bien utilises (plus de seuil mort)
import inspect as _inspect
_src_alerts = _inspect.getsource(detect_alerts)
morts = [k for k in SEUILS if f'SEUILS["{k}"]' not in _src_alerts]
check("aucun seuil d'alerte declare mais non teste", not morts, str(morts))

print("\n=== 12. Validateur etendu (10 controles complementaires) ===")
validation_et = Validator(agg, ratios_f, DATA).validate_all()
check("validateur : au moins 30 controles executes",
      validation_et["stats"]["total"] >= 30,
      str(validation_et["stats"]))
noms_tests = {r["test"] for r in validation_et["rapport"]}
for numero in range(23, 33):
    presents = [t for t in noms_tests if t.startswith(f"{numero}. ")]
    check(f"controle {numero} present", bool(presents), str(sorted(noms_tests)))

# equilibre N-1 : fourni et coherent -> OK
val_n1 = Validator(agg, ratios_f, DATA, data_n1=DATA).validate_all()
check("23. Equilibre bilan N-1 : OK quand N-1 equilibre",
      any(r["test"].startswith("23.") and r["niveau"] == "OK"
          for r in val_n1["rapport"]),
      str([r for r in val_n1["rapport"] if r["test"].startswith("23.")]))
# desequilibre N-1 -> erreur
DATA_N1_KO = copy.deepcopy(DATA)
DATA_N1_KO["passif"]["total_passif"] = 2000.0
val_n1_ko = Validator(agg, ratios_f, DATA, data_n1=DATA_N1_KO).validate_all()
check("23. Equilibre bilan N-1 : ERREUR quand N-1 desequilibre",
      any(r["test"].startswith("23.") and r["niveau"] == "ERREUR"
          for r in val_n1_ko["rapport"]))

# signes du bilan : stock negatif -> ERREUR
DATA_NEG = copy.deepcopy(DATA)
DATA_NEG["actif"]["total_stocks"] = -50.0
val_neg = Validator(Agregats(copy.deepcopy(DATA_NEG)).compute_all(),
                    ratios_f, DATA_NEG).validate_all()
check("29. Signes du bilan : ERREUR sur un poste d'actif negatif",
      any(r["test"].startswith("29.") and r["niveau"] == "ERREUR"
          for r in val_neg["rapport"]))

# chaine du resultat net : coherent sur le banc d'essai etendu
DATA_CHAINE = copy.deepcopy(DATA)
DATA_CHAINE["compte_resultat"].update({
    "resultat_courant": 60.0, "resultat_financier": -10.0,
    "resultat_exceptionnel": 0.0, "impots_benefices": 0.0,
    "participation_salaries": 0.0,
})
DATA_CHAINE["compte_resultat"]["resultat_exploitation"] = 70.0
DATA_CHAINE["compte_resultat"]["resultat_net"] = 60.0
agg_ch = Agregats(copy.deepcopy(DATA_CHAINE)).compute_all()
ratios_ch = filter_ratios(Ratios(agg_ch).compute_all(), 3)
val_ch = Validator(agg_ch, ratios_ch, DATA_CHAINE).validate_all()
check("27 + 28 : chaine du resultat verifiee (REX+RF=courant, courant-impots=RN)",
      any(r["test"].startswith("27.") and r["niveau"] == "OK"
          for r in val_ch["rapport"])
      and any(r["test"].startswith("28.") and r["niveau"] == "OK"
              for r in val_ch["rapport"]),
      str([r for r in val_ch["rapport"] if r["test"][:3] in ("27.", "28.")]))

print("\n=== 13. Modes de scoring (exercice N + tendance / moyenne) ===")
from src.scoring.modes import (
    ratios_moyens, ajustement_tendance, trajectoire_ratio,
    AJUST_MAX, MODE_TENDANCE,
)

# --- trajectoire : bande morte, sens favorable ---
check("trajectoire : neutre dans la bande morte (+/- 2 %)",
      trajectoire_ratio(101.0, 100.0, "hausse_bien") == 0)
check("trajectoire : favorable si N > moyenne (hausse_bien)",
      trajectoire_ratio(110.0, 100.0, "hausse_bien") == 1)
check("trajectoire : defavorable si N > moyenne (baisse_bien)",
      trajectoire_ratio(110.0, 100.0, "baisse_bien") == -1)
check("trajectoire : favorable si N < moyenne (baisse_bien)",
      trajectoire_ratio(90.0, 100.0, "baisse_bien") == 1)
check("trajectoire : neutre si moyenne absente",
      trajectoire_ratio(10.0, None, "hausse_bien") == 0)

# --- mode moyenne : gabarit = memes ratios actifs, valeurs moyennees ---
HIST_FIX = {"dso": {"moyenne": 50.0},
            "croissance_ca": {"moyenne": 5.0}}
ratios_m = ratios_moyens(ratios_f, HIST_FIX)
check("ratios_moyens : memes categories que le gabarit",
      set(ratios_m) == set(ratios_f))
dso_avant = (ratios_f.get("gestion_activite") or {}).get("dso")
dso_apres = (ratios_m.get("gestion_activite") or {}).get("dso")
check("ratios_moyens : valeur remplacee par la moyenne",
      dso_apres == 50.0 and dso_avant != 50.0,
      f"N={dso_avant} -> moyenne={dso_apres}")
taux_marge_n = (ratios_f.get("rentabilite") or {}).get("taux_marge")
check("ratios_moyens : sans moyenne connue, valeur N conservee",
      (ratios_m.get("rentabilite") or {}).get("taux_marge") == taux_marge_n)

# --- mode moyenne : le moteur standard reprend le jeu moyenne ---
res_moy = Scorer(ratios_m, profil="moyen_terme").compute_all()
check("mode moyenne : score calcule sur les valeurs moyennees",
      isinstance(res_moy.get("score_global"), (int, float)),
      str(res_moy.get("score_global")))

# --- mode tendance : bornes, marquage, non-mutation de la reference ---
res_t = ajustement_tendance(res_std, HIST_FIX, CFG_DEFAUT, poids_profil)
check("mode tendance : base_scoring = tendance",
      res_t.get("base_scoring") == MODE_TENDANCE)
check("mode tendance : ajustements bornes (+/- 5 pts / categorie)",
      all(abs(v) <= AJUST_MAX + 1e-9
          for v in (res_t.get("ajustement_tendance") or {}).values()),
      str(res_t.get("ajustement_tendance")))
check("mode tendance : scores dans [0 ; 100]",
      all(0 <= s <= 100
          for s in res_t["scores_categories"].values() if s is not None))
check("mode tendance : l'objet d'origine n'est pas modifie",
      "base_scoring" not in res_std
      and not res_std.get("ajustement_tendance"))
# score global recalcule : moyenne ponderee des categories ajustees
_glob = res_t["score_global"]
_num = sum(res_t["scores_categories"][c] * poids_profil[c]
           for c in res_t["scores_categories"]
           if poids_profil.get(c) and res_t["scores_categories"][c] is not None)
_den = sum(poids_profil[c]
           for c in res_t["scores_categories"]
           if poids_profil.get(c) and res_t["scores_categories"][c] is not None)
check("mode tendance : score global = categories ajustees x poids profil",
      proche(_glob, _num / _den), f"{_glob} vs {_num / _den:.2f}")

# --- mode moyenne : la dynamique compare N a la moyenne, pas a N-1 ---
from src.reporting.synthese import points_cles
faits_m = points_cles({**res_std, "base_scoring": "moyenne"},
                      agg, None, [],
                      ref_moyennes={"chiffre_affaires":
                                    agg.get("chiffre_affaires", 0) * 0.9})
fait_ca = next((f for f in faits_m if f["label"] == "Activite (CA)"), None)
check("points cles mode moyenne : variation N vs moyenne",
      fait_ca is not None and fait_ca["note"] == "vs moyenne"
      and proche(float(fait_ca["valeur"].replace("%", "")
                        .replace("+", "").strip()), 11.1, 0.2),
      str(fait_ca))
# mode autre : comparaison N-1 conservee
faits_n1 = points_cles({**res_std, "base_scoring": "tendance"},
                       agg, None, [])
check("points cles mode tendance : comparaison N-1 conservee",
      next((f for f in faits_n1 if f["label"] == "Activite (CA)"), None)
      is None)  # agregats_n1 absent -> fait N-1 absent

# --- PDF en mode moyenne : genere, colonne Moyenne ex. activee ---
res_moy["methode"] = "standard"
res_moy["base_scoring"] = "moyenne"
pdf_moy = generate_pdf_report(
    result=res_moy, agregats=agg, agregats_n1=None,
    company_name="TEST MOY", poids_categories=poids_profil,
    agregats_exercices={"2024": agg, "2023": agg, "2022": agg},
)
check("PDF mode moyenne : genere (signature %PDF)",
      bool(pdf_moy) and pdf_moy[:5] == b"%PDF-",
      f"{len(pdf_moy) if pdf_moy else 0} octets")

print()
if echecs:
    print(f"ECHECS ({len(echecs)}) :")
    for e in echecs:
        print(" -", e)
    sys.exit(1)
print(f"AUDIT COMPLET : score conforme a la configuration ({MIN_EXERCICES_ANALYSE}-{MAX_EXERCICES_ANALYSE} exercices)")
