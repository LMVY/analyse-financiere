"""Modes de scoring : base du score et ajustement de tendance.

Deux modes, choisis dans le dashboard (Options -> Base du score) :
- MODE_TENDANCE : le score reste fonde sur l'exercice N, AJUSTE par
  la trajectoire des ratios (N compare a la moyenne des exercices,
  au sens favorable de chaque ratio) ;
- MODE_MOYENNE : le score est calcule sur la moyenne arithmetique de
  chaque ratio sur tous les exercices fournis (meme regle que la
  colonne "Moyenne" du dashboard et du PDF).

Regles communes (concordance avec le moteur existant) :
- le meme moteur (Scorer standard ou SectorScorer) et la meme
  configuration effective : seul le jeu de valeurs change, jamais
  l'ensemble des ratios actifs ni les poids ;
- la trajectoire d'un ratio compare N a la moyenne des exercices,
  avec une bande morte de +/- BANDE_MORTE (trajectoire neutre) ;
- l'ajustement de tendance est borne : au plus +/- AJUST_MAX points
  par categorie, les scores ajustes restent dans [0 ; 100] ;
- le score global ajuste reutilise les poids de categories du profil
  d'analyse (meme pondereage que le scoring standard).
"""
import copy

AJUST_MAX = 5.0     # points max d'ajustement par categorie
BANDE_MORTE = 0.02  # +/- 2 % autour de la moyenne : trajectoire neutre

MODE_TENDANCE = "tendance"     # exercice N + ajustement trajectoire
MODE_MOYENNE = "moyenne"      # moyenne des exercices

LABELS_MODES = {
    MODE_TENDANCE: "Derniere annee + tendance",
    MODE_MOYENNE: "Moyenne des exercices",
}


def sens_ratio(nom, categorie, ratios_config):
    """Sens favorable d'un ratio depuis la configuration effective."""
    cfg = (ratios_config or {}).get(categorie) or {}
    return (cfg.get(nom) or {}).get("sens", "hausse_bien")


def trajectoire_ratio(v_n, v_moy, sens) -> int:
    """Trajectoire d'un ratio : +1 favorable, -1 defavorable, 0 neutre.

    Compare la valeur de l'exercice N a la moyenne des exercices, au
    sens favorable du ratio (hausse_bien / baisse_bien). Une variation
    inferieure a la bande morte est neutre : pas d'ajustement sur du
    bruit.
    """
    if v_n is None or v_moy is None or v_moy == 0:
        return 0
    ecart = (v_n - v_moy) / abs(v_moy)
    if abs(ecart) <= BANDE_MORTE:
        return 0
    favorable = ecart > 0 if sens == "hausse_bien" else ecart < 0
    return 1 if favorable else -1


def ratios_moyens(ratios_n: dict, historique: dict) -> dict:
    """Jeu de ratios pour le mode MOYENNE.

    ratios_n sert de gabarit (memes categories, memes ratios actifs -
    concordance avec la configuration effective) ; chaque valeur est
    remplacee par la moyenne du ratio sur tous les exercices fournis
    (calculer_historique). Un ratio sans moyenne (jamais calculable
    sur les autres exercices) garde sa valeur de N.
    """
    result = {}
    for cat, ratio_dict in (ratios_n or {}).items():
        result[cat] = {}
        for nom, val in (ratio_dict or {}).items():
            moy = (historique or {}).get(nom) or {}
            result[cat][nom] = moy.get("moyenne", val)
    return result


def ajustement_tendance(result: dict, historique: dict,
                        ratios_config: dict,
                        poids_categories: dict = None) -> dict:
    """Mode TENDANCE : ajuste le score N par la trajectoire.

    Pour chaque categorie : indice de trajectoire = moyenne ponderee
    (poids des ratios) des trajectoires +1 / -1 / 0 de ses ratios
    notes ; la categorie gagne ou perd indice x AJUST_MAX points
    (borne [0 ; 100]). Le score global est recalcule avec les poids
    de categories du profil d'analyse.

    Ne modifie pas l'objet recu : retourne une copie ajustee, marquee
    base_scoring = MODE_TENDANCE, avec :
    - result["ajustement_tendance"] : {categorie: points gagnes/perdus} ;
    - result["details"][nom]["trajectoire"] : +1 / -1 / 0 par ratio.
    """
    res = copy.deepcopy(result or {})
    historique = historique or {}
    details = res.get("details") or {}

    # 1. indice de trajectoire par categorie (pondere par les poids)
    indices = {}
    for nom, det in details.items():
        if det.get("score") is None:
            continue
        cat = det.get("categorie")
        h = historique.get(nom) or {}
        sens = sens_ratio(nom, cat, ratios_config)
        t = trajectoire_ratio(det.get("valeur"), h.get("moyenne"), sens)
        det["trajectoire"] = t
        if t:
            tot, poids = indices.get(cat, (0.0, 0.0))
            indices[cat] = (tot + t * (det.get("poids") or 0.0),
                            poids + (det.get("poids") or 0.0))

    # 2. ajustement borne par categorie
    ajust = {}
    for cat, sc in (res.get("scores_categories") or {}).items():
        if sc is None:
            continue
        tot, poids = indices.get(cat, (0.0, 0.0))
        indice = tot / poids if poids > 0 else 0.0
        delta = round(indice * AJUST_MAX, 2)
        if delta:
            res["scores_categories"][cat] = round(
                max(0.0, min(100.0, sc + delta)), 2)
            ajust[cat] = delta

    # 3. score global : memes poids de categories que le moteur
    poids_cats = poids_categories or {}
    total, poids_tot = 0.0, 0.0
    for cat, sc in (res.get("scores_categories") or {}).items():
        if sc is None:
            continue
        poids = poids_cats.get(cat)
        if not poids:
            continue
        total += sc * poids
        poids_tot += poids
    if poids_tot <= 0:
        # repli : equipondere les categories notees
        notes = [sc for sc in (res.get("scores_categories") or {}).values()
                 if sc is not None]
        total, poids_tot = sum(notes), float(len(notes))
    if poids_tot > 0:
        res["score_global"] = round(total / poids_tot, 2)

    res["base_scoring"] = MODE_TENDANCE
    res["ajustement_tendance"] = ajust
    return res
