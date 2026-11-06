"""Import des ratios sectoriels reels (BCE/INPI) dans secteurs_config.yaml.

Source : jeu de donnees officiel "indicateurs sectoriels financiers
(BCE/INPI)" - data.economie.gouv.fr, Licence Ouverte v2.
Percentiles (q10/q25/q50/q75/q90) par secteur x tranche de chiffre
d'affaires x exercice, cohortes de >= 50 bilans reels.

Le script :
1. telecharge le CSV (ou lit un fichier local avec --fichier) ;
2. detecte automatiquement les colonnes (secteur, tranche de CA,
   exercice, ratio, percentiles) ;
3. mappe les ratios du CSV vers les 33 ratios de la config ;
4. ramene les codes NAF aux sections puis a nos 8 secteurs ;
5. met a jour secteurs_config.yaml : q1 = q25, mediane = q50,
   q3 = q75, source = "BCE/INPI (exercice X)". Les ratios absents du
   CSV gardent leurs valeurs actuelles (indicatives).

Lancement (avec internet) :
    python scripts/import_referentiel_bce.py            # import reel
    python scripts/import_referentiel_bce.py --dry-run  # rapport seul
    python scripts/import_referentiel_bce.py --fichier ratios.csv --dry-run
Options :
    --exercice 2021    exercice a importer (defaut : le plus recent)
    --tranche ...      tranche de CA (defaut : toutes tailles si
                       presente, sinon la premiere trouvee ; la liste
                       des tranches disponibles est affichee)
    --secteurs-path config/secteurs_config.yaml
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from src.scoring.sector_scorer import DIVISIONS_NAF  # noqa: E402

URL_CSV = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/"
           "datasets/ratios_inpi_bce_sectors/exports/csv")

# nos secteurs : section NAF -> code du referentiel
SECTIONS = {
    "C": "industrie", "F": "construction", "G": "commerce", "H": "transport",
    "I": "hotellerie_restauration", "J": "information_communication",
    "L": "immobilier", "M": "services", "N": "services",
}

# candidats de noms de colonnes (minuscules, sans accents)
CAND_SECTEUR = ["secteur", "section_naf", "code_naf", "naf", "code_ape",
                "ape", "activite", "division"]
CAND_TRANCHE = ["tranche_ca", "tranche", "taille", "classe_ca", "ca"]
CAND_EXERCICE = ["exercice", "annee", "year", "date_cloture", "cloture"]
CAND_RATIO = ["ratio", "indicateur", "nom_ratio", "libelle_ratio", "libelle"]
CAND_Q = {"q1": ["q25", "percentile_25", "p25"],
          "mediane": ["q50", "percentile_50", "p50"],
          "q3": ["q75", "percentile_75", "p75"]}

# mapping : notre ratio -> candidats (mots-cles, sans accents)
MATCH = {
    "current_ratio": ["liquidite generale", "current ratio", "liquidite globale"],
    "quick_ratio": ["liquidite reduite", "quick ratio", "liquidite rapide"],
    "cash_ratio": ["liquidite immediate", "cash ratio", "tresorerie / passif"],
    "liquidite_immediate": ["tresorerie / dettes financieres"],
    "tresorerie_ca": ["tresorerie / chiffre", "tresorerie sur ca"],
    "couverture_caf_dette": ["caf / dette", "couverture caf", "caf sur dettes"],
    "gearing": ["gearing", "endettement financier / capitaux", "dette financiere / capitaux"],
    "levier_financier": ["levier financier", "endettement total / capitaux", "total dettes / capitaux"],
    "dette_nette_ebitda": ["dette nette / ebitda", "dette nette ebitda"],
    "dette_nette_fonds_propres": ["dette nette / fonds propres", "dette nette / capitaux propres"],
    "capacite_desendettement": ["capacite de desendettement", "capacite de remboursement", "dette / caf"],
    "autonomie_financiere": ["autonomie financiere"],
    "equilibre_financier": ["equilibre financier", "ressources stables"],
    "marge_brute": ["marge brute"],
    "marge_ebitda": ["marge d'ebitda", "marge ebitda", "marge brute d'excedent"],
    "marge_operationnelle": ["marge operationnelle", "marge d'exploitation", "resultat d'exploitation / ca"],
    "marge_nette": ["marge nette", "resultat net / chiffre", "taux de profit"],
    "roe": ["rentabilite financiere", "rentabilite des capitaux propres", "roe", "return on equity"],
    "roa": ["rentabilite des actifs", "roa", "return on assets", "rentabilite economique"],
    "roce": ["roce", "rentabilite du capital"],
    "croissance_ca": ["croissance du chiffre", "variation du chiffre", "taux de croissance"],
    "croissance_ebitda": ["croissance ebitda", "croissance de l'ebitda"],
    "croissance_resultat_net": ["croissance du resultat net", "variation du resultat net"],
    "croissance_capitaux_propres": ["croissance des capitaux propres", "croissance des fonds propres"],
    "dsi": ["duree de stockage", "duree de rotation des stocks", "poids des stocks", "stocks en jours"],
    "dpo": ["delai de paiement fournisseurs", "delai fournisseurs", "credit fournisseurs", "dpo", "duree de paiement"],
    "rotation_stocks": ["rotation des stocks", "taux de rotation des stocks"],
    "rotation_actif": ["rotation de l'actif", "rotation de l'actif total", "actif / chiffre d'affaires"],
    "rotation_immobilisations": ["rotation des immobilisations", "actif immobilise /"],
    "cycle_conversion_tresorerie": ["cycle de conversion", "cycle d'exploitation", "ccc"],
    "ratio_solvabilite": ["solvabilite", "capitaux propres / total", "capitaux propres / dettes"],
    "ratio_couverture_dettes": ["actif total / dettes", "couverture des dettes"],
    "ratio_liquidite_large": ["liquidite large"],
}


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def detecter_colonnes(entetes):
    """Trouve les colonnes par candidats ; retourne (dict, introuvables)."""
    trouves, manquants = {}, []
    normes = {norm(h): h for h in entetes}

    def cherche(cle, candidats, obligatoire=True):
        for cand in candidats:
            for n, orig in normes.items():
                if cand in n:
                    trouves[cle] = orig
                    return
        if obligatoire:
            manquants.append(cle)

    cherche("secteur", CAND_SECTEUR)
    cherche("exercice", CAND_EXERCICE)
    cherche("ratio", CAND_RATIO)
    for cle, cands in CAND_Q.items():
        cherche(cle, cands)
    cherche("tranche", CAND_TRANCHE, obligatoire=False)
    return trouves, manquants


def section_naf_valeur(v):
    """Valeur de secteur du CSV -> lettre de section NAF ou None."""
    v = str(v).strip().upper()
    if not v:
        return None
    if v[0].isalpha() and len(v) <= 4:
        return v[0]
    m = re.match(r"(\d{2})", v)
    return DIVISIONS_NAF.get(m.group(1)) if m else None


def lire_csv(chemin, url, dry_run):
    if chemin:
        lignes = open(chemin, encoding="utf-8", errors="replace").read()
    else:
        import urllib.request
        print(f"Telechargement : {url} ...")
        with urllib.request.urlopen(url) as r:
            lignes = r.read().decode("utf-8", errors="replace")
    sep = ";" if lignes.splitlines()[0].count(";") >= lignes.splitlines()[0].count(",") else ","
    return list(csv.DictReader(lignes.splitlines(), delimiter=sep))


def nombre(v):
    if v is None:
        return None
    v = str(v).strip().replace(" ", "").replace("\u202f", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fichier", help="CSV local (si telechargement manuel)")
    ap.add_argument("--url", default=URL_CSV)
    ap.add_argument("--exercice", default=None)
    ap.add_argument("--tranche", default=None)
    ap.add_argument("--secteurs-path",
                    default=str(ROOT / "config" / "secteurs_config.yaml"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import yaml

    lignes = lire_csv(args.fichier, args.url, args.dry_run)
    if not lignes:
        sys.exit("CSV vide ou illisible.")
    cols, manquants = detecter_colonnes(lignes[0].keys())
    if manquants:
        print("Colonnes du CSV :", list(lignes[0].keys()))
        sys.exit(f"Colonnes introuvables : {manquants} - "
                 "ajoute des candidats dans CAND_* du script.")
    print("Colonnes detectees :", cols)

    # exercice
    exercices = sorted({r[cols["exercice"]] for r in lignes}, reverse=True)
    exercice = args.exercice or exercices[0]
    print("Exercices disponibles :", exercices, "-> import :", exercice)
    lignes = [r for r in lignes if r[cols["exercice"]] == exercice]

    # tranche de CA
    tranches = sorted({(r.get(cols["tranche"]) or "").strip() for r in lignes})
    tranche = args.tranche
    if cols["tranche"] and not tranche:
        for t in ("toutes", "ensemble", "total", "tous", "100", "0"):
            if any(t in (tr or "").lower() for tr in tranches):
                tranche = next(tr for tr in tranches if t in tr.lower())
                break
        tranche = tranche or (tranches[0] if tranches else None)
    if cols["tranche"]:
        print("Tranches disponibles :", tranches, "-> import :", tranche)
        lignes = [r for r in lignes if (r.get(cols["tranche"]) or "").strip() == tranche]

    # secteur + ratio -> percentiles
    refs = defaultdict(lambda: defaultdict(dict))   # notre_secteur -> ratio -> {q1,med,q3}
    ratios_csv = defaultdict(set)
    non_mappe = set()
    for r in lignes:
        sec = SECTIONS.get(section_naf_valeur(r[cols["secteur"]]))
        nom_csv = norm(r[cols["ratio"]])
        ratios_csv[nom_csv].add(r[cols["ratio"]])
        cible = None
        for notre, cands in MATCH.items():
            if any(c in nom_csv for c in cands):
                cible = notre
                break
        if not cible:
            non_mappe.add(r[cols["ratio"]])
            continue
        if not sec:
            continue
        vals = {}
        for cle in ("q1", "mediane", "q3"):
            v = nombre(r.get(cols[cle]))
            if v is not None:
                vals[cle] = v
        if len(vals) == 3:
            refs[sec][cible] = vals   # si plusieurs lignes : la derniere gagne

    print(f"\nRatios du CSV : {len(ratios_csv)} noms distincts ; "
          f"non mappes : {len(non_mappe)}")
    for n in sorted(non_mappe)[:20]:
        print("   non mappe :", n)

    # mise a jour du referentiel
    with open(args.secteurs_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    source = f"BCE/INPI (exercice {exercice}"
    if tranche:
        source += f", tranche {tranche}"
    source += ")"
    maj = 0
    for sec, ratios in refs.items():
        if sec not in cfg:
            continue
        for nom, vals in ratios.items():
            if nom not in cfg[sec]["ratios"]:
                continue
            cfg[sec]["ratios"][nom] = {
                "mediane": vals["mediane"], "q1": vals["q1"],
                "q3": vals["q3"], "source": source}
            maj += 1
    print(f"\n{maj} references mises a jour "
          f"(sur {sum(len(s['ratios']) for s in cfg.values())}).")
    for sec in cfg:
        n = len([r for r in cfg[sec]["ratios"].values()
                 if r.get("source") == source])
        print(f"   {sec}: {n}/33 ratios avec donnees BCE/INPI")

    if args.dry_run:
        print("\n--dry-run : rien n'a ete ecrit.")
        return
    with open(args.secteurs_path, "w", encoding="utf-8") as f:
        f.write("# Referentiel sectoriel mis a jour par import BCE/INPI "
                f"(source : {source}).\n"
                "# Valeurs indicatives conservees pour les ratios absents "
                "du jeu de donnees.\n")
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False,
                  sort_keys=False, width=100)
    print(f"\n{args.secteurs_path} mis a jour.")


if __name__ == "__main__":
    main()
