"""Filtre les ratios selon les categories ACTIVES du YAML + le nombre d'exercices.

Source de verite : config/ratios_config.yaml -> categories.ratios_actifs
"""
import yaml
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "ratios_config.yaml"


# Ratios qui necessitent au moins 2 exercices
RATIOS_2_EXERCICES = {
    "croissance_ca", "croissance_resultat_net",
    "croissance_ebitda", "croissance_capitaux_propres",
}

# Ratios qui necessitent au moins 4 exercices
RATIOS_4_EXERCICES = {"tcac_ca_3ans"}


def load_categories():
    """Charge la liste des ratios actifs par categorie depuis le YAML."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cats = cfg.get("categories", {})
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
            if r in RATIOS_4_EXERCICES and nb_exercices < 4:
                continue
            actifs.append(r)
        result[cat] = actifs
    return result


def get_ratios_desactives(nb_exercices: int) -> dict:
    """Retourne les ratios desactives et la raison."""
    desactives = {}
    if nb_exercices < 2:
        desactives["croissance"] = {
            "ratios": list(RATIOS_2_EXERCICES),
            "raison": "Necessite 2 exercices (N et N-1)",
        }
    if nb_exercices < 4:
        if "croissance" not in desactives:
            desactives["croissance"] = {"ratios": [], "raison": ""}
        desactives["croissance"]["ratios"].append("tcac_ca_3ans")
        desactives["croissance"]["raison"] = "tcac_ca_3ans necessite 4 exercices"
    return desactives


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


if __name__ == "__main__":
    print("=== Ratios actifs par nb exercices ===\n")
    for nb in [1, 2, 3, 4, 5]:
        actifs = get_ratios_actifs(nb)
        total = sum(len(v) for v in actifs.values())
        print(f"  {nb} exercice(s) : {total} ratios")
    print()
    print("=== Detail a 4 exercices ===")
    actifs = get_ratios_actifs(4)
    for cat, liste in actifs.items():
        print(f"  {cat:25s} : {len(liste)} ratios")
