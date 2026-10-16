"""Test exhaustif avec surveillance memoire.

- Traite les fichiers un par un
- Libere la memoire entre chaque (gc)
- Affiche la RAM utilisee
- Pause si RAM > seuil
- Sauvegarde progressivement
"""
import sys
import time
import gc
import os
from pathlib import Path
from collections import Counter, defaultdict

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios


# ============================================================
# SURVEILLANCE MEMOIRE
# ============================================================
def ram_mb():
    """Retourne la RAM utilisee par le process en MB."""
    if not HAS_PSUTIL:
        return 0
    p = psutil.Process(os.getpid())
    return p.memory_info().rss / 1024 / 1024


def ram_systeme():
    """Retourne (utilisee_GB, totale_GB, pourcentage)."""
    if not HAS_PSUTIL:
        return 0, 0, 0
    v = psutil.virtual_memory()
    return v.used / 1e9, v.total / 1e9, v.percent


def afficher_ram():
    u, t, p = ram_systeme()
    proc = ram_mb()
    print(f"  💾 RAM système: {u:.1f}/{t:.1f} GB ({p:.0f}%)  |  Process: {proc:.0f} MB")


# ============================================================
# TAUX DE LECTURE
# ============================================================
ATTENDUS = {
    "DGFiP_PDF":     {"total": 70},
    "DGFiP_EXCEL":   {"total": 70},
    "PDF_NATIF":     {"total": 55},
    "PDF_OCR":       {"total": 30},
    "FEC":           {"total": 52},
    "EXCEL_NORMAL":  {"total": 30},
    "INCONNU":       {"total": 28},
}


def taux(valeur, attendu):
    if attendu <= 0:
        return 0
    return min(100, int(valeur / attendu * 100))


def badge(t):
    if t >= 70:
        return "🟢"
    if t >= 50:
        return "🟠"
    return "🔴"


# ============================================================
# DETECTION PARSER (rapide, sans OCR)
# ============================================================
def detecter_parser(fichier):
    from src.extraction.formats.dgfip_pdf import detect_dgfip_format
    from src.extraction.formats.dgfip_excel import detect_dgfip_excel
    from src.extraction.formats.fec import detect_fec_format
    from src.extraction.formats.excel_normal import detect_excel_format

    chemin = str(fichier)
    ext = fichier.suffix.lower()

    try:
        if ext in [".fec", ".txt"] and detect_fec_format(chemin):
            return "FEC"
        if ext in [".xlsx", ".xls", ".csv"]:
            if detect_dgfip_excel(chemin):
                return "DGFiP_EXCEL"
            if detect_excel_format(chemin):
                return "EXCEL_NORMAL"
        if ext == ".pdf":
            if detect_dgfip_format(chemin):
                return "DGFiP_PDF"
            import pdfplumber
            with pdfplumber.open(chemin) as pdf:
                pages_texte = 0
                for page in pdf.pages[:5]:
                    if len(page.chars) > 100:
                        pages_texte += 1
                if pages_texte > 0:
                    return "PDF_NATIF"
                return "PDF_OCR"
    except Exception:
        pass
    return "INCONNU"


# ============================================================
# TEST D'UN FICHIER
# ============================================================
def tester(fichier):
    r = {
        "nom": fichier.name,
        "ext": fichier.suffix.lower(),
        "parser": "INCONNU",
        "attendu": 0,
        "extrait": {"actif": 0, "passif": 0, "cr": 0, "total": 0},
        "taux": 0,
        "badge": "🔴",
        "ca": 0, "rn": 0, "cp": 0,
        "equilibre": None,
        "erreur": None,
        "duree_s": 0,
        "ram_avant": 0,
        "ram_apres": 0,
    }

    r["ram_avant"] = ram_mb()
    t0 = time.time()

    try:
        # 1) Parser detection (rapide)
        r["parser"] = detecter_parser(fichier)
        r["attendu"] = ATTENDUS.get(r["parser"], {"total": 28})["total"]

        # 2) Extraction
        data = BilanParser(str(fichier)).parse_simple(force_ocr=False)

        r["extrait"]["actif"] = len(data["actif"])
        r["extrait"]["passif"] = len(data["passif"])
        r["extrait"]["cr"] = len(data["compte_resultat"])
        r["extrait"]["total"] = sum(r["extrait"][k] for k in ["actif", "passif", "cr"])

        r["taux"] = taux(r["extrait"]["total"], r["attendu"])
        r["badge"] = badge(r["taux"])

        # 3) Agrégats
        agg = Agregats(data).compute_all()
        r["ca"] = agg.get("chiffre_affaires", 0) or 0
        r["rn"] = agg.get("resultat_net", 0) or 0
        r["cp"] = agg.get("capitaux_propres", 0) or 0

        ta = agg.get("total_actif", 0) or 0
        tp = agg.get("total_passif", 0) or 0
        if ta and tp:
            r["equilibre"] = abs(ta - tp) / max(abs(ta), abs(tp)) * 100

        # Liberer
        del data, agg
        gc.collect()

    except Exception as e:
        r["erreur"] = str(e)[:100]

    r["duree_s"] = time.time() - t0
    r["ram_apres"] = ram_mb()

    return r


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 100)
    print("TEST EXHAUSTIF AVEC SURVEILLANCE MEMOIRE")
    print("=" * 100)
    print()

    if not HAS_PSUTIL:
        print("⚠️  psutil non installe → pip install psutil")
        print()

    # RAM initiale
    afficher_ram()
    print()

    # Fichiers
    fichiers = sorted(list(Path("data/raw").glob("*.pdf")) +
                     list(Path("data/raw").glob("*.xlsx")) +
                     list(Path("data/raw").glob("*.fec")))

    total = len(fichiers)
    print(f"Fichiers a traiter : {total}")
    print()

    resultats = []
    t_global = time.time()

    # Seuil RAM pour pause
    RAM_SEUIL_PCT = 85

    for i, f in enumerate(fichiers, 1):
        print(f"[{i:>2}/{total}] {f.name[:70]}")
        afficher_ram()

        r = tester(f)
        resultats.append(r)

        sym = r["badge"]
        print(f"        {sym} Parser={r['parser']:<12s} | Extrait={r['extrait']['total']:>3}/{r['attendu']:>3} | Taux={r['taux']:>3}% | {r['duree_s']:.1f}s")
        print()

        # Sauvegarde progressive
        with open("test_en_cours.txt", "a", encoding="utf-8") as fp:
            fp.write(f"{i}|{f.name}|{r['parser']}|{r['extrait']['total']}|{r['taux']}|{r['duree_s']:.1f}\n")

        # Pause si RAM > seuil
        u, t, pct = ram_systeme()
        if pct > RAM_SEUIL_PCT:
            print(f"  ⚠️  RAM > {RAM_SEUIL_PCT}% → pause 5s pour stabiliser")
            gc.collect()
            time.sleep(5)
            print()

    t_total = time.time() - t_global

    # ============================================================
    # RESUME
    # ============================================================
    print("=" * 100)
    print("RESUME FINAL")
    print("=" * 100)
    print(f"Duree totale : {t_total:.1f}s ({t_total/60:.1f} min)")
    print(f"Duree moyenne : {t_total/total:.1f}s/fichier")
    print()

    stats = Counter(r["badge"] for r in resultats)
    for b, n in stats.most_common():
        pct = n / total * 100
        print(f"  {b} : {n:>3} ({pct:.0f}%)")

    # RAM finale
    print()
    afficher_ram()

    # Top 5 plus lents
    print()
    print("TOP 5 plus lents :")
    for r in sorted(resultats, key=lambda x: -x["duree_s"])[:5]:
        print(f"  {r['duree_s']:>6.1f}s | {r['nom'][:70]}")

    # Erreurs
    erreurs = [r for r in resultats if r["erreur"]]
    if erreurs:
        print()
        print(f"ERREURS ({len(erreurs)}) :")
        for r in erreurs:
            print(f"  {r['nom'][:60]} : {r['erreur'][:60]}")

    print()
    print("=" * 100)
