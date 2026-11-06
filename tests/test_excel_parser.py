"""Tests du lecteur Excel : genere ses propres classeurs de test dans
data/raw/test_excel puis verifie extraction, detection bilan/compte de
resultat et integrations au pipeline (agregats, ratios, porte).

Lancement : python tests/test_excel_parser.py (depuis la racine du projet)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from openpyxl import Workbook

from src.extraction.excel_parser import ExcelParser, detecter_documents
from src.extraction.controle_extraction import scorer_extraction
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios

TMP = ROOT / "data" / "raw" / "test_excel"
TMP.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Fixture 1 : bilan detaille (brut / amort / net par exercice)
# ------------------------------------------------------------------
wb = Workbook()
ws = wb.active
ws.title = "Actif"
ws["A1"] = "ENTREPRISE TEST SAS"
ws["A2"] = "SIREN : 123 456 789"
ws["C2"] = "Code NAF : 25.11Z"
ws["A4"] = "Libellé"
ws["B4"] = "2024"
ws["E4"] = "2023"
ws["A5"], ws["B5"], ws["C5"], ws["D5"] = "", "Brut", "Amortissements", "Net"
ws["E5"], ws["F5"], ws["G5"] = "Brut", "Amortissements", "Net"

actif_rows = [
    ("Immobilisations incorporelles", (60000, 10000, 50000, 70000, 10000, 60000)),
    ("Installations techniques, matériel et outillage industriel", (500000, 100000, 400000, 540000, 120000, 420000)),
    ("Autres immobilisations corporelles", (180000, 30000, 150000, 190000, 30000, 160000)),
    ("Autres immobilisations financières", (30000, 0, 30000, 30000, 0, 30000)),
    ("Total actif immobilisé", (None, None, 630000, None, None, 670000)),
    ("Stocks et en-cours", (None, None, 120000, None, None, 110000)),
    ("Créances clients et comptes rattachés", (None, None, 170000, None, None, 115000)),
    ("Disponibilités", (None, None, 40000, None, None, 35000)),
    ("Total actif circulant", (None, None, 330000, None, None, 260000)),
    ("TOTAL GÉNÉRAL", (None, None, 960000, None, None, 930000)),
]
for i, (lab, vals) in enumerate(actif_rows, start=6):
    ws.cell(row=i, column=1, value=lab)
    for j, v in enumerate(vals):
        if v is not None:
            ws.cell(row=i, column=2 + j, value=v)

wp = wb.create_sheet("Passif")
wp["A1"] = "Libellé"
wp["B1"] = "Exercice 2024"
wp["C1"] = "Exercice 2023"
passif_rows = [
    ("Capital social", 400000, 400000),
    ("Autres réserves", 120000, 100000),
    ("Report à nouveau", 30000, 20000),
    ("Résultat de l'exercice", 50000, 5000),
    ("Total capitaux propres", 600000, 525000),
    ("Emprunts et dettes auprès des établissements de crédit", 250000, 270000),
    ("Dettes fournisseurs et comptes rattachés", 80000, 100000),
    ("Dettes fiscales et sociales", 30000, 35000),
    ("Total des dettes", 360000, 405000),
    ("TOTAL GÉNÉRAL", 960000, 930000),
]
for i, (lab, v, v1) in enumerate(passif_rows, start=2):
    wp.cell(row=i, column=1, value=lab)
    wp.cell(row=i, column=2, value=v)
    wp.cell(row=i, column=3, value=v1)

p_bilan = TMP / "bilan_2024.xlsx"
wb.save(p_bilan)

# ------------------------------------------------------------------
# Fixture 2 : compte de resultat sans en-tetes, montants francais
# ------------------------------------------------------------------
wb2 = Workbook()
wc = wb2.active
wc.title = "Compte de résultat"
cr_rows = [
    ("Chiffre d'affaires", "1 200 000,00", "1 100 000,00"),
    ("Achats de matières premières", "400 000,00", "380 000,00"),
    ("Autres achats et charges externes", "250 000,00", "240 000,00"),
    ("Impôts et taxes", "20 000,00", "18 000,00"),
    ("Salaires et traitements", "300 000,00", "290 000,00"),
    ("Charges sociales", "120 000,00", "115 000,00"),
    ("Dotations aux amortissements", "40 000,00", "45 000,00"),
    ("Résultat d'exploitation", "70 000,00", "12 000,00"),
    ("Intérêts et charges assimilées", "10 000,00", "12 000,00"),
    ("Résultat courant avant impôts", "60 000,00", "0,00"),
    ("Impôts sur les bénéfices", "10 000,00", "(5 000,00)"),
    ("Résultat net", "50 000,00", "5 000,00"),
]
for i, (lab, v, v1) in enumerate(cr_rows, start=1):
    wc.cell(row=i, column=1, value=lab)
    wc.cell(row=i, column=2, value=v)
    wc.cell(row=i, column=3, value=v1)

p_cr = TMP / "compte_resultat_2024.xlsx"
wb2.save(p_cr)

# ------------------------------------------------------------------
# Fixture 3 : liasse combinee (bilan actif+passif / compte de resultat)
# ------------------------------------------------------------------
wb3 = Workbook()
wb3["Sheet"].title = "Bilan"
wsb = wb3["Bilan"]
wsb["A1"], wsb["B1"], wsb["C1"] = "Libellé", "2024", "2023"
bilan_rows = [
    ("Immobilisations incorporelles", 50000, 60000),
    ("Total actif immobilisé", 630000, 670000),
    ("Stocks et en-cours", 120000, 110000),
    ("Créances clients et comptes rattachés", 170000, 115000),
    ("Disponibilités", 40000, 35000),
    ("Total actif circulant", 330000, 260000),
    ("TOTAL GÉNÉRAL", 960000, 930000),
    ("Capital social", 400000, 400000),
    ("Autres réserves", 120000, 100000),
    ("Report à nouveau", 30000, 20000),
    ("Résultat de l'exercice", 50000, 5000),
    ("Total capitaux propres", 600000, 525000),
    ("Emprunts et dettes auprès des établissements de crédit", 250000, 270000),
    ("Dettes fournisseurs et comptes rattachés", 80000, 100000),
    ("Dettes fiscales et sociales", 30000, 35000),
    ("Total des dettes", 360000, 405000),
    ("TOTAL GÉNÉRAL", 960000, 930000),
]
for i, (lab, v, v1) in enumerate(bilan_rows, start=2):
    wsb.cell(row=i, column=1, value=lab)
    wsb.cell(row=i, column=2, value=v)
    wsb.cell(row=i, column=3, value=v1)
wsc = wb3.create_sheet("Compte de résultat")
wsc["A1"], wsc["B1"], wsc["C1"] = "Libellé", "2024", "2023"
for i, (lab, v, v1) in enumerate(cr_rows, start=2):
    wsc.cell(row=i, column=1, value=lab)
    wsc.cell(row=i, column=2, value=v)
    wsc.cell(row=i, column=3, value=v1)

p_liasse = TMP / "liasse_2024.xlsx"
wb3.save(p_liasse)

# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------
parser = ExcelParser()
echecs = []


def check(nom, cond, detail=""):
    etat = "OK " if cond else "KO "
    print(f"  [{etat}] {nom}" + (f" -> {detail}" if detail and not cond else ""))
    if not cond:
        echecs.append(f"{nom} : {detail}")


print("=== 1. Bilan detaille (brut/amort/net, en-tetes annees) ===")
data_bilan, meta_b = parser.lire(p_bilan)
check("meta siren", meta_b.get("siren") == "123456789", str(meta_b))
check("meta naf", meta_b.get("code_naf") == "25.11Z", str(meta_b))
check("meta raison sociale", meta_b.get("raison_sociale") == "ENTREPRISE TEST SAS", str(meta_b))
check("annees detectees", meta_b.get("annee_n") == 2024 and meta_b.get("annee_n1") == 2023, str(meta_b))
a = data_bilan["actif"]
check("net inc incorporelles (pas brut)", a.get("immobilisations_incorporelles") == 50000, str(a.get("immobilisations_incorporelles")))
check("net inc corporelles", a.get("installations_techniques") == 400000, str(a.get("installations_techniques")))
check("total actif", a.get("total_actif") == 960000, str(a.get("total_actif")))
check("total actif n-1", a.get("total_actif_n1") == 930000, str(a.get("total_actif_n1")))
check("stocks", a.get("total_stocks") == 120000, str(a.get("total_stocks")))
p = data_bilan["passif"]
check("capital", p.get("capital_social") == 400000, str(p.get("capital_social")))
check("total passif", p.get("total_passif") == 960000, str(p.get("total_passif")))
check("resultat exercice au passif", p.get("resultat_exercice") == 50000, str(p.get("resultat_exercice")))
det = detecter_documents(data_bilan)
check("bilan detecte", det["bilan"], str(det))
check("CR absent", not det["compte_resultat"], str(det))

print("\n=== 2. Compte de resultat (sans en-tetes, montants textuels) ===")
data_cr, meta_c = parser.lire(p_cr)
cr = data_cr["compte_resultat"]
check("CA", cr.get("chiffre_affaires") == 1200000.0, str(cr.get("chiffre_affaires")))
check("CA n-1", cr.get("chiffre_affaires_n1") == 1100000.0, str(cr.get("chiffre_affaires_n1")))
check("negatif entre parentheses", cr.get("impots_benefices_n1") == -5000.0, str(cr.get("impots_benefices_n1")))
check("resultat net", cr.get("resultat_net") == 50000.0, str(cr.get("resultat_net")))
check("resultat net n-1", cr.get("resultat_net_n1") == 5000.0, str(cr.get("resultat_net_n1")))
check("pas de pollution passif", len(data_cr["passif"]) == 0, str(data_cr["passif"]))
det = detecter_documents(data_cr)
check("CR detecte", det["compte_resultat"], str(det))
check("bilan absent", not det["bilan"], str(det))

print("\n=== 3. Fusion des deux fichiers -> pipeline complet ===")
fusion = {sec: {} for sec in ("actif", "passif", "compte_resultat")}
for src in (data_bilan, data_cr):
    for sec in fusion:
        for k, v in src[sec].items():
            fusion[sec].setdefault(k, v)
det = detecter_documents(fusion)
check("bilan + CR detectes", det["bilan"] and det["compte_resultat"], str(det))

ctrl = scorer_extraction(fusion, "excel")
check("controle acceptable", ctrl.acceptable, f"statut={ctrl.statut} score={ctrl.score} problemes={ctrl.problemes}")

agg = Agregats(fusion).compute_all()
check("CA agregat", agg.get("chiffre_affaires") == 1200000, str(agg.get("chiffre_affaires")))
check("RN agregat", agg.get("resultat_net") == 50000, str(agg.get("resultat_net")))
check("capitaux propres", agg.get("capitaux_propres") == 600000, str(agg.get("capitaux_propres")))
ratios = Ratios(agg).compute_all()
nb_ratios = sum(len(v) for v in ratios.values() if isinstance(v, dict))
check("ratios calcules", nb_ratios > 10, f"{nb_ratios} ratios")
print("  categories :", {k: len(v) for k, v in ratios.items() if isinstance(v, dict)})

print("\n=== 4. Liasse combinee (bilan complet + CR dans un classeur) ===")
data_l, meta_l = parser.lire(p_liasse)
check("total general actif", data_l["actif"].get("total_actif") == 960000,
      str(data_l["actif"].get("total_actif")))
check("total general passif (2e occurrence)",
      data_l["passif"].get("total_passif") == 960000,
      str(data_l["passif"].get("total_passif")))
check("resultat de l'exercice -> passif",
      data_l["passif"].get("resultat_exercice") == 50000,
      str(data_l["passif"].get("resultat_exercice")))
check("impots benefices -> compte_resultat",
      data_l["compte_resultat"].get("impots_benefices") == 10000,
      str(data_l["compte_resultat"].get("impots_benefices")))
det = detecter_documents(data_l)
check("liasse : bilan + CR", det["bilan"] and det["compte_resultat"], str(det))
ctrl = scorer_extraction(data_l, "excel")
check("liasse : controle acceptable", ctrl.acceptable,
      f"statut={ctrl.statut} score={ctrl.score} problemes={ctrl.problemes}")

print("\n=== 5. Portes negatives ===")
det = detecter_documents(data_bilan)
check("bilan seul -> CR manquant (doit bloquer)", not det["compte_resultat"], str(det))
det = detecter_documents(data_cr)
check("CR seul -> bilan manquant (doit bloquer)", not det["bilan"], str(det))

print("\n=== 6. Replication exacte du flux dashboard (fusion par exercice + porte) ===")
from src.analysis.filter_ratios import MIN_EXERCICES_ANALYSE, MAX_EXERCICES_ANALYSE
SECTIONS = ("actif", "passif", "compte_resultat")


def scinder_exercices(data):
    n, n1 = {}, {}
    for sec in SECTIONS:
        n[sec] = {k: v for k, v in data.get(sec, {}).items() if not k.endswith("_n1")}
        n1[sec] = {k[:-3]: v for k, v in data.get(sec, {}).items() if k.endswith("_n1")}
    return n, n1


def fusionner_exercice(par_annee, cle, data):
    if cle not in par_annee:
        par_annee[cle] = data
        return True
    for sec in SECTIONS:
        for k, v in data.get(sec, {}).items():
            par_annee[cle].setdefault(sec, {})
            par_annee[cle][sec].setdefault(k, v)
    return False


def flux_dashboard(fichiers):
    """fichiers : [(nom, data_standard, meta)] -> (bilans_data, gate_passe, det).

    Reproduit la porte du dashboard : seuls les exercices complets
    (bilan actif+passif ET compte de resultat) comptent ; il en faut
    MIN_EXERCICES_ANALYSE minimum, MAX_EXERCICES_ANALYSE maximum
    (les plus recents sont conserves).
    """
    extraits = []
    for nom, data, meta in fichiers:
        n, n1 = scinder_exercices(data)
        import re as _re
        m = _re.search(r"(20\d{2})", nom)
        annee = int(m.group(1)) if m else meta.get("annee_n")
        extraits.append((nom, n, n1, annee, meta))
    par_annee = {}
    for direct in (True, False):
        for _, n, n1, annee, _ in extraits:
            if direct:
                fusionner_exercice(par_annee, annee if annee else "N", n)
            else:
                fusionner_exercice(par_annee, (annee - 1) if annee else "N-1", n1)
    cles = (sorted([c for c in par_annee if isinstance(c, int)], reverse=True)
            + [c for c in par_annee if not isinstance(c, int)])
    bilans_data = [par_annee[c] for c in cles]
    complets = [i for i, bd in enumerate(bilans_data)
                if detecter_documents(bd)["complet"]]
    if len(complets) < MIN_EXERCICES_ANALYSE:
        return bilans_data, False, detecter_documents(bilans_data[0])
    complets = complets[:MAX_EXERCICES_ANALYSE]
    bilans_data = [bilans_data[i] for i in complets]
    return bilans_data, True, detecter_documents(bilans_data[0])


# trois exercices complets (2024, 2023, 2022) : la porte passe
fichiers_3 = [
    ("bilan_2024.xlsx", data_bilan, meta_b),
    ("compte_resultat_2024.xlsx", data_cr, meta_c),
    ("bilan_2023.xlsx", data_bilan, meta_b),
    ("compte_resultat_2023.xlsx", data_cr, meta_c),
]
bilans_data, gate, det = flux_dashboard(fichiers_3)
check(f"porte passee (trois exercices complets)", gate, str(det))
check("3 exercices complets fusionnes", len(bilans_data) == 3, f"{len(bilans_data)} exercices")
agg = Agregats(bilans_data[0]).compute_all()
agg1 = Agregats(bilans_data[1]).compute_all()
agg2 = Agregats(bilans_data[2]).compute_all()
check("exercice 2023 = donnees N du fichier 2023 (CA 1 200 000)",
      agg1.get("chiffre_affaires") == 1200000,
      str(agg1.get("chiffre_affaires")))
check("exercice 2022 = donnees N-1 (CA 1 100 000)",
      agg2.get("chiffre_affaires") == 1100000,
      str(agg2.get("chiffre_affaires")))

# deux exercices complets seulement : porte bloquee (minimum 3)
bilans2, gate2, det2 = flux_dashboard(
    [("bilan_2024.xlsx", data_bilan, meta_b),
     ("compte_resultat_2024.xlsx", data_cr, meta_c)])
check("porte bloquee (2 exercices complets, minimum 3)", not gate2, str(det2))

# CR d'une annee differente : un seul exercice complet, porte bloquee
bilans2b, gate2b, det2b = flux_dashboard(
    [("bilan_2024.xlsx", data_bilan, meta_b),
     ("compte_resultat_2023.xlsx", data_cr, meta_c)])
check("porte bloquee (CR d'une autre annee : 1 seul exercice complet)",
      not gate2b, str(det2b))

# un seul exercice complet (documents sans N-1) : porte bloquee
def _sans_n1(data):
    return {s: {k: v for k, v in data[s].items() if not k.endswith("_n1")}
            for s in ("actif", "passif", "compte_resultat")}

bilans3, gate3, det3 = flux_dashboard(
    [("bilan_2024.xlsx", _sans_n1(data_bilan), meta_b),
     ("compte_resultat_2024.xlsx", _sans_n1(data_cr), meta_c)])
check("porte bloquee (un seul exercice complet)", not gate3, str(det3))

# neuf exercices complets : seuls les huit plus recents sont analyses
fichiers_9 = []
for annee in range(2016, 2025):
    fichiers_9.append((f"bilan_{annee}.xlsx", data_bilan, meta_b))
    fichiers_9.append((f"compte_resultat_{annee}.xlsx", data_cr, meta_c))
bilans9, gate9, det9 = flux_dashboard(fichiers_9)
check("9 exercices -> porte passee", gate9, str(det9))
check(f"9 exercices -> plafonne a {MAX_EXERCICES_ANALYSE} (les plus recents)",
      len(bilans9) == MAX_EXERCICES_ANALYSE,
      f"{len(bilans9)} exercices gardes")

print("\n=== 7. Liasse fiscale DGFiP (codes, en-tetes fusionnes, renvois) ===")
wb4 = Workbook()
wf = wb4.active
wf.title = "Bilan"
wf["A1"] = "Désignation de l'entreprise"
wf["E1"] = "TEST SCI"
wf["A2"] = "Siren"
wf["E2"] = 523003978
wf["I3"] = "Exercice N\nclos le 31/12/2024"
wf["P3"] = "Exercice N-1\nclos le 31/12/2023"
wf["A4"] = "Libellé"
wf["I4"] = "Brut 1"
wf["L4"] = "Amortissements"
wf["O4"] = "Net 3"
wf["P4"] = "Net 4"
actif_fiscal = [
    # (col A, col C, code brut, brut, code amort, amort, net, net_n1)
    ("Capital souscrit non appelé (TOTAL (I))", None, "AA", None, None, None, None, None),
    (None, "Concessions, brevets et droits similaires", "AF", 30000, "AG", None, 30000, 25000),
    (None, "Fonds commercial", "AH", 10000, None, None, 10000, 10000),
    (None, "Autres immobilisations financières", "BH", 5000, None, None, 5000, 0),
    ("TOTAL (II)", None, "BJ", 45000, "BK", 0, 45000, 35000),
    (None, "Clients et comptes rattachés", "BX", 8000, None, None, 8000, 4000),
    (None, "Disponibilités", "CF", 2000, None, None, 2000, 3000),
    ("TOTAL (III)", None, "CJ", 10000, "CK", 0, 10000, 7000),
    ("TOTAL GÉNÉRAL", None, "CO", 55000, None, None, 55000, 45000),
]
for i, (a, c, code, brut, codea, amort, net, net1) in enumerate(actif_fiscal, start=5):
    if a:
        wf.cell(row=i, column=1, value=a)
    if c:
        wf.cell(row=i, column=3, value=c)
    if code:
        wf.cell(row=i, column=9, value=code)
    if brut is not None:
        wf.cell(row=i, column=10, value=brut)
    if codea:
        wf.cell(row=i, column=12, value=codea)
    if amort is not None:
        wf.cell(row=i, column=13, value=amort)
    if net is not None:
        wf.cell(row=i, column=15, value=net)
    if net1 is not None:
        wf.cell(row=i, column=16, value=net1)

wfp = wb4.create_sheet("Passif")
wfp["Q1"] = "Exercice N"
wfp["S1"] = "Exercice N-1"     # en-tetes fusionnes, sans annees
passif_fiscal = [
    ("Capital social ou individuel", "DA", 40000, 35000),
    ("Résultat de l'exercice", "DI", 10000, 7000),
    ("TOTAL (I)", "DL", 50000, 42000),
    ("Dettes fournisseurs et comptes rattachés", "DX", 4000, 3000),
    ("TOTAL (IV)", "EC", 4000, 3000),
    ("TOTAL GENERAL (I à V)", "EE", 55000, 45000),
]
for i, (lab, code, v, v1) in enumerate(passif_fiscal, start=2):
    wfp.cell(row=i, column=3, value=lab)
    wfp.cell(row=i, column=17, value=code)
    wfp.cell(row=i, column=18, value=v)
    wfp.cell(row=i, column=19, value=v1)
# ligne de renvoi : ne doit jamais polluer produits_constates_avance
wfp.cell(row=9, column=2, value=-4)
wfp.cell(row=9, column=3, value="Dettes et produits constatés d'avance à moins d'un an (4)")
wfp.cell(row=9, column=17, value="EG")
wfp.cell(row=9, column=18, value=999)
wfp.cell(row=9, column=19, value=999)

p_fiscal = TMP / "liasse_fiscale_2024.xlsx"
wb4.save(p_fiscal)

data_f, meta_f = parser.lire(p_fiscal)
af = data_f["actif"]
check("fiscal : immo incorporelles (premier code AF, colonne NET)",
      af.get("immobilisations_incorporelles") == 30000,
      str(af.get("immobilisations_incorporelles")))
check("fiscal : actif immobilise (code BJ remappe, NET)",
      af.get("actif_immobilise") == 45000 and af.get("actif_immobilise_n1") == 35000,
      str(af.get("actif_immobilise")))
check("fiscal : total actif circulant", af.get("total_actif_circulant") == 10000,
      str(af.get("total_actif_circulant")))
check("fiscal : total actif", af.get("total_actif") == 55000,
      str(af.get("total_actif")))
check("fiscal : capital souscrit non appele non rempli (ligne vide)",
      "capital_souscrit_non_appele" not in af, str(af))
pf = data_f["passif"]
check("fiscal : capital social", pf.get("capital_social") == 40000,
      str(pf.get("capital_social")))
check("fiscal : total capitaux propres", pf.get("total_capitaux_propres") == 50000,
      str(pf.get("total_capitaux_propres")))
check("fiscal : total passif", pf.get("total_passif") == 55000,
      str(pf.get("total_passif")))
check("fiscal : renvoi ignore (pas de produits constates d'avance a 999)",
      pf.get("produits_constates_avance") is None,
      str(pf.get("produits_constates_avance")))
check("fiscal : meta siren", meta_f.get("siren") == "523003978", str(meta_f))
check("fiscal : meta raison sociale (designation)",
      meta_f.get("raison_sociale") == "TEST SCI", str(meta_f))
check("fiscal : annees depuis les en-tetes",
      meta_f.get("annee_n") == 2024 and meta_f.get("annee_n1") == 2023, str(meta_f))
ctrl = scorer_extraction(data_f, "excel")
check("fiscal : equilibre actif/passif",
      ctrl.equilibre_ecart_pct is not None and ctrl.equilibre_ecart_pct < 1.0,
      f"ecart={ctrl.equilibre_ecart_pct}")
det = detecter_documents(data_f)
check("fiscal : bilan detecte, CR absent", det["bilan"] and not det["compte_resultat"],
      str(det))

print("\n=== 8. Service d'extraction unifie (ExtractionService) ===")
from src.extraction.service import ExtractionService, EXTENSIONS_SUPPORTES

svc = ExtractionService()
ex = svc.extraire(p_bilan)
check("service : source excel", ex.source == "excel", ex.source)
check("service : 2 exercices portees", ex.exercices == 2, str(ex.exercices))
check("service : data = format standard du parser",
      ex.data["actif"].get("total_actif") == 960000
      and ex.data["passif"].get("total_passif") == 960000,
      str(ex.data["actif"].get("total_actif")))
check("service : meta conservee", ex.meta.get("siren") == "123456789", str(ex.meta))

# format non supporte -> ValueError (l'appelant decide d'ignorer)
try:
    svc.extraire(TMP / "fichier_inconnu.txt")
    check("service : format non supporte rejete", False, "aucune exception")
except ValueError as e:
    check("service : format non supporte rejete", "non supporte" in str(e), str(e))
except Exception as e:
    check("service : format non supporte rejete", False, repr(e))

# la liasse fiscale (bilan N et N-1, sans CR) ne passe pas la porte :
# aucun exercice complet
bilans_f, gate_f, det_f = flux_dashboard([("liasse_fiscale_2024.xlsx",
                                           data_f, meta_f)])
check("service/porte : liasse fiscale sans CR -> bloque", not gate_f, str(det_f))

print("\n=== 9. Nuance des libelles (pluriel, faute, mots en plus) ===")
wb5 = Workbook()

def feuille_floue(wb, titre, entetes, lignes):
    ws = wb.create_sheet(titre)
    ws["A1"] = "Libellé"
    ws["B1"], ws["C1"] = entetes
    for i, (lab, v, v1) in enumerate(lignes, start=2):
        ws.cell(row=i, column=1, value=lab)
        ws.cell(row=i, column=2, value=v)
        ws.cell(row=i, column=3, value=v1)
    return ws

feuille_floue(wb5, "Actif flou", ("Exercice N", "Exercice N-1"), [
    ("Instalations techniques, matériel et outillage industriel", 500000, 480000),
    ("Constructions sur sol propre", 200000, 210000),
    ("Trésorerie et disponibilités diverses", 380000, 370000),
])
feuille_floue(wb5, "Passif flou", ("Exercice N", "Exercice N-1"), [
    ("Réserves légales", 5000, 4000),
    ("Report à nouveau créditeur", 3000, 2000),
])
feuille_floue(wb5, "CR flou", ("Exercice N", "Exercice N-1"), [
    ("Chiffres d'affaires nets", 900000, 850000),
    ("Salaires et traitements du personnel", 250000, 240000),
    ("Nombre de mois de l'exercice", 12, 12),       # ne doit jamais matcher
])
p_flou = TMP / "libelles_flous.xlsx"
wb5.save(p_flou)

data_flou, meta_flou = parser.lire(p_flou)
check("fuzzy : faute de frappe 'Instalations techniques...' -> installations_techniques",
      data_flou["actif"].get("installations_techniques") == 500000,
      str(data_flou["actif"]))
check("fuzzy : 'Constructions sur sol propre' -> constructions",
      data_flou["actif"].get("constructions") == 200000,
      str(data_flou["actif"].get("constructions")))
check("fuzzy : 'Trésorerie et disponibilités diverses' -> disponibilites",
      data_flou["actif"].get("disponibilites") == 380000,
      str(data_flou["actif"].get("disponibilites")))
check("fuzzy : pluriel 'Réserves légales' -> reserve_legale",
      data_flou["passif"].get("reserve_legale") == 5000,
      str(data_flou["passif"]))
check("fuzzy : 'Report à nouveau créditeur' -> report_a_nouveau",
      data_flou["passif"].get("report_a_nouveau") == 3000,
      str(data_flou["passif"].get("report_a_nouveau")))
check("fuzzy : pluriel 'Chiffres d'affaires nets' -> chiffre_affaires",
      data_flou["compte_resultat"].get("chiffre_affaires") == 900000,
      str(data_flou["compte_resultat"]))
check("fuzzy : 'Salaires et traitements du personnel' -> salaires_traitements",
      data_flou["compte_resultat"].get("salaires_traitements") == 250000,
      str(data_flou["compte_resultat"]))
hors_sujet = [k for sec in data_flou.values() for k, v in sec.items() if v in (12.0,)]
check("fuzzy : 'Nombre de mois de l'exercice' ne matche aucun poste",
      not hors_sujet, str(hors_sujet))

print()
if echecs:
    print(f"ECHECS ({len(echecs)}) :")
    for e in echecs:
        print(" -", e)
    sys.exit(1)
print("TOUS LES TESTS PASSENT")
