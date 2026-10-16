"""Diagnostic : quel parser choisi + validation."""
import time
from pathlib import Path
from collections import defaultdict, Counter
import pdfplumber

from src.extraction.formats.dgfip_pdf import detect_dgfip_format
from src.extraction.formats.dgfip_excel import detect_dgfip_excel
from src.extraction.formats.fec import detect_fec_format
from src.extraction.formats.excel_normal import detect_excel_format
from src.extraction.etats_financiers import BilanParser


def detecter_parser(chemin):
    """Retourne (parser, signaux, duree_detection)."""
    t0 = time.time()
    ext = Path(chemin).suffix.lower()
    signaux = {}

    try:
        # FEC
        if ext in [".fec", ".txt"]:
            signaux["ext_fec"] = ext
            if detect_fec_format(chemin):
                return "FEC", signaux, time.time() - t0
            return "INCONNU", signaux, time.time() - t0

        # Excel/CSV
        if ext in [".xlsx", ".xls", ".csv"]:
            is_dgfip = detect_dgfip_excel(chemin)
            signaux["dgfip_excel"] = is_dgfip
            if is_dgfip:
                return "DGFiP_EXCEL", signaux, time.time() - t0
            return "EXCEL_NORMAL", signaux, time.time() - t0

        # PDF
        if ext == ".pdf":
            is_dgfip = detect_dgfip_format(chemin)
            signaux["dgfip_pdf"] = is_dgfip
            if is_dgfip:
                return "DGFiP_PDF", signaux, time.time() - t0

            # Natif vs OCR
            with pdfplumber.open(chemin) as pdf:
                pages_texte = sum(1 for p in pdf.pages[:10] if len(p.chars) >= 100)
                pages_total = len(pdf.pages[:10])
            signaux["pages_texte"] = pages_texte
            signaux["pages_total"] = pages_total

            if pages_texte >= pages_total * 0.5:
                return "PDF_NATIF", signaux, time.time() - t0
            return "PDF_OCR", signaux, time.time() - t0

    except Exception as e:
        signaux["erreur"] = str(e)[:60]

    return "INCONNU", signaux, time.time() - t0


def analyser(chemin):
    """Analyse sans OCR pour aller vite."""
    t0 = time.time()
    parser, signaux, t_det = detecter_parser(chemin)

    try:
        data = BilanParser(chemin).parse_simple(force_ocr=False)
        nb_a = len(data["actif"])
        nb_p = len(data["passif"])
        nb_c = len(data["compte_resultat"])
        nb_t = nb_a + nb_p + nb_c
    except Exception as e:
        nb_a = nb_p = nb_c = nb_t = 0

    return {
        "parser": parser,
        "signaux": signaux,
        "nb_actif": nb_a,
        "nb_passif": nb_p,
        "nb_cr": nb_c,
        "nb_total": nb_t,
        "duree_det": t_det,
        "duree_tot": time.time() - t0,
    }


# ============================================================
# MAIN
# ============================================================
fichiers = sorted(list(Path("data/raw").glob("*.pdf")) +
                 list(Path("data/raw").glob("*.xlsx")))

print("=" * 115)
print(f"DIAGNOSTIC PARSER - {len(fichiers)} fichiers (SANS OCR)")
print("=" * 115)
print()

par_parser = defaultdict(list)
t_global = time.time()

for i, f in enumerate(fichiers, 1):
    r = analyser(str(f))
    par_parser[r["parser"]].append((f.name, r))

    sym = "🟢" if r["nb_total"] >= 40 else "🟠" if r["nb_total"] >= 15 else "🔴"
    print(f"  [{i:>2}/{len(fichiers)}] {sym} {r['parser']:<14s} | A={r['nb_actif']:>2} P={r['nb_passif']:>2} CR={r['nb_cr']:>2} T={r['nb_total']:>3} | {f.name[:55]}")

t_total = time.time() - t_global

# Resume par parser
print()
print("=" * 115)
print("RESUME PAR PARSER")
print("=" * 115)
for parser_nom, items in sorted(par_parser.items()):
    n = len(items)
    t_moyen = sum(r["nb_total"] for _, r in items) / n
    t_duree = sum(r["duree_tot"] for _, r in items) / n
    ok = sum(1 for _, r in items if r["nb_total"] >= 40)
    print(f"\n  🔧 {parser_nom} ({n} fichiers)")
    print(f"     Postes moyen : {t_moyen:.1f}")
    print(f"     Duree moyenne: {t_duree:.2f}s")
    print(f"     Fichiers OK  : {ok}/{n}")
    if parser_nom in ("PDF_OCR", "PDF_NATIF"):
        for nom, r in items:
            sig = r["signaux"]
            print(f"       • {nom[:50]:50s} | pages_texte={sig.get('pages_texte','?')}/{sig.get('pages_total','?')}")

print()
print(f"  ⏱  Duree totale : {t_total:.1f}s")
