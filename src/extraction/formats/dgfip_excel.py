"""Parser DGFiP Excel : lit les liasses fiscales au format Excel.

Structure reconnue :
- Feuille "Actif"      -> codes AA, AB, AF, BJ, BX...
- Feuille "Passif"     -> codes DA, DD, DI, DX, EE...
- Feuille "Compte de résultat" -> codes FJ, GG, HN...

Le Net est l'avant-dernière valeur de la ligne.
"""
from pathlib import Path


# Codes DGFiP (repris de dgfip_pdf.py)
from src.extraction.formats.dgfip_pdf import CODES_DGFIP


# ============================================================

def detect_dgfip_excel(file_path):
    """Détecte si un Excel est une liasse fiscale DGFiP."""
    p = Path(file_path)
    if p.suffix.lower() not in [".xlsx", ".xlsm", ".xls"]:
        return False

    try:
        from python_calamine import CalamineWorkbook
    except ImportError:
        return False

    try:
        wb = CalamineWorkbook.from_path(str(p))
        sheet_names = [s.lower() for s in wb.sheet_names]
        has_actif = any("actif" in s and "passif" not in s for s in sheet_names)
        has_passif = any("passif" in s for s in sheet_names)
        return has_actif and has_passif
    except Exception:
        return False


def extract_dgfip_values_from_excel(file_path):
    """Extrait les valeurs DGFiP d'un Excel (liasse fiscale).

    Reconnait les feuilles 'Actif', 'Passif', 'Compte de résultat'
    et cherche les codes DGFiP (AA, AB, AF, DX, EE...).

    Structure :
    - ACTIF  : colonne code (Brut) + valeur, puis colonne code (Amort) + valeur.
               Le Net et Net N-1 sont les 2 dernieres valeurs de la ligne.
    - PASSIF : code + valeur N + valeur N-1
    - CR     : code + valeur N + valeur N-1
    """
    from python_calamine import CalamineWorkbook

    result = {"actif": {}, "passif": {}, "compte_resultat": {}}

    try:
        wb = CalamineWorkbook.from_path(str(file_path))
    except Exception as e:
        print(f"  Erreur ouverture Excel : {e}")
        return result

    for sheet_name in wb.sheet_names:
        sheet_lower = sheet_name.lower()

        # Determiner la section
        if "actif" in sheet_lower and "passif" not in sheet_lower and "amort" not in sheet_lower and "immo" not in sheet_lower and "provision" not in sheet_lower and "creance" not in sheet_lower:
            section = "actif"
        elif "passif" in sheet_lower:
            section = "passif"
        elif "compte de r" in sheet_lower:
            section = "compte_resultat"
        else:
            continue

        try:
            rows = wb.get_sheet_by_name(sheet_name).to_python()
        except Exception as e:
            print(f"  Erreur lecture feuille '{sheet_name}' : {e}")
            continue

        for row in rows:
            if not row:
                continue

            # Parcourir la ligne pour trouver les codes DGFiP
            for idx, cell in enumerate(row):
                if not isinstance(cell, str):
                    continue
                code = cell.strip()
                if code not in CODES_DGFIP:
                    continue

                code_std = CODES_DGFIP[code]

                if section == "actif":
                    # Le Net est l'avant-derniere valeur de la ligne
                    if len(row) >= 2 and isinstance(row[-2], (int, float)):
                        if code_std not in result["actif"]:
                            result["actif"][code_std] = float(row[-2])
                            if isinstance(row[-1], (int, float)):
                                result["actif"][code_std + "_n1"] = float(row[-1])
                else:
                    # Passif / CR : les valeurs sont juste apres le code
                    montants = []
                    for j in range(idx + 1, min(idx + 6, len(row))):
                        val = row[j]
                        if isinstance(val, str) and val.strip() in CODES_DGFIP:
                            break
                        if isinstance(val, (int, float)):
                            montants.append(float(val))

                    if montants and code_std not in result[section]:
                        result[section][code_std] = montants[0]
                        if len(montants) >= 2:
                            result[section][code_std + "_n1"] = montants[1]

    # === CALCULS DERIVES ===
    actif = result["actif"]

    if "total_immobilisations_brutes" in actif:
        brut = actif["total_immobilisations_brutes"]
        actif["actif_immobilise"] = brut

    if "stocks_marchandises" in actif:
        actif["total_stocks"] = actif["stocks_marchandises"]

    if "creances_clients" in actif or "autres_creances" in actif:
        creances = actif.get("creances_clients", 0) + actif.get("autres_creances", 0)
        actif["total_creances"] = creances

    return result


