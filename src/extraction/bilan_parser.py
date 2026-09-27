"""Parser unifie : extrait et structure les postes comptables d'un PDF.

Combine :
- Detection auto du type de PDF (natif/scanne)
- Extraction (pdfplumber ou OCR)
- Detection des sections (Actif, Passif, Compte de resultat)
- Extraction des lignes (libelle + montants)
- Normalisation PCG (avec fuzzy matching)
"""
import re
from pathlib import Path
from typing import Optional

from src.extraction.auto_extractor import AutoExtractor
from src.analysis.pcg_normalizer import PCGNormalizer, normalize_text


# Mots-cles pour detecter les sections
SECTION_KEYWORDS = {
    "actif": [
        "bilan actif",
        "actif",
        "actif immobilise",
    ],
    "passif": [
        "bilan passif",
        "passif",
        "capitaux propres",
    ],
    "compte_resultat": [
        "compte de resultat",
        "compte de resultats",
        "compte de produits et charges",
    ],
}

# Mots-cles a ignorer (en-tetes, pieds de page)
IGNORE_PATTERNS = [
    r"^page\s+\d+",
    r"^exercice\s+clos",
    r"^au\s+\d{2}/\d{2}/\d{4}",
    r"^devise",
    r"^en\s+euros?",
    r"^en\s+milliers",
    r"^\d{2}/\d{2}/\d{4}$",
    r"^poste$",
    r"^rubriques?$",
    r"^brut$",
    r"^amort",
    r"^net$",
    r"^montant$",
    r"^\d{4}$",  # annee seule
]


class BilanParser:
    """Parse un PDF de bilan et retourne un dict structure."""

    def __init__(self, pdf_path: str, referentiel_path: str = "config/pcg_referentiel.yaml"):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.normalizer = PCGNormalizer(referentiel_path)

    def parse(self, force_ocr: bool = False) -> dict:
        """Parse le PDF et retourne un dict structure."""
        # 1. Extraire le texte
        print(f"Extraction du texte...")
        extractor = AutoExtractor(self.pdf_path)
        result = extractor.extract(force_ocr=force_ocr)
        texte = result["texte"]
        print(f"  Type : {result['type']}")
        print(f"  Taille : {len(texte):,} caracteres")
        print()

        # 2. Parser les lignes
        print(f"Parsing des postes...")
        lignes = texte.split("\n")
        data = self._parse_lines(lignes)

        # 3. Stats
        total = sum(len(data[s]) for s in data)
        print(f"  Actif : {len(data['actif'])} postes")
        print(f"  Passif : {len(data['passif'])} postes")
        print(f"  Compte de resultat : {len(data['compte_resultat'])} postes")
        print(f"  TOTAL : {total} postes extraits")

        return data

    def _parse_lines(self, lignes: list[str]) -> dict:
        """Parse les lignes et remplit les 3 sections."""
        result = {"actif": {}, "passif": {}, "compte_resultat": {}}
        section_courante = None
        stats = {"ignorees": 0, "non_matchees": 0, "ok": 0}

        for ligne in lignes:
            ligne_clean = ligne.strip()
            if not ligne_clean:
                continue

            # Detecter les changements de section
            nouvelle_section = self._detect_section(ligne_clean)
            if nouvelle_section:
                section_courante = nouvelle_section
                continue

            # Ignorer si pas dans une section
            if section_courante is None:
                continue

            # Ignorer les en-tetes
            if self._should_ignore(ligne_clean):
                stats["ignorees"] += 1
                continue

            # Extraire libelle + montants
            parsed = self._parse_ligne_comptable(ligne_clean)
            if not parsed:
                stats["ignorees"] += 1
                continue

            libelle, montants = parsed

            # Normaliser via PCG
            code_std = self.normalizer.normalize_label(
                libelle, section_hint=section_courante
            )

            if code_std:
                result[section_courante][code_std["code"]] = {
                    "libelle_original": libelle,
                    "montants": montants,
                    "score": code_std["score"],
                    "methode": code_std["methode"],
                }
                stats["ok"] += 1
            else:
                stats["non_matchees"] += 1

        return result

    def _detect_section(self, ligne: str) -> Optional[str]:
        """Detecte si la ligne est un titre de section."""
        norm = normalize_text(ligne)
        # Ne pas confondre avec "total actif" ou "actif immobilise"
        if "total" in norm:
            return None

        for section, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if norm == kw or norm.startswith(kw + " "):
                    # Eviter les faux positifs
                    if section == "actif" and "actif immobilise" in norm:
                        continue
                    return section
        return None

    def _should_ignore(self, ligne: str) -> bool:
        """Detecte si la ligne doit etre ignoree."""
        norm = normalize_text(ligne)
        if not norm:
            return True
        # Ignorer les lignes courtes sans chiffres
        if len(norm) < 3:
            return True
        return False

    def _parse_ligne_comptable(self, ligne: str) -> Optional[tuple]:
        """Separe le libelle des montants.
        
        Gere plusieurs formats :
        - "Chiffre d'affaires 800 000 720 000"
        - "Chiffre d'affaires    800 000,00    720 000,00"
        - "Immobilisations corporelles    250 000    230 000"
        """
        # Pattern : libelle suivi de 1, 2 ou 3 nombres
        # Un nombre = chiffres avec separateurs espaces/points/virgules
        pattern = re.compile(
            r"^(.+?)\s+"
            r"(\d[\d\s]*(?:[.,]\d+)?)"
            r"(?:\s+(\d[\d\s]*(?:[.,]\d+)?))?"
            r"(?:\s+(\d[\d\s]*(?:[.,]\d+)?))?"
            r"\s*$"
        )

        match = pattern.match(ligne)
        if not match:
            return None

        libelle = match.group(1).strip()

        # Ignorer si le libelle est trop court ou trop long
        if len(libelle) < 3 or len(libelle) > 150:
            return None

        montants = {}
        annees = ["N", "N-1", "N-2"]
        for i, group in enumerate([match.group(2), match.group(3), match.group(4)]):
            if group:
                val = self.normalizer.parse_amount(group)
                if val is not None:
                    montants[annees[i]] = val

        if not montants:
            return None

        return libelle, montants


if __name__ == "__main__":
    import sys
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    print("=" * 60)
    print(f"PARSING : {pdf_path}")
    print("=" * 60)
    print()

    parser = BilanParser(pdf_path)
    data = parser.parse()

    print()
    print("=" * 60)
    print("RESULTAT")
    print("=" * 60)
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))
