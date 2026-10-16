"""Verification complete des calculs sur un fichier."""
import sys
from pathlib import Path
from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import filter_ratios


def fmt(v):
    if v is None:
        return "N/A"
    if isinstance(v, float) and abs(v) < 1000:
        return f"{v:>12.2f}"
    return f"{v:>12,.0f}".replace(",", " ")


def verifier(fichier):
    print("=" * 70)
    print(f"FICHIER : {Path(fichier).name}")
    print("=" * 70)

    data = BilanParser(fichier).parse_simple()

    print(f"\n--- POSTES EXTRAITS ---")
    print(f"Actif          : {len(data['actif'])} postes")
    print(f"Passif         : {len(data['passif'])} postes")
    print(f"Compte resultat: {len(data['compte_resultat'])} postes")

    # Agregats
    agg = Agregats(data).compute_all()

    print(f"\n--- AGREGATS CLES ---")
    checks = [
        ("chiffre_affaires", "CA"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebe", "EBE"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_actif", "Total actif"),
        ("total_passif", "Total passif"),
        ("total_dettes", "Total dettes"),
        ("bfr", "BFR"),
        ("fdr", "FDR"),
        ("tresorerie", "Tresorerie"),
    ]
    for code, label in checks:
        print(f"  {label:25s} : {fmt(agg.get(code))}")

    # Verifications
    print(f"\n--- VERIFICATIONS ---")
    ta, tp = agg.get("total_actif", 0), agg.get("total_passif", 0)
    ecart = abs(ta - tp)
    pct = (ecart / max(abs(ta), abs(tp), 1)) * 100
    status = "OK " if pct < 1 else "WARN"
    print(f"  [{status}] Equilibre bilan : Actif={fmt(ta)} vs Passif={fmt(tp)}  (ecart {pct:.2f}%)")

    # Ratios
    ratios = Ratios(agg).compute_all()
    ratios_f = filter_ratios(ratios, nb_exercices=4)

    print(f"\n--- RATIOS PAR CATEGORIE ---")
    for cat, d in ratios_f.items():
        print(f"\n  {cat.upper()} ({len(d)} ratios)")
        for nom, val in d.items():
            print(f"    {nom:35s} : {fmt(val)}")

    return agg, ratios_f


if __name__ == "__main__":
    # Prendre TOUS les fichiers de data/raw/
    fichiers = sorted(Path("data/raw").glob("*.xlsx")) + \
               sorted(Path("data/raw").glob("*.pdf")) + \
               sorted(Path("data/raw").glob("*.fec"))

    if not fichiers:
        print("Aucun fichier dans data/raw/")
        sys.exit(1)

    for f in fichiers:
        try:
            verifier(str(f))
            print()
        except Exception as e:
            print(f"ERREUR sur {f.name} : {e}\n")
