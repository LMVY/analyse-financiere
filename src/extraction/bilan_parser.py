"""Parse un PDF de bilan et retourne les donnees structurees."""
import re
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
            # Reconstruire la ligne en texte
            ligne = " ".join(row)

            # Detecter le changement de section
            section = self._detect_section(ligne)
            if section:
                section_courante = section
                continue

            if section_courante is None:
                continue

            # Extraire libelle et montants
            parsed = self._parse_row(row)
            if not parsed:
                continue

            libelle, montants = parsed
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

    def _parse_row(self, row: list[str]):
        """Parse une ligne (liste de tokens). Retourne (libelle, montants)."""
        # Ignorer les en-tetes et titres
        joined = " ".join(row).lower()
        if "poste" in joined and "2024" in joined:
            return None
        if row[0].upper() in ("BILAN", "COMPTE"):
            return None

        # Trouver la position du premier token numerique (montant)
        idx_premier_num = None
        for i, token in enumerate(row):
            # Un montant commence par un chiffre
            if re.match(r"^\d", token):
                idx_premier_num = i
                break

        if idx_premier_num is None or idx_premier_num == 0:
            return None

        # Libelle = tous les tokens avant le premier nombre
        libelle = " ".join(row[:idx_premier_num]).strip()

        # Tokens de montants
        tokens_montants = row[idx_premier_num:]

        # Reconstituer les nombres : "50", "000", "45", "000" -> [50000, 45000]
        nombres = self._reconstruct_numbers(tokens_montants)

        if len(nombres) < 2:
            return None

        return libelle, {"2024": nombres[0], "2023": nombres[1]}

    def _reconstruct_numbers(self, tokens: list[str]) -> list[float]:
        """Reconstruit les nombres a partir de tokens separes.
        
        Ex: ['50', '000', '45', '000'] -> [50000.0, 45000.0]
        """
        # Joindre tous les tokens et chercher les groupes de chiffres
        texte = " ".join(tokens)
        
        # Pattern : nombre avec espaces comme separateurs de milliers
        # "50 000" ou "1 234 567" ou "45,50"
        pattern = r"\d{1,3}(?:\s\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
        matches = re.findall(pattern, texte)
        
        nombres = []
        for m in matches:
            # Supprimer les espaces, remplacer virgule par point
            cleaned = m.replace(" ", "").replace(",", ".")
            try:
                nombres.append(float(cleaned))
            except ValueError:
                continue
        
        return nombres


if __name__ == "__main__":
    parser = BilanParser("data/raw/bilan_test.pdf")
    data = parser.parse()

    import json
    print(json.dumps(data, indent=2, ensure_ascii=False))
