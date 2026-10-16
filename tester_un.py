"""Teste un fichier specifique avec diagnostic complet."""
import sys
import time
from pathlib import Path
from src.extraction.etats_financiers import BilanParser
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios


def tester(fichier):
    print("=" * 100)
    print(f"FICHIER : {fichier}")
    print("=" * 100)
    print()

    t0 = time.time()
    try:
        parser = BilanParser(str(fichier))
        data = parser.parse_simple(force_ocr=False)
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        return

    duree = time.time() - t0

    # Postes
    nb_a = len(data["actif"])
    nb_p = len(data["passif"])
    nb_c = len(data["compte_resultat"])
    total = nb_a + nb_p + nb_c

    print(f"⏱  Duree : {duree:.2f}s")
    print()
    print(f"📊 POSTES EXTRAITS :")
    print(f"   Actif           : {nb_a:>4}")
    print(f"   Passif          : {nb_p:>4}")
    print(f"   Compte resultat : {nb_c:>4}")
    print(f"   ─────────────────────")
    print(f"   TOTAL           : {total:>4}")
    print()

    # Statut
    if total >= 40:
        badge = "🟢 EXCELLENT"
    elif total >= 25:
        badge = "🟢 BON"
    elif total >= 15:
        badge = "🟠 MOYEN"
    elif total >= 5:
        badge = "🟠 FAIBLE"
    else:
        badge = "🔴 CRITIQUE"
    print(f"   Taux de lecture : {badge}")
    print()

    # Agregats
    agg = Agregats(data).compute_all()

    print("💰 AGREGATS CLES :")
    for code, label in [
        ("chiffre_affaires", "CA"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
        ("total_actif", "Total actif"),
        ("total_passif", "Total passif"),
    ]:
        v = agg.get(code, 0) or 0
        print(f"   {label:20s} : {v:>15,.0f}".replace(",", " "))

    # Equilibre
    ta = agg.get("total_actif", 0) or 0
    tp = agg.get("total_passif", 0) or 0
    if ta and tp:
        ecart = abs(ta - tp) / max(abs(ta), abs(tp)) * 100
        sym = "✅" if ecart < 1 else "⚠️" if ecart < 5 else "❌"
        print(f"\n   Equilibre bilan : {ecart:.2f}% {sym}")
    print()

    # Ratios
    ratios = Ratios(agg).compute_all()
    print("📈 RATIOS (apercu) :")
    for cat, d in ratios.items():
        vals = [(k, v) for k, v in d.items() if v is not None]
        if vals:
            print(f"\n   {cat.upper()}")
            for nom, val in vals[:5]:
                if isinstance(val, float):
                    print(f"     {nom:35s} : {val:>10.2f}")
                else:
                    print(f"     {nom:35s} : {val:>10,.0f}".replace(",", " "))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python tester_un.py <chemin_fichier>")
        print()
        print("Exemples :")
        print("  python tester_un.py 'data/raw/HAPPY IMMO - Comptes sociaux 2022.pdf'")
        print("  python tester_un.py 'data/raw/ENTREP TRAVAUX ELECTRIQUES CANALISATIONS- Comptes sociaux 2024.xlsx'")
        sys.exit(1)

    fichier = Path(sys.argv[1])
    if not fichier.exists():
        print(f"❌ Fichier introuvable : {fichier}")
        sys.exit(1)

    tester(fichier)
