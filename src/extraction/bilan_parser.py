"""Parser unifie : extrait et structure les postes comptables d'un PDF."""
from pathlib import Path
from typing import Optional

from src.extraction.ocr_extractor import OCRExtractor
from src.extraction.pdfplumber_extractor import PDFPlumberExtractor
from src.analysis.pcg_normalizer import PCGNormalizer, normalize_text
import pdfplumber


SECTION_KEYWORDS = {
    "actif": ["bilan actif", "actif", "actif immobilise"],
    "passif": ["bilan passif", "passif", "capitaux propres"],
    "compte_resultat": ["compte de resultat", "compte de resultats", "compte de produits et charges"],
}


class BilanParser:
    """Parse un PDF de bilan et retourne un dict structure."""

    def __init__(self, pdf_path: str, referentiel_path: str = "config/pcg_referentiel.yaml"):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.normalizer = PCGNormalizer(referentiel_path)

    def _detect_type(self) -> str:
        """Detecte si le PDF est natif ou scanne."""
        with pdfplumber.open(self.pdf_path) as pdf:
            total_chars = sum(len(p.chars) for p in pdf.pages)
            total_pages = len(pdf.pages)
            avg = total_chars / total_pages if total_pages else 0
            if avg >= 50:
                return "native"
            return "scanned"

    def parse(self, force_ocr: bool = False, dpi: int = 300) -> dict:
        """Parse le PDF et retourne un dict structure."""
        print("Extraction du texte...")
        pdf_type = "scanned" if force_ocr else self._detect_type()
        print(f"  Type : {pdf_type}")
        print()

        if pdf_type == "native":
            print("  Extraction pdfplumber (mots avec positions)...")
            extractor = PDFPlumberExtractor(self.pdf_path)
            rows = extractor.extract_rows()
        else:
            print("  Extraction OCR (mots avec positions)...")
            extractor = OCRExtractor(self.pdf_path)
            rows = extractor.extract_rows(dpi=dpi)

        print(f"  {len(rows)} lignes extraites")
        print()

        print("Parsing des postes...")
        data = self._parse_rows(rows)

        total = sum(len(data[s]) for s in data)
        print(f"  Actif : {len(data['actif'])} postes")
        print(f"  Passif : {len(data['passif'])} postes")
        print(f"  Compte de resultat : {len(data['compte_resultat'])} postes")
        print(f"  TOTAL : {total} postes extraits")

        return data

    def _parse_rows(self, rows: list) -> dict:
        result = {"actif": {}, "passif": {}, "compte_resultat": {}}
        section_courante = None

        for row in rows:
            if not row:
                continue
            ligne = " ".join(row).strip()
            if not ligne:
                continue

            nouvelle = self._detect_section(ligne)
            if nouvelle:
                section_courante = nouvelle
                continue

            if section_courante is None:
                continue

            if self._should_skip(row):
                continue

            parsed = self._parse_row_comptable(row)
            if not parsed:
                continue

            libelle, montants = parsed
            code_std = self.normalizer.normalize_label(
                libelle, section_hint=section_courante, seuil=92.0
            )

            if code_std:
                result[section_courante][code_std["code"]] = {
                    "libelle_original": libelle,
                    "montants": montants,
                    "score": code_std["score"],
                    "methode": code_std["methode"],
                }

        return result

    def _detect_section(self, ligne: str) -> Optional[str]:
        norm = normalize_text(ligne)
        if "total" in norm:
            return None
        for section, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if norm == kw or norm.startswith(kw + " "):
                    if section == "actif" and "actif immobilise" in norm:
                        continue
                    return section
        return None

    def _should_skip(self, row: list) -> bool:
        if len(row) < 2:
            return True
        if not row[0].strip():
            return True
        has_amount = False
        for cell in row[1:]:
            if self.normalizer.parse_amount(cell) is not None:
                has_amount = True
                break
        if not has_amount:
            return True
        norm = normalize_text(" ".join(row))
        skip_keywords = ["rubriques", "poste", "montant"]
        if any(kw in norm for kw in skip_keywords) and "total" not in norm:
            return True
        return False

    def _parse_row_comptable(self, row: list) -> Optional[tuple]:
        libelle = row[0].strip()
        if len(libelle) < 3:
            return None

        montants = []
        for cell in row[1:]:
            val = self.normalizer.parse_amount(cell)
            if val is not None:
                montants.append(val)

        if not montants:
            return None

        montants = [m for m in montants if abs(m) < 1e9]
        if not montants:
            return None

        colonnes = ["brut", "amort", "net", "net_n1", "net_n2", "autre"]
        montants_dict = {}
        for i, val in enumerate(montants[:6]):
            montants_dict[colonnes[i]] = val

        return libelle, montants_dict


if __name__ == "__main__":
    import sys
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    print("=" * 60)
    print(f"PARSING : {pdf_path}")
    print("=" * 60)
    print()

    parser = BilanParser(pdf_path)
    data = parser.parse(force_ocr=True)

    print()
    print("=" * 60)
    print("RESULTAT")
    print("=" * 60)
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))
