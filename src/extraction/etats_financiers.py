"""Parser unifie : extrait et structure les postes comptables d'un PDF.

Regle metier : les 2 dernieres valeurs sont toujours Net N et Net N-1.
"""
from pathlib import Path
from typing import Optional

from src.extraction.outils.pdfplumber_tools import PDFPlumberExtractor
from src.analysis.pcg_normalizer import PCGNormalizer, normalize_text
from src.extraction.formats.dgfip_pdf import (
    extract_dgfip_values, detect_dgfip_format,
)
from src.extraction.formats.dgfip_excel import (
    extract_dgfip_values_from_excel, detect_dgfip_excel,
)
from src.extraction.formats.excel_normal import extract_excel_values, detect_excel_format
from src.extraction.formats.fec import extract_fec_values, detect_fec_format
from src.analysis.selector import ColumnSelector
import pdfplumber



# Titres de section a ignorer (ce ne sont pas des postes comptables)
# Codes agrégés : NE PAS sommer (évite les doublons total_* sur PDF récapitulatif)
CODES_AGREGES = {
    "total_actif", "total_passif", "total_capitaux_propres", "actif_immobilise",
    "total_dettes", "chiffre_affaires", "resultat_net", "total_stocks",
    "total_creances", "total_immobilisations_brutes", "resultat_exploitation",
    "total_produits", "total_charges",
}

STOPWORDS = [
    "dettes",
    "creances",
    "immobilisations",
    "capitaux propres",
    "capitaux",
    "provisions",
    "stocks",
    "actif circulant",
    "passif circulant",
    "comptes de regularisation",
    "total",
    "totaux",
    "bilan",
    "compte de resultat",
]

SECTION_KEYWORDS = {
    "actif": ["bilan actif", "actif", "actif immobilise"],
    "passif": ["bilan passif", "passif", "capitaux propres"],
    "compte_resultat": ["compte de resultat", "compte de resultats", "compte de produits et charges"],
}


class BilanParser:
    """Parse un PDF de bilan et retourne un dict structure."""

    def __init__(self, pdf_path: str, referentiel_path: str = None):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF non trouve : {pdf_path}")
        self.normalizer = PCGNormalizer(referentiel_path)
        self._last_type = None  # 'native' | 'scanned' — mémorisé pour éviter double OCR

    def _detect_type(self) -> str:
        """Detecte si le PDF est natif, scanne, ou mixte."""
        with pdfplumber.open(self.pdf_path) as pdf:
            pages_texte = 0
            pages_image = 0
            for page in pdf.pages:
                chars = len(page.chars)
                # Une vraie page comptable contient beaucoup de texte (>= 500 char).
                # En dessous, on considère que c'est une image (scan).
                if chars >= 500:
                    pages_texte += 1
                else:
                    pages_image += 1

            # Bascule agressive : dès qu'il y a autant d'images que de texte, on OCR
            if pages_image >= pages_texte and pages_image > 0:
                return "scanned"
            return "native"

    def parse(self, force_ocr: bool = False, dpi: int = 300) -> dict:
        print("Extraction du texte...")
        pdf_type = "scanned" if force_ocr else self._detect_type()
        print(f"  Type : {pdf_type}")
        print()

        self._last_type = pdf_type  # mémoriser pour parse_simple

        self._last_type = pdf_type

        if pdf_type == "native":
            extractor = PDFPlumberExtractor(self.pdf_path)
            rows = extractor.extract_rows()
        else:
            # PDF scanne : pas d'OCR. On retourne un resultat vide propre.
            print("  ⚠️  PDF scanne (image) : OCR desactive")
            print("     → Veuillez fournir le PDF natif ou l'Excel DGFiP")
            return {"actif": {}, "passif": {}, "compte_resultat": {}}

        print(f"  {len(rows)} lignes extraites")
        print()

        print("Parsing des postes...")
        data = self._parse_rows(rows)

        total = sum(len(data[s]) for s in data)
        print(f"  Actif : {len(data['actif'])} postes")
        print(f"  Passif : {len(data['passif'])} postes")
        print(f"  Compte de resultat : {len(data['compte_resultat'])} postes")
        print(f"  TOTAL : {total} postes extraits")

        return data

    def parse_simple(self, force_ocr: bool = False, dpi: int = 300) -> dict:
        """Parse et retourne les valeurs par poste.

        Detecte automatiquement le format :
        - DGFiP (liasse fiscale) -> dgfip_parser
        - Standard -> pdfplumber/OCR
        """
        # 1. Verifier le format
        path_str = str(self.pdf_path)

        # FEC ?
        if detect_fec_format(path_str):
            print("  Format FEC detecte -> parser FEC")
            fec_data = extract_fec_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in fec_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # Excel/CSV ?
        if detect_excel_format(path_str):
            # Verifier si c'est une liasse fiscale DGFiP au format Excel
            if detect_dgfip_excel(path_str):
                print("  Format DGFiP Excel detecte -> parser DGFiP Excel")
                excel_data = extract_dgfip_values_from_excel(path_str)
            else:
                print("  Format Excel/CSV detecte -> parser Excel")
                excel_data = extract_excel_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in excel_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # DGFiP ?
        if detect_dgfip_format(path_str):
            print("  Format DGFiP detecte -> parser DGFiP")
            dgfip_data = extract_dgfip_values(path_str)
            result = {}
            for section in ["actif", "passif", "compte_resultat"]:
                result[section] = {
                    k: v for k, v in dgfip_data.get(section, {}).items()
                    if not k.endswith("_n1")
                }
            return result

        # 2. Sinon, parser classique
        data = self.parse(force_ocr=force_ocr, dpi=dpi)
        result = {}
        for section in ["actif", "passif", "compte_resultat"]:
            selector = ColumnSelector(section)
            result[section] = selector.select_all(data[section])

        # 3. RETRY avec OCR si on a trop peu de postes (seuil relatif ~40% d'un attendu moyen)
        total_postes = sum(len(result[s]) for s in result)
        seuil_retry = 25  # Forcer l'OCR plus souvent si extraction native pauvre
        if total_postes < seuil_retry and not force_ocr and self._last_type != "scanned":
            print(f"  Seulement {total_postes} postes extraits → retry avec OCR")
            data_ocr = self.parse(force_ocr=True, dpi=dpi)
            result_ocr = {}
            for section in ["actif", "passif", "compte_resultat"]:
                selector = ColumnSelector(section)
                result_ocr[section] = selector.select_all(data_ocr[section])
            total_ocr = sum(len(result_ocr[s]) for s in result_ocr)
            if total_ocr > total_postes:
                print(f"  OCR meilleur : {total_ocr} postes")
                return self._sanity_filter(result_ocr)

        return self._sanity_filter(result)

    def _sanity_filter(self, result: dict) -> dict:
        """Désactivé : le filtre détruisait des données valides.
        On garde la signature pour compatibilité."""
        return result

    def _parse_rows(self, rows: list) -> dict:
        result = {"actif": {}, "passif": {}, "compte_resultat": {}}
        section_courante = None

        for row in rows:
            if not row:
                continue

            ligne = " ".join([c[0] if isinstance(c, tuple) else c for c in row]).strip()
            if not ligne:
                continue

            nouvelle = self._detect_section(ligne)
            if nouvelle:
                section_courante = nouvelle
                continue

            if section_courante is None:
                # OCR : section manquante -> deviner par mots-clés
                libelle_norm = normalize_text(ligne)
                if any(k in libelle_norm for k in
                       ["capital", "reserve", "report a nouveau", "resultat",
                        "provisions reglementees", "subventions d'investissement",
                        "total capitaux propres", "dettes fournisseurs",
                        "dettes fiscales", "emprunts", "total dettes"]):
                    section_courante = "passif"
                elif any(k in libelle_norm for k in
                         ["immobilisations", "stocks", "creances", "clients",
                          "disponibilites", "total actif", "vmp", "banque",
                          "constructions", "terrains", "materiel"]):
                    section_courante = "actif"
                elif any(k in libelle_norm for k in
                         ["chiffre d'affaires", "ventes", "achats", "charges",
                          "produits", "dotations", "resultat d'exploitation",
                          "resultat net", "interets"]):
                    section_courante = "compte_resultat"

            if section_courante is None:
                continue

            if self._should_skip(row):
                continue

            parsed = self._parse_row_comptable(row, section_courante)
            if not parsed:
                continue

            libelle, montants = parsed

            code_std = self.normalizer.normalize_label(
                libelle, section_hint=section_courante, seuil=90.0
            )

            if code_std:
                code = code_std["code"]
                # Anti-somme : pour les totaux, garder le max en valeur absolue
                if code in result[section_courante]:
                    existing = result[section_courante][code]["montants"]
                    if code in CODES_AGREGES:
                        val_new = montants.get("net", 0)
                        val_old = existing.get("net", 0)
                        if abs(val_new) > abs(val_old):
                            result[section_courante][code]["montants"] = montants
                    else:
                        for col, val in montants.items():
                            if col in existing:
                                existing[col] += val
                            else:
                                existing[col] = val
                else:
                    result[section_courante][code] = {
                        "libelle_original": libelle,
                        "montants": montants,
                        "score": code_std["score"],
                        "methode": code_std["methode"],
                    }

        return result

    def _detect_section(self, ligne: str) -> Optional[str]:
        """Détection tolérante : gère l'OCR bruité et les en-têtes manquants."""
        norm = normalize_text(ligne)
        if not norm:
            return None
        # Trop long = probablement un paragraphe, pas un titre
        if len(norm) > 60:
            return None
        # Exclure les "total *" sauf s'ils introduisent une section
        if norm.startswith("total ") and "actif" not in norm and "passif" not in norm:
            return None

        # Compte de résultat (priorité : à tester AVANT "actif"/"passif")
        if any(k in norm for k in ["compte de resultat", "compte de resultats",
                                    "produits et charges", "produits et charge"]):
            return "compte_resultat"

        # Passif : n'importe quel "passif" isolé
        if "passif" in norm:
            return "passif"

        # Actif : "actif" seul, ou en début de titre
        if "actif" in norm and "immobilise" not in norm and "circulant" not in norm:
            return "actif"

        return None

    def _should_skip(self, row: list) -> bool:
        if len(row) < 2:
            return True

        first_cell = row[0][0] if isinstance(row[0], tuple) else row[0]
        if not first_cell.strip():
            return True

        norm = normalize_text(first_cell)
        if len(norm) <= 2 and not norm.isalpha():
            return True

        has_amount = False
        for cell in row[1:]:
            text = cell[0] if isinstance(cell, tuple) else cell
            if self.normalizer.parse_amount(text) is not None:
                has_amount = True
                break
        if not has_amount:
            return True

        # Ignorer les titres de section
        libelle_norm = normalize_text(first_cell)
        if libelle_norm in STOPWORDS:
            return True

        return False

    def _parse_row_comptable(self, row: list, section: str) -> Optional[tuple]:
        """Extrait (libelle, montants) avec la regle metier.

        REGLE : les 2 dernieres valeurs = Net N et Net N-1.
        """
        first = row[0]
        libelle = first[0] if isinstance(first, tuple) else first
        libelle = libelle.strip()
        if len(libelle) < 3:
            return None

        # Recuperer toutes les valeurs numeriques
        valeurs = []
        for cell in row[1:]:
            text = cell[0] if isinstance(cell, tuple) else cell
            val = self.normalizer.parse_amount(text)
            if val is not None and abs(val) < 1e9:
                valeurs.append(val)

        if not valeurs:
            return None

        montants_dict = {}
        n = len(valeurs)

        if section == "actif":
            # Bilan actif : Brut | Amort | Net [| Net N-1]
            if n == 1:
                montants_dict["net"] = valeurs[0]
            elif n == 2:
                montants_dict["amort"] = valeurs[0]
                montants_dict["net"] = valeurs[1]
            elif n == 3:
                montants_dict["brut"] = valeurs[0]
                montants_dict["amort"] = valeurs[1]
                montants_dict["net"] = valeurs[2]
            elif n >= 4:
                montants_dict["brut"] = valeurs[0]
                montants_dict["amort"] = valeurs[1]
                montants_dict["net"] = valeurs[2]
                montants_dict["net_n1"] = valeurs[3]
        else:
            # Bilan passif ou compte de resultat : Net [| Net N-1 | Net N-2]
            if n == 1:
                montants_dict["net"] = valeurs[0]
            elif n == 2:
                montants_dict["net"] = valeurs[0]
                montants_dict["net_n1"] = valeurs[1]
            elif n >= 3:
                montants_dict["net"] = valeurs[0]
                montants_dict["net_n1"] = valeurs[1]
                montants_dict["net_n2"] = valeurs[2]

        return libelle, montants_dict


if __name__ == "__main__":
    import sys
    import json

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/bilan_standard.pdf"

    print("=" * 60)
    print(f"PARSING : {pdf_path}")
    print("=" * 60)
    print()

    parser = BilanParser(pdf_path)
    data = parser.parse(force_ocr=True)

    print()
    print("=" * 60)
    print("RESULTAT")
    print("=" * 60)
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ============================================================
# FONCTION D'ENTREE POUR LE VALIDATEUR
# ============================================================
def extraire_fichier(chemin: str) -> dict:
    """Extrait un fichier et retourne {actif, passif, compte_resultat}.

    Point d'entree simplifie pour tester_validateur.py.
    """
    parser = BilanParser(chemin)
    return parser.parse_simple(force_ocr=False)
