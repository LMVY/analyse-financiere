"""Extraction RapidOCR : PDFs scannes (remplace Tesseract et PaddleOCR).

RapidOCR = PaddleOCR converti en ONNX Runtime :
- Stable sur CPU (pas de bug OneDNN)
- 10x plus leger (100 Mo)
- Meme qualite que PaddleOCR
- Sortie : liste de [bbox, texte, score]
"""
from pathlib import Path
from pdf2image import convert_from_path
import numpy as np


class RapidOCRExtractor:
    """OCR base sur RapidOCR (ONNX Runtime)."""

    def __init__(self):
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr = RapidOCR()
        return self._ocr

    def extract_rows(self, pdf_path, dpi=250, max_pages=20):
        """Extrait les lignes avec positions X (compatible avec les autres extracteurs).

        Format de sortie :
            [ [(texte, x), (texte, x), ...],  # ligne 1
              [(texte, x), ...],              # ligne 2
              ... ]
        """
        ocr = self._get_ocr()
        p = Path(pdf_path)

        print(f"  RapidOCR : conversion PDF (dpi={dpi}, max {max_pages} pages)...")
        images = convert_from_path(p, dpi=dpi)[:max_pages]
        print(f"  {len(images)} pages a traiter")

        all_rows = []
        for i, img in enumerate(images, 1):
            print(f"  RapidOCR page {i}/{len(images)}...", end=" ", flush=True)

            img_array = np.array(img)

            try:
                result = ocr(img_array)
            except Exception as e:
                print(f"ERREUR: {e}")
                continue

            if not result or not result[0]:
                print("0 bloc")
                continue

            blocs = result[0]  # liste de [bbox, texte, score]
            rows = self._group_lines(blocs)
            all_rows.extend(rows)
            print(f"{len(rows)} lignes ({len(blocs)} blocs)")

        return all_rows

    def _group_lines(self, blocs):
        """Groupe les blocs en lignes selon Y puis cellules selon X."""
        if not blocs:
            return []

        mots = []
        for bloc in blocs:
            try:
                bbox, texte, conf = bloc
            except (ValueError, TypeError):
                continue

            try:
                score = float(conf)
            except (ValueError, TypeError):
                score = 1.0

            if score < 0.5:
                continue
            if not texte or not texte.strip():
                continue

            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]

            mots.append({
                "text": texte.strip(),
                "x": min(xs), "y": min(ys),
                "x1": max(xs), "y1": max(ys),
            })

        if not mots:
            return []

        mots.sort(key=lambda m: (m["y"], m["x"]))

        # Grouper en lignes (tolerance Y)
        # Tolerance proportionnelle a la hauteur moyenne des blocs
        h_moy = sum(m["y1"] - m["y"] for m in mots) / len(mots)
        Y_TOL = max(10, h_moy * 0.6)

        lignes = []
        courant = [mots[0]]
        y_courant = mots[0]["y"]

        for m in mots[1:]:
            if abs(m["y"] - y_courant) <= Y_TOL:
                courant.append(m)
            else:
                lignes.append(courant)
                courant = [m]
                y_courant = m["y"]
        lignes.append(courant)

        # Chaque ligne -> cellules selon gap X
        CELL_GAP = 30
        rows = []
        for ligne in lignes:
            ligne.sort(key=lambda m: m["x"])
            cells = []
            cell_words = [ligne[0]["text"]]
            cell_x = ligne[0]["x"]
            last_x_end = ligne[0]["x1"]

            for m in ligne[1:]:
                gap = m["x"] - last_x_end
                if gap > CELL_GAP:
                    cells.append((" ".join(cell_words), cell_x))
                    cell_words = [m["text"]]
                    cell_x = m["x"]
                else:
                    cell_words.append(m["text"])
                last_x_end = m["x1"]
            cells.append((" ".join(cell_words), cell_x))
            rows.append(cells)

        return rows

    def extract_text_from_pdf(self, pdf_path, dpi=250, max_pages=20):
        """Extrait tout le texte (mode simple)."""
        ocr = self._get_ocr()
        images = convert_from_path(pdf_path, dpi=dpi)[:max_pages]
        texte = []
        for img in images:
            try:
                result = ocr(np.array(img))
            except Exception:
                continue
            if result and result[0]:
                for bloc in result[0]:
                    try:
                        _, txt, _ = bloc
                        texte.append(txt)
                    except (ValueError, TypeError):
                        continue
        return "\n".join(texte)


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "/tmp/page1.png"
    extractor = RapidOCRExtractor()
    rows = extractor.extract_rows(pdf, max_pages=3)
    print(f"\nTotal : {len(rows)} lignes")
    for row in rows[:15]:
        print(f"  {row}")
