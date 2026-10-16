"""Palette de couleurs centralisee pour tout le dashboard.

Regle : un score suit TOUJOURS ce bareme, partout.
"""

# ============================================================
# PALETTE SCORE (5 niveaux)
# ============================================================
SCORE_COLORS = {
    "excellent": "#27ae60",   # >= 75  Vert emeraude
    "bon":       "#2980b9",   # >= 60  Bleu
    "moyen":     "#f39c12",   # >= 45  Orange
    "faible":    "#e67e22",   # >= 30  Orange fonce
    "critique":  "#e74c3c",   # <  30  Rouge
}

# Palette continue pour degrades
SCORE_SCALE = [
    [0.00, "#e74c3c"],  # 0   Rouge
    [0.30, "#e67e22"],  # 30  Orange fonce
    [0.45, "#f39c12"],  # 45  Orange
    [0.60, "#2980b9"],  # 60  Bleu
    [0.75, "#27ae60"],  # 75  Vert
    [1.00, "#27ae60"],  # 100 Vert
]

# ============================================================
# COULEURS NEUTRES
# ============================================================
NEUTRAL = {
    "primaire":   "#2c3e50",   # Bleu nuit (titres)
    "secondaire": "#7f8c8d",   # Gris ardoise
    "fond":       "#f8f9fa",   # Gris tres clair
    "bordure":    "#dee2e6",   # Gris bordure
    "texte":      "#212529",   # Noir doux
}

# ============================================================
# COULEURS POUR GRAPHES
# ============================================================
CHART = {
    "n":          "#3498db",   # Bleu (exercice N)
    "n1":         "#95a5a6",   # Gris (exercice N-1)
    "positif":    "#27ae60",   # Vert
    "negatif":    "#e74c3c",   # Rouge
    "cible":      "#2c3e50",   # Ligne cible
    "radar":      "rgba(52, 152, 219, 0.3)",
    "radar_line": "#3498db",
}

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def get_score_color(score):
    """Retourne la couleur hex selon le score (0-100)."""
    if score is None:
        return NEUTRAL["secondaire"]
    if score >= 75:
        return SCORE_COLORS["excellent"]
    elif score >= 60:
        return SCORE_COLORS["bon"]
    elif score >= 45:
        return SCORE_COLORS["moyen"]
    elif score >= 30:
        return SCORE_COLORS["faible"]
    else:
        return SCORE_COLORS["critique"]


def get_score_label(score):
    """Retourne le label selon le score."""
    if score is None:
        return "N/A"
    if score >= 75:
        return "Excellent"
    elif score >= 60:
        return "Bon"
    elif score >= 45:
        return "Moyen"
    elif score >= 30:
        return "Faible"
    else:
        return "Critique"


def get_score_emoji(score):
    """Retourne un emoji selon le score."""
    if score is None:
        return "⚪"
    if score >= 75:
        return "🟢"
    elif score >= 60:
        return "🔵"
    elif score >= 45:
        return "🟠"
    elif score >= 30:
        return "🟧"
    else:
        return "🔴"


def get_delta_color(delta, inverse=False):
    """Couleur selon variation.

    Args:
        delta: variation (positive ou negative)
        inverse: si True, une baisse est bonne (ex: gearing)
    """
    if delta is None:
        return NEUTRAL["secondaire"]
    positif = delta > 0
    if inverse:
        positif = not positif
    return CHART["positif"] if positif else CHART["negatif"]


def format_score_badge(score):
    """Retourne un badge colore pour un score."""
    color = get_score_color(score)
    emoji = get_score_emoji(score)
    return f"{emoji} **{score:.1f}**/100"


if __name__ == "__main__":
    # Test
    print("=== Tests ===")
    for s in [80, 65, 50, 35, 20, None]:
        print(f"  Score {s} : {get_score_color(s)} | {get_score_label(s)} | {get_score_emoji(s)}")
