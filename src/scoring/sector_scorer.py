"""Scoring base sur les referentiels sectoriels.

Compare chaque ratio a la distribution du secteur (Q1, mediane, Q3)
au lieu d'utiliser des seuils fixes.
"""
import re
import yaml
from pathlib import Path
from typing import Optional

SECTOR_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "secteurs_config.yaml"

# NAF rev. 2 : division (2 premiers chiffres du code APE) -> section (lettre)
DIVISIONS_NAF = {
    "01": "A", "02": "A", "03": "A",
    "05": "B", "06": "B", "07": "B", "08": "B", "09": "B",
    "10": "C", "11": "C", "12": "C", "13": "C", "14": "C", "15": "C",
    "16": "C", "17": "C", "18": "C", "19": "C", "20": "C", "21": "C",
    "22": "C", "23": "C", "24": "C", "25": "C", "26": "C", "27": "C",
    "28": "C", "29": "C", "30": "C", "31": "C", "32": "C", "33": "C",
    "35": "D",
    "36": "E", "37": "E", "38": "E", "39": "E",
    "41": "F", "42": "F", "43": "F",
    "45": "G", "46": "G", "47": "G",
    "49": "H", "50": "H", "51": "H", "52": "H", "53": "H",
    "55": "I", "56": "I",
    "58": "J", "59": "J", "60": "J", "61": "J", "62": "J", "63": "J",
    "64": "K", "65": "K", "66": "K",
    "68": "L",
    "69": "M", "70": "M", "71": "M", "72": "M", "73": "M", "74": "M", "75": "M",
    "77": "N", "78": "N", "79": "N", "80": "N", "81": "N", "82": "N",
    "84": "O",
    "85": "P",
    "86": "Q", "87": "Q", "88": "Q",
    "90": "R", "91": "R", "92": "R", "93": "R",
    "94": "S", "95": "S", "96": "S",
    "97": "T",
    "98": "U",
}


def section_naf(code_naf: str) -> Optional[str]:
    """Retourne la lettre de section NAF (A-U) depuis un code NAF/APE.

    Accepte les deux formats :
    - avec section : "F41.20A", "C25.99Z"
    - APE seul     : "41.20A", "25.99Z", "6201Z"
    """
    if not code_naf:
        return None
    code = code_naf.strip().upper()
    if not code:
        return None
    if code[0].isalpha():
        return code[0]
    m = re.match(r"(\d{2})", code)
    return DIVISIONS_NAF.get(m.group(1)) if m else None


def load_secteurs(path=None):
    p = Path(path) if path else SECTOR_CONFIG_PATH
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def detect_secteur(code_naf: str, secteurs: dict = None) -> Optional[str]:
    """Detecte le secteur a partir du code NAF/APE.

    Args:
        code_naf: code NAF (ex: "C25.99Z", "41.20A", "6201Z")
        secteurs: dict des secteurs (charge si None)

    Returns:
        code du secteur (ex: "industrie") ou None
    """
    if not code_naf:
        return None
    if secteurs is None:
        secteurs = load_secteurs()

    # Section NAF (lettre) depuis le code, quel que soit le format
    section = section_naf(code_naf)
    if section is None:
        return None

    for cat, info in secteurs.items():
        prefixes = info.get("code_naf_prefix", []) or []
        if section in prefixes:
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

    def _get_ratio_ref(self, nom_ratio: str) -> Optional[dict]:
        """Recupere les references sectorielles pour un ratio."""
        if not self.secteur or self.secteur not in self.secteurs:
            return None
        ratios_secteur = self.secteurs[self.secteur].get("ratios", {})
        return ratios_secteur.get(nom_ratio)

    def _est_desactive(self, nom_ratio: str) -> bool:
        """Un ratio desactive n'est pas pertinent pour ce secteur."""
        if not self.secteur or self.secteur not in self.secteurs:
            return False
        desactives = self.secteurs[self.secteur].get("ratios_desactives") or []
        return nom_ratio in desactives

    def _score_vs_sector(self, nom_ratio: str, valeur: float, sens: str) -> Optional[float]:
        """Note un ratio par rapport au secteur.

        Utilise Q1, mediane, Q3 comme bornes.
        - Q1  = 25e percentile (mauvais)
        - Q2  = mediane
        - Q3  = 75e percentile (bon)
        """
        ref = self._get_ratio_ref(nom_ratio)
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
                if q1 < 0:
                    # Q1 negatif (ex croissance) : mappe [2*Q1, Q1] -> [0, 40]
                    return max(0, min(40, (valeur - 2 * q1) / (-q1) * 40))
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
                if self._est_desactive(nom):
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
                        "ref_secteur": self._get_ratio_ref(nom),
                        "methode": "sectorielle",
                    }

        self.details = resultats
        return resultats

    def compute_scores_by_category(self, ratios_config: dict) -> dict:
        """Retourne les scores par categorie (comme Scorer.compute_all)."""
        sector_scores = self.compute_sector_scores(ratios_config)

        # Agreger par categorie (moyenne ponderee)
        par_cat = {}
        for nom, info in sector_scores.items():
            cat = info["categorie"]
            par_cat.setdefault(cat, {"total": 0.0, "poids": 0.0})
            par_cat[cat]["total"] += info["score"] * info["poids"]
            par_cat[cat]["poids"] += info["poids"]

        scores_categories = {}
        for cat, agg in par_cat.items():
            scores_categories[cat] = round(agg["total"] / agg["poids"], 2) if agg["poids"] > 0 else None

        # Score global (moyenne ponderee des categories)
        total_score = 0.0
        total_poids = 0.0
        for cat, sc in scores_categories.items():
            if sc is None:
                continue
            # Poids de la categorie = somme des poids de ses ratios
            poids_cat = par_cat[cat]["poids"]
            total_score += sc * poids_cat
            total_poids += poids_cat

        score_global = total_score / total_poids if total_poids > 0 else 0.0

        # Details par ratio (format Scorer)
        details = {}
        for nom, info in sector_scores.items():
            details[nom] = {
                "score": info["score"],
                "valeur": info["valeur"],
                "poids": info["poids"],
                "source": info["source"],
                "cible": info["cible"],
                "categorie": info["categorie"],
                "methode": "sectorielle",
            }

        return {
            "score_global": round(score_global, 2),
            "profil": f"sectoriel_{self.secteur}",
            "methode": "sectorielle",
            "scores_categories": scores_categories,
            "scores_ratios": {n: info["score"] for n, info in sector_scores.items()},
            "details": details,
        }

if __name__ == "__main__":

    # Test : detecter le secteur depuis le code NAF
    print("=== DETECTION SECTEUR ===")
    for naf in ["C25.99Z", "41.20A", "6201Z", "46.75B", "55.10Z", "68.20A", "M70.22Z"]:
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
