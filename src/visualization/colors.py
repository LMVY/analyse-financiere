"""Palette de couleurs centralisee pour tout le projet.

Source unique de verite : le dashboard, charts.py et pdf_report.py
importent tous depuis ce module. Toute evolution se fait ici.

Regles :
- un score suit TOUJOURS le meme bareme partout (3 couleurs) ;
- l'exercice N est accent, l'exercice N-1 est neutre/gris ;
- les couleurs de statut (ok/warn/bad) sont reservees au sens,
  jamais a la decoration.
"""

# ============================================================
# THEME (aligne sur le dashboard : _analyse_body.py)
# ============================================================
THEME = {
    "bg":     "#F5F6F8",   # fond de page
    "paper":  "#FFFFFF",   # surfaces (cartes, tables)
    "ink":    "#101828",   # texte principal
    "muted":  "#667085",   # texte secondaire
    "line":   "#E4E7EC",   # bordures, grilles
    "accent": "#2B50C8",   # couleur d'accent (exercice N, series principales)
    "ok":     "#1F9D6B",   # statut positif
    "warn":   "#D98E04",   # statut vigilance
    "bad":    "#D64545",   # statut negatif
}

# ============================================================
# SCORES (3 niveaux, partout identiques)
# ============================================================
SEUIL_SOLIDE = 70
SEUIL_SURVEILLANCE = 40

SCORE_COLORS = {
    "solide":     THEME["ok"],
    "surveiller": THEME["warn"],
    "fragile":    THEME["bad"],
}


def get_score_color(score):
    """Couleur d'un score (0-100), meme bareme que le dashboard."""
    if score is None:
        return THEME["muted"]
    if score >= SEUIL_SOLIDE:
        return SCORE_COLORS["solide"]
    if score >= SEUIL_SURVEILLANCE:
        return SCORE_COLORS["surveiller"]
    return SCORE_COLORS["fragile"]


def get_score_verdict(score):
    """Verdict court d'un score (aligne sur le dashboard)."""
    if score is None:
        return "Non evaluable"
    if score >= SEUIL_SOLIDE:
        return "Situation solide"
    if score >= SEUIL_SURVEILLANCE:
        return "Situation a surveiller"
    return "Situation fragile"


def get_score_label(score):
    """Label nuance (5 niveaux) pour les tableaux detailles."""
    if score is None:
        return "N/A"
    if score >= 80:
        return "Excellent"
    if score >= 70:
        return "Bon"
    if score >= 55:
        return "Moyen +"
    if score >= 40:
        return "Moyen -"
    if score >= 25:
        return "Faible"
    return "Critique"


# ============================================================
# CATEGORIES (une couleur par categorie, graphs multi-series)
# ============================================================
CATEGORIES = {
    "liquidite":          "#2B8FE8",   # Bleu
    "endettement":        "#E85D2B",   # Rouge-orange
    "rentabilite":        "#1F9D6B",   # Vert
    "croissance":         "#9B59B6",   # Violet
    "gestion_activite":   "#F39C12",   # Orange dore
    "risque_solvabilite": "#16A085",   # Turquoise
}


def get_categorie_color(cat):
    """Couleur d'une categorie (fallback : accent)."""
    return CATEGORIES.get(cat, THEME["accent"])


# ============================================================
# COULEURS POUR GRAPHES
# ============================================================
CHART = {
    "n":          THEME["accent"],       # exercice N
    "n1":         "#98A2B3",             # exercice N-1 (neutre)
    "cible":      THEME["ink"],          # lignes de cible / mediane
    "radar":      THEME["accent"],
    "grid":       THEME["line"],
    "texte":      THEME["muted"],
}

SCORE_SCALE = [
    [0.00, THEME["bad"]],
    [0.40, THEME["warn"]],
    [0.70, THEME["ok"]],
    [1.00, THEME["ok"]],
]


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def hex_rgba(h, a):
    """'#1F9D6B', 0.3 -> 'rgba(31,157,107,0.3)'."""
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def get_delta_color(delta, inverse=False):
    """Couleur selon une variation.

    Args:
        delta: variation (positive ou negative)
        inverse: si True, une baisse est bonne (ex: gearing)
    """
    if delta is None:
        return THEME["muted"]
    positif = delta > 0
    if inverse:
        positif = not positif
    return THEME["ok"] if positif else THEME["bad"]


if __name__ == "__main__":
    for s in [85, 72, 55, 40, 20, None]:
        print(f"score {s} : {get_score_color(s)} | {get_score_verdict(s)} | {get_score_label(s)}")
