"""Tests de la moyenne multi-exercices (src.analysis.historique).

Regle unique, alignee sur le rendu du dashboard et du PDF :
pour CHAQUE ratio (stock comme flux), la moyenne affichee est la
moyenne arithmetique des valeurs du ratio sur tous les exercices
fournis ; les exercices ou le ratio n'est pas calculable sont
ecartes du denominateur. Seule la tendance reste reservee aux
ratios de flux.

Lancement : python tests/test_historique.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.analysis.historique import calculer_historique

echecs = []


def check(nom, cond):
    print(("OK   " if cond else "ECHEC") + f" - {nom}")
    if not cond:
        echecs.append(nom)


# 1. Ratio STOCK : la moyenne couvre tous les exercices (et ne
#    reprend plus la valeur N comme avant)
h = calculer_historique({
    "2024": {"liquidite": {"gearing": 1.8}},
    "2023": {"liquidite": {"gearing": 1.2}},
    "2022": {"liquidite": {"gearing": 1.5}},
})
r = h["gearing"]
check("stock : N = valeur du dernier exercice", r["N"] == 1.8)
check("stock : moyenne = (1.8 + 1.2 + 1.5) / 3",
      abs(r["moyenne"] - 1.5) < 1e-9)
check("stock : type conserve", r["type"] == "stock")
check("stock : pas de tendance", r["tendance"] == "→")

# 2. Ratio FLUX : la moyenne deja calculee sur tous les exercices ne
#    change pas (meme regle qu'avant)
h = calculer_historique({
    "2024": {"rentabilite": {"taux_marge": 10.0}},
    "2023": {"rentabilite": {"taux_marge": 4.0}},
})
r = h["taux_marge"]
check("flux : moyenne = (10 + 4) / 2", abs(r["moyenne"] - 7.0) < 1e-9)
check("flux : type conserve", r["type"] == "flux")

# 3. Exercice ou le ratio n'est pas calculable : ecarte du
#    denominateur (moyenne sur les seules valeurs disponibles)
h = calculer_historique({
    "2024": {"liquidite": {"gearing": 2.0}},
    "2023": {"liquidite": {"gearing": None}},
    "2022": {"liquidite": {"gearing": 1.0}},
})
r = h["gearing"]
check("non calculable : moyenne sur les valeurs disponibles",
      abs(r["moyenne"] - 1.5) < 1e-9)

# 4. Un seul exercice : moyenne = N
h = calculer_historique({
    "2024": {"liquidite": {"gearing": 1.6}},
})
r = h["gearing"]
check("un seul exercice : moyenne = N", abs(r["moyenne"] - 1.6) < 1e-9)

print()
if echecs:
    print(f"{len(echecs)} test(s) en echec")
    sys.exit(1)
print("Tous les tests historique : OK")
