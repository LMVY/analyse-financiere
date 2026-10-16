"""Analyse avec DIAGNOSTIC de la detection du parser.

Pour chaque fichier :
- Quel parser a ete choisi
- Pourquoi (signaux detectes)
- Est-ce le bon ?
- Combien de postes extraits vs attendus
"""
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
import pdfplumber

from src.extraction.etats_financiers import BilanParser
from src.extraction.formats.dgfip_pdf import detect_dgfip_format, CODES_DGFIP
from src.extraction.formats.dgfip_excel import detect_dgfip_excel
from src.extraction.formats.fec import detect_fec_format
from src.extraction.formats.excel_normal import detect_excel_format
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios


# ============================================================
# ATTENDUS PAR TYPE
# ============================================================
ATTENDUS = {
    "DGFiP_PDF":     {"actif": 20, "passif": 15, "cr": 35, "total": 70},
    "DGFiP_EXCEL":   {"actif": 20, "passif": 15, "cr": 35, "total": 70},
    "PDF_NATIF":     {"actif": 20, "passif": 15, "cr": 20, "total": 55},
    "PDF_OCR":       {"actif": 15, "passif": 12, "cr": 15, "total": 42},
    "FEC":           {"actif": 15, "passif": 12, "cr": 25, "total": 52},
    "EXCEL_NORMAL":  {"actif": 10, "passif": 8,  "cr": 12, "total": 30},
    "INCONNU":       {"actif": 10, "passif": 8,  "cr": 10, "total": 28},
}


# ============================================================
# DIAGNOSTIC DETAILLE DE LA DETECTION
# ============================================================
def diagnostiquer(fichier):
    """Retourne le parser choisi + tous les signaux detectes."""
    diag = {
        "ext": fichier.suffix.lower(),
        "signaux": {},
        "parser_choisi": "INCONNU",
        "raison": "",
        "erreur": None,
    }

    chemin = str(fichier)
    ext = fichier.suffix.lower()

    try:
        # --- Test 1 : FEC ? ---
        if ext in [".fec", ".txt"]:
            try:
                is_fec = detect_fec_format(chemin)
                diag["signaux"]["FEC (ext .fec/.txt)"] = is_fec
                if is_fec:
                    diag["parser_choisi"] = "FEC"
                    diag["raison"] = "Extension + entete FEC detectee"
                    return diag
            except Exception as e:
                diag["signaux"]["FEC"] = f"erreur: {e}"

        # --- Test 2 : Excel/CSV ? ---
        if ext in [".xlsx", ".xls", ".csv"]:
            try:
                is_dgfip_xl = detect_dgfip_excel(chemin)
                diag["signaux"]["Feuilles Actif+Passif"] = is_dgfip_xl
                if is_dgfip_xl:
                    diag["parser_choisi"] = "DGFiP_EXCEL"
                    diag["raison"] = "Feuilles 'Actif' + 'Passif' detectees"
                    return diag
            except Exception as e:
                diag["signaux"]["DGFiP_Excel"] = f"erreur: {e}"

            try:
                is_xl = detect_excel_format(chemin)
                diag["signaux"]["Excel/CSV (ext)"] = is_xl
                if is_xl:
                    diag["parser_choisi"] = "EXCEL_NORMAL"
                    diag["raison"] = "Extension .xlsx/.xls/.csv sans feuilles DGFiP"
                    return diag
            except Exception as e:
                diag["signaux"]["Excel"] = f"erreur: {e}"

        # --- Test 3 : PDF ? ---
        if ext == ".pdf":
            # 3a. DGFiP PDF ?
            try:
                is_dgfip = detect_dgfip_format(chemin)
                diag["signaux"]["Codes DGFiP (AA/AB/BJ...)"] = is_dgfip
                if is_dgfip:
                    diag["parser_choisi"] = "DGFiP_PDF"
                    diag["raison"] = "Codes DGFiP detectes dans le PDF"
                    # Compter les codes trouves (echantillon)
                    try:
                        with pdfplumber.open(chemin) as pdf:
                            nb_codes = 0
                            for page in pdf.pages[:5]:
                                words = page.extract_words()
                                texts = [w["text"] for w in words]
                                nb_codes = sum(1 for c in CODES_DGFIP if c in texts)
                            diag["signaux"]["Nb codes DGFiP (5 1eres pages)"] = nb_codes
                    except Exception:
                        pass
                    return diag
            except Exception as e:
                diag["signaux"]["DGFiP_PDF"] = f"erreur: {e}"

            # 3b. Natif ou OCR ?
            try:
                with pdfplumber.open(chemin) as pdf:
                    total_pages = len(pdf.pages)
                    pages_texte = 0
                    pages_image = 0
                    for page in pdf.pages:
                        chars = len(page.chars)
                        if chars >= 500:
                            pages_texte += 1
                        else:
                            pages_image += 1

                diag["signaux"]["Pages avec texte"] = pages_texte
                diag["signaux"]["Pages sans texte"] = pages_image
                diag["signaux"]["Total pages"] = total_pages

                if pages_image >= pages_texte and pages_image > 0:
                    diag["parser_choisi"] = "PDF_OCR"
                    diag["raison"] = f"{pages_image} pages sans texte sur {total_pages} -> OCR"
                else:
                    diag["parser_choisi"] = "PDF_NATIF"
                    diag["raison"] = f"{pages_texte} pages avec texte sur {total_pages} -> pdfplumber"
                return diag
            except Exception as e:
                diag["signaux"]["Detection natif/OCR"] = f"erreur: {e}"

    except Exception as e:
        diag["erreur"] = str(e)[:100]

    return diag


# ============================================================
# ANALYSE COMPLETE
# ============================================================
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


def analyser(fichier):
    """Analyse complete + diagnostic."""
    r = {
        "nom": fichier.name,
        "chemin": str(fichier),
        "ext": fichier.suffix.lower(),
        "diag": {},
        "extrait": {"actif": 0, "passif": 0, "cr": 0, "total": 0},
        "attendu": {},
        "taux": {"actif": 0, "passif": 0, "cr": 0, "global": 0},
        "badge": "🔴",
        "ca": 0, "rn": 0, "cp": 0,
        "equilibre": None,
        "ratios_ok": 0, "ratios_total": 0,
        "erreur": None,
        "duree_s": 0,
    }

    t0 = time.time()
    try:
        # 1) Diagnostic AVANT extraction
        r["diag"] = diagnostiquer(fichier)
        parser_nom = r["diag"]["parser_choisi"]
        r["attendu"] = ATTENDUS.get(parser_nom, ATTENDUS["INCONNU"])

        # 2) Extraction
        data = BilanParser(str(fichier)).parse_simple(force_ocr=False)

        r["extrait"]["actif"] = len(data["actif"])
        r["extrait"]["passif"] = len(data["passif"])
        r["extrait"]["cr"] = len(data["compte_resultat"])
        r["extrait"]["total"] = sum(r["extrait"][k] for k in ["actif", "passif", "cr"])

        r["taux"]["actif"] = taux(r["extrait"]["actif"], r["attendu"]["actif"])
        r["taux"]["passif"] = taux(r["extrait"]["passif"], r["attendu"]["passif"])
        r["taux"]["cr"] = taux(r["extrait"]["cr"], r["attendu"]["cr"])
        r["taux"]["global"] = taux(r["extrait"]["total"], r["attendu"]["total"])
        r["badge"] = badge(r["taux"]["global"])

        # 3) Agregats
        agg = Agregats(data).compute_all()
        r["ca"] = agg.get("chiffre_affaires", 0) or 0
        r["rn"] = agg.get("resultat_net", 0) or 0
        r["cp"] = agg.get("capitaux_propres", 0) or 0

        ta = agg.get("total_actif", 0) or 0
        tp = agg.get("total_passif", 0) or 0
        if ta and tp:
            r["equilibre"] = abs(ta - tp) / max(abs(ta), abs(tp)) * 100

        # 4) Ratios
        ratios = Ratios(agg).compute_all()
        ratios_f = filter_ratios(ratios, nb_exercices=4)
        for cat, d in ratios_f.items():
            for nom, val in d.items():
                r["ratios_total"] += 1
                if val is not None:
                    r["ratios_ok"] += 1

    except Exception as e:
        r["erreur"] = str(e)[:100]

    r["duree_s"] = time.time() - t0
    return r


# ============================================================
# AFFICHAGE CONSOLE
# ============================================================
def afficher(r):
    d = r["diag"]
    print(f"  ┌─ {r['nom']}")
    print(f"  │")
    print(f"  │  📁 Extension   : {r['ext']}")
    print(f"  │  🔍 SIGNAUX DETECTES :")
    for signal, valeur in d.get("signaux", {}).items():
        if isinstance(valeur, bool):
            sym = "✅" if valeur else "❌"
            print(f"  │    {sym} {signal} : {valeur}")
        else:
            print(f"  │    • {signal} : {valeur}")
    print(f"  │")
    print(f"  │  🎯 PARSER CHOISI : {d['parser_choisi']}")
    print(f"  │     Raison : {d['raison']}")
    print(f"  │")
    print(f"  │  📊 EXTRACTION :")
    att = r["attendu"]
    ext = r["extrait"]
    t = r["taux"]
    print(f"  │  {'Zone':<18} {'Attendu':>8} {'Extrait':>8} {'Taux':>6}")
    for zone, lab in [("actif", "Actif"), ("passif", "Passif"), ("cr", "Compte resultat")]:
        print(f"  │  {lab:<18} {att.get(zone, 0):>8} {ext[zone]:>8} {t[zone]:>5}%")
    print(f"  │  {'TOTAL':<18} {att.get('total', 0):>8} {ext['total']:>8} {t['global']:>5}%  {r['badge']}")
    print(f"  │")
    print(f"  │  💰 CA={r['ca']:>12,.0f}  RN={r['rn']:>10,.0f}  CP={r['cp']:>12,.0f}".replace(",", " "))
    if r["equilibre"] is not None:
        eq = r["equilibre"]
        sym = "✅" if eq < 1 else "⚠️" if eq < 5 else "❌"
        print(f"  │  ⚖️  Equilibre bilan : {eq:.2f}% {sym}")
    print(f"  │  📈 Ratios : {r['ratios_ok']}/{r['ratios_total']}  ({r['duree_s']:.2f}s)")
    if r["erreur"]:
        print(f"  │  ❌ {r['erreur']}")
    print(f"  └─")


# ============================================================
# RAPPORT
# ============================================================
def generer_rapport(resultats, chemin="rapport_parser.txt"):
    lines = []
    lines.append("=" * 110)
    lines.append("RAPPORT D'ANALYSE - DIAGNOSTIC DU PARSER PAR FICHIER")
    lines.append(f"Fichiers analyses : {len(resultats)}")
    lines.append("=" * 110)
    lines.append("")

    # Tableau recap parser
    lines.append("┌" + "─" * 106 + "┐")
    lines.append(f"│ {'#':>3} │ {'FICHIER':<40} │ {'PARSER':<12} │ {'ATT':>4} │ {'EXT':>4} │ {'TAUX':>5} │")
    lines.append("├" + "─" * 106 + "┤")
    for i, r in enumerate(resultats, 1):
        nom = r["nom"][:39]
        parser = r["diag"]["parser_choisi"][:12]
        att = r["attendu"].get("total", 0)
        ext = r["extrait"]["total"]
        t = f"{r['taux']['global']}%"
        lines.append(f"│ {i:>3} │ {nom:<40} │ {parser:<12} │ {att:>4} │ {ext:>4} │ {t:>5} │")
    lines.append("└" + "─" * 106 + "┘")
    lines.append("")

    # Statistiques par parser
    lines.append("=" * 110)
    lines.append("STATISTIQUES PAR PARSER")
    lines.append("=" * 110)
    par_parser = defaultdict(list)
    for r in resultats:
        par_parser[r["diag"]["parser_choisi"]].append(r)

    for parser_nom, rs in sorted(par_parser.items()):
        n = len(rs)
        taux_moy = sum(r["taux"]["global"] for r in rs) / n if n else 0
        ok = sum(1 for r in rs if r["taux"]["global"] >= 70)
        lines.append(f"\n  🔧 {parser_nom} ({n} fichiers)")
        lines.append(f"     Taux moyen : {taux_moy:.1f}%")
        lines.append(f"     Fichiers OK (>=70%) : {ok}/{n}")

    # Detail par fichier
    lines.append("")
    lines.append("=" * 110)
    lines.append("DETAIL PAR FICHIER")
    lines.append("=" * 110)

    for i, r in enumerate(resultats, 1):
        d = r["diag"]
        lines.append("")
        lines.append(f"{'━' * 110}")
        lines.append(f"[{i:>3}] {r['badge']} {r['nom']}")
        lines.append(f"{'━' * 110}")
        lines.append(f"  Extension : {r['ext']}")
        lines.append(f"")
        lines.append(f"  SIGNAUX DETECTES :")
        for signal, valeur in d.get("signaux", {}).items():
            if isinstance(valeur, bool):
                sym = "✅" if valeur else "❌"
                lines.append(f"    {sym} {signal} : {valeur}")
            else:
                lines.append(f"    • {signal} : {valeur}")
        lines.append(f"")
        lines.append(f"  PARSER CHOISI : {d['parser_choisi']}")
        lines.append(f"    Raison : {d['raison']}")
        lines.append(f"")
        lines.append(f"  EXTRACTION :")
        lines.append(f"    {'Zone':<18} {'Attendu':>8} {'Extrait':>8} {'Taux':>6}")
        for zone, lab in [("actif", "Actif"), ("passif", "Passif"), ("cr", "Compte resultat")]:
            lines.append(f"    {lab:<18} {r['attendu'].get(zone, 0):>8} {r['extrait'][zone]:>8} {r['taux'][zone]:>5}%")
        lines.append(f"    {'TOTAL':<18} {r['attendu'].get('total', 0):>8} {r['extrait']['total']:>8} {r['taux']['global']:>5}%  {r['badge']}")
        lines.append(f"")
        lines.append(f"  CA             : {r['ca']:>15,.0f}".replace(",", " "))
        lines.append(f"  Resultat net   : {r['rn']:>15,.0f}".replace(",", " "))
        lines.append(f"  Capitaux propres: {r['cp']:>15,.0f}".replace(",", " "))
        if r["equilibre"] is not None:
            eq = r["equilibre"]
            sym = "✅" if eq < 1 else "⚠️" if eq < 5 else "❌"
            lines.append(f"  Equilibre      : {eq:.2f}% {sym}")
        lines.append(f"  Ratios         : {r['ratios_ok']}/{r['ratios_total']}")
        if r["erreur"]:
            lines.append(f"  ❌ ERREUR : {r['erreur']}")
        lines.append(f"  Duree          : {r['duree_s']:.2f}s")

    lines.append("")
    lines.append("=" * 110)
    lines.append("SYNTHESE")
    lines.append("=" * 110)

    for parser_nom, rs in sorted(par_parser.items()):
        n = len(rs)
        par_badge = Counter(r["badge"] for r in rs)
        lines.append(f"  {parser_nom:15s} : {n:>3} fichiers | "
                     f"🟢={par_badge.get('🟢', 0)} 🟠={par_badge.get('🟠', 0)} 🔴={par_badge.get('🔴', 0)}")

    lines.append("")
    lines.append(f"  Duree totale : {sum(r['duree_s'] for r in resultats):.1f}s")
    lines.append("")
    lines.append("=" * 110)

    Path(chemin).write_text("\n".join(lines), encoding="utf-8")
    return chemin


# ============================================================
# POINT D'ENTREE
# ============================================================
if __name__ == "__main__":
    taille_lot = int(sys.argv[1]) if len(sys.argv) > 1 else 4

    fichiers = sorted(list(Path("data/raw").glob("*.pdf")) +
                     list(Path("data/raw").glob("*.xlsx")) +
                     list(Path("data/raw").glob("*.fec")))

    total = len(fichiers)
    print("=" * 110)
    print(f"ANALYSE DE {total} FICHIERS PAR LOTS DE {taille_lot} - AVEC DIAGNOSTIC PARSER")
    print("=" * 110)

    resultats = []
    t_debut = time.time()

    nb_lots = (total + taille_lot - 1) // taille_lot
    for lot_i in range(nb_lots):
        debut = lot_i * taille_lot
        fin = min(debut + taille_lot, total)

        print(f"\n{'═' * 110}")
        print(f"  LOT {lot_i + 1}/{nb_lots}  ·  Fichiers {debut + 1} à {fin} sur {total}")
        print(f"{'═' * 110}")

        for f in fichiers[debut:fin]:
            r = analyser(f)
            resultats.append(r)
            afficher(r)

    duree = time.time() - t_debut

    chemin = generer_rapport(resultats, "rapport_parser.txt")

    print()
    print("=" * 110)
    print("TERMINE")
    print("=" * 110)
    print(f"  Fichiers analyses : {total}")
    print(f"  Duree totale      : {duree:.1f}s")
    print(f"  Rapport           : {chemin}")
