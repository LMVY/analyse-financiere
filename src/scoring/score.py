"""Moteur de scoring parametrable."""
from typing import Optional


PROFILS = {
    "tres_court_terme": {
        "label": "Tres court terme (< 1 an)",
        "poids": {"liquidite": 0.40, "endettement": 0.20, "rentabilite": 0.10,
                  "structure_financiere": 0.10, "croissance": 0.05,
                  "gestion_activite": 0.05, "tresorerie": 0.05, "risque_solvabilite": 0.05},
    },
    "court_terme": {
        "label": "Court terme (1-3 ans)",
        "poids": {"liquidite": 0.30, "endettement": 0.25, "rentabilite": 0.15,
                  "structure_financiere": 0.10, "croissance": 0.05,
                  "gestion_activite": 0.05, "tresorerie": 0.05, "risque_solvabilite": 0.05},
    },
    "moyen_terme": {
        "label": "Moyen terme (3-7 ans)",
        "poids": {"liquidite": 0.15, "endettement": 0.25, "rentabilite": 0.20,
                  "structure_financiere": 0.15, "croissance": 0.10,
                  "gestion_activite": 0.05, "tresorerie": 0.05, "risque_solvabilite": 0.05},
    },
    "long_terme": {
        "label": "Long terme (> 7 ans)",
        "poids": {"liquidite": 0.05, "endettement": 0.20, "rentabilite": 0.25,
                  "structure_financiere": 0.20, "croissance": 0.15,
                  "gestion_activite": 0.05, "tresorerie": 0.05, "risque_solvabilite": 0.05},
    },
}


GRILLES = {
    "current_ratio":        {"seuils": [0.5, 1.0, 1.5, 2.0, 3.0], "sens": "hausse_bien"},
    "quick_ratio":          {"seuils": [0.3, 0.6, 1.0, 1.5, 2.0], "sens": "hausse_bien"},
    "cash_ratio":           {"seuils": [0.05, 0.1, 0.2, 0.5, 1.0], "sens": "hausse_bien"},
    "liquidite_immediate":  {"seuils": [0.1, 0.3, 0.5, 1.0, 2.0], "sens": "hausse_bien"},
    "liquidite_generale":   {"seuils": [0.5, 1.0, 1.5, 2.0, 3.0], "sens": "hausse_bien"},
    "gearing":              {"seuils": [30, 50, 100, 150, 200], "sens": "baisse_bien"},
    "levier_financier":     {"seuils": [50, 100, 150, 200, 300], "sens": "baisse_bien"},
    "dette_nette_ebitda":   {"seuils": [0, 1, 2, 3.5, 5], "sens": "baisse_bien"},
    "dette_nette_fonds_propres": {"seuils": [0, 20, 50, 100, 150], "sens": "baisse_bien"},
    "interest_coverage":    {"seuils": [0.5, 1, 2, 4, 8], "sens": "hausse_bien"},
    "capacite_desendettement": {"seuils": [0.5, 1, 2, 3, 5], "sens": "baisse_bien"},
    "marge_brute":          {"seuils": [5, 15, 25, 40, 60], "sens": "hausse_bien"},
    "marge_ebitda":         {"seuils": [2, 5, 10, 15, 25], "sens": "hausse_bien"},
    "marge_operationnelle": {"seuils": [0, 2, 5, 10, 15], "sens": "hausse_bien"},
    "marge_nette":          {"seuils": [0, 1, 3, 5, 10], "sens": "hausse_bien"},
    "roe":                  {"seuils": [0, 3, 8, 15, 25], "sens": "hausse_bien"},
    "roa":                  {"seuils": [0, 1, 3, 5, 10], "sens": "hausse_bien"},
    "roce":                 {"seuils": [0, 3, 7, 12, 20], "sens": "hausse_bien"},
    "rentabilite_economique": {"seuils": [0, 3, 5, 10, 15], "sens": "hausse_bien"},
    "roic":                 {"seuils": [0, 3, 7, 12, 20], "sens": "hausse_bien"},
    "autonomie_financiere": {"seuils": [10, 20, 30, 50, 70], "sens": "hausse_bien"},
    "poids_des_dettes":     {"seuils": [30, 50, 70, 85, 95], "sens": "baisse_bien"},
    "equilibre_financier":  {"seuils": [0.5, 0.8, 1.0, 1.5, 2.0], "sens": "hausse_bien"},
    "rotation_stocks":      {"seuils": [1, 2, 4, 8, 15], "sens": "hausse_bien"},
    "dsi":                  {"seuils": [15, 30, 60, 90, 120], "sens": "baisse_bien"},
    "dso":                  {"seuils": [15, 30, 45, 60, 90], "sens": "baisse_bien"},
    "dpo":                  {"seuils": [15, 30, 45, 60, 90], "sens": "hausse_bien"},
    "rotation_actif":       {"seuils": [0.3, 0.5, 1.0, 1.5, 2.5], "sens": "hausse_bien"},
    "rotation_capitaux_employes": {"seuils": [0.3, 0.5, 1.0, 1.5, 2.5], "sens": "hausse_bien"},
    "tresorerie_ca":        {"seuils": [1, 3, 5, 10, 20], "sens": "hausse_bien"},
    "tresorerie_dettes_ct": {"seuils": [0.05, 0.1, 0.2, 0.5, 1.0], "sens": "hausse_bien"},
    "couverture_caf_dette": {"seuils": [5, 10, 20, 40, 80], "sens": "hausse_bien"},
    "ratio_solvabilite":    {"seuils": [10, 25, 50, 100, 200], "sens": "hausse_bien"},
    "ratio_couverture_dettes": {"seuils": [1.0, 1.2, 1.5, 2.0, 3.0], "sens": "hausse_bien"},
    "ratio_liquidite_large": {"seuils": [0.5, 1.0, 1.5, 2.5, 4.0], "sens": "hausse_bien"},
    "score_conan_holder":   {"seuils": [-10, -3, 0, 5, 10], "sens": "hausse_bien"},
    "croissance_ca":        {"seuils": [-20, -10, 0, 5, 15], "sens": "hausse_bien"},
    "croissance_ebitda":    {"seuils": [-30, -15, 0, 10, 25], "sens": "hausse_bien"},
    "croissance_resultat_net": {"seuils": [-50, -20, 0, 10, 30], "sens": "hausse_bien"},
}


class Scorer:
    """Moteur de scoring parametrable."""

    def __init__(self, ratios: dict, profil: str = "moyen_terme", poids_custom: dict = None):
        self.ratios = ratios
        self.profil = profil
        self.poids = poids_custom if poids_custom else PROFILS[profil]["poids"]
        self.scores_ratios = {}
        self.scores_categories = {}

    def _score_ratio(self, nom, valeur):
        if valeur is None:
            return None
        grille = GRILLES.get(nom)
        if not grille:
            return None
        seuils = grille["seuils"]
        sens = grille["sens"]

        if sens == "hausse_bien":
            if valeur <= seuils[0]:
                return 0.0
            for i in range(len(seuils) - 1):
                if seuils[i] <= valeur <= seuils[i + 1]:
                    pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
                    return (i + pct) * 20
            return 100.0
        else:
            if valeur <= seuils[0]:
                return 100.0
            for i in range(len(seuils) - 1):
                if seuils[i] <= valeur <= seuils[i + 1]:
                    pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
                    return 100 - (i + pct) * 20
            return 0.0

    def compute_all(self):
        for cat, ratios in self.ratios.items():
            for nom, valeur in ratios.items():
                score = self._score_ratio(nom, valeur)
                if score is not None:
                    self.scores_ratios[nom] = score

        for cat, ratios in self.ratios.items():
            scores_cat = [self.scores_ratios[n] for n in ratios.keys() if n in self.scores_ratios]
            self.scores_categories[cat] = sum(scores_cat) / len(scores_cat) if scores_cat else None

        score_global = 0.0
        total_poids = 0.0
        for cat, poids in self.poids.items():
            if cat in self.scores_categories and self.scores_categories[cat] is not None:
                score_global += self.scores_categories[cat] * poids
                total_poids += poids

        if total_poids > 0:
            score_global = score_global / total_poids

        return {
            "score_global": round(score_global, 2),
            "profil": self.profil,
            "scores_categories": {c: round(s, 2) if s is not None else None for c, s in self.scores_categories.items()},
            "scores_ratios": {n: round(s, 2) for n, s in self.scores_ratios.items()},
        }

    def get_recommandation(self, score):
        if score >= 75:
            return "Risque faible - Acceptation recommandee"
        elif score >= 60:
            return "Risque modere - Acceptation avec garanties"
        elif score >= 45:
            return "Risque eleve - Analyse approfondie requise"
        elif score >= 30:
            return "Risque tres eleve - Acceptation deconseillee"
        else:
            return "Risque critique - Refus"
