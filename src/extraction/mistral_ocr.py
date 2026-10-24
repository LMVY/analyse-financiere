"""Client Mistral OCR : envoie un fichier, recoit du Markdown structure."""
import os
import json
import base64
import hashlib
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache_mistral"


class MistralOCRExtractor:
    """Envoie un fichier (PDF/image) a Mistral OCR, retourne du Markdown."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY manquante. "
                "Copie .env.example en .env et mets ta cle."
            )
        self._client = None
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
        """Retourne {"pages": [{"index": 0, "markdown": "..."}, ...]}."""
        fichier = str(fichier)
        ext = Path(fichier).suffix.lower()
        cache_path = CACHE_DIR / f"{self._hash_fichier(fichier)}{ext}.json"

        if cache_path.exists():
            print(f"  Cache hit : {cache_path.name}")
            return json.loads(cache_path.read_text(encoding="utf-8"))

        print(f"  Envoi a Mistral OCR : {Path(fichier).name}")
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
            include_image_base64=False,
        )

        result = {
            "pages": [
                {"index": p.index, "markdown": p.markdown}
                for p in response.pages
            ]
        }
        cache_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python -m src.extraction.mistral_ocr fichier.pdf")
        sys.exit(1)
    ext = MistralOCRExtractor()
    result = ext.extraire(sys.argv[1])
    print(f"\n{len(result['pages'])} pages")
    print(result["pages"][0]["markdown"][:500])
