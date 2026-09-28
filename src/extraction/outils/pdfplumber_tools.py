"""Extraction de tableaux PDF avec pdfplumber.

Retourne le meme format que OCRExtractor :
- extract_rows() -> list de lignes, chaque ligne = list de tuples (text, x)
"""
import pdfplumber
from pathlib import Path


class PDFPlumberExtractor:
    """Extrait les tableaux et le texte d'un PDF de bilan."""

    CELL_GAP = 15  # pixels

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")

    def extract_text(self) -> str:
        texte = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texte += t + "\n"
        return texte

    def extract_tables(self) -> list:
        tables = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for t in page_tables:
                    if t:
                        tables.append({"page": i + 1, "data": t})
        return tables

    def extract_rows(self) -> list:
        """Extrait les lignes avec positions X (comme OCRExtractor)."""
        all_rows = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                if not words:
                    continue
                rows = self._group_words_into_rows(words)
                all_rows.extend(rows)
        return all_rows

    def _group_words_into_rows(self, words: list) -> list:
        """Groupe les mots par ligne (Y) puis par cellule (gap X)."""
        if not words:
            return []

        Y_TOLERANCE = 3
        words_sorted = sorted(words, key=lambda w: (w["top"], w["x0"]))

        lines = []
        current_line = [words_sorted[0]]
        current_y = words_sorted[0]["top"]

        for w in words_sorted[1:]:
            if abs(w["top"] - current_y) <= Y_TOLERANCE:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_y = w["top"]
        lines.append(current_line)

        rows = []
        for line in lines:
            line.sort(key=lambda w: w["x0"])
            cells = []
            current_cell_words = [line[0]["text"]]
            current_cell_x = line[0]["x0"]
            last_x_end = line[0]["x1"]

            for w in line[1:]:
                gap = w["x0"] - last_x_end
                if gap > self.CELL_GAP:
                    cells.append((" ".join(current_cell_words), current_cell_x))
                    current_cell_words = [w["text"]]
                    current_cell_x = w["x0"]
                else:
                    current_cell_words.append(w["text"])
                last_x_end = w["x1"]
            cells.append((" ".join(current_cell_words), current_cell_x))
            rows.append(cells)

        return rows

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
    rows = extractor.extract_rows()
    print(f"Nombre de lignes : {len(rows)}")
    print()
    for row in rows[:15]:
        print(row)
