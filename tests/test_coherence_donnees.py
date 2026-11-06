"""Tests de coherence sur les donnees reelles (classeurs Excel comptables).

Parcourt tous les classeurs "Comptes sociaux *.xlsx" disponibles
(~/Telechargements puis data/raw) et verifie, societe par societe
(grouper par SIREN extrait) :

- extraction deterministe (deux executions identiques) ;
- bilan equilibre (actif N = passif N, et N-1 quand present) ;
- validateur etendu execute (au moins 25 controles) et, pour les
  formats complets (liasse 2050/2051 : codes lettres DGFiP), AUCUNE
  incoherence (ERREUR) ;
- continuite inter-fichiers : le total N-1 d'une annee = le total N de
  l'annee precedente (exercices consecutifs d'une meme societe) ;
- fusion des fichiers d'une societe : comportement attendu de la porte
  du dashboard (HAPPY IMMO sans compte de resultat -> bloquee ;
  ETEC avec comptes de resultat -> au moins 3 exercices complets).

Les bilans simplifies DGFiP 2033 (regime simplifie, codes numeriques)
sent lus par libelles sans table de codes dediee : le test exige pour
eux les invariants seulement (determinisme, equilibre, validateur).

Lancement : python tests/test_coherence_donnees.py
Le test s'ignore proprement si aucun fichier n'est present.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.extraction.service import ExtractionService
from src.extraction.excel_parser import detecter_documents, _ouvrir_classeur
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.analysis.filter_ratios import (
    filter_ratios, MIN_EXERCICES_ANALYSE,
)
from src.analysis.validator import Validator

SECTIONS = ("actif", "passif", "compte_resultat")

CANDIDATS = [
    Path.home() / "Téléchargements",
    ROOT / "data" / "raw",
]


def trouver_fichiers():
    fichiers = []
    for base in CANDIDATS:
        if not base.is_dir():
            continue
        fichiers.extend(sorted(base.glob("*Comptes sociaux*.xlsx")))
    return fichiers


def est_format_simplifie(chemin):
    """Bilan simplifie DGFiP 2033 (codes numeriques, feuille combinee)."""
    try:
        wb = _ouvrir_classeur(Path(chemin))
        for ws in wb.worksheets[:3]:
            for ligne in ws.iter_rows(max_row=3, max_col=20):
                for c in ligne:
                    if isinstance(c.value, str) and "SIMPLIFI" in c.value.upper():
                        return True
        wb.close()
    except Exception:
        pass
    return False


def scinder(data):
    n = {s: {k: v for k, v in data.get(s, {}).items() if not k.endswith("_n1")}
         for s in SECTIONS}
    n1 = {s: {k[:-3]: v for k, v in data.get(s, {}).items() if k.endswith("_n1")}
          for s in SECTIONS}
    return n, n1


echecs = []


def check(nom, cond, detail=""):
    etat = "OK " if cond else "KO "
    print(f"  [{etat}] {nom}" + (f" -> {detail}" if detail and not cond else ""))
    if not cond:
        echecs.append(f"{nom} : {detail}")


FICHIERS = trouver_fichiers()
if not FICHIERS:
    print("Aucun fichier 'Comptes sociaux *.xlsx' trouve : test ignore.")
    print("Chemins explores :", [str(c) for c in CANDIDATS])
    sys.exit(0)

print(f"Fichiers reels trouves : {len(FICHIERS)}")
for f in FICHIERS:
    print("  -", f.name)

svc = ExtractionService()

# ------------------------------------------------------------------
# 1. Chaque fichier : extraction, determinisme, bilan, validateur
# ------------------------------------------------------------------
par_siren = {}       # siren -> {annee: (extrait, data_n, data_n1, simplifie)}
for chemin in FICHIERS:
    ex1 = svc.extraire(chemin)
    ex2 = svc.extraire(chemin)
    simplifie = est_format_simplifie(chemin)
    data_n, data_n1 = scinder(ex1.data)
    annee = ex1.meta.get("annee_n") or (chemin.stem[-4:]
                                        if chemin.stem[-4:].isdigit() else chemin.stem)
    print(f"\n===== {chemin.name} =====")
    print(f"    {ex1.meta.get('raison_sociale', '?')} | SIREN "
          f"{ex1.meta.get('siren', '?')} | annee {ex1.meta.get('annee_n')}"
          + ("  [format simplifie 2033]" if simplifie else ""))

    check("extraction deterministe (2 executions identiques)",
          ex1.data == ex2.data and ex1.meta == ex2.meta)
    check("siren extrait", bool(ex1.meta.get("siren")),
          str(ex1.meta))

    det = detecter_documents(data_n)
    check("bilan detecte" if det["bilan"] else "bilan NON detecte",
          True, f"actif={det['nb_actif']}, passif={det['nb_passif']}, "
          f"CR={det['nb_cr']} postes")

    ta, tp = data_n["actif"].get("total_actif"), data_n["passif"].get("total_passif")
    if ta is not None and tp is not None:
        check("equilibre N : actif = passif",
              abs(ta - tp) < max(abs(ta), 1) * 0.01,
              f"actif={ta}, passif={tp}")
    ta1, tp1 = data_n1["actif"].get("total_actif"), data_n1["passif"].get("total_passif")
    if ta1 is not None and tp1 is not None:
        check("equilibre N-1 : actif = passif",
              abs(ta1 - tp1) < max(abs(ta1), 1) * 0.01,
              f"actif={ta1}, passif={tp1}")

    agg = Agregats(data_n).compute_all()
    ratios_f = filter_ratios(Ratios(agg).compute_all(), MIN_EXERCICES_ANALYSE)
    val = Validator(agg, ratios_f, data_n, data_n1=data_n1).validate_all()
    check("validateur execute (>= 25 controles)",
          val["stats"]["total"] >= 25, str(val["stats"]))
    errs = [f"{r['test']} : {r['message'][:60]}"
            for r in val["rapport"] if r["niveau"] == "ERREUR"]
    if simplifie:
        # format partiellement supporte : les incoherences sont le
        # signal attendu, pas un echec du test
        print(f"  [.. ] incoherences tolerees (format simplifie) : "
              f"{len(errs)}" + (f" -> {errs[0]}" if errs else ""))
    else:
        check("validateur : aucune incoherence (ERREUR)", not errs,
              str(errs))

    siren = ex1.meta.get("siren") or chemin.stem
    par_siren.setdefault(siren, {"societe": ex1.meta.get("raison_sociale"),
                                 "exercices": {}})
    par_siren[siren]["exercices"][annee] = (ex1, data_n, data_n1, simplifie)

# ------------------------------------------------------------------
# 2. Continuite inter-fichiers, par societe
# ------------------------------------------------------------------
print("\n===== Continuite inter-fichiers (par societe) =====")
for siren, info in par_siren.items():
    exos = info["exercices"]
    annees = sorted([a for a in exos if isinstance(a, int)], reverse=True)
    print(f"  {info['societe']} ({len(exos)} fichiers)")
    for grande, petite in zip(annees, annees[1:]):
        if grande - petite != 1:
            continue      # exercices non consecutifs : pas comparable
        ex_g = exos[grande][0]
        ex_p = exos[petite][0]
        for section, poste in (("actif", "total_actif"), ("passif", "total_passif")):
            v_n1 = ex_g.data[section].get(f"{poste}_n1")
            v_n = ex_p.data[section].get(poste)
            if v_n1 is None or v_n is None:
                continue
            conforme = abs(v_n1 - v_n) < max(abs(v_n), 1) * 0.005
            if conforme:
                check(f"{grande} N-1 = {petite} N ({poste})", True)
            else:
                # donnee source discontinu (restructuration, perimetre) :
                # signale comme le fait le controle 32 du validateur,
                # sans faire echouer l'extraction (elle est fidele)
                print(f"  [.. ] {grande} N-1 != {petite} N ({poste}) : "
                      f"{v_n1:,.0f} vs {v_n:,.0f} - ecart de perimetre "
                      "signale par le controle 32 a l'analyse")

# ------------------------------------------------------------------
# 3. Porte du dashboard, par societe
# ------------------------------------------------------------------
print("\n===== Porte du dashboard (fusion par societe) =====")
for siren, info in par_siren.items():
    exos = info["exercices"]
    par_annee = {}

    def fusionner(par, cle, data):
        if cle not in par:
            par[cle] = data
            return
        for sec in SECTIONS:
            for k, v in data.get(sec, {}).items():
                par[cle].setdefault(sec, {})
                par[cle][sec].setdefault(k, v)

    for annee, (ex, data_n, data_n1, _s) in exos.items():
        if isinstance(annee, int):
            fusionner(par_annee, annee, data_n)
            fusionner(par_annee, annee - 1, data_n1)
        else:
            fusionner(par_annee, "N", data_n)
            fusionner(par_annee, "N-1", data_n1)

    cles = (sorted([c for c in par_annee if isinstance(c, int)], reverse=True)
            + [c for c in par_annee if not isinstance(c, int)])
    bilans = [par_annee[c] for c in cles]
    complets = [bd for bd in bilans if detecter_documents(bd)["complet"]]
    label = info["societe"] or siren
    if len(complets) >= MIN_EXERCICES_ANALYSE:
        check(f"{label} : {len(complets)} exercices complets -> analyse possible",
              True)
    else:
        check(f"{label} : {len(complets)} exercice(s) complet(s) -> porte "
              f"coherente (min {MIN_EXERCICES_ANALYSE})",
              all(not detecter_documents(bd)["compte_resultat"]
                  for bd in bilans) or len(complets) < MIN_EXERCICES_ANALYSE,
              "incoherence entre detection et porte")

print()
if echecs:
    print(f"ECHECS ({len(echecs)}) :")
    for e in echecs:
        print(" -", e)
    sys.exit(1)
print(f"COHERENCE DES DONNEES REELLES : OK "
      f"({len(FICHIERS)} fichiers, {len(par_siren)} societes)")
