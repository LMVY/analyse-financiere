"""Calcul des ratios sur historique multi-exercices.

Pour chaque ratio :
- Valeur N (dernier exercice)
- Moyenne sur la période
- Tendance (hausse/baisse/stable)
"""

# Classification des ratios
RATIOS_STOCK = {
    # Stock = on garde N seulement
    "gearing", "levier_financier", "dette_nette_fonds_propres",
    "autonomie_financiere", "equilibre_financier", "current_ratio", "quick_ratio",
    "cash_ratio", "liquidite_immediate",
    "dette_nette_ebitda", "ratio_solvabilite", "ratio_couverture_dettes",
    "ratio_liquidite_large", "capacite_desendettement",
}

RATIOS_FLUX = {
    # Flux = moyenne + tendance
    "marge_brute", "marge_ebitda", "marge_nette", "marge_operationnelle",
    "roe", "roa", "roce", "dpo", "dsi", "rotation_stocks", "rotation_actif", "rotation_immobilisations", "cycle_conversion_tresorerie",
    "tresorerie_ca", "couverture_caf_dette",
}

def tendance_ratio(valeurs: list) -> str:
    """Retourne '↗', '↘' ou '→' selon l'evolution."""
    vals = [v for v in valeurs if v is not None]
    if len(vals) < 2:
        return "→"
    if vals[0] > vals[-1] * 1.05:
        return "↗"
    if vals[0] < vals[-1] * 0.95:
        return "↘"
    return "→"

def calculer_historique(ratios_par_annee: dict) -> dict:
    """Calcule N / Moyenne / Tendance pour chaque ratio.

    Args:
        ratios_par_annee: {
            "2024": {"liquidite": {"current_ratio": 1.5, ...}, ...},
            "2023": {...},
            "2022": {...},
        }

    Returns:
        {
            "current_ratio": {
                "N": 1.5,
                "moyenne": 1.4,
                "tendance": "↗",
                "type": "stock",  # ou "flux"
                "valeurs": [1.5, 1.4, 1.3],
            },
            ...
        }
    """
    if not ratios_par_annee:
        return {}

    # Trier annees decroissantes
    annees = sorted(ratios_par_annee.keys(), reverse=True)

    # Rassembler tous les ratios vus
    tous_ratios = {}
    for annee in annees:
        for cat, ratio_dict in ratios_par_annee[annee].items():
            for nom, val in ratio_dict.items():
                tous_ratios.setdefault(nom, {})
                tous_ratios[nom][annee] = val

    result = {}
    for nom, valeurs_par_annee in tous_ratios.items():
        # Liste ordonnee N, N-1, ...
        valeurs = [valeurs_par_annee.get(a) for a in annees]
        val_n = valeurs[0]

        # Determiner le type
        if nom in RATIOS_STOCK:
            type_ratio = "stock"
            moyenne = val_n  # pas de moyenne pour un stock
        else:
            type_ratio = "flux"
            vals_valides = [v for v in valeurs if v is not None]
            moyenne = sum(vals_valides) / len(vals_valides) if vals_valides else None

        # Tendance
        tend = tendance_ratio(valeurs) if type_ratio == "flux" else "→"

        result[nom] = {
            "N": val_n,
            "moyenne": moyenne,
            "tendance": tend,
            "type": type_ratio,
            "valeurs": valeurs,
        }

    return result

if __name__ == "__main__":
    # Test rapide
    test = {
        "2024": {"rentabilite": {"marge_nette": 3.2, "roe": 8.5},
                 "endettement": {"gearing": 145}},
        "2023": {"rentabilite": {"marge_nette": 4.1, "roe": 10.2},
                 "endettement": {"gearing": 138}},
        "2022": {"rentabilite": {"marge_nette": 3.8, "roe": 9.1},
                 "endettement": {"gearing": 150}},
    }

    res = calculer_historique(test)

    print(f"{'Ratio':20s} {'N':>8s} {'Moyenne':>10s} {'Tend.':>6s} {'Type':>8s}")
    print("-" * 60)
    for nom, info in sorted(res.items()):
        n = f"{info['N']:.2f}" if info['N'] is not None else "N/A"
        m = f"{info['moyenne']:.2f}" if info['moyenne'] is not None else "N/A"
        print(f"{nom:20s} {n:>8s} {m:>10s} {info['tendance']:>6s} {info['type']:>8s}")
