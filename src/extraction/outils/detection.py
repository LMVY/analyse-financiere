"""Detection automatique du type de document comptable.

Distingue :
- Bilan (actif + passif)
- Compte de resultat
- Document mixte (bilan + CR dans le meme PDF)

Et detecte l'annee/exercice du document.
"""
import re
from pathlib import Path
import pdfplumber


def detect_doc_type(pdf_path: str) -> str:
    """Detecte le type de document.

    Returns:
        "bilan" | "compte_resultat" | "mixte" | "inconnu"
    """
    p = Path(pdf_path)
    if not p.exists():
        return "inconnu"

    texte = ""
    try:
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                texte += t + "\n"
    except Exception:
        return "inconnu"

    texte_lower = texte.lower()

    # Mots-cles bilan
    bilan_keywords = [
        "bilan actif", "bilan passif", "actif immobilise",
        "total actif", "total passif", "capitaux propres",
    ]
    # Mots-cles compte de resultat
    cr_keywords = [
        "compte de resultat", "produits d'exploitation",
        "chiffre d'affaires", "charges d'exploitation",
        "resultat d'exploitation", "resultat net",
    ]

    has_bilan = any(kw in texte_lower for kw in bilan_keywords)
    has_cr = any(kw in texte_lower for kw in cr_keywords)

    if has_bilan and has_cr:
        return "mixte"
    elif has_bilan:
        return "bilan"
    elif has_cr:
        return "compte_resultat"
    return "inconnu"


def detect_annee(pdf_path: str) -> str:
    """Detecte l'annee/exercice du document.

    Cherche :
    1. Dans le nom du fichier (2024, 2023...)
    2. Dans le contenu du PDF (date de cloture)

    Returns:
        annee (ex: "2024") ou None
    """
    p = Path(pdf_path)

    # 1. Chercher dans le nom du fichier
    filename = p.stem
    match = re.search(r"(20\d{2})", filename)
    if match:
        return match.group(1)

    # 2. Chercher dans le contenu
    try:
        with pdfplumber.open(p) as pdf:
            texte = ""
            for page in pdf.pages[:2]:  # 2 premieres pages
                t = page.extract_text() or ""
                texte += t + "\n"

        # Chercher une date : 31/12/2024, 30/06/2024, etc.
        dates = re.findall(r"\d{2}/\d{2}/(20\d{2})", texte)
        if dates:
            return max(dates)  # Annee la plus recente
    except Exception:
        pass

    return None


def classify_pdfs(pdf_paths: list) -> dict:
    """Classe une liste de PDFs par type et par annee.

    Returns:
        {
            "bilans": {annee: path},
            "comptes_resultat": {annee: path},
            "mixtes": {annee: path},
            "inconnus": [path],
        }
    """
    result = {
        "bilans": {},
        "comptes_resultat": {},
        "mixtes": {},
        "inconnus": [],
    }

    for pdf_path in pdf_paths:
        doc_type = detect_doc_type(pdf_path)
        annee = detect_annee(pdf_path) or f"ex_{len(result['bilans']) + len(result['comptes_resultat']) + len(result['mixtes'])}"

        if doc_type == "bilan":
            result["bilans"][annee] = pdf_path
        elif doc_type == "compte_resultat":
            result["comptes_resultat"][annee] = pdf_path
        elif doc_type == "mixte":
            result["mixtes"][annee] = pdf_path
        else:
            result["inconnus"].append(pdf_path)

    return result


def build_exercices(pdf_paths: list) -> list:
    """Construit la liste des exercices ordonnee (N, N-1, ...).

    Returns:
        [
            {"annee": "2025", "bilan": path, "compte_resultat": path},
            {"annee": "2024", "bilan": path, "compte_resultat": path},
        ]
    """
    classes = classify_pdfs(pdf_paths)

    # Recuperer toutes les annees
    annees = set(classes["bilans"].keys()) | set(classes["comptes_resultat"].keys()) | set(classes["mixtes"].keys())
    annees = sorted([a for a in annees if a.isdigit()], reverse=True)

    exercices = []
    for annee in annees:
        ex = {
            "annee": annee,
            "bilan": classes["bilans"].get(annee),
            "compte_resultat": classes["comptes_resultat"].get(annee),
            "mixte": classes["mixtes"].get(annee),
        }
        # Si c'est un mixte, il sert pour les 2
        if ex["mixte"]:
            ex["bilan"] = ex["bilan"] or ex["mixte"]
            ex["compte_resultat"] = ex["compte_resultat"] or ex["mixte"]
        exercices.append(ex)

    return exercices


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.outils.detection fichier1.pdf fichier2.pdf ...")
        sys.exit(1)

    paths = sys.argv[1:]
    print("=== CLASSIFICATION DES PDFs ===")
    print()

    for p in paths:
        typ = detect_doc_type(p)
        annee = detect_annee(p)
        print(f"  {Path(p).name:50s} -> {typ:20s} (annee: {annee})")

    print()
    print("=== EXERCICES CONSTRUITS ===")
    exercices = build_exercices(paths)
    for ex in exercices:
        print(f"  Annee {ex['annee']} :")
        print(f"    Bilan : {Path(ex['bilan']).name if ex['bilan'] else 'AUCUN'}")
        print(f"    CR    : {Path(ex['compte_resultat']).name if ex['compte_resultat'] else 'AUCUN'}")
