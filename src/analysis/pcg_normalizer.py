"""Normalisation des libelles comptables vers les postes standards PCG.

Combine :
- Normalisation stricte (accents, casse, ponctuation)
- Recherche exacte
- Fuzzy matching (rapidfuzz)
- Filtrage par section pour lever les ambiguites
- Mapping par numeros de comptes PCG
"""
import re
import unicodedata
import yaml
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process


def normalize_text(text: str) -> str:
    """Normalise un texte : minuscules, sans accents, sans ponctuation."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class PCGNormalizer:
    """Normalise les libelles comptables vers les codes PCG standards."""

    SEUIL_FUZZY = 85.0

    def __init__(self, referentiel_path=None):
        if referentiel_path is None:
            referentiel_path = Path(__file__).parent.parent.parent / "config" / "pcg_referentiel.yaml"
        self.referentiel_path = Path(referentiel_path)
        with open(self.referentiel_path, "r", encoding="utf-8") as f:
            self.referentiel = yaml.safe_load(f)

        self.index = {}
        self.index_par_section = {"actif": {}, "passif": {}, "compte_resultat": {}}
        self.comptes_pcg = {}

        self._build_indexes()

    def _build_indexes(self):
        for section in ["actif", "passif", "compte_resultat"]:
            if section not in self.referentiel:
                continue
            for code_std, variantes in self.referentiel[section].items():
                for libelle in variantes:
                    norm = normalize_text(libelle)
                    if not norm:
                        continue
                    self.index[norm] = {"section": section, "code": code_std}
                    self.index_par_section[section][norm] = code_std

        for code_std, prefixes in self.referentiel.get("comptes_pcg", {}).items():
            for prefix in prefixes:
                self.comptes_pcg[str(prefix)] = code_std

    def normalize_label(
        self,
        label: str,
        section_hint: Optional[str] = None,
        seuil: Optional[float] = None,
    ) -> Optional[dict]:
        """Trouve le code standard pour un libelle."""
        norm = normalize_text(label)
        if not norm:
            return None

        seuil = seuil or self.SEUIL_FUZZY

        # 1. Recherche exacte
        if norm in self.index:
            entry = self.index[norm]
            if not section_hint or entry["section"] == section_hint:
                return {
                    "code": entry["code"],
                    "section": entry["section"],
                    "score": 100.0,
                    "methode": "exacte",
                }

        # 2. Fuzzy matching
        candidates = self.index
        if section_hint and section_hint in self.index_par_section:
            candidates = {
                lib: {"section": section_hint, "code": code}
                for lib, code in self.index_par_section[section_hint].items()
            }

        if not candidates:
            return None

        result = process.extractOne(
            norm,
            list(candidates.keys()),
            scorer=fuzz.WRatio,
            score_cutoff=seuil,
        )

        if result:
            libelle_trouve, score, _ = result
            entry = candidates[libelle_trouve]
            return {
                "code": entry["code"],
                "section": entry["section"],
                "score": round(score, 2),
                "methode": "fuzzy",
            }

        return None

    def normalize_from_account_number(self, num_compte: str) -> Optional[dict]:
        """Trouve le code standard a partir d'un numero de compte PCG."""
        num = str(num_compte).strip()
        if not num:
            return None

        matches = []
        for prefix, code_std in self.comptes_pcg.items():
            if num.startswith(prefix):
                matches.append((len(prefix), prefix, code_std))

        if matches:
            matches.sort(reverse=True)
            _, prefix, code_std = matches[0]
            return {"code": code_std, "prefixe": prefix}

        return None

    def parse_amount(self, text: str) -> Optional[float]:
        """Convertit un montant textuel en float."""
        if not text:
            return None

        cleaned = str(text).strip()
        negatif = cleaned.startswith("-") or (
            cleaned.startswith("(") and cleaned.endswith(")")
        )
        cleaned = cleaned.strip("()-")
        cleaned = cleaned.replace("\u202f", "").replace(" ", "")
        cleaned = cleaned.replace("\u20ac", "").replace("EUR", "").strip()
        cleaned = cleaned.replace(",", ".")
        cleaned = re.sub(r"[^\d.]", "", cleaned)

        if not cleaned:
            return None

        try:
            val = float(cleaned)
            return -val if negatif else val
        except ValueError:
            return None


if __name__ == "__main__":
    normalizer = PCGNormalizer()

    print("=== Index ===")
    print(f"  Libelles total : {len(normalizer.index)}")
    print(f"  Comptes PCG : {len(normalizer.comptes_pcg)}")
    print()

    print("=== Test 1 : normalisation exacte ===")
    tests = [
        "Chiffre d'affaires",
        "chiffre d affaires",
        "Immobilisations corporelles",
        "Creances clients",
        "Dettes fournisseurs",
    ]
    for t in tests:
        res = normalizer.normalize_label(t)
        print(f"  {t:40s} -> {res}")

    print()
    print("=== Test 2 : fuzzy matching ===")
    tests_fuzzy = [
        "Installations techniques, materiel et outillage",
        "Chiffres d'affaires net",
        "Resultat dexploitation",
        "Amortissements des immobilisations corporelles",
    ]
    for t in tests_fuzzy:
        res = normalizer.normalize_label(t)
        print(f"  {t:45s} -> {res}")

    print()
    print("=== Test 3 : ambiguite (section) ===")
    t = "Reprises sur provisions et depreciations"
    print(f"  {t}")
    for section in ["compte_resultat", None]:
        res = normalizer.normalize_label(t, section_hint=section)
        print(f"    section={section} -> {res}")

    print()
    print("=== Test 4 : numeros de comptes ===")
    for num in ["101000", "411000", "6071", "707000", "512000", "280000"]:
        res = normalizer.normalize_from_account_number(num)
        print(f"  {num} -> {res}")

    print()
    print("=== Test 5 : parse montants ===")
    for t in ["250 000", "250 000,00", "-1 234", "(1 234)", "45.50", "N/A"]:
        print(f"  {t!r} -> {normalizer.parse_amount(t)}")
