"""Moteur de scoring parametrable.

Lit la configuration depuis config/ratios_config.yaml.
"""
import yaml
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "ratios_config.yaml"


def load_config(path=None):
    """Charge la config effective (user > defauts)."""
    from src.scoring.config_loader import load_effective_config
    _, ratios = load_effective_config()
    return ratios


def load_profils():
    """Charge les profils effectifs (user > defauts)."""
    from src.scoring.config_loader import load_effective_config
    profils, _ = load_effective_config()
    return profils


PROFILS = {
    "tres_court_terme": {
        "label": "Tres court terme (< 1 an)",
        "poids": {"liquidite": 0.40, "endettement": 0.20, "rentabilite": 0.10, "croissance": 0.05,
                  "gestion_activite": 0.05, "risque_solvabilite": 0.05},
    },
    "court_terme": {
        "label": "Court terme (1-3 ans)",
        "poids": {"liquidite": 0.30, "endettement": 0.25, "rentabilite": 0.15, "croissance": 0.05,
                  "gestion_activite": 0.05, "risque_solvabilite": 0.05},
    },
    "moyen_terme": {
        "label": "Moyen terme (3-7 ans)",
        "poids": {"liquidite": 0.15, "endettement": 0.25, "rentabilite": 0.20, "croissance": 0.10,
                  "gestion_activite": 0.05, "risque_solvabilite": 0.05},
    },
    "long_terme": {
        "label": "Long terme (> 7 ans)",
        "poids": {"liquidite": 0.05, "endettement": 0.20, "rentabilite": 0.25, "croissance": 0.15,
                  "gestion_activite": 0.05, "risque_solvabilite": 0.05},
    },
}


class Scorer:
    """Moteur de scoring parametrable (lit le YAML)."""

    def __init__(self, ratios: dict, profil: str = "moyen_terme", poids_custom: dict = None, config_path=None):
        self.ratios = ratios
        self.profil = profil
        self.config = load_config(config_path)
        # Charger les profils dynamiquement (user > defauts)
        profils = load_profils()
        if profil in profils and "poids_categories" in profils[profil]:
            poids_defaut = profils[profil]["poids_categories"]
        elif profil in PROFILS:
            poids_defaut = PROFILS[profil]["poids"]
        else:
            poids_defaut = {}
        self.poids = poids_custom if poids_custom else poids_defaut
        self.scores_ratios = {}
        self.scores_categories = {}
        self.details = {}

    def _score_ratio(self, nom, valeur):
        """Note un ratio selon sa config YAML."""
        if valeur is None:
            return None

        # Chercher la config du ratio dans toutes les categories
        grille = None
        for cat, ratios in self.config.items():
            if cat in ("agregats",):
                continue
            if nom in ratios:
                grille = ratios[nom]
                break

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
        # 1. Score de chaque ratio (avec poids)
        for cat, ratios in self.ratios.items():
            if cat not in self.config:
                continue
            for nom, valeur in ratios.items():
                if nom not in self.config[cat]:
                    continue
                score = self._score_ratio(nom, valeur)
                if score is not None:
                    poids_ratio = self.config[cat][nom].get("poids", 0)
                    self.scores_ratios[nom] = score
                    self.details[nom] = {
                        "score": round(score, 2),
                        "valeur": valeur,
                        "poids": poids_ratio,
                        "source": self.config[cat][nom].get("source", ""),
                        "cible": self.config[cat][nom].get("cible", ""),
                        "categorie": cat,
                    }

        # 2. Score par categorie (moyenne ponderee par les poids des ratios)
        for cat, ratios in self.config.items():
            if cat == "agregats":
                continue
            total_score = 0.0
            total_poids = 0.0
            for nom in ratios.keys():
                if nom in self.scores_ratios:
                    total_score += self.scores_ratios[nom] * ratios[nom]["poids"]
                    total_poids += ratios[nom]["poids"]
            if total_poids > 0:
                self.scores_categories[cat] = total_score / total_poids
            else:
                self.scores_categories[cat] = None

        # 3. Score global (moyenne ponderee par les poids des categories)
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
            "details": self.details,
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
