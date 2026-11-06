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
    "bg":     "#F8FAFC",   # fond de page (slate 50)
    "paper":  "#FFFFFF",   # surfaces (cartes, tables)
    "ink":    "#0F172A",   # texte principal (slate 900)
    "muted":  "#64748B",   # texte secondaire (slate 500)
    "line":   "#E2E8F0",   # bordures, grilles (slate 200)
    "accent": "#4F46E5",   # indigo - accent principal, exercice N
    "ok":     "#059669",   # emeraude - statut positif
    "warn":   "#D97706",   # ambre - statut vigilance
    "bad":    "#DC2626",   # rouge - statut negatif
    "accent2": "#818CF8",  # indigo clair - series secondaires
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

# ancre basse du degrade continu : rouge TRES fonce a 0
ROUGE_FONCE = "#7F1D1D"
# ancre intermediaire : vert jaunatre a 70, le vert plein n'arrive
# qu'a 100 -- la couleur doit changer a chaque tranche de 5 %
VERT_DEGRADE = "#65A30D"


def get_score_color(score):
    """Couleur d'un score (0-100), meme bareme que le dashboard."""
    if score is None:
        return THEME["muted"]
    if score >= SEUIL_SOLIDE:
        return SCORE_COLORS["solide"]
    if score >= SEUIL_SURVEILLANCE:
        return SCORE_COLORS["surveiller"]
    return SCORE_COLORS["fragile"]


def _mix_hex(h1, h2, t):
    """Melange lineaire de deux couleurs hex (t dans [0, 1])."""
    a = [int(h1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(h2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * max(0.0, min(1.0, t))):02X}"
                         for x, y in zip(a, b))


def get_score_gradient(score):
    """Couleur CONTINUE d'un score (0-100), degrade sur TOUTE l'echelle.

    Rouge fonce a 0, rouge a 20, ambre a 40, vert jaunatre a 70 puis
    vert plein a 100 : chaque tranche de 5 % a sa nuance propre
    (100 % vert, 95 % vert degrades, 90 % vert degrades encore...).
    """
    if score is None:
        return THEME["muted"]
    s = max(0.0, min(100.0, float(score)))
    if s <= 20:
        return _mix_hex(ROUGE_FONCE, SCORE_COLORS["fragile"], s / 20)
    if s <= 40:
        return _mix_hex(SCORE_COLORS["fragile"], SCORE_COLORS["surveiller"],
                        (s - 20) / 20)
    if s <= 70:
        return _mix_hex(SCORE_COLORS["surveiller"], VERT_DEGRADE,
                        (s - 40) / 30)
    return _mix_hex(VERT_DEGRADE, SCORE_COLORS["solide"], (s - 70) / 30)


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
    "croissance":         "#8B5CF6",   # Violet
    "rentabilite":        "#10B981",   # Emeraude
    "gestion_activite":   "#F59E0B",   # Ambre
    "endettement":        "#E11D48",   # Framboise
    "partage_valeur":     "#0EA5E9",   # Bleu ciel
}


def get_categorie_color(cat):
    """Couleur d'une categorie (fallback : accent)."""
    return CATEGORIES.get(cat, THEME["accent"])


def tint_hex(hex_color, t):
    """Couleur teinte : melange blanc -> hex_color selon t (0 = blanc, 1 = pleine).

    Sert aux representations denses (treemap) : la couleur de la
    categorie est conservee, son intensite porte le niveau du score.
    """
    return _mix_hex("#FFFFFF", hex_color, t)


# ============================================================
# COULEURS POUR GRAPHES
# ============================================================
CHART = {
    "n":          THEME["accent"],       # exercice N
    "n1":         "#94A3B8",             # exercice N-1 (neutre)
    "cible":      THEME["ink"],          # lignes de cible / mediane
    "radar":      THEME["accent"],
    "grid":       THEME["line"],
    "texte":      THEME["muted"],
}


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
