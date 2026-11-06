"""Filtre les ratios selon les categories ACTIVES du YAML + le nombre d'exercices.

Source de verite : la configuration EFFECTIVE (config/ratios_config.yaml,
surchagee par data/config_user.yaml s'il existe) -> categories.ratios_actifs.
"""
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "ratios_config.yaml"

# Bornes d'exercices pour lancer une analyse (porte du dashboard)
MIN_EXERCICES_ANALYSE = 3
MAX_EXERCICES_ANALYSE = 8

# Ratios qui necessitent au moins 2 exercices (taux de variation)
RATIOS_2_EXERCICES = {"croissance_ca", "croissance_va"}


def load_categories():
    """Charge les ratios actifs par categorie depuis la config effective
    (config utilisateur prioritaire sur les defauts)."""
    from src.scoring.config_loader import load_effective_config
    _, ratios = load_effective_config()
    cats = ratios.get("categories", {})
    return {cat: info.get("ratios_actifs", []) for cat, info in cats.items()}


def get_ratios_actifs(nb_exercices: int) -> dict:
    """Retourne les ratios actifs selon le nombre d'exercices."""
    cats = load_categories()
    result = {}
    for cat, ratios in cats.items():
        actifs = []
        for r in ratios:
            if r in RATIOS_2_EXERCICES and nb_exercices < 2:
                continue
            actifs.append(r)
        result[cat] = actifs
    return result


def filter_ratios(ratios: dict, nb_exercices: int) -> dict:
    """Filtre un dict de ratios pour ne garder que ceux actifs du YAML."""
    actifs = get_ratios_actifs(nb_exercices)
    result = {}

    for cat, ratio_dict in ratios.items():
        if cat not in actifs:
            continue
        result[cat] = {}
        for nom, val in ratio_dict.items():
            if nom in actifs[cat]:
                result[cat][nom] = val

    return result
