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
    "marge_nette_faible": 2,       # %
    "endettement_court_terme_eleve": 70,  # % des dettes
    "liquidite_generale_faible": 1.0,
    "variation_ca_suspecte": 200,  # % de variation
}


def detect_alerts(agregats: dict, ratios: dict) -> List[Dict]:
    """Detecte les alertes a partir des agregats et ratios.

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

    # --- Marge nette faible ---
    marge = _get_ratio(ratios, "rentabilite", "marge_nette")
    if marge is not None and 0 < marge < SEUILS["marge_nette_faible"]:
        alertes.append({
            "niveau": "info",
            "code": "marge_nette_faible",
            "message": f"Marge nette faible ({marge:.1f}%) - rentabilite limitee",
            "valeur": marge,
        })

    return alertes


def _get_ratio(ratios: dict, categorie: str, nom: str):
    """Recupere un ratio de maniere securisee."""
    cat = ratios.get(categorie, {})
    if isinstance(cat, dict):
        return cat.get(nom)
    return None


def format_alerts(alertes: List[Dict]) -> str:
    """Formate les alertes en texte."""
    if not alertes:
        return "Aucune alerte detectee"
    lines = []
    for a in alertes:
        lines.append(f"[{a['niveau'].upper()}] {a['message']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test rapide
    test_agregats = {"capitaux_propres": -50000, "resultat_net": -10000, "tresorerie": -5000}
    test_ratios = {"endettement": {"gearing": 250}, "gestion": {"dso": 120}}
    alerts = detect_alerts(test_agregats, test_ratios)
    print(format_alerts(alerts))
