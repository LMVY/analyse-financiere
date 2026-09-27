"""Scoring base sur les referentiels sectoriels.

Compare chaque ratio a la distribution du secteur (Q1, mediane, Q3)
au lieu d'utiliser des seuils fixes.
"""
import yaml
from pathlib import Path
from typing import Optional


SECTOR_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "secteurs_config.yaml"


def load_secteurs(path=None):
    p = Path(path) if path else SECTOR_CONFIG_PATH
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def detect_secteur(code_naf: str, secteurs: dict = None) -> Optional[str]:
    """Detecte le secteur a partir du code NAF/APE.

    Args:
        code_naf: code NAF (ex: "C25.99Z", "6201Z", "F41.20A")
        secteurs: dict des secteurs (charge si None)

    Returns:
        code du secteur (ex: "industrie") ou None
    """
    if not code_naf:
        return None
    if secteurs is None:
        secteurs = load_secteurs()

    # Normaliser : enlever les points et chiffres, garder la lettre
    code = code_naf.strip().upper()
    if not code:
        return None

    # La 1re lettre est la section NAF
    first_letter = code[0]

    for cat, info in secteurs.items():
        prefixes = info.get("code_naf_prefix", [])
        if first_letter in prefixes:
            return cat

    return None


class SectorScorer:
    """Score les ratios en les comparant au secteur."""

    def __init__(self, ratios: dict, secteur: str = None, secteurs_config: dict = None):
        self.ratios = ratios
        self.secteur = secteur
        self.secteurs = secteurs_config or load_secteurs()
        self.scores_ratios = {}
        self.details = {}

    def _get_sector_ref(self, nom_ratio: str) -> Optional[dict]:
        """Recupere les references sectorielles pour un ratio."""
        if not self.secteur or self.secteur not in self.secteurs:
            return None
        ratios_secteur = self.secteurs[self.secteur].get("ratios", {})
        return ratios_secteur.get(nom_ratio)

    def _score_vs_sector(self, nom_ratio: str, valeur: float, sens: str) -> Optional[float]:
        """Note un ratio par rapport au secteur.

        Utilise Q1, mediane, Q3 comme bornes.
        - Q1  = 25e percentile (mauvais)
        - Q2  = mediane
        - Q3  = 75e percentile (bon)
        """
        ref = self._get_sector_ref(nom_ratio)
        if not ref:
            return None

        q1 = ref.get("q1", 0)
        med = ref.get("mediane", 0)
        q3 = ref.get("q3", 0)

        if sens == "hausse_bien":
            # Plus la valeur est haute, mieux c'est
            if valeur <= q1:
                # 0 a 40
                if q1 > 0:
                    return max(0, (valeur / q1) * 40)
                return 0
            elif valeur <= med:
                # 40 a 60
                return 40 + ((valeur - q1) / (med - q1)) * 20 if med > q1 else 40
            elif valeur <= q3:
                # 60 a 80
                return 60 + ((valeur - med) / (q3 - med)) * 20 if q3 > med else 60
            else:
                # 80 a 100
                return min(100, 80 + ((valeur - q3) / max(abs(q3), 1)) * 20)
        else:
            # baisse_bien : plus c'est bas, mieux c'est
            if valeur <= q1:
                # 80 a 100
                return min(100, 80 + ((q1 - valeur) / max(abs(q1), 1)) * 20) if q1 else 100
            elif valeur <= med:
                # 60 a 80
                return 60 + ((med - valeur) / (med - q1)) * 20 if med > q1 else 60
            elif valeur <= q3:
                # 40 a 60
                return 40 + ((q3 - valeur) / (q3 - med)) * 20 if q3 > med else 40
            else:
                # 0 a 40
                return max(0, 40 - ((valeur - q3) / max(abs(q3), 1)) * 40)

    def compute_sector_scores(self, ratios_config: dict) -> dict:
        """Calcule les scores sectoriels pour chaque ratio.

        Args:
            ratios_config: config YAML des ratios (poids, sens, source)

        Returns:
            dict : {nom_ratio: {"score": float, "valeur": float, "ref_secteur": dict}}
        """
        resultats = {}

        for cat, ratio_dict in self.ratios.items():
            if cat not in ratios_config:
                continue
            for nom, valeur in ratio_dict.items():
                if valeur is None:
                    continue
                cfg = ratios_config[cat].get(nom)
                if not cfg:
                    continue

                sens = cfg.get("sens", "hausse_bien")
                score = self._score_vs_sector(nom, valeur, sens)

                if score is not None:
                    resultats[nom] = {
                        "score": round(score, 2),
                        "valeur": valeur,
                        "sens": sens,
                        "poids": cfg.get("poids", 0),
                        "source": cfg.get("source", ""),
                        "cible": cfg.get("cible", ""),
                        "categorie": cat,
                        "ref_secteur": self._get_sector_ref(nom),
                        "methode": "sectorielle",
                    }

        self.details = resultats
        return resultats


if __name__ == "__main__":
    from src.scoring.score import load_config

    # Test : detecter le secteur depuis le code NAF
    print("=== DETECTION SECTEUR ===")
    for naf in ["C25.99Z", "F41.20A", "6201Z", "I55.10Z", "M70.22Z"]:
        secteur = detect_secteur(naf)
        label = load_secteurs().get(secteur, {}).get("label", "?") if secteur else "INCONNU"
        print(f"  {naf:12s} -> {secteur} ({label})")

    print()
    print("=== REFERENCES SECTORIELLES ===")
    secteurs = load_secteurs()
    for cat, info in secteurs.items():
        print(f"\n--- {info['label']} ---")
        for nom, ref in list(info["ratios"].items())[:3]:
            print(f"  {nom:25s} : Q1={ref['q1']}, Med={ref['mediane']}, Q3={ref['q3']}")
