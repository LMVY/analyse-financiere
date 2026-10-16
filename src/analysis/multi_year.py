"""Module multi-exercices : gere 2 a 5 bilans + comptes de resultat.

Deux modes :
- Mode 1 : plusieurs PDFs separes (1 par exercice)
- Mode 2 : 1 PDF avec plusieurs colonnes d'exercices

Detecte automatiquement les exercices et calcule les ratios de croissance.
"""
from pathlib import Path
from typing import Optional
import re

from src.extraction.etats_financiers import BilanParser


class MultiYearData:
    """Gere les donnees de plusieurs exercices."""

    def __init__(self):
        # {annee: {"actif": {...}, "passif": {...}, "compte_resultat": {...}}}
        self.exercices = {}
        self.annees_triees = []

    def add_exercice(self, annee: str, data: dict):
        """Ajoute un exercice."""
        self.exercices[annee] = data
        self._trier()

    def _trier(self):
        """Trie les annees (N, N-1, N-2, ...)."""
        # Extraire les annees numeriques
        annees = []
        for annee in self.exercices.keys():
            match = re.search(r"\d{4}", annee)
            if match:
                annees.append((int(match.group()), annee))
            else:
                annees.append((0, annee))
        annees.sort(key=lambda x: x[0], reverse=True)
        self.annees_triees = [a[1] for a in annees]

    def get(self, annee: str) -> Optional[dict]:
        return self.exercices.get(annee)

    def latest(self) -> Optional[dict]:
        """Retourne l'exercice le plus recent."""
        if not self.annees_triees:
            return None
        return self.exercices[self.annees_triees[0]]

    def previous(self, annee: str = None) -> Optional[dict]:
        """Retourne l'exercice precedent."""
        if annee is None:
            annee = self.annees_triees[0] if self.annees_triees else None
        if annee not in self.annees_triees:
            return None
        idx = self.annees_triees.index(annee)
        if idx + 1 < len(self.annees_triees):
            return self.exercices[self.annees_triees[idx + 1]]
        return None

    def count(self) -> int:
        return len(self.exercices)

    def summary(self) -> dict:
        return {
            "nb_exercices": len(self.exercices),
            "annees": self.annees_triees,
        }


class MultiYearLoader:
    """Charge plusieurs PDFs et les associe aux exercices."""

    def __init__(self, referentiel_path: str = None):
        self.referentiel_path = referentiel_path

    def load_multiple_pdfs(self, pdf_paths: list, force_ocr: bool = False) -> MultiYearData:
        """Charge une liste de PDFs separes.
        
        L'annee est detectee automatiquement dans chaque PDF.
        """
        multi = MultiYearData()

        for pdf_path in pdf_paths:
            print(f"\n{'=' * 60}")
            print(f"Chargement : {pdf_path}")
            print(f"{'=' * 60}")

            parser = BilanParser(pdf_path)
            data = parser.parse_simple(force_ocr=force_ocr)

            # Detecter l'annee
            annee = self._detect_year_from_pdf(pdf_path, data)
            if annee is None:
                annee = f"exercice_{len(multi.exercices) + 1}"

            print(f"  Annee detectee : {annee}")
            print(f"  Postes : actif={len(data['actif'])}, passif={len(data['passif'])}, cr={len(data['compte_resultat'])}")

            multi.add_exercice(annee, data)

        return multi

    def _detect_year_from_pdf(self, pdf_path: str, data: dict) -> Optional[str]:
        """Detecte l'annee dans le PDF ou le nom du fichier."""
        # 1. Chercher dans le nom du fichier
        filename = Path(pdf_path).stem
        match = re.search(r"(20\d{2})", filename)
        if match:
            return match.group(1)

        # 2. Chercher dans le nom (format YY)
        match = re.search(r"_(\d{2})\.", filename)
        if match:
            return f"20{match.group(1)}"

        return None


class GrowthCalculator:
    """Calcule les ratios de croissance entre exercices."""

    def __init__(self, multi: MultiYearData):
        self.multi = multi

    def _get_value(self, data: dict, code: str) -> Optional[float]:
        """Recupere une valeur dans les 3 sections."""
        for section in ["actif", "passif", "compte_resultat"]:
            if code in data.get(section, {}):
                return data[section][code]
        return None

    def compute_growth(self, code: str) -> dict:
        """Calcule la croissance d'un poste sur tous les exercices disponibles.
        
        Returns:
            {"N_vs_N-1": 0.05, "N_vs_N-2": 0.10, "tcac": 0.05}
        """
        annees = self.multi.annees_triees
        if len(annees) < 2:
            return {}

        # Recuperer les valeurs
        valeurs = []
        for annee in annees:
            data = self.multi.exercices[annee]
            val = self._get_value(data, code)
            valeurs.append((annee, val))

        result = {}

        # Croissance N vs N-1
        if len(valeurs) >= 2 and valeurs[0][1] and valeurs[1][1]:
            if valeurs[1][1] != 0:
                result["N_vs_N-1"] = (valeurs[0][1] - valeurs[1][1]) / valeurs[1][1]

        # Croissance N vs N-2
        if len(valeurs) >= 3 and valeurs[0][1] and valeurs[2][1]:
            if valeurs[2][1] != 0:
                result["N_vs_N-2"] = (valeurs[0][1] - valeurs[2][1]) / valeurs[2][1]

        # Croissance N vs N-3
        if len(valeurs) >= 4 and valeurs[0][1] and valeurs[3][1]:
            if valeurs[3][1] != 0:
                result["N_vs_N-3"] = (valeurs[0][1] - valeurs[3][1]) / valeurs[3][1]

        # Croissance N vs N-4
        if len(valeurs) >= 5 and valeurs[0][1] and valeurs[4][1]:
            if valeurs[4][1] != 0:
                result["N_vs_N-4"] = (valeurs[0][1] - valeurs[4][1]) / valeurs[4][1]

        # TCAC (Taux de Croissance Annuel Moyen)
        nb_annees = len(valeurs) - 1
        if nb_annees >= 1 and valeurs[0][1] and valeurs[-1][1]:
            if valeurs[-1][1] > 0 and valeurs[0][1] > 0:
                tcac = (valeurs[0][1] / valeurs[-1][1]) ** (1 / nb_annees) - 1
                result["tcac"] = tcac

        return result

    def compute_all_growth(self) -> dict:
        """Calcule la croissance pour les postes cles."""
        postes = [
            "chiffre_affaires",
            "ebitda",
            "resultat_net",
            "total_actif",
            "total_passif",
            "capitaux_propres",
            "dettes_financieres",
            "tresorerie",
        ]

        result = {}
        for code in postes:
            growth = self.compute_growth(code)
            if growth:
                result[code] = growth

        return result


if __name__ == "__main__":
    # Test avec 3 PDFs
    import sys

    pdf_paths = sys.argv[1:] if len(sys.argv) > 1 else [
        "data/raw/bilan_standard.pdf",
    ]

    loader = MultiYearLoader()
    multi = loader.load_multiple_pdfs(pdf_paths, force_ocr=True)

    print()
    print("=" * 60)
    print("RESUME MULTI-EXERCICES")
    print("=" * 60)
    print()
    summary = multi.summary()
    print(f"  Nombre d'exercices : {summary['nb_exercices']}")
    print(f"  Annees : {summary['annees']}")
    print()

    # Calculer les croissances
    calc = GrowthCalculator(multi)
    growth = calc.compute_all_growth()

    print("=== CROISSANCES ===")
    for code, g in growth.items():
        print(f"\n{code}:")
        for k, v in g.items():
            print(f"  {k:15s} : {v * 100:>8.2f} %")
