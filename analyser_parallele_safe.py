"""Analyse parallèle LIMITÉE pour ne pas crasher le PC.

- Détecte la RAM disponible, plafonne les workers à 2-3
- Écrit les résultats AU FUR ET À MESURE dans un fichier
- Reprise possible si crash (skip fichiers déjà traités)
"""
import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def detect_workers():
    """Détecte le nombre de workers safe selon la RAM."""
    try:
        import psutil
        ram_gb = psutil.virtual_memory().available / (1024**3)
        # 500 DPI + streaming ≈ 500 MB par worker
        workers = max(1, min(4, int(ram_gb / 0.6)))
        print(f"RAM dispo : {ram_gb:.1f} GB → {workers} worker(s)")
        return workers
    except ImportError:
        # Pas psutil : on est prudent
        print("psutil absent → 2 workers par sécurité")
        return 2


def traiter_un_fichier(chemin):
    """Traite 1 fichier. Isolé dans un processus."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))

    from src.extraction.etats_financiers import BilanParser
    from src.analysis.agregats import Agregats
    from src.analysis.ratios import Ratios
    from src.analysis.filter_ratios import filter_ratios

    t0 = time.time()
    r = {
        "nom": Path(chemin).name,
        "chemin": str(chemin),
        "statut": "ERREUR",
        "postes": {"actif": 0, "passif": 0, "cr": 0, "total": 0},
        "ca": 0, "rn": 0, "cp": 0,
        "equilibre": None,
        "ratios_ok": 0, "ratios_total": 0,
        "erreur": None,
        "duree_s": 0,
    }
    try:
        data = BilanParser(str(chemin)).parse_simple(force_ocr=False)
        r["postes"]["actif"] = len(data["actif"])
        r["postes"]["passif"] = len(data["passif"])
        r["postes"]["cr"] = len(data["compte_resultat"])
        r["postes"]["total"] = sum(r["postes"][k] for k in ["actif", "passif", "cr"])

        agg = Agregats(data).compute_all()
        r["ca"] = agg.get("chiffre_affaires", 0) or 0
        r["rn"] = agg.get("resultat_net", 0) or 0
        r["cp"] = agg.get("capitaux_propres", 0) or 0
        ta = agg.get("total_actif", 0) or 0
        tp = agg.get("total_passif", 0) or 0
        if ta and tp:
            r["equilibre"] = abs(ta - tp) / max(abs(ta), abs(tp)) * 100

        ratios = Ratios(agg).compute_all()
        ratios_f = filter_ratios(ratios, nb_exercices=4)
        for cat, d in ratios_f.items():
            for nom, val in d.items():
                r["ratios_total"] += 1
                if val is not None:
                    r["ratios_ok"] += 1

        # Statut
        if r["postes"]["total"] >= 40:
            r["statut"] = "OK"
        elif r["postes"]["total"] >= 15:
            r["statut"] = "PARTIEL"
        elif r["postes"]["total"] >= 5:
            r["statut"] = "FAIBLE"
        else:
            r["statut"] = "KO"
    except Exception as e:
        r["erreur"] = str(e)[:120]

    r["duree_s"] = time.time() - t0
    return r


def main():
    if len(sys.argv) > 1:
        workers = int(sys.argv[1])
    else:
        workers = detect_workers()

    data_dir = Path("data/raw")
    fichiers = sorted(
        list(data_dir.glob("*.pdf")) +
        list(data_dir.glob("*.xlsx")) +
        list(data_dir.glob("*.xls")) +
        list(data_dir.glob("*.fec"))
    )

    # Reprise : skip les fichiers déjà traités
    log_file = Path("rapport_progress.jsonl")
    deja_faits = set()
    if log_file.exists():
        for line in log_file.read_text(encoding="utf-8").splitlines():
            try:
                deja_faits.add(json.loads(line)["nom"])
            except Exception:
                pass
        print(f"Reprise : {len(deja_faits)} fichiers déjà traités")

    a_traiter = [f for f in fichiers if f.name not in deja_faits]
    print(f"\n{len(a_traiter)} fichiers à traiter, {workers} worker(s)\n")

    t0 = time.time()
    log_fp = open(log_file, "a", encoding="utf-8")

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(traiter_un_fichier, str(f)): f for f in a_traiter}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                r = fut.result()
                # Écrit IMMÉDIATEMENT dans le log
                log_fp.write(json.dumps(r, ensure_ascii=False) + "\n")
                log_fp.flush()
                os.fsync(log_fp.fileno())

                sym = {"OK": "🟢", "PARTIEL": "🟠", "FAIBLE": "🟡", "KO": "🔴", "ERREUR": "💥"}[r["statut"]]
                print(f"  [{i:>2}/{len(a_traiter)}] {sym} {r['postes']['total']:>3} postes | "
                      f"{r['duree_s']:>6.1f}s | {r['nom'][:55]}")
            except Exception as e:
                print(f"  [{i:>2}/{len(a_traiter)}] 💥 {e}")

    log_fp.close()
    duree = time.time() - t0
    print(f"\n✅ {len(a_traiter)} fichiers traités en {duree:.1f}s")
    print(f"   Log complet : {log_file}")
    print(f"\nPour générer le rapport : python generer_rapport_depuis_log.py")


if __name__ == "__main__":
    main()
