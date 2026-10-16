"""Validation complete sur tous les formats."""
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


def valider(fichier, nom_court=None):
    nom_court = nom_court or Path(fichier).name[:50]
    print("=" * 70)
    print(f"FICHIER : {nom_court}")
    print("=" * 70)

    try:
        data = BilanParser(fichier).parse_simple()
    except Exception as e:
        print(f"  ERREUR PARSING : {e}\n")
        return

    # Postes
    print(f"\n--- POSTES ---")
    print(f"  Actif          : {len(data['actif'])} postes")
    print(f"  Passif         : {len(data['passif'])} postes")
    print(f"  Compte resultat: {len(data['compte_resultat'])} postes")

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
        ("bfr", "BFR"),
        ("fdr", "FDR"),
        ("tresorerie", "Tresorerie"),
        ("total_stocks", "Total stocks"),
        ("dettes_financieres", "Dettes fin."),
    ]
    for code, label in checks:
        print(f"  {label:25s} : {fmt(agg.get(code))}")

    # Verifs
    print(f"\n--- VERIFICATIONS ---")
    ta, tp = agg.get("total_actif", 0), agg.get("total_passif", 0)
    if ta and tp:
        pct = abs(ta - tp) / max(abs(ta), abs(tp)) * 100
        status = "OK " if pct < 1 else "WARN"
        print(f"  [{status}] Equilibre bilan (ecart {pct:.2f}%)")
    else:
        print(f"  [WARN] Total actif ou passif manquant")

    # Ratios
    ratios = Ratios(agg).compute_all()
    ratios_f = filter_ratios(ratios, nb_exercices=4)
    print(f"\n--- RATIOS (extraits) ---")
    for cat, d in ratios_f.items():
        valeurs = [f"{k}={fmt(v).strip()}" for k, v in list(d.items())[:3]]
        print(f"  {cat:20s} : {' | '.join(valeurs)}")

    # Sanity checks
    print(f"\n--- SANITY CHECKS ---")
    checks_sanity = []

    # CA > 0
    if agg.get("chiffre_affaires", 0) > 0:
        checks_sanity.append(("OK", "CA > 0"))
    else:
        checks_sanity.append(("WARN", "CA = 0"))

    # Marge brute < 100%
    mb = ratios_f.get("rentabilite", {}).get("marge_brute", 0)
    if mb is not None and 0 <= mb <= 100:
        checks_sanity.append(("OK", f"Marge brute {mb:.1f}%"))
    else:
        checks_sanity.append(("WARN", f"Marge brute aberrante : {mb}"))

    # DSI
    dsi = ratios_f.get("gestion_activite", {}).get("dsi")
    if dsi is None:
        checks_sanity.append(("INFO", "DSI non calculable (pas de stock)"))
    elif 0 <= dsi <= 365:
        checks_sanity.append(("OK", f"DSI {dsi:.0f} jours"))
    else:
        checks_sanity.append(("WARN", f"DSI aberrante : {dsi}"))

    # DPO
    dpo = ratios_f.get("gestion_activite", {}).get("dpo")
    if dpo is None:
        checks_sanity.append(("INFO", "DPO non calculable"))
    elif 0 <= dpo <= 365:
        checks_sanity.append(("OK", f"DPO {dpo:.0f} jours"))
    else:
        checks_sanity.append(("WARN", f"DPO aberrante : {dpo}"))

    for status, msg in checks_sanity:
        print(f"  [{status}] {msg}")

    print()


# ============================================================
if __name__ == "__main__":
    fichiers = sorted(Path("data/raw").glob("*.xlsx")) + \
               sorted(Path("data/raw").glob("sogeca_2024.pdf")) + \
               sorted(Path("data/raw").glob("bilan_standard.pdf")) + \
               sorted(Path("data/raw").glob("bilan_test.pdf"))

    for f in fichiers:
        try:
            valider(str(f))
        except Exception as e:
            print(f"  ERREUR GLOBALE sur {f.name} : {e}\n")
