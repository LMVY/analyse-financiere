"""Parser Excel/CSV pour bilans et comptes de resultat.

Supporte :
- .xlsx, .xls (Excel)
- .csv (CSV standard)

Detecte automatiquement la structure et mappe vers les codes standards.
"""
import re
import pandas as pd
from pathlib import Path


# Dictionnaire de mapping libelle -> code standard
# (reutilise le referentiel PCG)
MAPPING_LIBELLES = {
    # ACTIF
    "immobilisations incorporelles": "immobilisations_incorporelles",
    "immob incorporelles": "immobilisations_incorporelles",
    "fonds commercial": "fonds_commercial",
    "immobilisations corporelles": "immobilisations_corporelles",
    "immob corporelles": "immobilisations_corporelles",
    "terrains": "terrains",
    "constructions": "constructions",
    "installations techniques": "installations_techniques",
    "materiel et outillage": "installations_techniques",
    "autres immobilisations corporelles": "autres_immobilisations_corporelles",
    "immobilisations financieres": "immobilisations_financieres",
    "participations": "participations",
    "stocks": "stocks_marchandises",
    "stocks et en-cours": "total_stocks",
    "creances clients": "creances_clients",
    "clients": "creances_clients",
    "autres creances": "autres_creances",
    "disponibilites": "disponibilites",
    "banque": "disponibilites",
    "tresorerie": "disponibilites",
    "valeurs mobilieres": "valeurs_mobilieres_placement",
    "charges constatees d'avance": "charges_constatees_avance",
    "total actif": "total_actif",
    "actif immobilise": "actif_immobilise",
    "actif circulant": "total_actif_circulant",

    # PASSIF
    "capital social": "capital_social",
    "primes": "primes_emission",
    "reserve legale": "reserve_legale",
    "reserves": "autres_reserves",
    "report a nouveau": "report_a_nouveau",
    "resultat de l'exercice": "resultat_exercice",
    "total capitaux propres": "total_capitaux_propres",
    "capitaux propres": "total_capitaux_propres",
    "provisions pour risques": "provisions_risques",
    "provisions pour charges": "provisions_charges",
    "emprunts": "dettes_financieres",
    "emprunts et dettes": "dettes_financieres",
    "dettes financieres": "dettes_financieres",
    "dettes fournisseurs": "dettes_fournisseurs",
    "fournisseurs": "dettes_fournisseurs",
    "dettes fiscales et sociales": "dettes_fiscales_sociales",
    "dettes fiscales": "dettes_fiscales_sociales",
    "autres dettes": "autres_dettes",
    "produits constates d'avance": "produits_constates_avance",
    "total dettes": "total_dettes",
    "total passif": "total_passif",

    # COMPTE DE RESULTAT
    "chiffre d'affaires": "chiffre_affaires",
    "ventes de marchandises": "ventes_marchandises",
    "production vendue": "production_vendue_services",
    "achats de marchandises": "achats_marchandises",
    "achats de matieres": "achats_matieres",
    "autres achats": "autres_achats_charges_externes",
    "charges externes": "autres_achats_charges_externes",
    "impots et taxes": "impots_taxes",
    "salaires": "salaires_traitements",
    "charges sociales": "charges_sociales",
    "charges de personnel": "charges_personnel",
    "dotations aux amortissements": "dotations_amortissements_immob",
    "dotations": "dotations_amortissements_immob",
    "resultat d'exploitation": "resultat_exploitation",
    "resultat financier": "resultat_financier",
    "resultat courant": "resultat_courant",
    "resultat exceptionnel": "resultat_exceptionnel",
    "impots sur les benefices": "impots_benefices",
    "resultat net": "resultat_net",
    "total produits": "total_produits",
    "total charges": "total_charges",
}


def normalize_text(t):
    """Normalise un libelle : minuscules, sans accents, sans ponctuation."""
    if not t or pd.isna(t):
        return ""
    import unicodedata
    t = unicodedata.normalize("NFD", str(t))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def find_code_std(libelle):
    """Trouve le code standard correspondant a un libelle."""
    norm = normalize_text(libelle)
    if not norm:
        return None

    # Recherche exacte
    if norm in MAPPING_LIBELLES:
        return MAPPING_LIBELLES[norm]

    # Recherche partielle
    for key, code in MAPPING_LIBELLES.items():
        if key in norm or norm in key:
            return code

    return None


def parse_montant(val):
    """Parse une valeur numerique."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = str(val).strip()
    if not cleaned:
        return None
    negatif = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    cleaned = cleaned.replace(" ", "").replace("\u202f", "")
    cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned or cleaned in "-." or cleaned == ".":
        return None
    try:
        v = float(cleaned)
        return -v if negatif else v
    except ValueError:
        return None


def read_file(file_path):
    """Lit un fichier Excel ou CSV."""
    p = Path(file_path)
    ext = p.suffix.lower()

    if ext in [".xlsx", ".xls"]:
        # Excel : lire toutes les feuilles
        try:
            return pd.read_excel(p, sheet_name=None, header=None)
        except Exception as e:
            print(f"  Erreur Excel : {e}")
            return {}
    elif ext == ".csv":
        # CSV : essayer plusieurs separateurs
        for sep in [";", ",", "\t", "|"]:
            try:
                df = pd.read_csv(p, sep=sep, header=None, encoding="utf-8")
                if df.shape[1] > 1:
                    return {"csv": df}
            except Exception:
                continue
        try:
            df = pd.read_csv(p, header=None, encoding="latin1")
            return {"csv": df}
        except Exception as e:
            print(f"  Erreur CSV : {e}")
            return {}
    return {}


def detect_section(libelle):
    """Detecte la section a partir du libelle."""
    norm = normalize_text(libelle)
    if not norm:
        return None
    if "total passif" in norm or "capitaux propres" in norm or "dettes" in norm:
        return "passif"
    if "chiffre d'affaires" in norm or "resultat" in norm or "charges" in norm:
        return "compte_resultat"
    if "actif" in norm or "immobilisations" in norm or "stocks" in norm:
        return "actif"
    return None


def extract_excel_values(file_path):
    """Extrait les valeurs d'un fichier Excel/CSV.

    Returns:
        {"actif": {...}, "passif": {...}, "compte_resultat": {...}}
    """
    result = {"actif": {}, "passif": {}, "compte_resultat": {}}

    sheets = read_file(file_path)
    if not sheets:
        return result

    for sheet_name, df in sheets.items():
        if df is None or df.empty:
            continue

        # Detecter la ligne d'en-tete (contient Brut, Amort, Net, etc.)
        header_idx = None
        col_net = None
        col_net_n1 = None
        col_libelle = None

        for idx, row in df.iterrows():
            row_norm = [normalize_text(c) for c in row]
            has_brut = any("brut" in c for c in row_norm)
            has_net = any("net" in c for c in row_norm)
            has_amort = any("amort" in c or "deprec" in c for c in row_norm)

            if has_net and (has_brut or has_amort):
                header_idx = idx
                for j, cell in enumerate(row_norm):
                    if "net" in cell and "n 1" not in cell and "n-1" not in cell:
                        if col_net is None:
                            col_net = j
                    elif "net" in cell and ("n 1" in cell or "n-1" in cell):
                        col_net_n1 = j
                    elif "libelle" in cell or "poste" in cell or "rubrique" in cell:
                        col_libelle = j
                break

        # Fallback si pas d'en-tete detecte
        if col_net is None:
            col_net = 3  # 4e colonne par defaut
        if col_libelle is None:
            col_libelle = 0

        # Parcourir les lignes apres l'en-tete
        start_idx = (header_idx + 1) if header_idx is not None else 0

        for idx in range(start_idx, len(df)):
            row = df.iloc[idx]

            libelle = row.iloc[col_libelle] if col_libelle < len(row) else None
            if not isinstance(libelle, str) or len(libelle) < 3:
                continue

            code_std = find_code_std(libelle)
            if not code_std:
                continue

            # Prendre la valeur de la colonne Net
            val = None
            if col_net < len(row):
                val = parse_montant(row.iloc[col_net])

            if val is not None and code_std not in result["actif"] and code_std not in result["passif"] and code_std not in result["compte_resultat"]:
                section = detect_section(libelle) or "actif"
                result[section][code_std] = val

                # Net N-1
                if col_net_n1 is not None and col_net_n1 < len(row):
                    val_n1 = parse_montant(row.iloc[col_net_n1])
                    if val_n1 is not None:
                        result[section][code_std + "_n1"] = val_n1

    return result


def detect_excel_format(file_path):
    """Verifie si le fichier est Excel ou CSV."""
    p = Path(file_path)
    return p.suffix.lower() in [".xlsx", ".xls", ".csv"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.excel_parser fichier.xlsx")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"=== {file_path} ===")
    print(f"Format Excel/CSV : {detect_excel_format(file_path)}")
    print()

    data = extract_excel_values(file_path)

    for section in ["actif", "passif", "compte_resultat"]:
        print(f"--- {section.upper()} ({len(data[section])} postes) ---")
        for code, val in sorted(data[section].items()):
            if val:
                print(f"  {code:40s} : {val:>15,.0f}")
        print()
