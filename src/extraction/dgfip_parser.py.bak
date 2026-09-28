"""Parser DGFiP : recolle les montants coupes en plusieurs mots."""
import re
from pathlib import Path
import pdfplumber


CODES_DGFIP = {
    "DA": "capital_social", "DB": "primes_emission", "DD": "reserve_legale",
    "DG": "autres_reserves", "DH": "report_a_nouveau", "DI": "resultat_exercice",
    "DK": "provisions_reglementees", "DL": "total_capitaux_propres",
    "DP": "provisions_risques", "DQ": "provisions_charges",
    "DS": "emprunts_obligataires", "DU": "dettes_financieres",
    "DV": "emprunts_dettes_financieres_divers", "DX": "dettes_fournisseurs",
    "DY": "dettes_fiscales_sociales", "DZ": "dettes_immobilisations",
    "EA": "autres_dettes", "EB": "produits_constates_avance",
    "EC": "total_dettes", "EE": "total_passif",
    "AB": "frais_etablissement", "AF": "immobilisations_incorporelles",
    "AH": "fonds_commercial", "AJ": "autres_immobilisations_incorporelles",
    "AP": "constructions", "AR": "installations_techniques",
    "AT": "autres_immobilisations_corporelles",
    "BJ": "total_immobilisations_brutes", "CU": "participations",
    "BD": "autres_titres_immobilises", "BH": "autres_immobilisations_financieres",
    "BT": "stocks_marchandises", "BX": "creances_clients",
    "BZ": "autres_creances", "CD": "valeurs_mobilieres_placement",
    "CF": "disponibilites", "CH": "charges_constatees_avance",
    "CJ": "total_actif_circulant", "CO": "total_actif",
    "FA": "ventes_marchandises", "FG": "production_vendue_services",
    "FJ": "chiffre_affaires", "FO": "subventions_exploitation",
    "FP": "reprises_amortissements", "FQ": "autres_produits",
    "FR": "total_produits_exploitation", "FS": "achats_marchandises",
    "FT": "variation_stocks_marchandises", "FU": "achats_matieres",
    "FW": "autres_achats_charges_externes", "FX": "impots_taxes",
    "FY": "salaires_traitements", "FZ": "charges_sociales",
    "GA": "dotations_amortissements_immob", "GB": "dotations_depreciations_immob",
    "GC": "dotations_depreciations_actif_circulant",
    "GD": "dotations_provisions_risques", "GE": "autres_charges",
    "GF": "total_charges_exploitation", "GG": "resultat_exploitation",
    "GJ": "produits_participations", "GL": "autres_interets_produits",
    "GM": "reprises_provisions_financieres", "GP": "total_produits_financiers",
    "GQ": "dotations_amortissements_financiers", "GR": "interets_charges_assimilees",
    "GU": "total_charges_financieres", "GV": "resultat_financier",
    "GW": "resultat_courant", "HA": "produits_exceptionnels_gestion",
    "HB": "produits_exceptionnels_capital", "HC": "reprises_provisions_exceptionnelles",
    "HD": "total_produits_exceptionnels", "HE": "charges_exceptionnelles_gestion",
    "HF": "charges_exceptionnelles_capital", "HG": "dotations_exceptionnelles",
    "HH": "total_charges_exceptionnelles", "HI": "resultat_exceptionnel",
    "HJ": "participation_salaries", "HK": "impots_benefices",
    "HL": "total_produits", "HM": "total_charges", "HN": "resultat_net",
}

SECTION_CODES = {
    "actif": ["AB","AF","AH","AJ","AP","AR","AT","BJ","CU","BD","BH","BT","BX","BZ","CD","CF","CH","CJ","CO"],
    "passif": ["DA","DB","DD","DG","DH","DI","DK","DL","DP","DQ","DS","DU","DV","DX","DY","DZ","EA","EB","EC","EE"],
    "compte_resultat": ["FA","FG","FJ","FO","FP","FQ","FR","FS","FT","FU","FW","FX","FY","FZ","GA","GB","GC","GD","GE","GF","GG","GJ","GL","GM","GP","GQ","GR","GU","GV","GW","HA","HB","HC","HD","HE","HF","HG","HH","HI","HJ","HK","HL","HM","HN"],
}


def group_words_into_cells(words, line_tolerance=3, cell_gap=15):
    """Groupe les mots en lignes, puis en cellules."""
    if not words:
        return []

    # Grouper par Y
    lines = {}
    for w in words:
        y_key = round(w["top"] / line_tolerance) * line_tolerance
        lines.setdefault(y_key, []).append(w)

    result = []
    for y in sorted(lines.keys()):
        line_words = sorted(lines[y], key=lambda w: w["x0"])

        cells = []
        current = [line_words[0]["text"]]
        last_x_end = line_words[0]["x1"]

        for w in line_words[1:]:
            gap = w["x0"] - last_x_end
            if gap > cell_gap:
                cells.append(" ".join(current))
                current = [w["text"]]
            else:
                current.append(w["text"])
            last_x_end = w["x1"]

        cells.append(" ".join(current))
        result.append((y, cells))

    return result


def parse_montant(texte):
    if not texte:
        return None
    # Recolle les morceaux : "217 913 443,63" -> 217913443.63
    cleaned = texte.strip().replace("\u202f", "")
    # Detecter les nombres negatifs entre parentheses
    negatif = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    # Enlever les espaces (separateurs de milliers)
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned or cleaned in "-." or cleaned == ".":
        return None
    try:
        val = float(cleaned)
        return -val if negatif else val
    except ValueError:
        return None


def extract_dgfip_values(pdf_path):
    p = Path(pdf_path)
    if not p.exists():
        return {"actif": {}, "passif": {}, "compte_resultat": {}}

    result = {"actif": {}, "passif": {}, "compte_resultat": {}}

    with pdfplumber.open(p) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue

            # Verifier que la page contient des codes DGFiP
            texts = [w["text"] for w in words]
            if sum(1 for c in CODES_DGFIP if c in texts) < 3:
                continue

            # Grouper en cellules
            lignes = group_words_into_cells(words)

            # Traiter chaque ligne
            for y, cells in lignes:
                # Chercher un code DGFiP dans les cellules
                for i, cell in enumerate(cells):
                    code = cell.strip()
                    if code in CODES_DGFIP:
                        # Les cellules suivantes contiennent les montants
                        montants = []
                        for j in range(i + 1, min(i + 5, len(cells))):
                            val = parse_montant(cells[j])
                            if val is not None and abs(val) >= 100:
                                montants.append(val)
                            if len(montants) >= 2:
                                break

                        if montants:
                            code_std = CODES_DGFIP[code]
                            section = None
                            for s, codes in SECTION_CODES.items():
                                if code in codes:
                                    section = s
                                    break
                            if section:
                                result[section][code_std] = montants[0]
                                if len(montants) >= 2:
                                    result[section][code_std + "_n1"] = montants[1]
                        break

    return result


def detect_dgfip_format(pdf_path):
    p = Path(pdf_path)
    if not p.exists():
        return False
    try:
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages[:15]:
                words = page.extract_words()
                texts = [w["text"] for w in words]
                if sum(1 for c in CODES_DGFIP if c in texts) >= 3:
                    return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/sogeca_2024.pdf"

    print(f"=== {pdf_path} ===")
    data = extract_dgfip_values(pdf_path)

    for section in ["actif", "passif", "compte_resultat"]:
        print(f"--- {section.upper()} ({len(data[section])} postes) ---")
        for code, val in sorted(data[section].items()):
            if val:
                print(f"  {code:40s} : {val:>15,.0f}")
        print()
