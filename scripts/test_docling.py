"""Test d'extraction Docling sur des PDFs reels."""
from docling.document_converter import DocumentConverter
from pathlib import Path
import time


PDFS = [
    ("bilan_standard.pdf", "Standard (L'ORTEGA)"),
    ("bilan_dunamis.pdf", "Standard (DUNAMIS)"),
    ("bilan_complexe.pdf", "Complexe (@COM Expertise)"),
]


def test_pdf(pdf_name: str, label: str, converter: DocumentConverter):
    """Test un PDF et retourne des stats."""
    pdf_path = Path("data/raw") / pdf_name

    if not pdf_path.exists():
        print(f"  [SKIP] {pdf_name} non trouve")
        return None

    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"  Fichier : {pdf_name}")
    print(f"{'=' * 70}")

    start = time.time()
    result = converter.convert(str(pdf_path))
    elapsed = time.time() - start

    markdown = result.document.export_to_markdown()

    # Sauvegarder
    output_path = Path("data/processed") / f"{pdf_path.stem}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"  Temps : {elapsed:.1f}s")
    print(f"  Taille : {len(markdown):,} caracteres")
    print(f"  Sauvegarde : {output_path}")

    # Chercher des elements cles
    checks = {
        "Total actif": ["total actif", "total de l'actif"],
        "Total passif": ["total passif", "total du passif"],
        "Chiffre d'affaires": ["chiffre d'affaires"],
        "Resultat net": ["resultat net", "resultat de l'exercice"],
        "Capital social": ["capital social"],
        "Immobilisations": ["immobilisations"],
        "Dettes": ["dettes"],
    }

    markdown_lower = markdown.lower()
    print(f"\n  Detection des postes cles :")
    for element, patterns in checks.items():
        found = any(p in markdown_lower for p in patterns)
        symbol = "OK" if found else "MANQUANT"
        print(f"    [{symbol:8s}] {element}")

    return markdown


if __name__ == "__main__":
    print("=" * 70)
    print("TEST DOCLING SUR 3 PDFs REELS")
    print("=" * 70)
    print("\nPremier lancement : telechargement des modeles IA (~500 Mo)")
    print("Cela peut prendre 5-10 minutes.\n")

    converter = DocumentConverter()

    for pdf_name, label in PDFS:
        try:
            test_pdf(pdf_name, label, converter)
        except Exception as e:
            print(f"  ERREUR : {e}")
