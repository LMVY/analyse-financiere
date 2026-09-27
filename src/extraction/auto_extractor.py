"""Detection automatique du type de PDF et extraction adaptee."""
from pathlib import Path
import pdfplumber

from src.extraction.pdfplumber_extractor import PDFPlumberExtractor
from src.extraction.ocr_extractor import OCRExtractor


class AutoExtractor:
    """Detecte si un PDF est natif ou scanne, puis extrait le texte."""

    CHARS_THRESHOLD = 50

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")

    def detect_type(self) -> str:
        """Retourne 'native', 'scanned' ou 'mixed'."""
        with pdfplumber.open(self.pdf_path) as pdf:
            total_chars = 0
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                total_chars += len(page.chars)
            avg_chars = total_chars / total_pages if total_pages > 0 else 0
            if avg_chars >= self.CHARS_THRESHOLD:
                return "native"
            elif avg_chars == 0:
                return "scanned"
            else:
                return "mixed"

    def extract(self, dpi: int = 300, force_ocr: bool = False) -> dict:
        """Detecte le type et extrait le texte."""
        pdf_type = self.detect_type()

        if force_ocr:
            print(f"  OCR force par l'utilisateur")
            pdf_type = "scanned"
        else:
            print(f"  Type detecte : {pdf_type}")

        if pdf_type == "native":
            print("  Methode : pdfplumber (texte natif)")
            extractor = PDFPlumberExtractor(self.pdf_path)
            texte = extractor.extract_text()
        else:
            print("  Methode : Tesseract OCR")
            extractor = OCRExtractor(self.pdf_path)
            texte = extractor.extract_text_from_pdf(dpi=dpi)

        return {
            "type": pdf_type,
            "texte": texte,
            "taille": len(texte),
        }


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    print(f"=== {pdf_path} ===")
    extractor = AutoExtractor(pdf_path)
    result = extractor.extract()

    print(f"  Taille : {result['taille']:,} caracteres")
    print()
    print("--- Apercu ---")
    print(result["texte"][:500])
