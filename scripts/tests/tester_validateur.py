"""Applique le validateur a un dossier de fichiers, sans brancher sur le pipeline.

Usage :
    python scripts/tests/tester_validateur.py data/raw \
        --extracteur "src.extraction.etats_financiers:extraire_fichier" \
        --out baseline_avant.csv
"""

import argparse
import csv
import importlib
import sys
import time
import traceback
from pathlib import Path

# Ajouter la racine du projet au sys.path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.extraction.validateur_resultat import scorer_extraction

EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".fec"}
COLONNES = ["fichier", "statut", "score", "acceptable", "nb_postes", "nb_actif",
            "nb_passif", "nb_cr", "ecart_pct", "methode_equilibre", "duree_s",
            "problemes", "avertissements", "erreur"]


def charger_extracteur(spec: str):
    module, _, fonction = spec.partition(":")
    return getattr(importlib.import_module(module), fonction)


def lancer(dossier: Path, extracteur, out: Path):
    fichiers = sorted(p for p in dossier.rglob("*") if p.suffix.lower() in EXTENSIONS)
    if not fichiers:
        sys.exit(f"Aucun fichier trouve dans {dossier}")

    lignes = []
    for i, f in enumerate(fichiers, 1):
        t0 = time.time()
        erreur = ""
        try:
            data = extracteur(str(f))
            r = scorer_extraction(data, "")
        except Exception as e:
            traceback.print_exc()
            erreur = f"{type(e).__name__}: {e}"
            r = scorer_extraction(None, "")
        duree = round(time.time() - t0, 1)
        lignes.append({
            "fichier": str(f.relative_to(dossier)),
            "statut": r.statut, "score": r.score, "acceptable": r.acceptable,
            "nb_postes": r.nb_postes, "nb_actif": r.nb_actif,
            "nb_passif": r.nb_passif, "nb_cr": r.nb_cr,
            "ecart_pct": "" if r.equilibre_ecart_pct is None else round(r.equilibre_ecart_pct, 2),
            "methode_equilibre": r.equilibre_methode or "",
            "duree_s": duree,
            "problemes": " | ".join(r.problemes),
            "avertissements": " | ".join(r.avertissements),
            "erreur": erreur,
        })
        print(f"[{i:>3}/{len(fichiers)}] {r.statut:<12} {r.score:>3}/100  {f.name[:60]}")

    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(lignes)

    nb = len(lignes)
    ok = sum(1 for l in lignes if l["acceptable"])
    print("\n=== Resume ===")
    for statut in ("ok", "incomplet", "desequilibre", "vide"):
        n = sum(1 for l in lignes if l["statut"] == statut)
        print(f"  {statut:<13} {n:>3}/{nb}")
    print(f"  acceptables   {ok:>3}/{nb}")
    print(f"Detail : {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--extracteur", required=True)
    ap.add_argument("--out", type=Path, default=Path("baseline_validation.csv"))
    args = ap.parse_args()
    lancer(args.dossier, charger_extracteur(args.extracteur), args.out)
