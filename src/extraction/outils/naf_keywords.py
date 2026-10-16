"""Detection du secteur par mots-cles dans le nom d'entreprise.

Approche pragmatique : sans API, on regarde les mots du nom.
Ex: "ENTREP TRAVAUX ELECTRIQUES CANALISATIONS" -> construction
"""
import re
import unicodedata


# Mots-cles par secteur (insensibles accents/casse)
MOTS_CLES = {
    "construction": [
        "travaux", "construction", "batiment", "btp", "canalisation",
        "electricite", "electricien", "plomberie", "maconnerie",
        "charpente", "couverture", "renovation", "genie civil",
        "pavage", "terrassement", "peinture batiment",
    ],
    "industrie": [
        "industrie", "industriel", "fabrication", "manufacture",
        "usine", "production", "atelier mecanique", "metal",
        "mecanique", "chaudronnerie", "forge", "fonderie",
    ],
    "commerce": [
        "commerce", "vente", "magasin", "boutique", "distribution",
        "negoce", "grossiste", "detaillant", "supermarche", "epicerie",
    ],
    "transport": [
        "transport", "logistique", "camion", "routier", "fret",
        "livraison", "taxi", "ambulance", "demenagement",
    ],
    "hotellerie_restauration": [
        "hotel", "restaurant", "brasserie", "cafe", "bar",
        "traiteur", "cuisine", "pizzeria", "boulangerie", "patisserie",
    ],
    "information_communication": [
        "informatique", "logiciel", "software", "digital", "web",
        "communication", "media", "studio", "telecom", "edition",
        "developpement", "startup", "data", "tech",
    ],
    "immobilier": [
        "immobilier", "promotion", "fonciere", "agence immobiliere",
        "gestion locative", "syndic",
    ],
    "services": [
        "conseil", "consulting", "audit", "expertise", "comptable",
        "avocat", "notaire", "medecin", "sante", "clinique",
        "formation", "education", "enseignement", "recherche",
        "architecture", "ingenierie", "design", "publicite",
        "marketing", "restauration collective", "securite",
        "nettoyage", "entretien", "jardin", "paysage",
    ],
    "agriculture": [
        "agricole", "agriculture", "elevage", "culture", "viticole",
        "vigne", "ferme", "exploitation agricole", "peche",
    ],
}


def normalize_text(text):
    """Minuscules sans accents."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_secteur_from_nom(nom_entreprise):
    """Detecte le secteur a partir du nom de l'entreprise.

    Args:
        nom_entreprise: str

    Returns:
        (secteur, mots_trouves) ou (None, [])
    """
    if not nom_entreprise:
        return None, []

    norm = normalize_text(nom_entreprise)
    scores = {}

    for secteur, mots in MOTS_CLES.items():
        matches = []
        for mot in mots:
            if mot in norm:
                matches.append(mot)
        if matches:
            scores[secteur] = matches

    if not scores:
        return None, []

    # Prendre le secteur avec le plus de matches
    meilleur = max(scores.items(), key=lambda x: len(x[1]))
    return meilleur[0], meilleur[1]


if __name__ == "__main__":
    tests = [
        "ENTREP TRAVAUX ELECTRIQUES CANALISATIONS",
        "SOGECA",
        "Boulangerie Martin",
        "Cabinet Conseil Dupont",
        "Transport Express SARL",
    ]

    for nom in tests:
        secteur, mots = detect_secteur_from_nom(nom)
        print(f"  {nom:50s} -> {secteur}  ({mots})")
