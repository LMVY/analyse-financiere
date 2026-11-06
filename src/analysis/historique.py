"""Calcul des ratios sur historique multi-exercices.

Pour chaque ratio :
- Valeur N (dernier exercice)
- Moyenne sur la période
- Tendance (hausse/baisse/stable)
"""

# Classification des ratios
RATIOS_STOCK = {
    # Stock = photo au dernier jour (les fleches de tendance ne
    # s'affichent pas pour ces ratios) ; la moyenne couvre tout de
    # meme tous les exercices, comme pour les ratios de flux.
    "gearing", "dette_nette_fonds_propres", "cout_apparent_endettement",
}

RATIOS_FLUX = {
    # Flux = moyenne + tendance
    "croissance_ca", "croissance_va", "taux_valeur_ajoutee",
    "taux_marge",
    "taux_excedent_brut_global", "rentabilite_financiere_capitaux_propres",
    "rentabilite_brute_capital_exploitation",
    "rendement_capital_exploitation", "dso", "dpo",
    "poids_interets_ebg", "repartition_personnel", "repartition_etat",
    "repartition_preteurs",
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
        else:
            type_ratio = "flux"

        # MEME REGLE POUR TOUS LES RATIOS (stock et flux) : la
        # moyenne affichee est la moyenne arithmetique des valeurs
        # du ratio sur tous les exercices fournis (les exercices ou
        # le ratio n'est pas calculable sont ecartes du denominateur).
        vals_valides = [v for v in valeurs if v is not None]
        moyenne = (sum(vals_valides) / len(vals_valides)
                   if vals_valides else None)

        # Tendance : flux uniquement (un stock se lit en niveau)
        tend = tendance_ratio(valeurs) if type_ratio == "flux" else "→"

        result[nom] = {
            "N": val_n,
            "moyenne": moyenne,
            "tendance": tend,
            "type": type_ratio,
            "valeurs": valeurs,
        }

    return result


# ============================================================
# Exercices : fusion et decoupage (utilise par le dashboard)
# ============================================================
def calculer_croissance(v_n, v_n1):
    """Taux de croissance (%) de v_n1 -> v_n ; None si impossible."""
    if v_n1 and v_n1 != 0 and v_n is not None:
        return (v_n - v_n1) / abs(v_n1) * 100
    return None


def scinder_exercices(data: dict, sections=("actif", "passif", "compte_resultat")) -> tuple:
    """Data standard Document AI (poste + poste_n1) -> (N, N-1)."""
    n, n1 = {}, {}
    for sec in sections:
        n[sec] = {k: v for k, v in data.get(sec, {}).items() if not k.endswith("_n1")}
        n1[sec] = {k[:-3]: v for k, v in data.get(sec, {}).items() if k.endswith("_n1")}
    return n, n1


def fusionner_exercice(par_annee: dict, cle, data: dict,
                       sections=("actif", "passif", "compte_resultat")):
    """Ajoute un exercice ; complete les postes manquants s'il existe deja."""
    if cle not in par_annee:
        par_annee[cle] = data
        return True
    for sec in sections:
        for k, v in data.get(sec, {}).items():
            par_annee[cle].setdefault(sec, {})
            par_annee[cle][sec].setdefault(k, v)
    return False
