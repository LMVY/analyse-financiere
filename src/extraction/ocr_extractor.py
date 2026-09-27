"""Extraction de texte depuis un PDF scanne via OCR (Tesseract)."""
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output


class OCRExtractor:
    """OCR pour PDFs scannes (images)."""

    CELL_GAP = 30

    def __init__(self, pdf_path: str, lang: str = "fra"):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.lang = lang

    def extract_text_from_pdf(self, dpi: int = 300) -> str:
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

    def extract_rows(self, dpi: int = 300) -> list:
        print(f"  Conversion PDF -> images (dpi={dpi})...")
        images = convert_from_path(self.pdf_path, dpi=dpi)
        print(f"  {len(images)} pages a traiter")
        all_rows = []
        for i, image in enumerate(images, 1):
            print(f"  OCR page {i}/{len(images)}...", end=" ", flush=True)
            data = pytesseract.image_to_data(image, lang=self.lang, output_type=Output.DICT)
            rows = self._group_words_into_rows(data)
            all_rows.extend(rows)
            print(f"{len(rows)} lignes")
        return all_rows

    def _group_words_into_rows(self, data: dict) -> list:
        words = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i]) if data["conf"][i] != "-1" else -1
            if text and conf > 30:
                words.append({
                    "text": text,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                })
        if not words:
            return []

        Y_TOLERANCE = 10
        words.sort(key=lambda w: (w["y"], w["x"]))
        lines = []
        current_line = [words[0]]
        current_y = words[0]["y"]
        for w in words[1:]:
            if abs(w["y"] - current_y) <= Y_TOLERANCE:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_y = w["y"]
        lines.append(current_line)

        rows = []
        for line in lines:
            line.sort(key=lambda w: w["x"])
            cells = []
            current_cell = [line[0]["text"]]
            last_x_end = line[0]["x"] + line[0]["width"]
            for w in line[1:]:
                gap = w["x"] - last_x_end
                if gap > self.CELL_GAP:
                    cells.append(" ".join(current_cell))
                    current_cell = [w["text"]]
                else:
                    current_cell.append(w["text"])
                last_x_end = w["x"] + w["width"]
            cells.append(" ".join(current_cell))
            rows.append(cells)
        return rows

    def extract_page(self, page_num: int, dpi: int = 300) -> str:
        images = convert_from_path(
            self.pdf_path, dpi=dpi,
            first_page=page_num, last_page=page_num,
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0], lang=self.lang)


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"
    extractor = OCRExtractor(pdf_path)
    rows = extractor.extract_rows(dpi=300)
    print()
    print(f"Nombre total de lignes : {len(rows)}")
    print()
    print("=== Apercu des 30 premieres lignes ===")
    for row in rows[:30]:
        print(row)
