"""Detection automatique d'alertes financieres."""
from typing import List, Dict


# Seuils d'alerte
SEUILS = {
    "capitaux_propres_negatifs": 0,
    "gearing_eleve": 200,          # %
    "bfr_sur_ca_eleve": 30,        # %
    "dso_eleve": 90,               # jours
    "dpo_eleve": 120,              # jours
    "tresorerie_negative": 0,
    "resultat_net_negatif": 0,
    "taux_ebg_faible": 3,          # % du CA
    "endettement_court_terme_eleve": 70,  # % des dettes
    "variation_ca_suspecte": 200,  # % de variation
    "variation_cp_suspecte": -30,  # % de baisse des capitaux propres
}


def detect_alerts(agregats: dict, ratios: dict,
                  agregats_n1: dict = None) -> List[Dict]:
    """Detecte les alertes a partir des agregats et ratios.

    agregats_n1 (optionnel) active les alertes de variation N/N-1.

    Returns:
        Liste de dicts {niveau, code, message, valeur}
    """
    alertes = []

    # --- Capitaux propres negatifs ---
    cp = agregats.get("capitaux_propres", 0)
    if cp is not None and cp < SEUILS["capitaux_propres_negatifs"]:
        alertes.append({
            "niveau": "critique",
            "code": "capitaux_propres_negatifs",
            "message": f"Capitaux propres negatifs ({cp:,.0f} EUR) - situation nette negative",
            "valeur": cp,
        })

    # --- Forte baisse des capitaux propres (N vs N-1) ---
    # Une baisse superieure au seuil signale une distribution
    # exceptionnelle de dividendes, une perte ou une restructuration :
    # information determinante pour l'analyste credit.
    if agregats_n1:
        cp_n1 = agregats_n1.get("capitaux_propres")
        if (cp is not None and cp_n1 is not None and cp_n1 > 0):
            var_cp = (cp - cp_n1) / abs(cp_n1) * 100
            if var_cp <= SEUILS["variation_cp_suspecte"]:
                alertes.append({
                    "niveau": "warning",
                    "code": "variation_cp_suspecte",
                    "message": (f"Capitaux propres en forte baisse "
                                f"({var_cp:.0f} % vs N-1) : distribution "
                                f"exceptionnelle, perte ou restructuration ?"),
                    "valeur": round(var_cp, 1),
                })

    # --- Resultat net negatif ---
    rn = agregats.get("resultat_net", 0)
    if rn is not None and rn < SEUILS["resultat_net_negatif"]:
        alertes.append({
            "niveau": "warning",
            "code": "resultat_net_negatif",
            "message": f"Resultat net negatif ({rn:,.0f} EUR) - perte sur l'exercice",
            "valeur": rn,
        })

    # --- Tresorerie negative ---
    treso = agregats.get("tresorerie", 0)
    if treso is not None and treso < SEUILS["tresorerie_negative"]:
        alertes.append({
            "niveau": "critique",
            "code": "tresorerie_negative",
            "message": f"Tresorerie negative ({treso:,.0f} EUR)",
            "valeur": treso,
        })

    # --- Taux d'excedent brut global faible (marge operationnelle) ---
    ebg = _get_ratio(ratios, "rentabilite", "taux_excedent_brut_global")
    if ebg is not None and 0 < ebg < SEUILS["taux_ebg_faible"]:
        alertes.append({
            "niveau": "info",
            "code": "taux_ebg_faible",
            "message": f"Marge d'excedent brut faible ({ebg:.1f} % du CA) - "
                       "rentabilite operationnelle limitee",
            "valeur": ebg,
        })

    # --- Gearing eleve (dette financiere / capitaux propres) ---
    gearing = _get_ratio(ratios, "endettement", "gearing")
    if gearing is not None and gearing >= SEUILS["gearing_eleve"]:
        alertes.append({
            "niveau": "warning",
            "code": "gearing_eleve",
            "message": f"Niveau d'endettement financier eleve ({gearing:.0f} %) - dette financiere "
                       f"superieure a {SEUILS['gearing_eleve'] // 100} fois "
                       "les capitaux propres",
            "valeur": gearing,
        })

    # --- BFR / CA eleve ---
    ca = agregats.get("chiffre_affaires")
    bfr = agregats.get("bfr")
    if ca and bfr is not None and bfr / ca * 100 >= SEUILS["bfr_sur_ca_eleve"]:
        alertes.append({
            "niveau": "warning",
            "code": "bfr_sur_ca_eleve",
            "message": f"BFR eleve ({bfr / ca * 100:.0f} % du chiffre "
                       "d'affaires) - cycle d'exploitation tres consommateur "
                       "de tresorerie",
            "valeur": bfr / ca * 100,
        })

    # --- Creances clients elevees (DSO BdF, en jours de CA) ---
    dso = _get_ratio(ratios, "gestion_activite", "dso")
    if dso is not None and dso >= SEUILS["dso_eleve"]:
        alertes.append({
            "niveau": "warning",
            "code": "dso_eleve",
            "message": f"Delai de paiement des clients eleve ({dso:.0f} jours de chiffre "
                       "d'affaires) - recouvrement a surveiller",
            "valeur": dso,
        })

    # --- Delai de paiement fournisseurs eleve ---
    dpo = _get_ratio(ratios, "gestion_activite", "dpo")
    if dpo is not None and dpo >= SEUILS["dpo_eleve"]:
        alertes.append({
            "niveau": "warning",
            "code": "dpo_eleve",
            "message": f"Delai de paiement des fournisseurs eleve "
                       f"({dpo:.0f} jours) - dependance aux fournisseurs "
                       "ou tensions de tresorerie",
            "valeur": dpo,
        })

    # --- Endettement court terme eleve ---
    dettes_ct = ((agregats.get("dettes_fournisseurs") or 0)
                 + (agregats.get("dettes_fiscales_sociales") or 0))
    total_dettes = agregats.get("total_dettes")
    if total_dettes and dettes_ct / total_dettes * 100 >= SEUILS["endettement_court_terme_eleve"]:
        alertes.append({
            "niveau": "warning",
            "code": "endettement_court_terme_eleve",
            "message": f"Dettes court terme elevees "
                       f"({dettes_ct / total_dettes * 100:.0f} % du total "
                       "des dettes) - echeances proches a couvrir",
            "valeur": dettes_ct / total_dettes * 100,
        })

    # --- Variation de CA suspecte ---
    var_ca = _get_ratio(ratios, "croissance", "croissance_ca")
    if var_ca is not None and abs(var_ca) >= SEUILS["variation_ca_suspecte"]:
        alertes.append({
            "niveau": "info",
            "code": "variation_ca_suspecte",
            "message": f"Variation de chiffre d'affaires atypique "
                       f"({var_ca:+.0f} %) - verifier le perimetre et la "
                       "continuite d'activite avant interpretation",
            "valeur": var_ca,
        })

    return alertes


def _get_ratio(ratios: dict, categorie: str, nom: str):
    """Recupere un ratio de maniere securisee."""
    cat = ratios.get(categorie, {})
    if isinstance(cat, dict):
        return cat.get(nom)
    return None
