"""Detecte le code NAF/APE dans un PDF ou un nom de fichier."""
import re
from pathlib import Path

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# Mapping NAF -> secteur (code interne)
NAF_TO_SECTEUR = {
    "A": "agriculture",
    "B": "industrie",
    "C": "industrie",
    "D": "industrie",
    "E": "industrie",
    "F": "construction",
    "G": "commerce",
    "H": "transport",
    "I": "hotellerie_restauration",
    "J": "information_communication",
    "K": "services",
    "L": "immobilier",
    "M": "services",
    "N": "services",
    "O": "services",
    "P": "services",
    "Q": "services",
    "R": "services",
    "S": "services",
}


def detect_naf_in_text(texte: str):
    """Cherche un code NAF dans un texte.

    Ex: "Code activite (NAF) 4774Z" ou "APE: 6201Z"
    """
    if not texte:
        return None

    # Pattern : code NAF = 4 chiffres + 1 lettre (ex: 4774Z)
    # ou 4 chiffres (ex: 4774)
    patterns = [
        r"(?:NAF|APE|code\s+activite|code\s+ape)[\s:]*(\d{4}[A-Z])",
        r"(?:NAF|APE)[\s:]*(\d{4})",
        r"\b(\d{4}[A-Z])\b",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, texte, re.IGNORECASE)
        if matches:
            return matches[0].upper()

    return None


def detect_naf_in_pdf(pdf_path: str):
    """Cherche un code NAF dans un PDF (5 premieres pages)."""
    if not HAS_PDFPLUMBER:
        return None

    p = Path(pdf_path)
    if not p.exists():
        return None

    try:
        with pdfplumber.open(p) as pdf:
            # Chercher dans TOUT le PDF (limite 30 pages)
            for page in pdf.pages[:30]:
                texte = page.extract_text() or ""
                naf = detect_naf_in_text(texte)
                if naf:
                    return naf
    except Exception:
        pass

    return None


def naf_to_secteur(naf_code: str):
    """Convertit un code NAF en code secteur interne.

    Ex: "4774Z" -> "commerce" (section G)
    """
    if not naf_code:
        return None

    # Extraire la section (1ere lettre pour les NAF avec lettre)
    # Pour NAF numerique, la 1ere lettre est determinee par les 2 premiers chiffres
    if len(naf_code) >= 5 and naf_code[-1].isalpha():
        # Format "4774Z" : la section est determinee par le code
        # On utilise une table simplifiee
        prefix = naf_code[:2]
        prefix_to_section = {
            "01": "agriculture", "02": "agriculture", "03": "agriculture",
            "05": "industrie", "06": "industrie", "07": "industrie",
            "08": "industrie", "09": "industrie", "10": "industrie",
            "11": "industrie", "12": "industrie", "13": "industrie",
            "14": "industrie", "15": "industrie", "16": "industrie",
            "17": "industrie", "18": "industrie", "19": "industrie",
            "20": "industrie", "21": "industrie", "22": "industrie",
            "23": "industrie", "24": "industrie", "25": "industrie",
            "26": "industrie", "27": "industrie", "28": "industrie",
            "29": "industrie", "30": "industrie", "31": "industrie",
            "32": "industrie", "33": "industrie",
            "35": "industrie", "36": "industrie", "37": "industrie",
            "38": "industrie", "39": "industrie",
            "41": "construction", "42": "construction", "43": "construction",
            "45": "commerce", "46": "commerce", "47": "commerce",
            "49": "transport", "50": "transport", "51": "transport",
            "52": "transport", "53": "transport",
            "55": "hotellerie_restauration", "56": "hotellerie_restauration",
            "58": "information_communication", "59": "information_communication",
            "60": "information_communication", "61": "information_communication",
            "62": "information_communication", "63": "information_communication",
            "64": "services", "65": "services", "66": "services",
            "68": "immobilier",
            "69": "services", "70": "services", "71": "services",
            "72": "services", "73": "services", "74": "services",
            "75": "services", "77": "services", "78": "services",
            "79": "services", "80": "services", "81": "services",
            "82": "services",
            "85": "services", "86": "services", "87": "services",
            "88": "services",
            "90": "services", "91": "services", "92": "services",
            "93": "services", "94": "services", "95": "services",
            "96": "services",
        }
        return prefix_to_section.get(prefix)

    return None


def detect_secteur_auto(file_path: str):
    """Detecte automatiquement le secteur d'un fichier.

    Returns:
        (code_naf, code_secteur) ou (None, None)
    """
    p = Path(file_path)

    # 1. Chercher dans le nom du fichier
    filename = p.stem
    naf = detect_naf_in_text(filename)

    # 2. Chercher dans le PDF
    if not naf and p.suffix.lower() == ".pdf":
        naf = detect_naf_in_pdf(file_path)

    if not naf:
        return None, None

    secteur = naf_to_secteur(naf)
    return naf, secteur


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.naf_detector fichier.pdf")
        sys.exit(1)

    file_path = sys.argv[1]
    naf, secteur = detect_secteur_auto(file_path)

    print(f"Fichier : {file_path}")
    print(f"Code NAF : {naf}")
    print(f"Secteur  : {secteur}")
