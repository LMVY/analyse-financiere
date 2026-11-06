"""Service d'extraction unifie : fichier -> format standard + meta.

Un seul point d'entree pour le dashboard, la ligne de commande et les
tests. Le service route selon l'extension :
- PDF natif ou scanne, JPG, PNG -> Mistral Document AI (annotation JSON) ;
- Excel (.xlsx / .xlsm) -> lecteur local (excel_parser), sans appel API.

Le retour est un Extraction homogene :
- data   : format standard {"actif": {...}, "passif": {...},
           "compte_resultat": {...}} avec les cles "<poste>" (exercice N)
           et "<poste>_n1" (exercice N-1) ;
- meta   : {"raison_sociale", "siren", "code_naf", "annee_n", ...} ;
- source : "excel" ou "mistral_docai" (alimente le controle d'extraction).

Usage :
    from src.extraction.service import ExtractionService
    extrait = ExtractionService().extraire("bilan_2024.xlsx")
    extrait.data, extrait.meta, extrait.source
"""
from dataclasses import dataclass, field
from pathlib import Path

from src.extraction.excel_parser import EXCEL_EXTENSIONS, ExcelParser
from src.extraction.mistral_docai import DocumentAIExtractor

EXTENSIONS_DOC_AI = (".pdf", ".jpg", ".jpeg", ".png")
EXTENSIONS_SUPPORTES = EXCEL_EXTENSIONS + EXTENSIONS_DOC_AI


@dataclass
class Extraction:
    """Resultat homogene d'une extraction, quel que soit le format source."""
    fichier: str
    data: dict                      # format standard (cles N et _n1)
    meta: dict = field(default_factory=dict)
    source: str = ""                # "excel" | "mistral_docai"

    @property
    def exercices(self) -> int:
        """Nombre d'exercices portees par le document (1 ou 2 : N et N-1)."""
        return 2 if any(str(k).endswith("_n1")
                        for sec in self.data.values()
                        for k in sec) else 1


class ExtractionService:
    """Route un fichier comptable vers le bon extracteur et normalise
    la sortie. Le client Document AI n'est cree qu'au premier PDF/image,
    les fichiers Excel ne demandent aucune cle API."""

    def __init__(self, api_key: str = None):
        self._api_key = api_key
        self._docai = None

    # ------------------------------------------------------------
    # Extracteurs
    # ------------------------------------------------------------
    def _document_ai(self) -> DocumentAIExtractor:
        if self._docai is None:
            self._docai = DocumentAIExtractor(self._api_key)
        return self._docai

    # ------------------------------------------------------------
    # API principale
    # ------------------------------------------------------------
    def extraire(self, fichier) -> Extraction:
        """Fichier (PDF, image ou Excel) -> Extraction au format standard.

        Leve ValueError si le format n'est pas supporte ou si le fichier
        est illisible ; l'appelant decide d'ignorer ou d'arreter.
        """
        chemin = Path(fichier)
        ext = chemin.suffix.lower()

        if ext in EXCEL_EXTENSIONS:
            data, meta = ExcelParser().lire(chemin)
            return Extraction(str(chemin), data, meta, "excel")

        if ext in EXTENSIONS_DOC_AI:
            extracteur = self._document_ai()
            annotation = extracteur.extraire(str(chemin))
            data = extracteur.vers_format_standard(annotation)
            return Extraction(str(chemin), data,
                              annotation.get("meta") or {}, "mistral_docai")

        raise ValueError(
            f"Format non supporte : {ext or 'sans extension'} "
            f"(acceptes : {', '.join(EXTENSIONS_SUPPORTES)}). "
            "Convertissez le fichier en PDF ou en .xlsx."
        )


# ============================================================
# Test en ligne de commande
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.service fichier.pdf|.xlsx|.jpg|.png")
        sys.exit(1)

    ex = ExtractionService().extraire(sys.argv[1])
    print(f"\nFichier : {ex.fichier}")
    print(f"Source  : {ex.source} ({ex.exercices} exercice(s))")
    print("Meta    :", ex.meta)
    for sec in ("actif", "passif", "compte_resultat"):
        print(f"\n{sec.upper()} ({len(ex.data.get(sec) or {})})")
        for k, v in sorted((ex.data.get(sec) or {}).items()):
            print(f"  {k:40s} : {v:>15,.0f}")
