"""Parse le Markdown Mistral OCR -> dict comptable standard.

Toutes les données de mapping viennent de config/pcg_referentiel.yaml :
- codes_dgfip : codes officiels DGFiP par section
- actif/passif/compte_resultat : libellés français -> code standard
"""
import re
import unicodedata
from pathlib import Path
import yaml


YAML_PATH = Path(__file__).parent.parent.parent / "config" / "pcg_referentiel.yaml"


def _charger_referentiel():
    """Charge les codes DGFiP et les libellés depuis le YAML."""
    with open(YAML_PATH, encoding="utf-8") as f:
        ref = yaml.safe_load(f)

    codes = ref.get("codes_dgfip", {
        "actif": {}, "passif": {}, "compte_resultat": {}
    })

    # Inverser les libellés : {code_std: [libellés]} -> {libellé: code_std}
    libelles = {}
    for section in ["actif", "passif", "compte_resultat"]:
        for code_std, variantes in ref.get(section, {}).items():
            for lib in variantes:
                libelles[lib.lower()] = code_std

    return codes, libelles


CODES, LIBELLES = _charger_referentiel()


# ============================================================
# Helpers
# ============================================================
def _normalize(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFD", str(t))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _parse_montant(txt):
    if not txt:
        return None
    c = txt.strip().replace("\u202f", "").replace(" ", "")
    negatif = c.startswith("(") and c.endswith(")")
    c = c.strip("()").replace(",", ".")
    c = re.sub(r"[^\d.\-]", "", c)
    if not c or c in "-." or c == ".":
        return None
    try:
        v = float(c)
        return -v if negatif else v
    except ValueError:
        return None


def _detecter_section(ligne):
    """Titre de section -> 'actif', 'passif', 'compte_resultat' ou None."""
    norm = _normalize(ligne)
    if not norm or len(norm) > 80:
        return None
    if any(k in norm for k in ["compte de resultat", "compte de resultats",
                                "produits et charges"]):
        return "compte_resultat"
    if "passif" in norm:
        return "passif"
    if "actif" in norm and "immobilise" not in norm and "circulant" not in norm:
        return "actif"
    return None


def _chercher_code(ligne, section):
    """Cherche un code DGFiP ou un libellé DANS la section courante."""
    codes_section = CODES.get(section, {})

    # 1) Code DGFiP
    for code, std in codes_section.items():
        if re.search(rf"\b{code}\b", ligne):
            return std

    # 2) Libellé (plus long d'abord pour éviter les matchs partiels)
    norm = _normalize(ligne)
    for lib, std in sorted(LIBELLES.items(), key=lambda x: -len(x[0])):
        if lib in norm:
            return std
    return None


def _extraire_montants(ligne):
    """Montants >= 100. Passe 1 (décimales) puis passe 2 (entiers)."""
    montants = []
    for m in re.finditer(r"\(?[-+]?[\d\s.]*\d+[.,]\d{2}\)?", ligne):
        v = _parse_montant(m.group())
        if v is not None and abs(v) >= 100:
            montants.append(v)
    if not montants:
        for m in re.finditer(r"\b\d{3,}(?:\s\d{3})*\b", ligne):
            try:
                v = float(m.group().replace(" ", ""))
                if abs(v) >= 100:
                    montants.append(v)
            except ValueError:
                pass
    return montants


# ============================================================
# Fonction principale
# ============================================================
def extraire_depuis_markdown(pages: list) -> dict:
    """Parse les pages Markdown Mistral -> dict comptable standard.

    Args:
        pages: [{"index": int, "markdown": str}, ...]

    Returns:
        {"actif": {...}, "passif": {...}, "compte_resultat": {...}}
    """
    result = {"actif": {}, "passif": {}, "compte_resultat": {}}
    section = None

    for page in pages:
        for ligne in page["markdown"].split("\n"):
            ligne = ligne.strip()
            if not ligne:
                continue

            nouvelle = _detecter_section(ligne)
            if nouvelle:
                section = nouvelle
                continue

            if section is None:
                continue

            code_std = _chercher_code(ligne, section)
            if not code_std or code_std in result[section]:
                continue

            montants = _extraire_montants(ligne)
            if not montants:
                continue

            # Actif : Net = avant-dernier si >= 3 valeurs
            if section == "actif" and len(montants) >= 3:
                result[section][code_std] = montants[-2] if len(montants) >= 4 else montants[2]
            elif section == "actif" and len(montants) == 2:
                result[section][code_std] = montants[1]
            else:
                result[section][code_std] = montants[0]

            # N-1
            if section == "actif" and len(montants) >= 4:
                result[section][code_std + "_n1"] = montants[-1]
            elif section != "actif" and len(montants) >= 2:
                result[section][code_std + "_n1"] = montants[1]

    # Calcul dérivé
    if "total_immobilisations_brutes" in result["actif"]:
        result["actif"]["actif_immobilise"] = (
            result["actif"]["total_immobilisations_brutes"]
            - result["actif"].get("amortissements_immobilisations", 0)
        )

    return result


# ============================================================
# Test unitaire
# ============================================================
if __name__ == "__main__":
    print("=== CODES CHARGÉS DEPUIS LE YAML ===")
    print(f"  Actif          : {len(CODES.get('actif', {}))} codes")
    print(f"  Passif         : {len(CODES.get('passif', {}))} codes")
    print(f"  Compte résultat: {len(CODES.get('compte_resultat', {}))} codes")
    print(f"  Libellés total : {len(LIBELLES)}")

    test = [{"index": 0, "markdown": """
# BILAN ACTIF
Constructions  AP  1 243 780,00  167 838,00  1 075 941,00  1 112 741,00
TOTAL (I)  BJ  7 137 009,00  5 103 050,00  2 033 958,00  2 157 245,00

# BILAN PASSIF
Capital social  DA  1 003 454,00  947 808,00
Résultat de l'exercice  DI  85 537,00  243 883,00
TOTAL GÉNÉRAL  EE  8 255 399,00  8 307 752,00

# COMPTE DE RÉSULTAT
Chiffre d'affaires  FJ  6 895 839,00  7 431 476,00
Résultat net  HN  85 537,00  243 883,00
"""}]
    data = extraire_depuis_markdown(test)
    print("\n=== RESULTAT TEST UNITAIRE ===")
    for sec in ["actif", "passif", "compte_resultat"]:
        print(f"\n{sec.upper()}")
        for k, v in sorted(data[sec].items()):
            print(f"  {k:40s} : {v:>15,.0f}")
