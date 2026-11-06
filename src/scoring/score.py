"""Moteur de scoring parametrable.

Lit la configuration depuis config/ratios_config.yaml.
"""

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

# Repli uniquement si profils.yaml est illisible. Les poids copient
# config/profils.yaml (source de verite) : meme chose pour la concordance.
PROFILS = {
    "tres_court_terme": {
        "label": "Tres court terme",
        "poids": {
            "gestion_activite": 0.45,
            "endettement": 0.25,
            "rentabilite": 0.15,
            "partage_valeur": 0.15,
            "croissance": 0.0,
        },
    },
    "court_terme": {
        "label": "Court terme",
        "poids": {
            "endettement": 0.35,
            "gestion_activite": 0.25,
            "rentabilite": 0.2,
            "partage_valeur": 0.1,
            "croissance": 0.1,
        },
    },
    "moyen_terme": {
        "label": "Moyen terme",
        "poids": {
            "rentabilite": 0.3,
            "endettement": 0.3,
            "partage_valeur": 0.15,
            "croissance": 0.15,
            "gestion_activite": 0.1,
        },
    },
    "long_terme": {
        "label": "Long terme",
        "poids": {
            "rentabilite": 0.35,
            "croissance": 0.25,
            "endettement": 0.2,
            "partage_valeur": 0.1,
            "gestion_activite": 0.1,
        },
    },
}

def score_grille(valeur, seuils, sens="hausse_bien"):
    """Note une valeur (0-100) sur la grille standard de la config YAML.

    Partagee par le Scorer standard et, en REPLI, par le SectorScorer
    quand le secteur n'a pas de reference pour un ratio : une valeur
    disponible ne doit jamais rester sans score.
    """
    if valeur is None or not seuils:
        return None
    if sens == "hausse_bien":
        if valeur <= seuils[0]:
            return 0.0
        for i in range(len(seuils) - 1):
            if seuils[i] <= valeur <= seuils[i + 1]:
                pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
                return (i + pct) * 20
        return 100.0
    if valeur <= seuils[0]:
        return 100.0
    for i in range(len(seuils) - 1):
        if seuils[i] <= valeur <= seuils[i + 1]:
            pct = (valeur - seuils[i]) / (seuils[i + 1] - seuils[i])
            return 100 - (i + pct) * 20
    return 0.0


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
            if cat in ("categories", "agregats"):
                continue          # cles de structure
            if nom in ratios:
                grille = ratios[nom]
                break

        if not grille:
            return None
        return score_grille(valeur, grille["seuils"], grille["sens"])

    def _actifs(self, cat: str):
        """Ratios actifs de la categorie (config effective), None si absent."""
        cats = self.config.get("categories") or {}
        actifs = (cats.get(cat) or {}).get("ratios_actifs")
        return set(actifs) if isinstance(actifs, list) else None

    def compute_all(self):
        # 1. Score de chaque ratio ACTIF (config effective) avec son poids
        for cat, ratios in self.ratios.items():
            if cat not in self.config:
                continue
            actifs = self._actifs(cat)
            for nom, valeur in ratios.items():
                if nom not in self.config[cat]:
                    continue
                if actifs is not None and nom not in actifs:
                    continue      # ratio desactive dans la configuration
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

        # 2. Score par categorie (moyenne ponderee par les poids configures)
        for cat, ratios in self.config.items():
            if cat in ("categories", "agregats"):
                continue          # cles de structure, pas des categories
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
