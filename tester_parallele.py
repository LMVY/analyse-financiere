"""Test exhaustif PARALLELE - utilise tous les coeurs CPU."""
import os
import time
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios


# ============================================================
# UTILITAIRES
# ============================================================
def f_eur(v):
    if v is None:
        return "N/A"
    return f"{v:>15,.0f}".replace(",", " ")


def f_num(v):
    if v is None:
        return "N/A"
    if abs(v) < 1000:
        return f"{v:>8.2f}"
    return f"{v:>8,.0f}"


def taux_lecture(nb_postes):
    if nb_postes >= 40:
        return 100
    if nb_postes <= 0:
        return 0
    if nb_postes < 15:
        return int(nb_postes / 15 * 60)
    return 60 + int((nb_postes - 15) / 25 * 40)


def badge(taux):
    if taux >= 70:
        return "🟢"
    if taux >= 50:
        return "🟠"
    return "🔴"


def label_taux(taux):
    if taux >= 90:
        return "EXCELLENT"
    if taux >= 70:
        return "BON"
    if taux >= 50:
        return "MOYEN"
    if taux >= 30:
        return "FAIBLE"
    return "CRITIQUE"


# ============================================================
# TEST D'UN FICHIER (executable dans un worker)
# ============================================================
def tester_worker(chemin_str):
    """Traite un fichier. Retourne un dict (picklable)."""
    fichier = Path(chemin_str)
    r = {
        "nom": fichier.name,
        "chemin": str(fichier),
        "ext": fichier.suffix.lower(),
        "statut": "ERREUR",
        "postes": {"actif": 0, "passif": 0, "cr": 0, "total": 0},
        "taux": 0,
        "badge": "🔴",
        "label": "CRITIQUE",
        "ca": 0, "rn": 0, "cp": 0, "dettes": 0,
        "ebitda": 0, "total_actif": 0, "total_passif": 0,
        "equilibre": None,
        "ratios_ok": 0, "ratios_total": 0,
        "erreur": None,
        "duree_s": 0,
    }

    t0 = time.time()
    try:
        parser = BilanParser(str(fichier))
        data = parser.parse_simple(force_ocr=False)

        r["postes"]["actif"] = len(data["actif"])
        r["postes"]["passif"] = len(data["passif"])
        r["postes"]["cr"] = len(data["compte_resultat"])
        r["postes"]["total"] = sum(r["postes"][k] for k in ["actif", "passif", "cr"])

        r["taux"] = taux_lecture(r["postes"]["total"])
        r["badge"] = badge(r["taux"])
        r["label"] = label_taux(r["taux"])

        if r["taux"] >= 70:
            r["statut"] = "OK"
        elif r["taux"] >= 50:
            r["statut"] = "PARTIEL"
        elif r["taux"] >= 30:
            r["statut"] = "FAIBLE"
        else:
            r["statut"] = "KO"

        agg = Agregats(data).compute_all()
        r["ca"] = agg.get("chiffre_affaires", 0) or 0
        r["rn"] = agg.get("resultat_net", 0) or 0
        r["cp"] = agg.get("capitaux_propres", 0) or 0
        r["dettes"] = agg.get("total_dettes", 0) or 0
        r["ebitda"] = agg.get("ebitda", 0) or 0
        r["total_actif"] = agg.get("total_actif", 0) or 0
        r["total_passif"] = agg.get("total_passif", 0) or 0

        ta, tp = r["total_actif"], r["total_passif"]
        if ta and tp:
            r["equilibre"] = abs(ta - tp) / max(abs(ta), abs(tp)) * 100

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
# EXECUTION PARALLELE
# ============================================================
def executer_parallele(fichiers, workers=None):
    """Execute le test sur tous les fichiers en parallele."""
    if workers is None:
        workers = min(os.cpu_count() or 4, 8)  # max 8 par defaut

    chemins = [str(f) for f in fichiers]
    resultats = []

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(tester_worker, c): c for c in chemins}

        fait = 0
        for future in as_completed(futures):
            fait += 1
            try:
                r = future.result()
                resultats.append(r)
                print(f"  [{fait:>2}/{len(chemins)}] {r['badge']} {r['taux']:>3}% | {r['nom'][:60]}")
            except Exception as e:
                print(f"  [{fait:>2}/{len(chemins)}] 💥 ERREUR : {e}")

    duree_totale = time.time() - t0

    # Garder l'ordre alphabetique
    resultats.sort(key=lambda x: x["nom"])

    return resultats, duree_totale, workers


# ============================================================
# GENERATION DU RAPPORT
# ============================================================
def generer_rapport(resultats, duree, workers, sortie="rapport_exhaustif.txt"):
    lines = []

    lines.append("=" * 110)
    lines.append("RAPPORT D'EXTRACTION EXHAUSTIF")
    lines.append(f"Fichiers analyses : {len(resultats)}")
    lines.append(f"Coeurs utilises   : {workers}")
    lines.append(f"Duree totale      : {duree:.1f} s")
    lines.append(f"Duree moyenne/fich: {duree/len(resultats):.2f} s")
    lines.append("=" * 110)
    lines.append("")

    # Tableau recap
    lines.append("┌" + "─" * 106 + "┐")
    lines.append(f"│ {'#':>3} │ {'FICHIER':<48} │ {'TYPE':<5} │ {'TAUX':>5} │ {'POST':>5} │ {'CA':>18} │")
    lines.append("├" + "─" * 106 + "┤")
    for i, r in enumerate(resultats, 1):
        nom = r["nom"][:47]
        ext = r["ext"][:5]
        taux = f"{r['taux']}%"
        postes = r["postes"]["total"]
        ca = f"{r['ca']:>18,.0f}".replace(",", " ")
        lines.append(f"│ {i:>3} │ {nom:<48} │ {ext:<5} │ {taux:>5} │ {postes:>5} │ {ca:>18} │")
    lines.append("└" + "─" * 106 + "┘")
    lines.append("")

    # Resume
    lines.append("=" * 110)
    lines.append("RESUME GLOBAL")
    lines.append("=" * 110)
    stats = Counter(r["statut"] for r in resultats)
    total = len(resultats)
    for statut in ["OK", "PARTIEL", "FAIBLE", "KO", "ERREUR"]:
        n = stats.get(statut, 0)
        pct = n / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        lines.append(f"  {statut:8s} : {n:>3} ({pct:>5.1f}%)  {bar}")
    lines.append("")

    exts = defaultdict(list)
    for r in resultats:
        exts[r["ext"]].append(r)
    lines.append("  Par extension :")
    for ext, rs in sorted(exts.items()):
        n_ok = sum(1 for r in rs if r["statut"] == "OK")
        n_part = sum(1 for r in rs if r["statut"] == "PARTIEL")
        n_ko = len(rs) - n_ok - n_part
        taux_moyen = sum(r["taux"] for r in rs) / len(rs) if rs else 0
        lines.append(f"    {ext:8s} : {len(rs):>3} fichiers | OK={n_ok:>2} PART={n_part:>2} KO={n_ko:>2} | Taux moy. {taux_moyen:.0f}%")
    lines.append("")

    # Detail
    lines.append("=" * 110)
    lines.append("DETAIL PAR FICHIER")
    lines.append("=" * 110)
    for i, r in enumerate(resultats, 1):
        lines.append("")
        lines.append(f"{'━' * 110}")
        lines.append(f"[{i:>3}] {r['nom']}  ({r['duree_s']:.2f}s)")
        lines.append(f"{'━' * 110}")
        lines.append(f"  Type : {r['ext']}")
        lines.append(f"  Taux de lecture : {r['taux']}%  {r['badge']}  {r['label']}")
        lines.append(f"")
        lines.append(f"  POSTES EXTRAITS")
        lines.append(f"    Actif           : {r['postes']['actif']:>4}")
        lines.append(f"    Passif          : {r['postes']['passif']:>4}")
        lines.append(f"    Compte resultat : {r['postes']['cr']:>4}")
        lines.append(f"    ─────────────────────")
        lines.append(f"    TOTAL           : {r['postes']['total']:>4}")
        lines.append(f"")
        lines.append(f"  AGREGATS CLES")
        lines.append(f"    Chiffre d'affaires : {f_eur(r['ca'])}")
        lines.append(f"    EBITDA             : {f_eur(r['ebitda'])}")
        lines.append(f"    Resultat net       : {f_eur(r['rn'])}")
        lines.append(f"    Capitaux propres   : {f_eur(r['cp'])}")
        lines.append(f"    Total dettes       : {f_eur(r['dettes'])}")
        lines.append(f"    Total actif        : {f_eur(r['total_actif'])}")
        lines.append(f"    Total passif       : {f_eur(r['total_passif'])}")
        lines.append(f"")
        if r["equilibre"] is not None:
            eq = r["equilibre"]
            sym = "✅" if eq < 1 else "⚠️" if eq < 5 else "❌"
            lines.append(f"  Equilibre bilan : {eq:.2f}%  {sym}")
        lines.append(f"  Ratios calcules : {r['ratios_ok']}/{r['ratios_total']}")
        if r["erreur"]:
            lines.append(f"  ❌ ERREUR : {r['erreur']}")

    # Par entreprise
    lines.append("")
    lines.append("=" * 110)
    lines.append("PAR ENTREPRISE")
    lines.append("=" * 110)
    entreprises = defaultdict(list)
    for r in resultats:
        nom = r["nom"].rsplit(".", 1)[0]
        for sep in [" - ", "-"]:
            if sep in nom:
                nom = nom.split(sep)[0].strip()
                break
        entreprises[nom].append(r)

    for nom, rs in sorted(entreprises.items()):
        if len(rs) < 2:
            continue
        lines.append("")
        lines.append(f"🏢 {nom} ({len(rs)} fichiers)")
        for r in sorted(rs, key=lambda x: x["nom"]):
            annee = ""
            for token in r["nom"].split():
                if token.isdigit() and len(token) == 4:
                    annee = token
                    break
            lines.append(
                f"    {r['badge']} {annee:>4} | Taux={r['taux']:>3}% | "
                f"Postes={r['postes']['total']:>3} | CA={f_num(r['ca'])} | RN={f_num(r['rn'])}"
            )

    # Diagnostic
    lines.append("")
    lines.append("=" * 110)
    lines.append("DIAGNOSTIC")
    lines.append("=" * 110)

    echecs = [r for r in resultats if r["statut"] in ("KO", "ERREUR")]
    if echecs:
        lines.append(f"\n  ❌ FICHIERS EN ECHEC ({len(echecs)}) :")
        for r in echecs:
            lines.append(f"    - {r['nom']}  [taux={r['taux']}%]")
            if r["erreur"]:
                lines.append(f"      └─ {r['erreur']}")

    desq = [r for r in resultats if r["equilibre"] and r["equilibre"] > 5]
    if desq:
        lines.append(f"\n  ⚠️  DESEQUILIBRE BILAN > 5% ({len(desq)}) :")
        for r in desq:
            lines.append(f"    - {r['nom'][:70]:70s} : {r['equilibre']:.1f}%")

    no_ca = [r for r in resultats if r["ca"] == 0 and r["statut"] not in ("KO", "ERREUR")]
    if no_ca:
        lines.append(f"\n  ⚠️  SANS CA ({len(no_ca)}) :")
        for r in no_ca:
            lines.append(f"    - {r['nom']}")

    # Top 5 plus lents
    lines.append("")
    lines.append("  🐌 TOP 5 FICHIERS LES PLUS LENTS :")
    for r in sorted(resultats, key=lambda x: -x["duree_s"])[:5]:
        lines.append(f"    {r['duree_s']:>6.2f}s | {r['nom'][:70]}")

    lines.append("")
    lines.append("=" * 110)
    lines.append(f"FIN DU RAPPORT — {len(resultats)} fichiers en {duree:.1f}s sur {workers} coeurs")
    lines.append("=" * 110)

    texte = "\n".join(lines)
    Path(sortie).write_text(texte, encoding="utf-8")
    return sortie, resultats


# ============================================================
# POINT D'ENTREE
# ============================================================
if __name__ == "__main__":
    import sys

    # Nombre de coeurs (parametrable en argument)
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else None

    fichiers = sorted(list(Path("data/raw").glob("*.pdf")) +
                     list(Path("data/raw").glob("*.xlsx")) +
                     list(Path("data/raw").glob("*.fec")))

    print(f"Analyse de {len(fichiers)} fichiers en parallele")
    print(f"Coeurs disponibles : {os.cpu_count()}")
    print()

    resultats, duree, workers_used = executer_parallele(fichiers, workers=workers)

    chemin, _ = generer_rapport(resultats, duree, workers_used, "rapport_exhaustif.txt")

    print()
    print(f"✅ Rapport genere : {chemin}")
    print(f"   Duree totale   : {duree:.1f} s")
    print(f"   Coeurs utilises: {workers_used}")
    print(f"   Vitesse moyenne: {duree/len(resultats):.2f} s/fichier")
    print()
    print("Voir le rapport :")
    print("  cat rapport_exhaustif.txt | less")
