"""Filtre les ratios/agregats selon le nombre d'exercices disponibles.

Regles :
- 1 exercice  : 40 ratios (tous sauf croissance, burn_rate, runway, tcac)
- 2 exercices : 46 ratios (+ croissance, burn_rate, runway)
- 3 exercices : 46 ratios
- 4+ exercices: 47 ratios (+ tcac_ca_3ans)
"""

RATIOS_1_EXERCICE = {
    "liquidite": [
        "current_ratio", "quick_ratio", "cash_ratio",
        "liquidite_immediate", "liquidite_generale",
    ],
    "endettement": [
        "dette_nette_ebitda", "gearing", "interest_coverage",
        "capacite_desendettement", "levier_financier",
        "dette_nette_fonds_propres",
    ],
    "rentabilite": [
        "roe", "roce", "marge_ebitda", "marge_nette", "roa",
        "marge_operationnelle", "roic", "marge_brute",
        "rentabilite_economique",
    ],
    "structure_financiere": [
        "autonomie_financiere", "equilibre_financier",
        "poids_des_dettes", "couverture_emplois_stables",
    ],
    "gestion_activite": [
        "dso", "dpo", "dsi", "rotation_actif",
        "rotation_stocks", "bfr_jours_ca",
        "rotation_capitaux_employes", "rotation_immobilisations",
        "cycle_conversion_tresorerie",
    ],
    "tresorerie": [
        "tresorerie_ca", "couverture_caf_dette", "tresorerie_dettes_ct",
    ],
    "risque_solvabilite": [
        "score_conan_holder", "ratio_solvabilite",
        "ratio_couverture_dettes", "ratio_liquidite_large",
    ],
}

RATIOS_2_EXERCICES = {
    "croissance": [
        "croissance_ca", "croissance_resultat_net",
        "croissance_ebitda", "croissance_capitaux_propres",
    ],
}

RATIOS_2_EXERCICES_TRESORERIE = ["burn_rate", "runway"]

RATIOS_4_EXERCICES = {
    "croissance": ["tcac_ca_3ans"],
}


def get_ratios_actifs(nb_exercices: int) -> dict:
    """Retourne les ratios actifs selon le nombre d'exercices disponibles.

    Args:
        nb_exercices: nombre d'exercices (1, 2, 3, 4+)

    Returns:
        dict : {categorie: [liste des ratios actifs]}
    """
    # Copier la base (1 exercice)
    actifs = {}
    for cat, liste in RATIOS_1_EXERCICE.items():
        actifs[cat] = list(liste)

    # Ajouter les ratios necessitant 2 exercices
    if nb_exercices >= 2:
        for cat, liste in RATIOS_2_EXERCICES.items():
            if cat in actifs:
                actifs[cat].extend(liste)
            else:
                actifs[cat] = list(liste)

        # Ajouter burn_rate et runway a tresorerie
        actifs["tresorerie"].extend(RATIOS_2_EXERCICES_TRESORERIE)

    # Ajouter les ratios necessitant 4 exercices
    if nb_exercices >= 4:
        for cat, liste in RATIOS_4_EXERCICES.items():
            if cat in actifs:
                actifs[cat].extend(liste)

    return actifs


def get_ratios_desactives(nb_exercices: int) -> dict:
    """Retourne les ratios desactives et la raison."""
    desactives = {}

    if nb_exercices < 2:
        desactives["croissance"] = {
            "ratios": ["croissance_ca", "croissance_resultat_net",
                       "croissance_ebitda", "croissance_capitaux_propres"],
            "raison": "Necessite 2 exercices (N et N-1)",
        }
        desactives["tresorerie_burn"] = {
            "ratios": ["burn_rate", "runway"],
            "raison": "Necessite 2 exercices",
        }

    if nb_exercices < 4:
        if "croissance" not in desactives:
            desactives["croissance"] = {"ratios": [], "raison": ""}
        desactives["croissance"]["ratios"].append("tcac_ca_3ans")
        desactives["croissance"]["raison"] = "tcac_ca_3ans necessite 4 exercices"

    return desactives


def filter_ratios(ratios: dict, nb_exercices: int) -> dict:
    """Filtre un dict de ratios pour ne garder que ceux actifs.

    Args:
        ratios: dict retourne par Ratios.compute_all()
        nb_exercices: nombre d'exercices disponibles

    Returns:
        dict : ratios filtres
    """
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
    print("=" * 60)
    print("TEST FILTRE RATIOS")
    print("=" * 60)
    print()

    for nb in [1, 2, 3, 4, 5]:
        actifs = get_ratios_actifs(nb)
        total = sum(len(v) for v in actifs.values())
        print(f"  {nb} exercice(s) : {total} ratios actifs")

    print()
    print("=== DETAILS ===")
    for nb in [1, 2, 4]:
        actifs = get_ratios_actifs(nb)
        print(f"\n--- {nb} exercice(s) ---")
        for cat, liste in actifs.items():
            print(f"  {cat:25s} : {len(liste)} ratios")
