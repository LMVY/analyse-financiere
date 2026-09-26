"""Normalisation des libelles comptables vers les postes standards PCG."""
import re
import yaml
from pathlib import Path
from typing import Optional


class PCGNormalizer:
    """Transforme les libelles bruts en postes comptables standards."""

    def __init__(self, referentiel_path: str = "config/pcg_referentiel.yaml"):
        self.referentiel_path = Path(referentiel_path)
        with open(self.referentiel_path, "r", encoding="utf-8") as f:
            self.referentiel = yaml.safe_load(f)

        # Construire un index inverse : libelle -> code standard
        self.mapping = {}
        for section, postes in self.referentiel.items():
            for code, libelles in postes.items():
                for libelle in libelles:
                    self.mapping[libelle.lower().strip()] = {
                        "section": section,
                        "code": code,
                    }

    def normalize_label(self, label: str) -> Optional[dict]:
        """Retourne le code standard pour un libelle donne."""
        cleaned = label.lower().strip()

        # Recherche exacte
        if cleaned in self.mapping:
            return self.mapping[cleaned]

        # Recherche partielle (le libelle contient un mot-cle)
        for key, value in self.mapping.items():
            if key in cleaned:
                return value

        return None

    def parse_amount(self, text: str) -> Optional[float]:
        """Convertit '250 000' en 250000.0."""
        cleaned = text.replace(" ", "").replace("\u202f", "").replace(",", ".")
        cleaned = re.sub(r"[^\d.-]", "", cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return None


if __name__ == "__main__":
    normalizer = PCGNormalizer()
    print("Test de normalisation :\n")
    tests = [
        "Immobilisations corporelles",
        "Disponibilites",
        "Emprunts et dettes aupres des etablissements de credit",
        "Chiffre d'affaires",
        "Resultat net",
        "Poste inconnu",
    ]
    for t in tests:
        result = normalizer.normalize_label(t)
        print(f"  {t:60s} -> {result}")

    print(f"\nTest de parsing :")
    for t in ["250 000", "1 234 567", "45,50", "N/A"]:
        print(f"  '{t}' -> {normalizer.parse_amount(t)}")
