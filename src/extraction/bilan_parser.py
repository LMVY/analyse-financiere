"""Parse un PDF de bilan et retourne les donnees structurees."""
import json
from pathlib import Path
from src.extraction.pdf_extractor import PDFExtractor
from src.analysis.pcg_normalizer import PCGNormalizer


class BilanParser:
    """Combine extraction PDF et normalisation PCG."""

    SECTIONS = {
        "BILAN ACTIF": "actif",
        "BILAN PASSIF": "passif",
        "COMPTE DE RESULTAT": "compte_resultat",
    }

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.normalizer = PCGNormalizer()

    def parse(self) -> dict:
        """Parse le PDF et retourne un dict structure."""
        extractor = PDFExtractor(self.pdf_path)
        rows = extractor.extract_rows()
        extractor.close()

        result = {"actif": {}, "passif": {}, "compte_resultat": {}}
        section_courante = None

        for row in rows:
            ligne = " ".join(row)

            section = self._detect_section(ligne)
            if section:
                section_courante = section
                continue

            if section_courante is None:
                continue

            if self._is_header(row):
                continue

            if len(row) < 2:
                continue

            libelle = row[0].strip()
            montants = self._extract_montants(row[1:])

            if not montants:
                continue

            code_std = self.normalizer.normalize_label(libelle)
            if code_std and code_std["section"] == section_courante:
                result[section_courante][code_std["code"]] = montants

        return result

    def _detect_section(self, ligne: str) -> str:
        upper = ligne.upper()
        for titre, code in self.SECTIONS.items():
            if titre in upper:
                return code
        return None

    def _is_header(self, row: list[str]) -> bool:
        """Detecte les lignes d'en-tete (Poste, 2024, 2023)."""
        if not row:
            return False
        return row[0].strip().lower() == "poste"

    def _extract_montants(self, cells: list[str]) -> dict:
        """Extrait les montants d'une liste de cellules."""
        montants = {}
        annees = ["2024", "2023", "2022", "2021"]

        for i, cell in enumerate(cells):
            if i >= len(annees):
                break
            valeur = self.normalizer.parse_amount(cell)
            if valeur is not None:
                montants[annees[i]] = valeur

        return montants


if __name__ == "__main__":
    parser = BilanParser("data/raw/bilan_test.pdf")
    data = parser.parse()
    print(json.dumps(data, indent=2, ensure_ascii=False))
