"""Lecteur Excel (.xlsx / .xlsm) -> donnees comptables au format standard.

Meme contrat de sortie que mistral_docai.DocumentAIExtractor :
{"actif": {...}, "passif": {...}, "compte_resultat": {...}}
avec les cles "<poste>" (exercice N) et "<poste>_n1" (exercice N-1).

Deux familles de classeurs sont lues :
- liasse fiscale DGFiP (2051 et annexes, exports Pappers/experts...) :
  chaque ligne porte un code DGFiP (AA, AF, BJ, DL...) resolu via
  config/pcg_referentiel.yaml (section codes_dgfip) ; les colonnes de
  montants sont identifiees par profil (colonnes numeriques) et les
  en-tetes "Exercice N / N-1" parfois fusionnes sont recadres ;
- tableaux libres : libelles normalises (accents, casse, ponctuation)
  puis matches contre le referentiel.

Colonnes N / N-1 : deduites des en-tetes (annees, dates, "exercice"),
avec gestion des blocs Brut / Amortissements / Net (la colonne NET est
retenue) ; a defaut, premiers montants a droite du libelle (convention
francaise : exercice le plus recent a gauche).

Les libelles ambigus ("TOTAL GENERAL", "resultat"...) sont tranches
selon la section courante de la feuille ; les mentions "TOTAL (I)" a
"(IV)" suivent la convention fiscale ou classique selon la feuille.

detecter_documents() sert de porte avant l'analyse : elle indique si un
bilan (actif ET passif) et un compte de resultat sont presents.
"""
import difflib
import io
import re
import unicodedata
import zipfile
from pathlib import Path

import yaml
from openpyxl import load_workbook

from src.extraction.controle_extraction import (
    MIN_POSTES_CR,
    MIN_POSTES_PAR_COTE,
    SECTIONS,
)

YAML_PATH = Path(__file__).parent.parent.parent / "config" / "pcg_referentiel.yaml"

EXCEL_EXTENSIONS = (".xlsx", ".xlsm")

# Seuils ajustables
LONGUEUR_LABEL_MIN = 4           # taille mini d'un libelle pour matcher
LONGUEUR_CONTENANCE_MIN = 6      # taille mini pour le matching par contenance
LONGUEUR_FLOU_MIN = 8            # taille mini pour le rapprochement flou
SEUIL_FLOU = 0.87                # similarite mini (0-1) pour un match flou
MATCHES_FEUILLE_MIN = 2          # matches univoques pour une section presente
LIGNES_EN_TETE_MAX = 30          # zone de recherche des en-tetes d'exercices
LIGNES_META_MAX = 40             # zone de recherche SIREN / NAF / raison sociale
LIGNES_PROFIL_MAX = 300          # lignes scannees pour le profil des colonnes
COLS_SCAN_MAX = 30               # largeur de feuille scannee
DECALAGE_SNAP_MAX = 4            # decalage maxi en-tete fusionne -> colonne valeur

RE_ANNEE = re.compile(r"(?:19|20)\d{2}")
RE_SIREN = re.compile(r"\b(\d[\d ]{6,10}\d)\b")
RE_NAF = re.compile(r"\b(\d{2}\.\d{2}[ ]?[A-Z])\b")
RE_CODE_DGFIP = re.compile(r"[A-ZØ0-9]{1,3}")
RE_RENVOI = re.compile(r"-\d{1,2}")       # marqueur de renvoi DGFiP ("-4")
RE_FORME_JURIDIQUE = re.compile(
    r"\b(sas|sa|sarl|sasu|eurl|sci|snc|gie|selarl|scp|association)\b")

# Mots cles exclus de l'extraction de la raison sociale (faux positifs)
MOTS_SOCIALE_EXCLUS = ("designation", "adresse", "siren", "naf", "exercice",
                       "duree", "formulaire", "dgfip", "pappers", "fiche",
                       "raison sociale")

# ============================================================
# Ouverture tolérante des classeurs
# ============================================================
# Certains exports contiennent des styles invalides (ex. <fill/> vide dans
# xl/styles.xml) qu'openpyxl refuse de charger ("expected Fill"). Les valeurs
# des cellules sont pourtant lisibles : on repare le classeur en memoire.
FILL_VIDE = re.compile(r"<fill\s*/>|<fill>\s*</fill>")
FILL_CORRIGE = '<fill><patternFill patternType="none"/></fill>'
STYLES_MINIMAUX = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font/></fonts>'
    f'<fills count="1">{FILL_CORRIGE}</fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
    '<cellXfs count="1"><xf/></cellXfs>'
    '</styleSheet>'
)


def _reparer_zip(chemin: Path, styles: str) -> io.BytesIO:
    """Recopie le classeur en memoire en remplaçant xl/styles.xml."""
    bio = io.BytesIO()
    with zipfile.ZipFile(chemin) as zin, \
            zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/styles.xml":
                data = styles.encode("utf-8")
            zout.writestr(item, data)
    bio.seek(0)
    return bio


def _ouvrir_classeur(chemin: Path):
    """load_workbook, avec reparation des styles si openpyxl echoue."""
    try:
        return load_workbook(chemin, data_only=True, read_only=True)
    except Exception:
        pass
    try:
        with zipfile.ZipFile(chemin) as z:
            styles = z.read("xl/styles.xml").decode("utf-8", "replace")
    except Exception:
        raise
    # 1) corriger uniquement les fills vides (conserve les formats de
    #    nombres, donc la detection des dates dans les en-tetes)
    if FILL_VIDE.search(styles):
        try:
            return load_workbook(
                _reparer_zip(chemin, FILL_VIDE.sub(FILL_CORRIGE, styles)),
                data_only=True, read_only=True)
        except Exception:
            pass
    # 2) dernier recours : remplacer toute la feuille de styles (les
    #    cellules restent lisibles, mais les dates reviennent en serial)
    return load_workbook(_reparer_zip(chemin, STYLES_MINIMAUX),
                         data_only=True, read_only=True)


# ============================================================
# Utilitaires
# ============================================================
def _norm(texte) -> str:
    """Minuscules sans accents ni ponctuation, espaces collapses."""
    if not isinstance(texte, str):
        return ""
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower()
    texte = re.sub(r"[^a-z0-9]+", " ", texte)
    return texte.strip()


def _nombre(cellule):
    """Cellule -> float ou None. Accepte "1 234 567", "(1234)", "1 234,56", "1234-"."""
    if isinstance(cellule, bool) or cellule is None:
        return None
    if isinstance(cellule, (int, float)):
        return float(cellule)
    if not isinstance(cellule, str):
        return None
    s = cellule.strip()
    if not s or not re.search(r"\d", s):
        return None
    negatif = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace("\u202f", "").replace("\u00a0", " ")
    s = re.sub(r"[€$%]|EUR|eur", "", s)
    s = s.replace(" ", "")
    if s.endswith("-"):               # convention comptable "1234-"
        negatif = True
        s = s[:-1]
    if not re.fullmatch(r"-?\d+([.,]\d+)*", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):        # 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:                                  # 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        if s.count(",") == 1 and re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
            s = s.replace(",", "")              # 1,234,567 : milliers
        else:
            s = s.replace(",", ".")             # 1234,56 : virgule decimale
    elif s.count(".") > 1:
        s = s.replace(".", "")                  # 1.234.567
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if negatif else v


def _annee_cellule(cellule):
    """Cellule -> annee (int) si elle porte une annee, sinon None."""
    if isinstance(cellule, bool) or cellule is None:
        return None
    if isinstance(cellule, (int, float)):
        v = int(cellule)
        return v if 1900 <= v <= 2100 else None
    if hasattr(cellule, "year"):                # datetime
        return cellule.year
    if isinstance(cellule, str):
        m = RE_ANNEE.search(cellule)
        return int(m.group(0)) if m else None
    return None


def _est_code_dgfip(v) -> bool:
    """Cellule ressemble a un code DGFiP ('AA', '3T', 'ØC') ?"""
    if not isinstance(v, str):
        return False
    s = v.strip()
    return (bool(RE_CODE_DGFIP.fullmatch(s))
            and any(c.isalpha() for c in s))


def _plis(texte_norm: str) -> set:
    """Mots d'un libelle normalise, pluriel plie (francais : s/x finaux)."""
    return {t[:-1] if len(t) > 3 and t.endswith(("s", "x")) else t
            for t in texte_norm.split()}


def _similarite(texte: str, tok_texte: set, label: str) -> float:
    """Score de similarite (0-1) entre une cellule et un libelle du referentiel.

    Deux signaux :
    - inclusion : tous les mots du libelle (ou de la cellule) sont presents
      de l'autre cote, pluriel plie : "Reserves legales" ~ "reserve legale" ;
    - ratio de difflib : faut de frappe legere ou mots proches.
    """
    tok_label = _plis(label)
    if len(tok_label) >= 2 and (tok_label <= tok_texte or tok_texte <= tok_label):
        return 0.95
    if len(tok_texte) == 1 and len(tok_label) == 1:
        return 0.0
    return difflib.SequenceMatcher(None, texte, label).ratio()


# ============================================================
# Detection des documents (porte avant analyse)
# ============================================================
def detecter_documents(data: dict) -> dict:
    """Compte les postes du format standard et detecte la presence
    du bilan (actif ET passif) et du compte de resultat.

    Un exercice FISCAL COMPLET = bilan complet + compte de resultat
    (cle "complet" ci-dessous).

    Retour : {"bilan": bool, "compte_resultat": bool, "complet": bool,
              "nb_actif": int, "nb_passif": int, "nb_cr": int}
    """
    actif = data.get("actif") or {}
    passif = data.get("passif") or {}
    cr = data.get("compte_resultat") or {}
    nb_actif = sum(1 for k in actif if not str(k).endswith("_n1"))
    nb_passif = sum(1 for k in passif if not str(k).endswith("_n1"))
    nb_cr = sum(1 for k in cr if not str(k).endswith("_n1"))
    bilan = nb_actif >= MIN_POSTES_PAR_COTE and nb_passif >= MIN_POSTES_PAR_COTE
    compte_resultat = nb_cr >= MIN_POSTES_CR
    return {
        "bilan": bilan,
        "compte_resultat": compte_resultat,
        "complet": bilan and compte_resultat,
        "nb_actif": nb_actif,
        "nb_passif": nb_passif,
        "nb_cr": nb_cr,
    }


# ============================================================
# Lecteur Excel
# ============================================================
class ExcelParser:
    """Fichier Excel (.xlsx/.xlsm) -> format standard du pipeline."""

    def __init__(self, referentiel: dict = None):
        if referentiel is None:
            with open(YAML_PATH, encoding="utf-8") as f:
                referentiel = yaml.safe_load(f) or {}
        self._construire_lookup(referentiel)

    # ------------------------------------------------------------
    # Referentiel -> structures de matching
    # ------------------------------------------------------------
    def _construire_lookup(self, referentiel: dict):
        self.exact = {}        # label normalise -> [(section, poste), ...]
        self.contenance = []   # [(label normalise, section, poste)]
        for section in SECTIONS:
            for poste, labels in (referentiel.get(section) or {}).items():
                if not labels:
                    continue
                for lab in labels:
                    n = _norm(lab)
                    if not n:
                        continue
                    cible = (section, poste)
                    if n not in self.exact:
                        self.exact[n] = [cible]
                    elif cible not in self.exact[n]:
                        self.exact[n].append(cible)
                    if len(n) >= LONGUEUR_CONTENANCE_MIN:
                        self.contenance.append((n, section, poste))
        # libelles les plus longs d'abord : matches les plus precis gagnent
        self.contenance.sort(key=lambda e: -len(e[0]))

        # Codes DGFiP (liasse fiscale) : code -> (section, poste).
        # Ne garder que les codes dont le poste existe dans le referentiel ;
        # BK (amortissements, colonne non NET) est ecarte et BJ (total brut
        # des immobilisations) est remappe vers le total NET correspondant.
        self.codes = {}
        for section in SECTIONS:
            referentiel_section = referentiel.get(section) or {}
            for code, poste in ((referentiel.get("codes_dgfip") or {})
                                .get(section) or {}).items():
                if poste not in referentiel_section:
                    continue
                self.codes[code] = (section, poste)
        self.codes["BJ"] = ("actif", "actif_immobilise")

    def _match(self, texte_norm: str) -> list:
        """Label normalise -> liste de candidats (section, poste), vide sinon.

        Trois niveaux de rapprochement, du plus au moins strict :
        1. egalite exacte apres normalisation (accents, casse, ponctuation) ;
        2. contenance : le libelle du referentiel est contenu dans la cellule
           ("Total des immobilisations corporelles (xz)") ou l'inverse ;
        3. rapprochement flou : pluriel plie, mots supplementaires ou
           faute de frappe legere ("Instalations techniques materiel...").
           Seul le meilleur candidat est retenu ; ex aequo = ambiguite
           tranchee par la section courante de la feuille.
        """
        cands = self.exact.get(texte_norm)
        if cands:
            return list(cands)
        if len(texte_norm) < LONGUEUR_LABEL_MIN:
            return []

        trouves = []
        for n, section, poste in self.contenance:
            if n in texte_norm:
                cible = (section, poste)
                if cible not in trouves:
                    trouves.append(cible)
        if trouves:
            return trouves

        # niveau 3 : rapprochement flou (labels jamais trouves avant)
        if len(texte_norm) < LONGUEUR_FLOU_MIN:
            return []
        tok_cell = _plis(texte_norm)
        if len(tok_cell) < 2:
            return []
        meilleurs = []       # [(score, (section, poste))]
        for n, section, poste in self.contenance:
            score = _similarite(texte_norm, tok_cell, n)
            if score >= SEUIL_FLOU:
                meilleurs.append((score, (section, poste)))
        if not meilleurs:
            return []
        meilleurs.sort(key=lambda e: -e[0])
        # ex aequo proches : garder l'ambiguite pour la resolution par section
        seuil = meilleurs[0][0] - 0.02
        return [cible for score, cible in meilleurs if score >= seuil]

    # ------------------------------------------------------------
    # Profil des colonnes (pour recadrer les en-tetes fusionnes)
    # ------------------------------------------------------------
    @staticmethod
    def _profil_colonnes(lignes) -> list:
        """True par colonne : contient des montants (et pas que des codes)."""
        nb_num = [0] * COLS_SCAN_MAX
        nb_code = [0] * COLS_SCAN_MAX
        for ligne in lignes[:LIGNES_PROFIL_MAX]:
            for j, c in enumerate(ligne):
                if j >= COLS_SCAN_MAX:
                    break
                if _est_code_dgfip(c.value):
                    nb_code[j] += 1
                elif _nombre(c.value) is not None:
                    nb_num[j] += 1
        return [nb_num[j] >= 2 and nb_num[j] > nb_code[j]
                for j in range(COLS_SCAN_MAX)]

    @staticmethod
    def _snap(profil: list, col):
        """Colonne d'en-tete -> colonne de montants correspondante.

        Les en-tetes fusionnes ("Exercice N" au-dessus de code+valeur)
        laissent l'ancre sur une colonne de codes : on glisse a droite.
        """
        if col is None:
            return None
        if col < len(profil) and profil[col]:
            return col
        for j in range(col + 1, min(col + 1 + DECALAGE_SNAP_MAX, len(profil))):
            if profil[j]:
                return j
        return col

    # ------------------------------------------------------------
    # En-tetes : colonnes des exercices N et N-1
    # ------------------------------------------------------------
    @staticmethod
    def _chercher_en_tetes(ws, profil: list):
        """Cherche la ligne d'en-tete portant les exercices.

        Retourne (col_n, col_n1, annee_n, annee_n1), indices de colonnes
        dans les lignes produites par ws.iter_rows(), ou (None,)*4.
        Les annees decroissantes vers la droite placent N a gauche
        (2024 | 2023) ; croissantes le placent a droite (2023 | 2024).
        Si la colonne d'une annee porte "brut" (bilan detaille brut /
        amortissements / net), la colonne "net" correspondante est utilisee.
        """
        tete = [list(l) for l in ws.iter_rows(max_row=LIGNES_EN_TETE_MAX,
                                              max_col=COLS_SCAN_MAX)]
        # pile des textes d'en-tete par colonne (annee + brut/amort/net...)
        piles = [""] * COLS_SCAN_MAX
        for ligne in tete:
            for j, c in enumerate(ligne):
                if j >= COLS_SCAN_MAX:
                    break
                if isinstance(c.value, str) and c.value.strip():
                    piles[j] += " " + _norm(c.value)

        def _col_net(col, autres_cols):
            if "brut" not in piles[col] or "net" in piles[col]:
                return col
            limite = next((j for j in autres_cols if j > col), len(piles))
            for j in range(col + 1, limite):
                if "net" in piles[j]:
                    return j
            return col

        solution_annee = None
        solution_exercice = None
        for ligne in tete:
            if solution_annee is None:
                col_annee = {}      # annee -> colonne (derniere occurrence)
                for j, c in enumerate(ligne):
                    a = _annee_cellule(c.value)
                    if a:
                        col_annee[a] = j
                if len(col_annee) >= 2:
                    tri = sorted(col_annee, reverse=True)
                    an, an1 = tri[0], tri[1]
                    tous = sorted(col_annee.values())
                    solution_annee = (_col_net(col_annee[an], tous),
                                      _col_net(col_annee[an1], tous), an, an1)
            if solution_exercice is None:
                col_exercice = []    # colonnes "exercice" sans annee
                for j, c in enumerate(ligne):
                    if isinstance(c.value, str):
                        n = _norm(c.value)
                        if n.startswith("exercice") and "duree" not in n:
                            a = _annee_cellule(c.value)
                            if a is None:
                                col_exercice.append(j)
                if len(col_exercice) >= 2:
                    an = next(iter(col_annee)) if col_annee else None
                    autres = [j for j in col_exercice if j != col_exercice[0]]
                    j1 = (min(autres, key=lambda j: abs(j - col_exercice[0]))
                          if autres else col_exercice[1])
                    solution_exercice = (col_exercice[0], j1, an, None)
        solution = solution_annee or solution_exercice
        if solution is None:
            return None, None, None, None
        col_n, col_n1, an, an1 = solution
        return (ExcelParser._snap(profil, col_n),
                ExcelParser._snap(profil, col_n1), an, an1)

    # ------------------------------------------------------------
    # Meta : SIREN, NAF, raison sociale
    # ------------------------------------------------------------
    @staticmethod
    def _chercher_meta(ws):
        meta = {}
        candidat_sociale = None
        for ligne in ws.iter_rows(max_row=LIGNES_META_MAX, max_col=15):
            cells = [(j, c.value) for j, c in enumerate(ligne)
                     if c.value not in (None, "")]
            norms = [_norm(v) for _, v in cells]
            joined = " ".join(norms)

            # SIREN : mot-cle dans la ligne, chiffres dans la ligne
            if "siren" in joined and "siren" not in meta:
                for _, v in cells:
                    m = RE_SIREN.search(str(v))
                    if m:
                        siren = re.sub(r"\D", "", m.group(1))
                        if len(siren) == 9:
                            meta["siren"] = siren
                            break

            # Raison sociale : mot-cle ("Raison sociale", "Désignation"),
            # valeur dans la meme cellule apres ':' ou dans la cellule voisine
            if "raison_sociale" not in meta:
                for pos, (jcol, v) in enumerate(cells):
                    n = norms[pos]
                    if not (("raison sociale" in n or "designation" in n)
                            and "siren" not in n and "naf" not in n):
                        continue
                    if isinstance(v, str) and ":" in v:
                        reste = v.split(":", 1)[1].strip()
                        if reste and _norm(reste) not in MOTS_SOCIALE_EXCLUS:
                            meta["raison_sociale"] = reste
                            break
                    for k in range(pos + 1, len(cells)):
                        vk, nk = cells[k][1], norms[k]
                        if nk and not any(m in nk for m in MOTS_SOCIALE_EXCLUS):
                            meta["raison_sociale"] = str(vk).strip()
                            break
                    break

            for _, v in cells:
                if not isinstance(v, str):
                    continue
                n = _norm(v)
                m = RE_NAF.search(v)
                if m:
                    meta.setdefault("code_naf", m.group(1).replace(" ", ""))
                # raison sociale sans mot-cle : titre avec forme juridique
                if (candidat_sociale is None
                        and not any(m in n for m in MOTS_SOCIALE_EXCLUS)
                        and RE_FORME_JURIDIQUE.search(n)
                        and 3 <= len(v.strip()) <= 60):
                    candidat_sociale = v.strip()
        meta.setdefault("raison_sociale", candidat_sociale)
        return meta

    # ------------------------------------------------------------
    # Lecture d'une feuille
    # ------------------------------------------------------------
    def _lire_feuille(self, ws):
        """Une feuille -> ({section: {poste: n, ..._n1: ...}}, annee_n, annee_n1).

        Indices de colonnes = positions dans les lignes de ws.iter_rows().
        """
        lignes = [list(l) for l in ws.iter_rows(max_row=2000,
                                                max_col=COLS_SCAN_MAX)]
        profil = self._profil_colonnes(lignes)
        col_n, col_n1, annee_n, annee_n1 = self._chercher_en_tetes(ws, profil)

        # ----------------------------------------------------------
        # 1er passage : sections presentes, convention fiscale
        # ----------------------------------------------------------
        presents = {s: 0 for s in SECTIONS}
        fiscale = False
        for ligne in lignes:
            norms_ligne = []
            for c in ligne:
                if isinstance(c.value, str):
                    s = c.value.strip()
                    if s in self.codes:
                        presents[self.codes[s][0]] += 1
                    n = _norm(c.value)
                    if n:
                        norms_ligne.append(n)
            if not fiscale:
                if "total iv" in norms_ligne:
                    fiscale = True
                elif "total i" in norms_ligne and \
                        any("capital souscrit" in n for n in norms_ligne):
                    fiscale = True
        # codes specifiques au formulaire 2051 (bilan DGFiP)
        fiscale = fiscale or any(c in self.codes for c in ("BJ", "CO", "DL", "EE"))
        sections_feuille = {s for s, n in presents.items()
                            if n >= MATCHES_FEUILLE_MIN}

        # Mentions "TOTAL (n)" selon la convention de la feuille
        if fiscale:
            aliases = {
                "total i": {"actif": "capital_souscrit_non_appele",
                            "passif": "total_capitaux_propres"},
                "total ii": {"actif": "actif_immobilise",
                             "passif": "total_autres_fonds_propres"},
                "total iii": {"actif": "total_actif_circulant",
                              "passif": "total_provisions"},
                "total iv": {"passif": "total_dettes"},
            }
        else:
            aliases = {
                "total i": {"actif": "actif_immobilise",
                            "passif": "total_capitaux_propres"},
                "total ii": {"actif": "total_actif_circulant",
                             "passif": "total_dettes"},
            }

        donnees = {s: {} for s in SECTIONS}
        cote = None       # section courante, pour trancher les libelles ambigus

        for ligne in lignes:
            # lignes de renvoi DGFiP (detail "dont", marquees -n, n petit) :
            # jamais de valeur primaire, elles pollueraient les postes
            if any((isinstance(c.value, str)
                    and RE_RENVOI.fullmatch(c.value.strip()))
                   or (isinstance(c.value, (int, float))
                       and not isinstance(c.value, bool)
                       and -99 <= c.value <= -1)
                   for c in ligne):
                continue

            # ------------------------------------------------------
            # 1) code DGFiP present sur la ligne ? (source la plus fiable)
            # ------------------------------------------------------
            code_poste = None
            for c in ligne:
                if isinstance(c.value, str):
                    s = c.value.strip()
                    if s in self.codes:
                        section, poste = self.codes[s]
                        if not sections_feuille or section in sections_feuille:
                            code_poste = (section, poste)
                            cote = section
                            break

            # ------------------------------------------------------
            # 2) sinon : libelle (mention TOTAL ou referentiel).
            # Plusieurs cellules d'une meme ligne peuvent matcher : les
            # titres de bloc occupent les premieres colonnes ("ACTIF
            # CIRCULANT", "CAPITAUX PROPRES"...), le libelle du poste
            # est plus profond. On retient la DERNIERE cellule qui
            # resout, pas la premiere.
            # ------------------------------------------------------
            def _resoudre(cands_c):
                if not cands_c:
                    return None
                if len(cands_c) == 1:
                    section_c, poste_c = cands_c[0]
                    if sections_feuille and section_c not in sections_feuille:
                        return None      # match isole hors sujet
                    return section_c, poste_c
                sections_c = [s for s, _ in cands_c]
                if cote and cote in sections_c:
                    section_c = cote
                else:
                    uniques = [s for s in sections_c if s in sections_feuille]
                    if len(uniques) != 1:
                        return None
                    section_c = uniques[0]
                poste_c = next(p for s, p in cands_c if s == section_c)
                return section_c, poste_c

            c_label, label_poste = None, None
            for c in ligne[:10]:
                if not isinstance(c.value, str):
                    continue
                n = _norm(c.value)
                if len(n) < LONGUEUR_LABEL_MIN or n.startswith("dont"):
                    continue      # detail "dont ..." : ligne d'eclatement
                resolu = None
                if n in aliases:
                    cote_ok = (cote if cote in aliases[n]
                               else (next(iter(sections_feuille))
                                     if len(sections_feuille) == 1
                                     and next(iter(sections_feuille)) in aliases[n]
                                     else None))
                    if cote_ok is not None:
                        resolu = (cote_ok, aliases[n][cote_ok])
                else:
                    resolu = _resoudre(self._match(n))
                if resolu is not None:
                    c_label, label_poste = c, resolu
                    cote = resolu[0]

            # ni code ni libelle : ligne sans interet
            if code_poste is None and label_poste is None:
                continue
            section, poste = code_poste or label_poste

            # ------------------------------------------------------
            # 3) montants : colonnes d'en-tete si connues, sinon les
            #    montants a droite du libelle (convention : N a gauche)
            # ------------------------------------------------------
            if col_n is not None:
                v_n = _nombre(ligne[col_n].value) if col_n < len(ligne) else None
                v_n1 = (_nombre(ligne[col_n1].value)
                        if col_n1 is not None and col_n1 < len(ligne) else None)
            else:
                debut = c_label.column if c_label is not None else 0
                nums = []
                for j in range(debut, len(ligne)):
                    v = _nombre(ligne[j].value)
                    if v is not None and not _est_code_dgfip(ligne[j].value):
                        nums.append(v)
                if len(nums) >= 2:
                    v_n, v_n1 = nums[0], nums[1]
                elif len(nums) == 1:
                    v_n, v_n1 = nums[0], None
                else:
                    continue

            dest = donnees[section]
            if v_n is not None and poste not in dest:
                dest[poste] = v_n
            if v_n1 is not None and f"{poste}_n1" not in dest:
                dest[f"{poste}_n1"] = v_n1

        return donnees, annee_n, annee_n1

    # ------------------------------------------------------------
    # API principale
    # ------------------------------------------------------------
    def lire(self, fichier) -> tuple:
        """Fichier Excel -> (format standard, meta).

        Format standard : {"actif": {...}, "passif": {...},
        "compte_resultat": {...}} avec cles "<poste>" (N) et "<poste>_n1".
        Meta : {"raison_sociale", "siren", "code_naf", "annee_n", "annee_n1"}.
        La premiere valeur rencontree gagne (jamais de cumul entre feuilles).
        """
        chemin = Path(fichier)
        if chemin.suffix.lower() not in EXCEL_EXTENSIONS:
            raise ValueError(
                f"Format non supporte : {chemin.suffix or 'sans extension'}. "
                "Convertissez le fichier en .xlsx."
            )
        try:
            wb = _ouvrir_classeur(chemin)
        except Exception as e:
            raise ValueError(f"Fichier Excel illisible : {e}") from e

        standard = {s: {} for s in SECTIONS}
        meta = {}
        annees = set()
        try:
            for ws in wb.worksheets:
                donnees, an, an1 = self._lire_feuille(ws)
                for sec in SECTIONS:
                    for k, v in donnees[sec].items():
                        standard[sec].setdefault(k, v)
                for k, v in self._chercher_meta(ws).items():
                    if v and not meta.get(k):
                        meta[k] = v
                if an:
                    annees.add(an)
                if an1:
                    annees.add(an1)
        finally:
            wb.close()

        if annees:
            meta["annee_n"] = max(annees)
            if len(annees) > 1:
                meta["annee_n1"] = min(annees)
        return standard, meta

    def lire_format_standard(self, fichier) -> dict:
        """Variante : retourne le format standard seul."""
        return self.lire(fichier)[0]


# ============================================================
# Test en ligne de commande
# ============================================================
if __name__ == "__main__":
    import sys
    from src.extraction.controle_extraction import scorer_extraction

    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.excel_parser fichier.xlsx")
        sys.exit(1)

    data, meta = ExcelParser().lire(sys.argv[1])
    print("\n=== IDENTIFICATION ===")
    for k in ("raison_sociale", "siren", "code_naf", "annee_n", "annee_n1"):
        print(f"  {k:16s}: {meta.get(k)}")
    for sec in SECTIONS:
        print(f"\n{sec.upper()} ({len(data[sec])} cles)")
        for k, v in sorted(data[sec].items()):
            print(f"  {k:40s} : {v:>15,.0f}")

    det = detecter_documents(data)
    print("\n=== DETECTION ===")
    print(f"  bilan           : {'oui' if det['bilan'] else 'non'} "
          f"(actif={det['nb_actif']}, passif={det['nb_passif']})")
    print(f"  compte resultat : {'oui' if det['compte_resultat'] else 'non'} "
          f"({det['nb_cr']} postes)")

    ctrl = scorer_extraction(data, "excel")
    print("\n=== CONTROLE ===")
    print(f"  statut : {ctrl.statut} ({ctrl.score}/100)")
    if ctrl.equilibre_ecart_pct is not None:
        print(f"  equilibre : {ctrl.equilibre_ecart_pct:.2f} % "
              f"({ctrl.equilibre_methode})")
    for p in ctrl.problemes:
        print(f"  probleme : {p}")
    for a in ctrl.avertissements:
        print(f"  avertissement : {a}")
