"""Glossaire des ratios : definitions, calcul et mode de lecture.

Source unique pour le vocabulaire du rapport PDF :
- CAT_LABELS : libelles des categories ;
- CAT_DESCRIPTIONS : ce que mesure chaque categorie (langage metier) ;
- GLOSSAIRE : pour chaque ratio, sa definition (calcul en clair) et son
  mode de lecture (sens favorable, interpretation, reperes generiques).
"""
from src.visualization.colors import get_score_label  # noqa: F401 (re-export)

CAT_LABELS = {
    "croissance": "Croissance",
    "rentabilite": "Rentabilite",
    "gestion_activite": "Gestion de l'activite",
    "endettement": "Endettement",
    "partage_valeur": "Partage de la valeur",
}

# Libelles francais des ratios, affiches partout (dashboard, PDF,
# treemaps, graphique secteur). Les anglicismes disparaissent :
# DSO, DPO et gearing deviennent des noms francais.
LABELS_RATIOS = {
    "croissance_ca": "Croissance du chiffre d'affaires",
    "croissance_va": "Croissance de la valeur ajoutee",
    "taux_valeur_ajoutee": "Taux de valeur ajoutee",
    "taux_marge": "Taux de marge (EBE / VA)",
    "taux_excedent_brut_global": "Taux d'excedent brut global (EBG / CA)",
    "rentabilite_financiere_capitaux_propres":
        "Rentabilite financiere des capitaux propres",
    "rentabilite_brute_capital_exploitation":
        "Rentabilite brute du capital d'exploitation",
    "rendement_capital_exploitation": "Rendement du capital d'exploitation",
    "dso": "Delai de paiement des clients",
    "dpo": "Delai de paiement des fournisseurs",
    "poids_bfr_exploitation": "Poids du BFR d'exploitation",
    "gearing": "Niveau d'endettement financier",
    "dette_nette_fonds_propres": "Dette nette / capitaux propres",
    "cout_apparent_endettement": "Cout apparent de l'endettement",
    "poids_interets_ebg": "Poids des interets sur l'EBG",
    "repartition_personnel": "Repartition - Personnel",
    "repartition_etat": "Repartition - Etat",
    "repartition_preteurs": "Repartition - Preteurs",
}


def label_ratio(nom):
    """Libelle francais d'un ratio (repli : nom avec espaces)."""
    return LABELS_RATIOS.get(nom, nom.replace("_", " "))

CAT_DESCRIPTIONS = {
    "croissance": "rythme de developpement de l'activite (CA et valeur "
                  "ajoutee)",
    "rentabilite": "marges, rentabilite des capitaux et du capital "
                   "d'exploitation",
    "gestion_activite": "efficacite du cycle d'exploitation (clients, "
                        "fournisseurs, stocks)",
    "endettement": "structure de financement, poids de la dette et cout "
                   "de l'endettement",
    "partage_valeur": "repartition de la valeur ajoutee entre personnel, "
                      "Etat et preteurs",
}


def label_categorie(cat):
    """Libelle lisible d'une categorie."""
    return CAT_LABELS.get(cat, cat.replace("_", " ").title())


# Glossaire : ratio -> (definition / calcul, mode de lecture et sens)
# Definitions reprises des fascicules sectoriels Banque de France.
GLOSSAIRE = {
    # --- Croissance ---
    "croissance_ca": (
        "Taux de variation du chiffre d'affaires HT : (CA N - CA N-1) / "
        "CA N-1, en %.",
        "Sens favorable : a la hausse. Une progression superieure a la "
        "mediane du secteur signale des parts de marche gagnees ; une "
        "evolution tres volatile appelle une lecture sur plusieurs "
        "exercices."),
    "croissance_va": (
        "Taux de variation de la valeur ajoutee : (VA N - VA N-1) / "
        "VA N-1, en %.",
        "Sens favorable : a la hausse. Croissance de l'activite reelle "
        "de l'entreprise ; a comparer a la croissance du CA : plus "
        "rapide, elle traduit un deplacement vers des productions de "
        "plus forte valeur."),
    # --- Rentabilite ---
    "taux_valeur_ajoutee": (
        "Valeur ajoutee / (production + ventes de marchandises), en %.",
        "Sens favorable : a la hausse. Part de richesse produite par "
        "l'entreprise apres consommations intermediaires ; depend "
        "fortement du secteur (comparaison sectorielle indispensable)."),
    "taux_marge": (
        "Excedent brut d'exploitation / valeur ajoutee, en %.",
        "Sens favorable : a la hausse. Part de la valeur ajoutee qui "
        "subsiste apres remuneration du travail et de l'impot ; mesure "
        "la performance economique intrinseque independamment du "
        "niveau d'integration."),
    "taux_excedent_brut_global": (
        "Excedent brut global / chiffre d'affaires HT, en % (proche de "
        "la marge d'EBITDA).",
        "Sens favorable : a la hausse. Rentabilite operationnelle de "
        "l'activite avant amortissements ; c'est la reference de "
        "marge la plus comparee entre entreprises."),
    "rentabilite_financiere_capitaux_propres": (
        "CAF nette / capitaux propres, en %.",
        "Sens favorable : a la hausse. Taux de rentabilite de l'actionnaire "
        "en base autofinancement ; plus robuste que le ROE sur resultat "
        "net, moins sensible aux elements exceptionnels."),
    "rentabilite_brute_capital_exploitation": (
        "EBE / capital d'exploitation (immobilisations + BFRE), en %.",
        "Sens favorable : a la hausse. Rentabilite economique avant "
        "amortissements du capital engage dans l'exploitation."),
    "rendement_capital_exploitation": (
        "Valeur ajoutee / capital d'exploitation, en %.",
        "Sens favorable : a la hausse. Intensite avec laquelle le capital "
        "d'exploitation produit de la richesse ; tres dependent du "
        "secteur (une usine et un cabinet de conseil ne se comparent "
        "que dans leur secteur)."),
    # --- Gestion de l'activite ---
    "dso": (
        "(Creances clients - avances recues) / chiffre d'affaires x 360, "
        "en jours.",
        "Sens favorable : a la baisse. Delai moyen de reglement des "
        "clients ; un delai superieur a la mediane du secteur signale "
        "un financement accru de la clientele. Calcule sur des flux "
        "HT (references BdF en TTC)."),
    "dpo": (
        "(Dettes fournisseurs - avances versees) / (achats et charges "
        "externes) x 360, en jours.",
        "Sens favorable : a la baisse. Delai moyen obtenu des "
        "fournisseurs ; un delai superieur a la mediane du secteur "
        "signale un financement par les fournisseurs au-dela des usages "
        "- confort de tresorerie ou tension selon le contexte."),
    "poids_bfr_exploitation": (
        "BFR d'exploitation / chiffre d'affaires HT x 360, en jours.",
        "Sens favorable : a la baisse. Jours de chiffre d'affaires "
        "immobilises dans le cycle (stocks + creances - dettes "
        "fournisseurs) ; mesure la consommation de tresorerie du "
        "cycle d'exploitation."),
    # --- Endettement ---
    "gearing": (
        "Endettement financier / capitaux propres, en %.",
        "Sens favorable : a la baisse. Rapport de la dette financiere "
        "aux capitaux propres ; au-dela de la mediane du secteur, la "
        "marge de manoeuvre financiere se resserre."),
    "dette_nette_fonds_propres": (
        "(Endettement financier - tresorerie active) / capitaux propres, "
        "en %.",
        "Sens favorable : a la baisse. Endettement reel apres "
        "deduction de la tresorerie ; une valeur negative traduit une "
        "tresorerie superieure a la dette."),
    "cout_apparent_endettement": (
        "Charges d'interets / endettement financier, en %.",
        "Sens favorable : a la baisse. Taux d'interet moyen apparent de "
        "la dette ; un cout superieur au secteur signale un "
        "financement plus risque ou plus court terme."),
    "poids_interets_ebg": (
        "Charges d'interets globales / excedent brut global, en %.",
        "Sens favorable : a la baisse. Part de l'excendent d'exploitation "
        "absorbee par les frais financiers ; au-dela du Q3 du secteur, "
        "la capacite a honorer les interets devient un point de "
        "vigilance prioritaire."),
    # --- Partage de la valeur ---
    "repartition_personnel": (
        "Charges de personnel / revenus repartis (VA + subventions), "
        "en %.",
        "Sens favorable : a la baisse. Part de la valeur ajoutee "
        "consacree a la remuneration du travail ; se lit au regard du "
        "secteur et de la taille (une part tres faible peut traduire "
        "une sous-remuneration ou une structure d'effectifs "
        "particuliere)."),
    "repartition_etat": (
        "Impots et taxes / revenus repartis (VA + subventions), en %.",
        "Sens favorable : a la baisse. Part de la valeur ajoutee "
        "preleeve par les taxes (hors impot sur les societes) ; varie "
        "peu entre entreprises d'un meme secteur."),
    "repartition_preteurs": (
        "Charges d'interets / revenus repartis (VA + subventions), en %.",
        "Sens favorable : a la baisse. Part de la valeur ajoutee "
        "versee aux preteurs ; une part superieure a la mediane du "
        "secteur confirme un endettement plus lourd ou plus cher."),
}
