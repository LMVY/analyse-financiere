"""Parser unifie : extrait et structure les postes comptables d'un PDF.

Regle metier : les 2 dernieres valeurs sont toujours Net N et Net N-1.
"""
from pathlib import Path
from typing import Optional

from src.extraction.outils.ocr_tools import OCRExtractor
from src.extraction.outils.pdfplumber_tools import PDFPlumberExtractor
from src.analysis.pcg_normalizer import PCGNormalizer, normalize_text
from src.extraction.formats.dgfip_pdf import (
    extract_dgfip_values, detect_dgfip_format,
)
from src.extraction.formats.dgfip_excel import (
    extract_dgfip_values_from_excel, detect_dgfip_excel,
)
from src.extraction.formats.excel_normal import extract_excel_values, detect_excel_format
from src.extraction.formats.fec import extract_fec_values, detect_fec_format
from src.analysis.selector import ColumnSelector
import pdfplumber



# Titres de section a ignorer (ce ne sont pas des postes comptables)
STOPWORDS = [
    "dettes",
    "creances",
    "immobilisations",
    "capitaux propres",
    "capitaux",
    "provisions",
    "stocks",
    "actif circulant",
    "passif circulant",
    "comptes de regularisation",
    "total",
    "totaux",
    "bilan",
    "compte de resultat",
]

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
        with pdfplumber.open(self.pdf_path) as pdf:
            total_chars = sum(len(p.chars) for p in pdf.pages)
            total_pages = len(pdf.pages)
            avg = total_chars / total_pages if total_pages else 0
            if avg >= 50:
                return "native"
            return "scanned"

    def parse(self, force_ocr: bool = False, dpi: int = 300) -> dict:
        print("Extraction du texte...")
        pdf_type = "scanned" if force_ocr else self._detect_type()
        print(f"  Type : {pdf_type}")
        print()

        if pdf_type == "native":
            extractor = PDFPlumberExtractor(self.pdf_path)
            rows = extractor.extract_rows()
        else:
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

    def parse_simple(self, force_ocr: bool = False, dpi: int = 300) -> dict:
        """Parse et retourne les valeurs par poste.

        Detecte automatiquement le format :
        - DGFiP (liasse fiscale) -> dgfip_parser
        - Standard -> pdfplumber/OCR
        """
        # 1. Verifier le format
        path_str = str(self.pdf_path)

        # FEC ?
        if detect_fec_format(path_str):
            print("  Format FEC detecte -> parser FEC")
            fec_data = extract_fec_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in fec_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # Excel/CSV ?
        if detect_excel_format(path_str):
            # Verifier si c'est une liasse fiscale DGFiP au format Excel
            if detect_dgfip_excel(path_str):
                print("  Format DGFiP Excel detecte -> parser DGFiP Excel")
                excel_data = extract_dgfip_values_from_excel(path_str)
            else:
                print("  Format Excel/CSV detecte -> parser Excel")
                excel_data = extract_excel_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in excel_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # DGFiP ?
        if detect_dgfip_format(path_str):
            print("  Format DGFiP detecte -> parser DGFiP")
            dgfip_data = extract_dgfip_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in dgfip_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # 2. Sinon, parser classique
        data = self.parse(force_ocr=force_ocr, dpi=dpi)
        result = {}
        for section in ["actif", "passif", "compte_resultat"]:
            selector = ColumnSelector(section)
            result[section] = selector.select_all(data[section])
        return result

    def _parse_rows(self, rows: list) -> dict:
        result = {"actif": {}, "passif": {}, "compte_resultat": {}}
        section_courante = None

        for row in rows:
            if not row:
                continue

            ligne = " ".join([c[0] if isinstance(c, tuple) else c for c in row]).strip()
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

            parsed = self._parse_row_comptable(row, section_courante)
            if not parsed:
                continue

            libelle, montants = parsed

            code_std = self.normalizer.normalize_label(
                libelle, section_hint=section_courante, seuil=90.0
            )

            if code_std:
                code = code_std["code"]
                # Sommer les montants si le code existe deja
                if code in result[section_courante]:
                    existing = result[section_courante][code]["montants"]
                    for col, val in montants.items():
                        if col in existing:
                            existing[col] += val
                        else:
                            existing[col] = val
                else:
                    result[section_courante][code] = {
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

        first_cell = row[0][0] if isinstance(row[0], tuple) else row[0]
        if not first_cell.strip():
            return True

        norm = normalize_text(first_cell)
        if len(norm) <= 2 and not norm.isalpha():
            return True

        has_amount = False
        for cell in row[1:]:
            text = cell[0] if isinstance(cell, tuple) else cell
            if self.normalizer.parse_amount(text) is not None:
                has_amount = True
                break
        if not has_amount:
            return True

        # Ignorer les titres de section
        libelle_norm = normalize_text(first_cell)
        if libelle_norm in STOPWORDS:
            return True

        return False

    def _parse_row_comptable(self, row: list, section: str) -> Optional[tuple]:
        """Extrait (libelle, montants) avec la regle metier.

        REGLE : les 2 dernieres valeurs = Net N et Net N-1.
        """
        first = row[0]
        libelle = first[0] if isinstance(first, tuple) else first
        libelle = libelle.strip()
        if len(libelle) < 3:
            return None

        # Recuperer toutes les valeurs numeriques
        valeurs = []
        for cell in row[1:]:
            text = cell[0] if isinstance(cell, tuple) else cell
            val = self.normalizer.parse_amount(text)
            if val is not None and abs(val) < 1e9:
                valeurs.append(val)

        if not valeurs:
            return None

        montants_dict = {}
        n = len(valeurs)

        if section == "actif":
            # Bilan actif : Brut | Amort | Net [| Net N-1]
            if n == 1:
                montants_dict["net"] = valeurs[0]
            elif n == 2:
                montants_dict["amort"] = valeurs[0]
                montants_dict["net"] = valeurs[1]
            elif n == 3:
                montants_dict["brut"] = valeurs[0]
                montants_dict["amort"] = valeurs[1]
                montants_dict["net"] = valeurs[2]
            elif n >= 4:
                montants_dict["brut"] = valeurs[0]
                montants_dict["amort"] = valeurs[1]
                montants_dict["net"] = valeurs[2]
                montants_dict["net_n1"] = valeurs[3]
        else:
            # Bilan passif ou compte de resultat : Net [| Net N-1 | Net N-2]
            if n == 1:
                montants_dict["net"] = valeurs[0]
            elif n == 2:
                montants_dict["net"] = valeurs[0]
                montants_dict["net_n1"] = valeurs[1]
            elif n >= 3:
                montants_dict["net"] = valeurs[0]
                montants_dict["net_n1"] = valeurs[1]
                montants_dict["net_n2"] = valeurs[2]

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
