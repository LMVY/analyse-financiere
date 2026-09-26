"""Extraction du texte et des tableaux depuis un PDF de bilan."""
import fitz  # PyMuPDF
from pathlib import Path


class PDFExtractor:
    """Extrait le texte d'un PDF de bilan/compte de resultat."""

    # Seuil de separation entre cellules (en points PDF)
    CELL_GAP = 20

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.doc = fitz.open(self.pdf_path)

    def extract_text(self) -> str:
        """Extrait tout le texte du PDF (brut)."""
        texte = ""
        for page in self.doc:
            texte += page.get_text()
        return texte

    def extract_rows(self) -> list[list[str]]:
        """Extrait les lignes du PDF en separant les cellules par position X.
        
        Retourne une liste de lignes, chaque ligne etant une liste de cellules.
        Ex: [["Immobilisations corporelles", "250 000", "230 000"], ...]
        """
        rows = []
        for page in self.doc:
            words = page.get_text("words")
            
            # Grouper par Y (ligne)
            lines_dict = {}
            for w in words:
                x0, y0, x1, text = w[0], w[1], w[2], w[4]
                y_key = round(y0)
                if y_key not in lines_dict:
                    lines_dict[y_key] = []
                lines_dict[y_key].append((x0, x1, text))
            
            # Pour chaque ligne, separer en cellules par gap X
            for y in sorted(lines_dict.keys()):
                words_in_line = sorted(lines_dict[y], key=lambda w: w[0])
                
                cells = []
                current_cell = [words_in_line[0][2]]
                last_x1 = words_in_line[0][1]
                
                for x0, x1, text in words_in_line[1:]:
                    gap = x0 - last_x1
                    if gap > self.CELL_GAP:
                        cells.append(" ".join(current_cell))
                        current_cell = [text]
                    else:
                        current_cell.append(text)
                    last_x1 = x1
                
                cells.append(" ".join(current_cell))
                rows.append(cells)
        
        return rows

    def get_page_count(self) -> int:
        return len(self.doc)

    def close(self):
        self.doc.close()


if __name__ == "__main__":
    extractor = PDFExtractor("data/raw/bilan_test.pdf")
    rows = extractor.extract_rows()
    print(f"Nombre de lignes : {len(rows)}\n")
    for row in rows:
        print(row)
    extractor.close()
