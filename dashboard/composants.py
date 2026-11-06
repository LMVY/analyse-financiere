"""Composants UI reutilisables de la page Analyse.

Fonctions d'affichage pures (anneaux de score, KPI, graphiques plotly,
tableaux HTML des ratios) : privees de toute logique metier, elles
dessinent a partir des valeurs qu'on leur passe.
"""
import plotly.graph_objects as go

from src.visualization.colors import (
    THEME, CATEGORIES, tint_hex, get_score_gradient,
)
from src.reporting.glossaire import GLOSSAIRE, label_ratio


# ============================================================
# THEME ET COULEURS
# ============================================================
def score_color(s):
    """Couleur CONTINUE d'un score : rouge (0) -> ambre (40) -> vert (70+).

    Plus fin que 3 niveaux : les barres 'Score par categorie', l'anneau
    et le verdict suivent le degradé, harmonises avec le PDF.
    """
    return get_score_gradient(s)

T = dict(THEME)
FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"


def hex_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def verdict(s):
    if s >= 70:
        return "Situation solide"
    if s >= 40:
        return "Situation à surveiller"
    return "Situation fragile"





# ============================================================
# FORMATAGE ET KPI
# ============================================================
def fmt_eur(v):
    return f"{(v or 0):,.0f} €".replace(",", "\u202f")


def label(cat):
    return cat.replace("_", " ").capitalize()


def kpi(name, value, delta, suffix="vs N-1"):
    d = ""
    if delta is not None:
        c = T["ok"] if delta >= 0 else T["bad"]
        arrow = "▲" if delta >= 0 else "▼"
        d = f'<div class="kpi-d" style="color:{c}">{arrow} {abs(delta):.1f} % {suffix}</div>'
    return f'<div class="kpi"><div class="kpi-l">{name}</div><div class="kpi-v">{fmt_eur(value)}</div>{d}</div>'



# ============================================================
# GRAPHIQUES (anneau, radar, contributions)
# ============================================================
def score_ring(score, size=260):
    """Anneau du score global : rempli jusqu'au score, reste VIDE.

    La portion 0 -> score est remplie avec LA couleur du score sur
    l'echelle degrade (vert a 100, nuance tous les 5 % jusqu'au
    rouge fonce a 0) ; le reste de l'anneau reste vide (piste
    discrete). Une seule couronne lisse, aucun trait de separation.
    Demarre a midi (comme une montre) et suit le sens horaire.
    """
    import math
    s = max(0.0, min(100.0, float(score))) if score is not None else 0.0
    r, sw = 82, 14
    cx, cy = 100, 100
    circ = 2 * math.pi * r
    dash = f"{circ * s / 100.0:.2f} {circ:.2f}"
    col = get_score_gradient(s)
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 200 200" role="img" aria-label="Score {score:.0f} sur 100">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{T['line']}" stroke-width="{sw}"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-dasharray="{dash}" transform="rotate(-90 {cx} {cy})"/>
      <text x="100" y="104" text-anchor="middle" font-family="{FONT}" fill="{T['ink']}">
        <tspan font-size="62" font-weight="700">{score:.0f}</tspan><tspan font-size="21" fill="{T['muted']}"> /100</tspan>
      </text>
      <text x="100" y="130" text-anchor="middle" font-family="{FONT}" font-size="14.5" fill="{T['muted']}">score global</text>
    </svg>"""


def category_rows(scores):
    html = ""
    for cat, s in scores.items():
        if s is None:
            continue
        dot = CATEGORIES.get(cat, T["accent"])
        col = score_color(s)
        html += (f'<div class="row"><div class="row-l"><span class="cat-dot" style="background:{dot}"></span>{label(cat)}</div>'
                 f'<div class="track"><div class="fill" style="width:{max(0, min(100, s))}%;background:{col}"></div></div>'
                 f'<div class="row-v" style="color:{col};font-weight:650">{s:.0f}</div></div>')
    return html


def base_layout(fig, height=340):
    """Habillage commun aligne sur charts.py : sobre, sans cadre."""
    grid = T["line"]
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["muted"], size=11.5),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"])),
    )
    fig.update_xaxes(showline=False, tickfont=dict(size=11))
    fig.update_yaxes(showline=False, tickfont=dict(size=11))
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid)
    return fig


def radar_chart(scores):
    items = [(label(k), v) for k, v in scores.items() if v is not None]
    if not items:
        return None
    theta = [i[0] for i in items] + [items[0][0]]
    r = [i[1] for i in items] + [items[0][1]]
    fig = go.Figure(go.Scatterpolar(
        r=r, theta=theta, fill="toself", name="Score",
        line=dict(color=T["accent"], width=2),
        fillcolor=hex_rgba(T["accent"], 0.12),
        marker=dict(size=5, color=T["accent"],
                    line=dict(width=1.5, color="#FFFFFF")),
        hovertemplate="<b>%{theta}</b> : %{r:.0f}/100<extra></extra>",
    ))
    base_layout(fig, 340)
    # Marges elargies : les libelles de categories les plus longs
    # ("risque solvabilite", "gestion activite") doivent rester
    # entiers dans la demi-colonne, rien ne depasse du conteneur
    fig.update_layout(showlegend=False, margin=dict(l=64, r=64, t=28, b=28), polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor=T["line"], linecolor=T["line"],
                        tickfont=dict(size=10, color=T["muted"]), tickvals=[25, 50, 75, 100]),
        angularaxis=dict(gridcolor=T["line"], linecolor=T["line"], tickfont=dict(color=T["ink"], size=12)),
    ))
    return fig




def contribution_chart(scores, poids, details=None, cible=60, medianes=None):
    """Ce qui construit le score : treemap des contributions, ratio par ratio.

    Refait pour la lisibilite :
    - le texte des tuiles ne deborde JAMAIS (uniformtext masque un
      libelle qui ne tient pas dans sa tuile) : les grands ratios
      gardent leur nom francais complet, les petits restent vides ;
    - le SURVOL dit tout : nom complet, categorie, valeur, mediane du
      secteur, score, poids et contribution en points et en % du
      score global - une carte blanche lisible, lignes courtes.
    """
    if not scores:
        return None
    details = details or {}
    medianes = medianes or {}

    cats = {c: s for c, s in scores.items() if s is not None}
    if not cats:
        return None
    total_poids_cats = sum((poids or {}).get(c, 1) for c in cats) or 1

    # ---- 1er passage : contributions par categorie et par ratio ----
    par_cat = {}       # cat -> [(libelle, contrib, score_ratio, survol)]
    for cat, cat_score in cats.items():
        poids_cat = (poids or {}).get(cat, 1)
        rat = {nom: det for nom, det in details.items()
               if det.get("categorie") == cat and det.get("score") is not None}
        if not rat:
            continue
        somme_poids_r = sum(d.get("poids", 0) for d in rat.values()) or 1
        tuiles = []
        for nom, det in rat.items():
            score_r = det.get("score") or 0
            poids_r = det.get("poids") or 0
            contrib = (score_r * poids_r / somme_poids_r
                       * poids_cat / total_poids_cats)
            val = det.get("valeur")
            val_txt = (f"{val:,.2f}".replace(",", " ")
                       if isinstance(val, (int, float)) else "n/d")
            survol = (f"<b>{label_ratio(nom)}</b><br>"
                      f"{label(cat)}<br>"
                      f"Valeur : {val_txt}<br>")
            med = medianes.get(nom)
            if med is not None:
                survol += f"Mediane du secteur : {med:,.2f}".replace(",", " ")
                survol += "<br>"
            survol += (f"Score du ratio : {score_r:.0f} / 100<br>"
                       f"Poids : {poids_r:.2f} dans la categorie "
                       f"({poids_cat / total_poids_cats * 100:.0f} % du profil)<br>"
                       f"Contribution : +{contrib:.1f} pts")
            tuiles.append((label_ratio(nom), contrib, score_r, survol))
        par_cat[cat] = tuiles

    if not par_cat:
        return None

    # ---- 2e passage : noeuds, valeurs EXPLICITES (jamais None) ----
    ids, labels, parents, values, couleurs, textes, survols = \
        [], [], [], [], [], [], []

    def _texte_tuille(contrib, nom, seuil_complet=1.5, seuil_nom=0.6):
        """Texte d'une tuile selon sa place : complet, nom seul, rien.

        Les libelles qui ne tiennent pas dans leur tuile sont masques
        par uniformtext (mode=hide) : aucun chevauchement, le detail
        complet reste au survol.
        """
        if contrib >= seuil_complet:
            return f"{nom}<br>+{contrib:.1f}"
        if contrib >= seuil_nom:
            return nom
        return ""

    for cat in sorted(par_cat,
                      key=lambda c: sum(t[1] for t in par_cat[c]),
                      reverse=True):
        tuiles = sorted(par_cat[cat], key=lambda t: t[1], reverse=True)
        contrib_cat = sum(t[1] for t in tuiles)
        cat_id = f"cat-{cat}"
        col_cat = CATEGORIES.get(cat, T["accent"])
        ids.append(cat_id)
        labels.append(label(cat))
        parents.append("racine")
        values.append(contrib_cat)          # valeur explicite, jamais None
        couleurs.append(tint_hex(col_cat, 0.16))
        textes.append(f"{label(cat)}<br>+{contrib_cat:.1f}")
        survols.append(f"<b>{label(cat)}</b><br>"
                       f"Score : {cats[cat]:.0f} / 100<br>"
                       f"{len(tuiles)} ratios evalues<br>"
                       f"Poids du profil : "
                       f"{(poids or {}).get(cat, 1) / total_poids_cats * 100:.0f} %")
        for nom, contrib, score_r, survol in tuiles:
            ids.append(f"{cat_id}-{nom}")
            labels.append(nom)
            parents.append(cat_id)
            values.append(contrib)
            couleurs.append(tint_hex(col_cat, 0.30 + 0.70 * score_r / 100))
            textes.append(_texte_tuille(contrib, nom))
            survols.append(survol)

    if not any(values):
        return None
    # score global = somme des contributions des CATEGORIES (values
    # contient aussi les tuiles : ne pas doubler le compte)
    score_global = sum(v for p, v in zip(parents, values) if p == "racine")
    n_ratios = sum(len(t) for t in par_cat.values())

    # racine : le score global obtenu, valeur explicite
    ids.insert(0, "racine")
    labels.insert(0, f"Score global {score_global:.0f} / 100")
    parents.insert(0, "")
    values.insert(0, score_global)
    couleurs.insert(0, "#FFFFFF")
    textes.insert(0, f"Score global {score_global:.0f} / 100")
    survols.insert(0, (f"<b>Score global</b><br>{score_global:.1f} / 100<br>"
                      f"{n_ratios} ratios evalues - {len(par_cat)} categories"))

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="remainder",
        marker=dict(colors=couleurs,
                    line=dict(color="#FFFFFF", width=2)),
        text=textes,
        textposition="top left",
        tiling=dict(pad=4),
        pathbar=dict(visible=False),
        customdata=survols,
        hovertemplate="%{customdata}<extra></extra>",
        # carte de survol : fond blanc, bord fin, texte encre, lisible
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"]),
                        align="left"),
        insidetextfont=dict(size=11.5, color=T["ink"]),
    ))
    fig.update_layout(
        height=460,
        margin=dict(l=4, r=4, t=10, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=T["ink"]),
        # un libelle qui ne tient pas dans sa tuile est MASQUE (jamais
        # de texte qui deborde ou se chevauche) ; le detail complet
        # reste disponible au survol
        uniformtext=dict(minsize=9, mode="hide"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=T["line"],
                        font=dict(family=FONT, size=12, color=T["ink"]),
                        align="left"),
    )
    return fig



# ============================================================
# TABLEAUX HTML DES RATIOS
# ============================================================
def _score_cell_html(sc):
    """Cellule Score /100 : mini-barre + chiffre colore.

    Rendu unique partage par la synthese et l'onglet Ratios : les
    scores s'affichent exactement de la meme facon partout.
    """
    if sc is None:
        return f'<span style="color:{T["muted"]}">n/d</span>'
    col = get_score_gradient(sc)
    return (f'<span class="rt-bar"><i style="width:'
            f'{max(0.0, min(100.0, sc)):.0f}%;background:{col}"></i></span>'
            f'<span class="rt-sc" style="color:{col}">{sc:.0f}</span>')


# Colonnes du tableau des ratios : grille PARTAGEE par tous les
# tableaux -> chaque colonne demarre au meme point partout (valeurs,
# moyennes, medianes du secteur et scores /100 parfaitement
# alignes). Largeurs en POURCENTAGES : les colonnes gardent leur
# place quel que soit la largeur disponible et les valeurs
# s'affichent en entier (la premiere colonne absorbe le reste ;
# min-width + defilement horizontal en CSS pour les ecrans etroits).
_RT_COLGROUP = (
    '<colgroup><col><col style="width:12%">'
    '<col style="width:12%"><col style="width:12%">'
    '<col style="width:7%"><col style="width:14%">'
    '<col style="width:10%"></colgroup>')


def _rt_thead(valeur_label="Valeur N"):
    """En-tete du tableau des ratios ; le libelle de la colonne valeur
    depend de la base du score (exercice N ou moyenne des exercices)."""
    return ('<thead><tr><th>Ratio</th>'
            f'<th>{valeur_label}</th><th>Moyenne</th>'
            '<th>M&eacute;d. secteur</th><th>Tend.</th>'
            '<th>Score /100</th><th>Poids</th></tr></thead>')

# Categories de controles du validateur : numero du controle -> famille.
# Numerotation SEQUENTIELLE : l'ordre d'execution = l'ordre des numeros
# (1-6 base, 7-18 comptable, 19-22 economique, 23-32 complementaires,
#  33-36 enrichissement, 37-39 sectoriel).
_CATEGORIE_CONTROLE = {
    1: "Structure du bilan", 23: "Structure du bilan",
    24: "Structure du bilan", 25: "Structure du bilan",
    26: "Structure du bilan", 29: "Structure du bilan",
    32: "Structure du bilan",
    2: "Soldes intermediaires et resultats", 3: "Soldes intermediaires et resultats",
    5: "Soldes intermediaires et resultats", 13: "Soldes intermediaires et resultats",
    14: "Soldes intermediaires et resultats", 15: "Soldes intermediaires et resultats",
    19: "Soldes intermediaires et resultats", 27: "Soldes intermediaires et resultats",
    28: "Soldes intermediaires et resultats",
    4: "Equilibres financiers", 7: "Equilibres financiers",
    8: "Equilibres financiers", 9: "Equilibres financiers",
    10: "Equilibres financiers", 11: "Equilibres financiers",
    12: "Equilibres financiers", 31: "Equilibres financiers",
    35: "Equilibres financiers", 36: "Equilibres financiers",
    6: "Plausibilite des donnees", 16: "Plausibilite des donnees",
    17: "Plausibilite des donnees", 18: "Plausibilite des donnees",
    20: "Plausibilite des donnees", 21: "Plausibilite des donnees",
    22: "Plausibilite des donnees", 30: "Plausibilite des donnees",
    33: "Plausibilite des donnees", 34: "Plausibilite des donnees",
    37: "Reference sectorielle", 38: "Reference sectorielle",
    39: "Reference sectorielle",
}
_ORDRE_CATEGORIES = ["Structure du bilan",
                     "Soldes intermediaires et resultats",
                     "Equilibres financiers",
                     "Plausibilite des donnees",
                     "Reference sectorielle"]


def _rt_val(v):
    if v is None:
        return "n/d"
    return f"{v:,.2f}".replace(",", " ")


def _rt_ligne(nom, det, h, med_sect=None):
    """Ligne du tableau des ratios : rendu UNIQUE partage.

    Utilise par la synthese et l'onglet Ratios : une ligne pour un
    ratio donnee est representee exactement pareil partout.
    med_sect : mediane du secteur (reference de comparaison), None si
    aucune reference sectorielle n'existe pour ce ratio.
    """
    det = det or {}
    h = h or {}
    sc = det.get("score")
    val_n = det.get("valeur")
    if val_n is None:
        val_n = h.get("N")
    val_moy = h.get("moyenne")
    med_txt = "—" if med_sect is None else _rt_val(med_sect)
    tendance = h.get("tendance", "-")
    if h.get("type") == "stock":
        tendance = "-"
    # Libelle francais + formule en info-bulle (titre de la cellule)
    libelle = label_ratio(nom)
    formule = (GLOSSAIRE.get(nom) or ("", ""))[0]
    tooltip = (f' title="{formule}"' if formule else "")
    type_r = h.get("type", "flux")
    t_s = str(tendance)
    if t_s in ("↗", "hausse", "▲"):
        t_col, t_txt = T["ok"], "↗"
    elif t_s in ("↘", "baisse", "▼"):
        t_col, t_txt = T["bad"], "↘"
    else:
        t_col, t_txt = T["muted"], "—"
    return (f'<tr><td><b{tooltip}>{libelle}</b><span class="rt-tag">{type_r}</span></td>'
            f'<td>{_rt_val(val_n)}</td><td>{_rt_val(val_moy)}</td>'
            f'<td>{med_txt}</td>'
            f'<td style="color:{t_col}">{t_txt}</td>'
            f'<td>{_score_cell_html(sc)}</td>'
            f'<td>{(det.get("poids") or 0):.2f}</td></tr>')


def ratios_table_html(details, historique=None, cats_scores=None,
                      filtre_cat="Toutes", filtre_type="Tous",
                      medianes=None, valeur_label="Valeur N"):
    """Tableau detaille des ratios, presente en cartes par categorie.

    Harmonise avec le design de la page : une carte par categorie
    (couleur habituelle + score de la categorie), lignes classees de
    la meilleure note a la moins bonne, score en mini-barre + chiffre
    colores par le degrade continu vert (100) -> rouge fonce (0),
    tendance en fleche coloree, valeurs alignees a droite.

    medianes : {nom_ratio: mediane du secteur} - la colonne "Med.
    secteur" donne la reference de comparaison sectorielle (la
    mediane, pas la moyenne : elle n'est pas deplacee par les valeurs
    extremes). Absente si aucun secteur n'est detecte ou si le ratio
    n'a pas de reference sectorielle.
    """
    historique = historique or {}
    by_cat = {}
    for nom, det in (details or {}).items():
        cat = det.get("categorie", "autre")
        if filtre_cat != "Toutes" and label(cat) != filtre_cat:
            continue
        h = historique.get(nom, {})
        if filtre_type != "Tous" and h.get("type", "flux") != filtre_type:
            continue
        by_cat.setdefault(cat, []).append((nom, det, h))
    if not by_cat:
        return ""

    blocs = []
    # Ordre des categories : score decroissant, meme ordre que la
    # synthese et que le PDF (les non notees passent en fin)
    for cat in sorted(by_cat,
                      key=lambda c: ((cats_scores or {}).get(c)
                                     if (cats_scores or {}).get(c) is not None
                                     else -1), reverse=True):
        # Ratios notes d'abord (score decroissant), non notes (n/d) en fin
        lignes = sorted(by_cat[cat],
                        key=lambda t: (t[1].get("score") is None,
                                       -(t[1].get("score") or 0)))
        col_cat = CATEGORIES.get(cat, T["accent"])
        rows_html = ""
        for nom, det, h in lignes:
            rows_html += _rt_ligne(nom, det, h, (medianes or {}).get(nom))
        sc_cat = (cats_scores or {}).get(cat)
        sc_cat_txt = f"{sc_cat:.0f} /100" if sc_cat is not None else ""
        sc_cat_col = get_score_gradient(sc_cat) if sc_cat is not None else T["muted"]
        blocs.append(
            '<div class="rt-wrap">'
            f'<div class="rt-cat" style="border-left:4px solid {col_cat}">'
            f'<span>{label(cat)}</span>'
            f'<span class="rd-hs" style="color:{sc_cat_col}">{sc_cat_txt}</span></div>'
            f'<table class="rt">{_RT_COLGROUP}{_rt_thead(valeur_label)}'
            f'<tbody>{rows_html}</tbody></table></div>')
    return "".join(blocs)



