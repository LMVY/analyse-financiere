"""Graphiques matplotlib du rapport PDF.

Palette importee de src.visualization.colors (source unique).
Chaque fonction retourne une figure matplotlib, ou None si les
donnees sont insuffisantes.

Regles de la refonte (rapport professionnel) :
- style unique, typographie DejaVu Sans (meme famille que le texte) ;
- pas de titre dans la figure quand le bandeau de section le porte :
  les figures embarquees gardent un court titre de lecture ;
- reperes de lecture systematiques (40 / 70 / cible) sur les echelles
  de score, la legende reste interne et sobre ;
- couleurs du theme uniquement, statut reserve au sens.
"""
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage

from src.reporting.glossaire import label_categorie
from src.visualization.colors import (
    THEME, get_score_gradient, CATEGORIES,
)

FONT_MPL = "DejaVu Sans"


def style_mpl():
    """Theme matplotlib aligne sur src.visualization.colors."""
    plt.rcParams.update({
        "font.family": FONT_MPL,
        "text.color": THEME["ink"],
        "axes.edgecolor": THEME["line"],
        "axes.labelcolor": THEME["muted"],
        "axes.linewidth": 0.8,
        "xtick.color": THEME["muted"],
        "ytick.color": THEME["muted"],
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.grid": True,
        "grid.color": THEME["line"],
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def fig_vers_image(fig, width_cm):
    """Figure matplotlib -> Image reportlab de la largeur donnee."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    from PIL import Image as PILImage
    with PILImage.open(buf) as img:
        px_w, px_h = img.size
    buf.seek(0)
    hauteur = width_cm * px_h / px_w
    return RLImage(buf, width=width_cm * cm, height=hauteur * cm)


# ============================================================
# RADAR DES CATEGORIES
# ============================================================
def chart_radar_categories(scores_categories):
    """Radar des scores par categorie (0-100), reperes 40 / 70."""
    cats = [(c, v) for c, v in scores_categories.items() if v is not None]
    if not cats:
        return None
    style_mpl()
    labels = [label_categorie(c) for c, _ in cats]
    vals = [v for _, v in cats]
    n = len(cats)
    angles = [i / n * 2 * np.pi for i in range(n)]
    vals_c = vals + [vals[0]]
    angles_c = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(4.4, 3.9),
                           subplot_kw=dict(polar=True))
    # reperes de niveau : 40 (vigilance) et 70 (confort), en filigrane
    ax.fill_between(np.linspace(0, 2 * np.pi, 200), 0, 40,
                    color=THEME["bad"], alpha=0.035)
    ax.fill_between(np.linspace(0, 2 * np.pi, 200), 40, 70,
                    color=THEME["warn"], alpha=0.035)
    ax.fill_between(np.linspace(0, 2 * np.pi, 200), 70, 100,
                    color=THEME["ok"], alpha=0.045)
    ax.plot(angles_c, [70] * (n + 1), color=THEME["ok"],
            linewidth=0.9, linestyle=(0, (2, 3)), alpha=0.7)
    ax.plot(angles_c, [40] * (n + 1), color=THEME["warn"],
            linewidth=0.9, linestyle=(0, (2, 3)), alpha=0.7)
    ax.plot(angles_c, vals_c, color=THEME["accent"], linewidth=2.2,
            marker="o", markersize=4.5,
            markerfacecolor=THEME["accent"], markeredgecolor="white",
            markeredgewidth=1.1)
    ax.fill(angles_c, vals_c, color=THEME["accent"], alpha=0.16)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=8, color=THEME["ink"])
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"],
                       fontsize=6.5, color=THEME["muted"])
    ax.grid(color=THEME["line"], linewidth=0.6)
    ax.spines["polar"].set_color(THEME["line"])
    # titille l'orientation : premier label vers le haut
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_title("Profil de risque par categorie (/100)",
                 fontsize=9.5, color=THEME["ink"], pad=16)
    return fig


# ============================================================
# NIVEAU DES CATEGORIES
# ============================================================
def chart_scores_categories(scores_categories):
    """Barres horizontales des scores par categorie, reperes 40 / 70."""
    cats = sorted([(v, c) for c, v in scores_categories.items()
                   if v is not None])
    if not cats:
        return None
    style_mpl()
    labels = [label_categorie(c) for _, c in cats]
    vals = [v for v, _ in cats]
    couleurs = [get_score_gradient(v) for v in vals]

    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    bars = ax.barh(labels, vals, color=couleurs, height=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 1.5, b.get_y() + b.get_height() / 2,
                f"{v:.0f}", va="center", fontsize=9, fontweight="bold",
                color=THEME["ink"])
    # reperes de lecture : seuils du bareme (40 vigilance, 70 confort)
    for seuil, col in ((40, THEME["warn"]), (70, THEME["ok"])):
        ax.axvline(seuil, color=col, linewidth=0.9,
                   linestyle=(0, (2, 3)), alpha=0.8)
        ax.text(seuil, len(labels) - 0.28, str(seuil), fontsize=6.5,
                color=col, ha="center", va="bottom")
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title("Niveau de chaque categorie (/100)", fontsize=9.5,
                 color=THEME["ink"], pad=10)
    ax.grid(axis="y", visible=False)
    return fig


# ============================================================
# CONSTRUCTION DU SCORE : CONTRIBUTIONS PAR CATEGORIE
# ============================================================
def chart_contributions_categories(scores_categories,
                                   poids_categories=None):
    """Barres horizontales : contribution de chaque categorie au score
    global, en points (score de la categorie x poids du profil).

    La somme des barres vaut exactement le score global : chaque
    contribution suit la meme formule que le moteur (poids du profil
    d'analyse, categories non ponderees ecartees, repli equipondere).
    """
    cats = {c: v for c, v in (scores_categories or {}).items()
            if v is not None}
    if not cats:
        return None
    poids_cfg = {c: (poids_categories or {}).get(c) for c in cats}
    poids = {c: p for c, p in poids_cfg.items() if p}
    if not poids:
        poids = {c: 1.0 for c in cats}
    total_poids = sum(poids.values()) or 1.0
    contribs = {c: cats[c] * poids[c] / total_poids for c in poids}

    tri = sorted(contribs, key=lambda c: contribs[c])
    labels = [label_categorie(c) for c in tri]
    vals = [contribs[c] for c in tri]
    couleurs = [CATEGORIES.get(c, THEME["accent"]) for c in tri]

    style_mpl()
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    bars = ax.barh(labels, vals, color=couleurs, height=0.62)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 0.5,
                b.get_y() + b.get_height() / 2,
                f"+{v:.1f} pts", va="center", fontsize=8.5,
                fontweight="bold", color=THEME["ink"])
    score_global = sum(vals)
    ax.set_xlim(0, max(max(vals), 1) * 1.18)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_xlabel("Points apportes au score global", fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Contribution des categories au score global "
        f"(total : {score_global:.0f} / 100)",
        fontsize=10, color=THEME["ink"], pad=10)
    return fig


# ============================================================
# AGREGATS CLES : N vs N-1
# ============================================================
def chart_comparaison_n_n1(agregats_n, agregats_n1):
    """Barres groupees des agregats cles N vs N-1 (kEUR)."""
    style_mpl()
    indicateurs = [
        ("chiffre_affaires", "Chiffre d'affaires"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
        ("tresorerie", "Tresorerie"),
    ]
    labels, vn, vn1 = [], [], []
    for code, label in indicateurs:
        a, b = agregats_n.get(code, 0), agregats_n1.get(code, 0)
        if a or b:
            labels.append(label)
            vn.append(a / 1000)
            vn1.append(b / 1000)
    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(7.4, 3.3))
    y = np.arange(len(labels))
    h = 0.36
    ax.barh(y - h / 2, vn, height=h, color=THEME["accent"],
            label="Exercice N")
    ax.barh(y + h / 2, vn1, height=h, color="#94A3B8",
            label="Exercice N-1")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("kEUR", fontsize=8.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.set_title("Agregats cles : exercice N vs exercice N-1 (kEUR)",
                 fontsize=10, color=THEME["ink"], pad=10)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(
            lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig
