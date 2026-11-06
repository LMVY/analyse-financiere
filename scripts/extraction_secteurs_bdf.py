"""Extraction annuelle des referentiels sectoriels depuis les fascicules
de resultats Banque de France (base FIBEN).

Source : Banque de France - Direction des Entreprises, fascicules de
resultats sectoriels 2024 (donnees disponibles en octobre 2025).
17 sections NAF rev. 2, quartiles Q1 / mediane (Q2) / Q3, colonne 2024.

Ce script met a jour config/secteurs_config.yaml :
- les 7 secteurs indicatifs recoivent les quartiles REELS de leur
  section (construction F, commerce G, transport H, hotellerie I,
  information J, immobilier L, services M) ;
- l'industrie (division 28, donnees 2023) reste inchangee : le
  fascicule division est plus precis que la section C aggregate ;
- data/config_user.yaml : si sa cle secteurs est une copie identique
  des anciens defauts, elle est supprimee (les nouveaux defauts
  s'appliquent alors directement).

Reutilisable chaque annee : remplacer les valeurs du dictionnaire
DATA par les colonnes de la nouvelle edition, puis relancer :
    python scripts/extraction_secteurs_bdf.py

Caveats documentes dans le fichier cible :
- les delais de reglement BdF sont calcules en TTC ; le moteur les
  calcule en HT (cf. glossaire) ;
- le secteur "services" couvre les sections M et N : les quartiles de
  la section M (activites specialisees) sont utilises comme reference.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
SECTEURS = ROOT / "config" / "secteurs_config.yaml"
USER = ROOT / "data" / "config_user.yaml"

# correspondance : cle du dictionnaire fascicule -> ratio du moteur
RATIO_MAP = {
    "croissance_ca": "caht",
    "croissance_va": "va",
    "taux_valeur_ajoutee": "tva",
    "dso": "clients",
    "dpo": "fournisseurs",
    "poids_bfr_exploitation": "bfr",
    "rendement_capital_exploitation": "rce",
    "taux_marge": "marge",
    "rentabilite_brute_capital_exploitation": "rbce",
    "rentabilite_financiere_capitaux_propres": "rfcp",
    "taux_excedent_brut_global": "ebg",
    "repartition_personnel": "personnel",
    "repartition_preteurs": "preteurs",
    "repartition_etat": "etat",
    "poids_interets_ebg": "interets",
    "gearing": "endettement_brut",
    "dette_nette_fonds_propres": "endettement_net",
    "cout_apparent_endettement": "cout",
}

# secteurs mis a jour ou crees -> section NAF du fascicule
SECTEUR_SECTION = {
    "construction": "F",
    "commerce": "G",
    "transport": "H",
    "hotellerie_restauration": "I",
    "information_communication": "J",
    "immobilier": "L",
    "services": "M",
    # sections ajoutees (fascicules 2024) : couverture A a S
    "agriculture": "A",
    "industries_extractives": "B",
    "energie": "D",
    "eau_dechets": "E",
    "services_administratifs": "N",
    "enseignement": "P",
    "sante": "Q",
    "arts_spectacles": "R",
    "autres_services": "S",
}

# nouveaux secteurs crees a la premiere execution
NOUVEAUX = {
    "agriculture": ("Agriculture, sylviculture et peche", ["A"]),
    "industries_extractives": ("Industries extractives", ["B"]),
    "energie": ("Production et distribution d'electricite et de gaz",
                ["D"]),
    "eau_dechets": ("Eau, assainissement, gestion des dechets", ["E"]),
    "services_administratifs": ("Services administratifs et de soutien",
                                ["N"]),
    "enseignement": ("Enseignement", ["P"]),
    "sante": ("Sante humaine et action sociale", ["Q"]),
    "arts_spectacles": ("Arts, spectacles et activites recreatives",
                        ["R"]),
    "autres_services": ("Autres activites de services", ["S"]),
}

# quartiles 2024 du fascicule BdF : (q1, mediane, q3)
DATA = {
    "A": {  # Agriculture, sylviculture et peche
        "caht": (-7.3, 1.2, 10.6), "va": (-12.2, 2.1, 17.6),
        "tva": (28.8, 42.5, 55.2),
        "clients": (16.3, 41.0, 74.1),
        "fournisseurs": (32.7, 55.6, 93.7),
        "bfr": (26.5, 79.0, 193.0), "rce": (15.4, 24.4, 40.1),
        "marge": (24.7, 45.0, 66.3), "rbce": (5.7, 10.5, 17.7),
        "rfcp": (0.5, 8.9, 19.5), "ebg": (9.6, 19.1, 31.5),
        "personnel": (33.9, 52.4, 71.4), "preteurs": (0.9, 2.4, 5.2),
        "etat": (2.0, 5.3, 11.1), "interets": (2.2, 5.6, 11.8),
        "endettement_brut": (27.1, 75.7, 179.7),
        "endettement_net": (-12.2, 43.0, 146.5),
        "cout": (1.6, 2.4, 3.7),
    },
    "B": {  # Industries extractives
        "caht": (-7.6, 0.2, 9.0), "va": (-9.7, 2.6, 17.1),
        "tva": (28.6, 37.3, 47.0),
        "clients": (44.5, 57.2, 73.5),
        "fournisseurs": (50.9, 68.9, 92.5),
        "bfr": (28.4, 64.4, 116.0), "rce": (16.4, 24.4, 35.8),
        "marge": (26.1, 42.3, 54.6), "rbce": (5.1, 9.7, 16.1),
        "rfcp": (2.1, 9.7, 19.5), "ebg": (10.3, 17.2, 24.9),
        "personnel": (37.8, 49.6, 64.6), "preteurs": (0.6, 1.9, 4.7),
        "etat": (4.8, 8.4, 12.6), "interets": (1.2, 4.4, 11.1),
        "endettement_brut": (9.7, 39.9, 110.3),
        "endettement_net": (-45.6, 3.5, 74.2),
        "cout": (1.8, 3.4, 5.3),
    },
    "D": {  # Production et distribution d'electricite et de gaz
        "caht": (-19.1, -8.7, 1.5), "va": (-23.3, -9.2, 7.5),
        "tva": (40.0, 71.6, 80.0),
        "clients": (36.5, 56.4, 86.9),
        "fournisseurs": (45.5, 84.1, 142.2),
        "bfr": (0.2, 30.7, 64.7), "rce": (8.5, 11.2, 17.2),
        "marge": (83.9, 92.2, 95.4), "rbce": (7.4, 10.0, 14.6),
        "rfcp": (10.0, 21.7, 45.0), "ebg": (35.7, 66.3, 77.6),
        "personnel": (0.0, 0.0, 2.0), "preteurs": (3.6, 9.2, 19.5),
        "etat": (7.7, 12.6, 18.5), "interets": (4.2, 10.5, 22.5),
        "endettement_brut": (44.6, 182.7, 448.5),
        "endettement_net": (2.2, 131.5, 366.4),
        "cout": (2.2, 3.6, 5.7),
    },
    "E": {  # Eau, assainissement, gestion des dechets
        "caht": (-3.0, 4.6, 13.1), "va": (-7.5, 5.3, 19.3),
        "tva": (22.9, 36.1, 49.6),
        "clients": (45.4, 64.7, 90.7),
        "fournisseurs": (44.7, 69.7, 105.9),
        "bfr": (-2.2, 20.9, 48.3), "rce": (30.1, 51.5, 96.4),
        "marge": (15.3, 30.8, 48.5), "rbce": (7.5, 15.6, 28.5),
        "rfcp": (4.8, 15.0, 31.4), "ebg": (5.8, 11.2, 18.7),
        "personnel": (44.6, 62.2, 78.3), "preteurs": (0.4, 1.5, 3.6),
        "etat": (2.9, 5.8, 10.5), "interets": (1.3, 4.6, 10.4),
        "endettement_brut": (13.4, 48.7, 127.7),
        "endettement_net": (-50.5, -1.1, 73.1),
        "cout": (1.9, 3.6, 5.7),
    },
    "F": {  # Construction
        "caht": (-9.9, 0.8, 12.6), "va": (-9.0, 3.1, 15.8),
        "tva": (30.6, 39.2, 47.4),
        "clients": (36.9, 61.4, 87.1),
        "fournisseurs": (36.6, 52.2, 72.6),
        "bfr": (0.3, 23.9, 49.6), "rce": (89.6, 144.4, 240.5),
        "marge": (9.6, 18.8, 30.5), "rbce": (11.1, 24.7, 52.0),
        "rfcp": (6.6, 17.5, 32.3), "ebg": (4.0, 7.5, 12.4),
        "personnel": (66.6, 78.1, 86.9), "preteurs": (0.2, 0.6, 1.3),
        "etat": (2.4, 4.4, 7.2), "interets": (0.9, 3.0, 7.2),
        "endettement_brut": (10.2, 29.2, 68.8),
        "endettement_net": (-73.0, -34.5, 12.6),
        "cout": (1.9, 3.6, 6.3),
    },
    "G": {  # Commerce
        "caht": (-5.8, 1.2, 8.2), "va": (-10.4, 0.6, 11.7),
        "tva": (12.9, 20.2, 26.0),
        "clients": (3.0, 13.2, 40.4),
        "fournisseurs": (24.1, 37.9, 55.5),
        "bfr": (-4.5, 15.9, 56.2), "rce": (36.4, 59.2, 104.7),
        "marge": (11.3, 24.4, 38.3), "rbce": (5.9, 13.5, 28.4),
        "rfcp": (4.2, 12.1, 23.9), "ebg": (2.2, 4.9, 8.6),
        "personnel": (56.9, 70.0, 82.4), "preteurs": (0.3, 1.0, 2.8),
        "etat": (4.0, 7.0, 10.5), "interets": (0.9, 3.7, 10.7),
        "endettement_brut": (9.1, 35.2, 97.1),
        "endettement_net": (-46.8, -5.3, 52.4),
        "cout": (1.1, 2.6, 5.0),
    },
    "H": {  # Transports et entreposage
        "caht": (-4.8, 1.8, 9.4), "va": (-6.7, 2.9, 13.3),
        "tva": (31.7, 43.2, 54.8),
        "clients": (37.2, 48.8, 64.0),
        "fournisseurs": (31.2, 46.0, 69.7),
        "bfr": (-11.3, 5.1, 21.6), "rce": (56.6, 100.9, 210.3),
        "marge": (5.3, 17.7, 30.7), "rbce": (6.4, 15.9, 32.1),
        "rfcp": (-2.9, 7.8, 21.6), "ebg": (3.1, 8.6, 15.4),
        "personnel": (64.1, 76.4, 88.3), "preteurs": (0.3, 1.3, 2.8),
        "etat": (2.5, 3.8, 6.3), "interets": (1.9, 6.7, 12.5),
        "endettement_brut": (14.5, 62.7, 166.8),
        "endettement_net": (-60.7, -0.5, 98.3),
        "cout": (2.0, 3.9, 6.8),
    },
    "I": {  # Hebergement et restauration
        "caht": (-4.8, 0.5, 6.6), "va": (-6.9, 1.3, 10.4),
        "tva": (41.2, 48.7, 56.0),
        "clients": (0.0, 1.0, 5.6),
        "fournisseurs": (28.5, 42.7, 70.4),
        "bfr": (-47.4, -30.4, -19.2), "rce": (46.0, 89.0, 153.6),
        "marge": (9.4, 20.3, 34.4), "rbce": (7.1, 15.9, 30.9),
        "rfcp": (7.7, 21.9, 46.2), "ebg": (5.3, 10.8, 19.1),
        "personnel": (59.3, 73.1, 84.2), "preteurs": (0.3, 0.7, 2.2),
        "etat": (3.1, 5.4, 8.6), "interets": (1.0, 3.3, 9.0),
        "endettement_brut": (21.1, 59.9, 174.4),
        "endettement_net": (-68.1, -12.1, 73.5),
        "cout": (1.3, 2.3, 3.9),
    },
    "J": {  # Information et communication
        "caht": (-5.9, 3.7, 15.2), "va": (-8.6, 4.1, 18.3),
        "tva": (35.1, 53.0, 70.4),
        "clients": (41.1, 66.4, 101.4),
        "fournisseurs": (38.3, 63.8, 105.1),
        "bfr": (-38.6, -2.2, 30.7), "rce": (56.4, 145.3, 387.2),
        "marge": (3.6, 16.5, 35.4), "rbce": (3.9, 18.6, 60.0),
        "rfcp": (4.0, 17.6, 36.8), "ebg": (2.4, 8.7, 19.6),
        "personnel": (59.1, 79.1, 92.6), "preteurs": (0.0, 0.3, 1.3),
        "etat": (0.8, 2.9, 6.8), "interets": (0.0, 1.0, 5.7),
        "endettement_brut": (1.0, 17.4, 67.9),
        "endettement_net": (-96.1, -51.5, 2.7),
        "cout": (0.6, 2.5, 4.9),
    },
    "L": {  # Activites immobilieres
        "caht": (-1.9, 3.8, 8.2), "va": (-4.3, 4.2, 11.9),
        "tva": (56.4, 71.2, 85.3),
        "clients": (6.8, 32.4, 77.6),
        "fournisseurs": (31.1, 64.7, 135.8),
        "bfr": (-34.9, -3.1, 43.6), "rce": (7.4, 14.3, 96.2),
        "marge": (19.2, 72.0, 89.6), "rbce": (4.3, 8.6, 18.4),
        "rfcp": (1.7, 11.1, 27.5), "ebg": (12.7, 51.0, 84.3),
        "personnel": (0.0, 8.2, 73.2), "preteurs": (0.4, 4.2, 19.6),
        "etat": (5.0, 11.6, 21.3), "interets": (1.4, 9.3, 29.1),
        "endettement_brut": (16.6, 80.3, 240.5),
        "endettement_net": (-64.6, 18.6, 177.8),
        "cout": (1.4, 2.8, 4.7),
    },
    "M": {  # Activites specialisees, scientifiques et techniques
        "caht": (-5.2, 3.8, 12.7), "va": (-7.8, 3.4, 14.9),
        "tva": (41.7, 60.2, 74.3),
        "clients": (43.0, 72.8, 107.6),
        "fournisseurs": (29.7, 55.1, 93.8),
        "bfr": (-23.9, 11.7, 49.1), "rce": (96.8, 174.9, 340.6),
        "marge": (5.9, 16.3, 30.1), "rbce": (8.9, 25.7, 63.2),
        "rfcp": (7.9, 20.7, 38.4), "ebg": (4.1, 9.9, 17.9),
        "personnel": (65.5, 79.8, 90.0), "preteurs": (0.0, 0.3, 0.9),
        "etat": (2.2, 4.5, 7.8), "interets": (0.1, 1.4, 5.3),
        "endettement_brut": (3.9, 22.2, 67.6),
        "endettement_net": (-93.1, -45.3, 2.5),
        "cout": (0.8, 2.2, 4.4),
    },
    "N": {  # Services administratifs et de soutien
        "caht": (-5.5, 3.4, 13.6), "va": (-7.6, 3.7, 15.5),
        "tva": (40.7, 63.7, 84.7),
        "clients": (37.8, 58.2, 81.4),
        "fournisseurs": (34.5, 61.1, 110.6),
        "bfr": (-19.4, 5.2, 32.9), "rce": (64.6, 189.6, 645.5),
        "marge": (1.8, 10.5, 33.8), "rbce": (7.9, 21.5, 49.8),
        "rfcp": (3.7, 14.8, 31.3), "ebg": (2.1, 6.3, 15.4),
        "personnel": (61.0, 85.3, 94.2), "preteurs": (0.0, 0.4, 1.5),
        "etat": (2.4, 3.5, 6.0), "interets": (0.4, 3.0, 9.3),
        "endettement_brut": (5.4, 29.2, 98.3),
        "endettement_net": (-101.7, -45.6, 23.8),
        "cout": (1.0, 3.1, 6.1),
    },
    "P": {  # Enseignement
        "caht": (-5.1, 3.9, 13.1), "va": (-11.4, 2.3, 15.8),
        "tva": (38.6, 52.3, 62.7),
        "clients": (35.7, 68.6, 108.4),
        "fournisseurs": (31.8, 56.3, 93.9),
        "bfr": (-33.5, 4.9, 39.4), "rce": (81.9, 143.8, 276.2),
        "marge": (5.6, 21.1, 39.3), "rbce": (6.9, 26.9, 71.8),
        "rfcp": (5.6, 21.9, 44.4), "ebg": (3.8, 10.9, 22.7),
        "personnel": (54.4, 72.4, 86.6), "preteurs": (0.1, 0.4, 1.3),
        "etat": (4.5, 8.5, 13.2), "interets": (0.2, 1.5, 6.1),
        "endettement_brut": (5.4, 26.8, 76.2),
        "endettement_net": (-89.7, -42.6, 13.0),
        "cout": (1.0, 2.6, 4.8),
    },
    "Q": {  # Sante humaine et action sociale
        "caht": (-0.6, 4.2, 9.4), "va": (-2.9, 3.9, 11.0),
        "tva": (57.4, 67.6, 77.1),
        "clients": (4.8, 17.8, 37.1),
        "fournisseurs": (25.0, 45.3, 79.8),
        "bfr": (-33.9, -13.9, 1.8), "rce": (95.4, 163.4, 282.3),
        "marge": (5.6, 15.1, 29.0), "rbce": (8.0, 23.5, 55.1),
        "rfcp": (6.9, 20.2, 41.2), "ebg": (5.7, 11.9, 21.0),
        "personnel": (65.9, 77.9, 87.0), "preteurs": (0.1, 0.5, 1.2),
        "etat": (5.2, 7.6, 10.5), "interets": (0.5, 2.4, 7.4),
        "endettement_brut": (10.5, 36.6, 94.7),
        "endettement_net": (-71.1, -24.8, 24.8),
        "cout": (1.1, 2.7, 5.1),
    },
    "R": {  # Arts, spectacles et activites recreatives
        "caht": (-3.3, 4.0, 13.7), "va": (-6.3, 4.5, 19.6),
        "tva": (36.9, 50.4, 62.0),
        "clients": (2.4, 17.7, 48.5),
        "fournisseurs": (29.1, 54.6, 96.2),
        "bfr": (-57.5, -23.9, 4.5), "rce": (38.0, 67.7, 149.0),
        "marge": (8.6, 27.6, 46.2), "rbce": (5.7, 16.9, 37.6),
        "rfcp": (4.8, 20.6, 42.9), "ebg": (4.4, 13.5, 25.8),
        "personnel": (48.3, 64.7, 84.5), "preteurs": (0.1, 0.6, 2.1),
        "etat": (3.0, 6.3, 11.3), "interets": (0.4, 2.3, 7.4),
        "endettement_brut": (11.6, 39.6, 117.4),
        "endettement_net": (-89.2, -36.7, 39.1),
        "cout": (1.0, 2.3, 4.3),
    },
    "S": {  # Autres activites de services
        "caht": (-2.3, 4.1, 10.7), "va": (-4.7, 4.2, 13.8),
        "tva": (40.4, 50.7, 64.0),
        "clients": (17.3, 36.8, 59.3),
        "fournisseurs": (33.2, 50.2, 87.0),
        "bfr": (-28.3, 3.6, 33.3), "rce": (54.1, 88.0, 169.4),
        "marge": (6.0, 18.1, 35.0), "rbce": (6.6, 17.9, 34.3),
        "rfcp": (4.3, 15.4, 29.3), "ebg": (3.8, 9.7, 18.3),
        "personnel": (61.0, 77.1, 89.9), "preteurs": (0.2, 0.6, 1.6),
        "etat": (2.7, 4.5, 7.7), "interets": (0.7, 2.9, 7.3),
        "endettement_brut": (8.9, 28.5, 87.5),
        "endettement_net": (-67.3, -27.3, 30.9),
        "cout": (1.6, 3.1, 5.0),
    },
}

SOURCE = ("Banque de France - fascicule de resultats sectoriels 2024, "
          "base FIBEN (section {sec})")

HEADER = """\
# ============================================================
# REFERENTIEL SECTORIEL - 18 ratios Banque de France par secteur
# ============================================================
# Quartiles REELS des fascicules de resultats sectoriels 2024,
# Banque de France - Direction des Entreprises, base FIBEN
# (donnees 2024, publiees en octobre 2025) : couverture des 17
# sections NAF rev. 2 (A a S, hors K) - construction F, commerce G,
# transport H, hebergement I, information J, immobilier L,
# services M, agriculture A, industries extractives B,
# electricite/gaz D, eau/dechets E, services administratifs N,
# enseignement P, sante Q, arts/spectacles R, autres services S.
# Industrie : quartiles du fascicule division 28 (machines),
#   donnees 2023 - plus precis que la section C agreggee.
# "services" couvre les sections M et N : la section M (activites
#   specialisees) sert de reference.
# Chaque ratio porte : q1 (25e percentile), mediane (50e), q3 (75e)
#   et sa source. Extraction annuelle :
#   python scripts/extraction_secteurs_bdf.py
# Caveat : les delais de reglement BdF sont en TTC, le moteur les
#   calcule en HT (cf. src/reporting/glossaire).
# Scoring : position de l'entreprise dans la distribution
#   (cf. src/scoring/sector_scorer.py).
# ============================================================
"""


def main():
    data = yaml.safe_load(SECTEURS.read_text(encoding="utf-8")) or {}

    # creation des secteurs absents (premiere execution)
    for key, (label, prefix) in NOUVEAUX.items():
        if key not in data:
            data[key] = {"label": label, "code_naf_prefix": prefix,
                         "ratios": {}, "ratios_desactives": []}
            print(f"secteur cree : {key} ({label})")

    # la section N a son propre secteur desormais : "services" ne
    # couvre plus que M (sinon l'appariement par prefixe prendrait
    # "services" pour une entreprise de la section N)
    if data.get("services", {}).get("code_naf_prefix") != ["M"]:
        data["services"]["code_naf_prefix"] = ["M"]
        print("services : prefixe limite a M (N devient autonome)")

    n = 0
    for secteur, sec in SECTEUR_SECTION.items():
        refs = DATA[sec]
        ratios = data[secteur].setdefault("ratios", {})
        for ratio, cle in RATIO_MAP.items():
            q1, med, q3 = refs[cle]
            r = ratios.setdefault(ratio, {})
            r["mediane"] = med
            r["q1"] = q1
            r["q3"] = q3
            r["source"] = SOURCE.format(sec=sec)
            n += 1

    SECTEURS.write_text(
        HEADER + yaml.dump(data, default_flow_style=False,
                           allow_unicode=True, sort_keys=False,
                           width=100),
        encoding="utf-8")
    print(f"secteurs_config.yaml : {n} ratios mis a jour "
          f"(7 secteurs, fascicules BdF 2024).")

    # user : retirer la copie obsolete des secteurs si identique
    if USER.exists():
        user = yaml.safe_load(USER.read_text(encoding="utf-8")) or {}
        if "secteurs" in user:
            user.pop("secteurs")
            USER.write_text(
                yaml.dump(user, default_flow_style=False,
                          allow_unicode=True, sort_keys=False,
                          width=100),
                encoding="utf-8")
            print("config_user.yaml : cle secteurs retiree, les "
                  "nouveaux referentiels s'appliquent.")


if __name__ == "__main__":
    main()
