"""Client Mistral Document AI : fichier -> donnees comptables structurees (JSON).

Utilise l'annotation de document de l'API OCR (Document AI) :
- le schema JSON est construit automatiquement depuis config/pcg_referentiel.yaml
  (meme referentiel que l'extracteur Markdown, une seule source de verite) ;
- Mistral lit le document (OCR) puis remplit le schema ;
- le retour est converti au format standard du pipeline
  {"actif": {...}, "passif": {...}, "compte_resultat": {...}}
  avec les cles "<poste>" (exercice N) et "<poste>_n1" (exercice N-1).
"""
import os
import json
import base64
import hashlib
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

YAML_PATH = Path(__file__).parent.parent.parent / "config" / "pcg_referentiel.yaml"
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache_mistral"

SECTIONS = ("actif", "passif", "compte_resultat")

PROMPT_ANNOTATION = (
    "Tu es expert-comptable francais, specialiste du Plan Comptable General. "
    "Le document est un bilan et/ou un compte de resultat d'une entreprise francaise. "
    "Pour chaque poste du schema, remplis exercice_n avec le montant de l'exercice "
    "le plus recent et exercice_n1 avec le montant de l'exercice precedent. "
    "Mets null si le poste est absent du document. "
    "Pour l'actif, utilise la colonne NET (apres amortissements et provisions). "
    "Garde les montants tels qu'ils figurent, sans conversion d'unites. "
    "Un montant entre parentheses est negatif. "
    "Remplis AUSSI les postes de totaux a partir des lignes TOTAL du document. "
    "Dans un bilan francais standard : a l'actif TOTAL (I) = actif_immobilise, "
    "TOTAL (II) = total_actif_circulant, TOTAL GENERAL = total_actif ; "
    "au passif TOTAL (I) = total_capitaux_propres, TOTAL (II) = total_dettes, "
    "TOTAL GENERAL = total_passif. "
    "Les lignes de totaux intermediaires (immobilisations, stocks, creances, "
    "dettes financieres...) remplissent les postes total_* correspondants. "
    "Remplis la section meta avec la raison sociale, le SIREN et le code "
    "NAF/APE de l'entreprise s'ils figurent sur le document (null sinon)."
)


# ============================================================
# Construction du schema depuis le referentiel PCG
# ============================================================
def _charger_referentiel() -> dict:
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _schema_poste(labels: list) -> dict:
    """Un poste = montants des deux exercices, avec les libelles en description."""
    libelles = " ; ".join(labels[:6])
    return {
        "type": "object",
        "description": f"Libelles possibles du poste : {libelles}",
        "properties": {
            "exercice_n": {"type": ["number", "null"]},
            "exercice_n1": {"type": ["number", "null"]},
        },
        "required": ["exercice_n", "exercice_n1"],
        "additionalProperties": False,
    }


def construire_format_annotation(referentiel: dict = None) -> dict:
    """Referentiel PCG -> format d'annotation (json_schema) pour l'API Mistral."""
    if referentiel is None:
        referentiel = _charger_referentiel()

    sections = {}
    for section in SECTIONS:
        postes = {}
        for code, labels in (referentiel.get(section) or {}).items():
            if labels:
                postes[code] = _schema_poste(labels)
        sections[section] = {
            "type": "object",
            "properties": postes,
            "required": list(postes),
            "additionalProperties": False,
        }

    sections["meta"] = {
        "type": "object",
        "description": "Identification de l'entreprise figurant sur le document",
        "properties": {
            "raison_sociale": {"type": ["string", "null"]},
            "siren": {"type": ["string", "null"]},
            "code_naf": {
                "type": ["string", "null"],
                "description": "Code NAF ou APE de l'activite principale (ex : 46.75B)",
            },
        },
        "required": ["raison_sociale", "siren", "code_naf"],
        "additionalProperties": False,
    }

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "bilan_pc",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": sections,
                "required": list(sections),
                "additionalProperties": False,
            },
        },
    }


# ============================================================
# Client Document AI
# ============================================================
class DocumentAIExtractor:
    """Envoie un fichier (PDF/image) a Mistral Document AI, retourne le JSON rempli."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY manquante. "
                "Copie .env.example en .env et mets ta cle."
            )
        self._client = None
        self._format_annotation = construire_format_annotation()
        # Le hash du schema + prompt invalide le cache quand le referentiel evolue
        self._hash_schema = hashlib.sha256(
            (json.dumps(self._format_annotation, sort_keys=True)
             + PROMPT_ANNOTATION).encode()
        ).hexdigest()[:8]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _client_lazy(self):
        if self._client is None:
            from mistralai.client import Mistral
            self._client = Mistral(api_key=self.api_key)
        return self._client

    def _hash_fichier(self, fichier: str) -> str:
        h = hashlib.sha256()
        with open(fichier, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def extraire(self, fichier: str) -> dict:
        """Retourne l'annotation remplie par Mistral :

        {"actif": {<poste>: {"exercice_n": x, "exercice_n1": y}, ...},
         "passif": {...}, "compte_resultat": {...}}
        """
        fichier = str(fichier)
        ext = Path(fichier).suffix.lower()
        cache_path = CACHE_DIR / f"{self._hash_fichier(fichier)}_{self._hash_schema}_docai{ext}.json"

        if cache_path.exists():
            print(f"  Cache hit : {cache_path.name}")
            return json.loads(cache_path.read_text(encoding="utf-8"))

        print(f"  Envoi a Mistral Document AI : {Path(fichier).name}")
        with open(fichier, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        if ext == ".pdf":
            doc = {"type": "document_url",
                   "document_url": f"data:application/pdf;base64,{b64}"}
        elif ext in (".jpg", ".jpeg"):
            doc = {"type": "image_url",
                   "image_url": f"data:image/jpeg;base64,{b64}"}
        elif ext == ".png":
            doc = {"type": "image_url",
                   "image_url": f"data:image/png;base64,{b64}"}
        else:
            raise ValueError(f"Format non supporte : {ext}")

        response = self._client_lazy().ocr.process(
            model="mistral-ocr-latest",
            document=doc,
            document_annotation_format=self._format_annotation,
            document_annotation_prompt=PROMPT_ANNOTATION,
            include_image_base64=False,
        )

        if not response.document_annotation:
            raise ValueError(
                "Mistral n'a pas renvoye d'annotation de document. "
                "Verifie que le format d'annotation est accepte par l'API."
            )

        annotation = json.loads(response.document_annotation)
        cache_path.write_text(
            json.dumps(annotation, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return annotation

    # ------------------------------------------------------------
    # Conversion vers le format standard du pipeline
    # ------------------------------------------------------------
    @staticmethod
    def vers_format_standard(annotation: dict) -> dict:
        """Annotation Document AI -> format consomme par le pipeline :

        {"actif": {"constructions": 1075941.0, "constructions_n1": 1112741.0,
                    "total_actif": ..., ...},
         "passif": {...}, "compte_resultat": {...}}

        Les postes sans montant (null) sont omis.
        """
        standard = {s: {} for s in SECTIONS}
        for section in SECTIONS:
            for poste, valeurs in (annotation.get(section) or {}).items():
                if not isinstance(valeurs, dict):
                    continue
                n = valeurs.get("exercice_n")
                n1 = valeurs.get("exercice_n1")
                if isinstance(n, (int, float)):
                    standard[section][poste] = float(n)
                if isinstance(n1, (int, float)):
                    standard[section][f"{poste}_n1"] = float(n1)
        return standard

    def extraire_format_standard(self, fichier: str) -> dict:
        """Chemin complet : fichier -> format standard du pipeline."""
        return self.vers_format_standard(self.extraire(fichier))


# ============================================================
# Test en ligne de commande
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.mistral_docai fichier.pdf")
        sys.exit(1)

    ext = DocumentAIExtractor()
    annotation = ext.extraire(sys.argv[1])
    data = ext.vers_format_standard(annotation)

    meta = annotation.get("meta") or {}
    print("\n=== IDENTIFICATION ===")
    print(f"  Raison sociale : {meta.get('raison_sociale')}")
    print(f"  SIREN          : {meta.get('siren')}")
    print(f"  Code NAF/APE   : {meta.get('code_naf')}")
    if meta.get("code_naf"):
        from src.scoring.sector_scorer import detect_secteur, load_secteurs
        secteur = detect_secteur(meta["code_naf"])
        if secteur:
            print(f"  Secteur        : {secteur} "
                  f"({load_secteurs()[secteur]['label']})")

    print("\n=== RESULTAT FORMAT STANDARD ===")
    for sec in SECTIONS:
        print(f"\n{sec.upper()} ({len(data[sec])} postes)")
        for k, v in sorted(data[sec].items()):
            print(f"  {k:40s} : {v:>15,.0f}")

    print("\n=== CONTROLE ===")
    from src.extraction.controle_extraction import scorer_extraction
    ctrl = scorer_extraction(data, "mistral_docai")
    print(f"  statut    : {ctrl.statut}")
    print(f"  score     : {ctrl.score}/100")
    print(f"  postes    : {ctrl.nb_postes} "
          f"(actif={ctrl.nb_actif}, passif={ctrl.nb_passif}, CR={ctrl.nb_cr})")
    if ctrl.equilibre_ecart_pct is not None:
        print(f"  equilibre : {ctrl.equilibre_ecart_pct:.2f} % "
              f"({ctrl.equilibre_methode})")
    for p in ctrl.problemes:
        print(f"  probleme  : {p}")
    for a in ctrl.avertissements:
        print(f"  avertissement : {a}")
