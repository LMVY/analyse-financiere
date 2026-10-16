"""Test ultra-light : 1 fichier, libere tout apres."""
import sys
import gc
import time
from pathlib import Path

# IMPORTANT : limiter les threads ONNX (evite plantage CPU)
import os
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["ONNX_NUM_THREADS"] = "2"

from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats


def tester(nom_fichier):
    fichier = Path("data/raw") / nom_fichier
    if not fichier.exists():
        print(f"❌ Introuvable : {fichier}")
        return

    print(f"=== {fichier.name} ===")
    print(f"Taille : {fichier.stat().st_size/1024:.0f} KB")
    print()

    t0 = time.time()
    try:
        parser = BilanParser(str(fichier))
        data = parser.parse_simple(force_ocr=False)
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return
    duree = time.time() - t0

    nb_a = len(data["actif"])
    nb_p = len(data["passif"])
    nb_c = len(data["compte_resultat"])
    total = nb_a + nb_p + nb_c

    print(f"⏱  {duree:.1f}s")
    print(f"📊 Actif:{nb_a} Passif:{nb_p} CR:{nb_c} TOTAL:{total}")

    if total >= 40:
        print(f"🟢 EXCELLENT")
    elif total >= 25:
        print(f"🟢 BON")
    elif total >= 15:
        print(f"🟠 MOYEN")
    elif total >= 5:
        print(f"🟠 FAIBLE")
    else:
        print(f"🔴 CRITIQUE")

    # Agregats (rapide)
    try:
        agg = Agregats(data).compute_all()
        ca = agg.get("chiffre_affaires", 0) or 0
        rn = agg.get("resultat_net", 0) or 0
        cp = agg.get("capitaux_propres", 0) or 0
        print(f"💰 CA={ca:>12,.0f}  RN={rn:>10,.0f}  CP={cp:>12,.0f}".replace(",", " "))
    except Exception:
        pass

    # Liberer
    del data
    gc.collect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python mini_test.py 'nom_fichier'")
        sys.exit(1)
    tester(sys.argv[1])
