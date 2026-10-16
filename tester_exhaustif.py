"""Test exhaustif : extraction + agrégats + équilibre + score."""
from pathlib import Path
from collections import Counter, defaultdict
from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios


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


def tester(fichier):
    """Retourne un dict avec tous les diagnostics."""
    result = {
        "nom": fichier.name,
        "ext": fichier.suffix.lower(),
        "statut": "ERREUR",
        "postes": {"actif": 0, "passif": 0, "cr": 0, "total": 0},
        "agregats": {},
        "equilibre": None,
        "ca": 0,
        "rn": 0,
        "cp": 0,
        "dettes": 0,
        "erreur": None,
        "sanity": [],
    }

    try:
        parser = BilanParser(str(fichier))
        data = parser.parse_simple(force_ocr=False)

        result["postes"]["actif"] = len(data["actif"])
        result["postes"]["passif"] = len(data["passif"])
        result["postes"]["cr"] = len(data["compte_resultat"])
        result["postes"]["total"] = sum(result["postes"][k] for k in ["actif", "passif", "cr"])

        # Agregats
        agg = Agregats(data).compute_all()
        result["agregats"] = agg

        result["ca"] = agg.get("chiffre_affaires", 0)
        result["rn"] = agg.get("resultat_net", 0)
        result["cp"] = agg.get("capitaux_propres", 0)
        result["dettes"] = agg.get("total_dettes", 0)

        ta = agg.get("total_actif", 0)
        tp = agg.get("total_passif", 0)

        if ta and tp:
            pct = abs(ta - tp) / max(abs(ta), abs(tp)) * 100
            result["equilibre"] = pct
        elif ta or tp:
            result["equilibre"] = 100

        # Statut global
        total = result["postes"]["total"]
        if total >= 40:
            result["statut"] = "OK"
        elif total >= 15:
            result["statut"] = "PARTIEL"
        elif total >= 5:
            result["statut"] = "FAIBLE"
        else:
            result["statut"] = "KO"

        # Sanity checks
        if result["ca"] > 0:
            result["sanity"].append(("OK", f"CA={f_num(result['ca'])}"))
        else:
            result["sanity"].append(("WARN", "CA=0"))

        if result["equilibre"] is not None:
            if result["equilibre"] < 1:
                result["sanity"].append(("OK", f"Equilibre {result['equilibre']:.2f}%"))
            elif result["equilibre"] < 5:
                result["sanity"].append(("INFO", f"Equilibre {result['equilibre']:.2f}%"))
            else:
                result["sanity"].append(("WARN", f"Equilibre {result['equilibre']:.1f}%"))

        if result["cp"] != 0:
            result["sanity"].append(("OK", f"CP={f_num(result['cp'])}"))
        else:
            result["sanity"].append(("WARN", "CP=0"))

    except Exception as e:
        result["erreur"] = str(e)[:80]

    return result


# ============================================================
# COLLECTE
# ============================================================
fichiers = sorted(list(Path("data/raw").glob("*.pdf")) +
                 list(Path("data/raw").glob("*.xlsx")) +
                 list(Path("data/raw").glob("*.fec")) +
                 list(Path("data/raw").glob("*.csv")))

print("=" * 120)
print(f"TEST EXHAUSTIF — {len(fichiers)} FICHIERS")
print("=" * 120)

resultats = []
for f in fichiers:
    r = tester(f)
    resultats.append(r)

# ============================================================
# RAPPORT DETAILLE
# ============================================================
for r in resultats:
    sym = {"OK": "✅", "PARTIEL": "⚠️ ", "FAIBLE": "🟡", "KO": "❌", "ERREUR": "💥"}[r["statut"]]
    print()
    print(f"{sym} [{r['statut']:8s}] {r['nom']}")
    print(f"  Postes : Actif={r['postes']['actif']:>3}  Passif={r['postes']['passif']:>3}  CR={r['postes']['cr']:>3}  Total={r['postes']['total']:>3}")
    print(f"  CA     : {f_eur(r['ca'])}")
    print(f"  RN     : {f_eur(r['rn'])}")
    print(f"  CP     : {f_eur(r['cp'])}")
    print(f"  Dettes : {f_eur(r['dettes'])}")
    if r["equilibre"] is not None:
        print(f"  Equilibre bilan : {r['equilibre']:.2f}%")
    for status, msg in r["sanity"]:
        if status == "WARN":
            print(f"  ⚠️  {msg}")
    if r["erreur"]:
        print(f"  💥 ERREUR : {r['erreur']}")

# ============================================================
# RESUME GLOBAL
# ============================================================
print()
print("=" * 120)
print("RESUME GLOBAL")
print("=" * 120)

stats = Counter(r["statut"] for r in resultats)
for statut in ["OK", "PARTIEL", "FAIBLE", "KO", "ERREUR"]:
    n = stats.get(statut, 0)
    pct = n / len(resultats) * 100 if resultats else 0
    bar = "█" * int(pct / 2)
    print(f"  {statut:8s} : {n:>3} ({pct:>5.1f}%)  {bar}")

# Stats par extension
print()
print("  Par extension :")
exts = defaultdict(list)
for r in resultats:
    exts[r["ext"]].append(r)

for ext, rs in sorted(exts.items()):
    ok = sum(1 for r in rs if r["statut"] == "OK")
    part = sum(1 for r in rs if r["statut"] == "PARTIEL")
    ko = len(rs) - ok - part
    print(f"    {ext:8s} : {len(rs):>3} fichiers | OK={ok} PARTIEL={part} KO/ERR={ko}")

# ============================================================
# GROUPEMENT PAR ENTREPRISE
# ============================================================
print()
print("=" * 120)
print("PAR ENTREPRISE (les entreprises avec >= 2 fichiers)")
print("=" * 120)

entreprises = defaultdict(list)
for r in resultats:
    # Extraire nom entreprise
    nom = r["nom"]
    # Enlever l'extension
    nom = nom.rsplit(".", 1)[0]
    # Split sur " - " ou "-"
    for sep in [" - ", "-"]:
        if sep in nom:
            nom = nom.split(sep)[0].strip()
            break
    entreprises[nom].append(r)

for nom, rs in sorted(entreprises.items()):
    if len(rs) < 2:
        continue
    print()
    print(f"  🏢 {nom} ({len(rs)} fichiers)")
    for r in rs:
        sym = {"OK": "✅", "PARTIEL": "⚠️ ", "FAIBLE": "🟡", "KO": "❌", "ERREUR": "💥"}[r["statut"]]
        annee = ""
        for token in r["nom"].split():
            if token.isdigit() and len(token) == 4:
                annee = token
                break
        print(f"    {sym} {annee:>4} | Postes={r['postes']['total']:>3} | CA={f_num(r['ca'])} | RN={f_num(r['rn'])}")

# ============================================================
# DIAGNOSTIC FINAL
# ============================================================
print()
print("=" * 120)
print("DIAGNOSTIC")
print("=" * 120)

# Fichiers en echec
echecs = [r for r in resultats if r["statut"] in ("KO", "ERREUR")]
if echecs:
    print(f"\n  ❌ FICHIERS EN ECHEC ({len(echecs)}) :")
    for r in echecs:
        print(f"    - {r['nom']}")
        if r["erreur"]:
            print(f"      └─ {r['erreur']}")

# Fichiers avec desequilibre
desq = [r for r in resultats if r["equilibre"] and r["equilibre"] > 5]
if desq:
    print(f"\n  ⚠️  DESEQUILIBRE BILAN > 5% ({len(desq)}) :")
    for r in desq:
        print(f"    - {r['nom'][:70]:70s} : {r['equilibre']:.1f}%")

# Fichiers sans CA
no_ca = [r for r in resultats if r["ca"] == 0 and r["statut"] not in ("KO", "ERREUR")]
if no_ca:
    print(f"\n  ⚠️  SANS CA ({len(no_ca)}) :")
    for r in no_ca:
        print(f"    - {r['nom']}")

print()
print("=" * 120)
