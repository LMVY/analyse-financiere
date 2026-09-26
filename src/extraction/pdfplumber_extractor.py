"""Extraction de tableaux PDF avec pdfplumber."""
import pdfplumber
from pathlib import Path


class PDFPlumberExtractor:
    """Extrait les tableaux et le texte d'un PDF de bilan."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")

    def extract_text(self) -> str:
        """Extrait tout le texte du PDF."""
        texte = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texte += t + "\n"
        return texte

    def extract_tables(self) -> list[dict]:
        """Extrait tous les tableaux du PDF."""
        tables = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for t in page_tables:
                    if t:
                        tables.append({"page": i + 1, "data": t})
        return tables

    def get_page_count(self) -> int:
        with pdfplumber.open(self.pdf_path) as pdf:
            return len(pdf.pages)


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    extractor = PDFPlumberExtractor(pdf_path)
    print(f"PDF : {pdf_path}")
    print(f"Pages : {extractor.get_page_count()}")
    print()

    tables = extractor.extract_tables()
    print(f"Nombre de tableaux : {len(tables)}")
    for t in tables:
        print(f"  Page {t['page']} : {len(t['data'])} lignes")
