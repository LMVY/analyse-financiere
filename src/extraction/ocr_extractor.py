"""Extraction de texte depuis un PDF scanne via OCR (Tesseract)."""
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract


class OCRExtractor:
    """OCR pour PDFs scannes (images)."""

    def __init__(self, pdf_path: str, lang: str = "fra"):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.lang = lang

    def extract_text_from_pdf(self, dpi: int = 300) -> str:
        """Convertit chaque page en image et applique l'OCR.
        
        Args:
            dpi: resolution de conversion (300 = standard OCR)
        """
        print(f"  Conversion PDF -> images (dpi={dpi})...")
        images = convert_from_path(self.pdf_path, dpi=dpi)
        print(f"  {len(images)} pages a traiter")

        texte_total = []
        for i, image in enumerate(images, 1):
            print(f"  OCR page {i}/{len(images)}...", end=" ", flush=True)
            texte = pytesseract.image_to_string(image, lang=self.lang)
            texte_total.append(f"===== Page {i} =====\n{texte}")
            print(f"{len(texte)} caracteres")

        return "\n\n".join(texte_total)

    def extract_page(self, page_num: int, dpi: int = 300) -> str:
        """OCR une seule page (1-indexed)."""
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            first_page=page_num,
            last_page=page_num,
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0], lang=self.lang)


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    extractor = OCRExtractor(pdf_path)
    texte = extractor.extract_text_from_pdf(dpi=300)

    output = Path("data/processed") / (Path(pdf_path).stem + "_ocr.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(texte, encoding="utf-8")

    print()
    print(f"Texte sauvegarde : {output}")
    print(f"Taille : {len(texte):,} caracteres")
    print()
    print("--- Apercu des 2000 premiers caracteres ---")
    print(texte[:2000])
