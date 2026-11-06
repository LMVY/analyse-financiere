"""Graphiques Plotly pour le dashboard.

Regles de design (source unique : src.visualization.colors) :
- pas de titre global : le titre de section de la page porte le sens ;
  exception : les courbes d'evolution affichent le nom de l'indicateur
  (elles sont presentees cote a cote, sans titres individuels ailleurs) ;
- grilles horizontales discretes uniquement, pas de cadres ;
- hover unifie : carte blanche, bord fin, texte encre ;
- barres horizontales des que les libelles sont longs (ratios) ;
- couleurs du theme uniquement, statut reserve au sens.
"""
import plotly.graph_objects as go
import pandas as pd

from src.visualization.colors import THEME, CHART, hex_rgba

FONT = "'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"


def base_layout(fig, height=420):
    """Habillage commun : fond transparent, grille discrete, hover unifie."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=THEME["muted"], size=11.5),
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor=THEME["line"],
            font=dict(family=FONT, size=12, color=THEME["ink"]),
        ),
        separators=", ",
    )
    fig.update_xaxes(
        gridcolor=CHART["grid"], zerolinecolor=CHART["grid"],
        showline=False, tickfont=dict(size=11),
    )
    fig.update_yaxes(
        gridcolor=CHART["grid"], zerolinecolor=CHART["grid"],
        showline=False, tickfont=dict(size=11),
    )
    return fig


def _grille_y_seule(fig):
    """Barres horizontales : la grille verticale suffit."""
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=True, gridwidth=1)
    return fig


# ============================================================
# BENCHMARK SECTORIEL : entreprise vs mediane du secteur
# ============================================================
def benchmark_sectoriel(ratios: dict, secteur: str, secteurs_config: dict,
                        scores: dict = None):
    """Barres horizontales entreprise vs mediane du secteur (100 = mediane).

    scores : {nom_ratio: score 0-100} - la couleur de chaque barre
    suit le DEGRADE continu du score (le meme que l'arc du score
    global : vert a 100, nuances tous les 5 %, rouge fonce a 0) ;
    neutre si le ratio n'est pas score.
    """
    if not secteur or secteur not in secteurs_config:
        return None

    ref_secteur = secteurs_config[secteur].get("ratios", {})
    scores = scores or {}
    from src.reporting.glossaire import label_ratio
    # libelle francais -> score (les cles de scores sont des noms de ratios)
    score_par_libelle = {label_ratio(nom): sc for nom, sc in scores.items()}

    data = []
    for cat, ratio_dict in ratios.items():
        for nom, val in ratio_dict.items():
            if val is None or nom not in ref_secteur:
                continue
            mediane = ref_secteur[nom].get("mediane", 0)
            idx = (val / mediane) * 100 if mediane != 0 else 0
            data.append({"Ratio": label_ratio(nom), "Indice": idx})

    if not data:
        return None

    # TOUS les ratios calculés ayant une référence sectorielle :
    # aucun plafond - la hauteur du graphe s'adapte au nombre de barres
    df = pd.DataFrame(data).sort_values("Indice")

    def _couleur(libelle):
        sc = score_par_libelle.get(libelle)
        if sc is not None:
            from src.visualization.colors import get_score_gradient
            return get_score_gradient(sc)
        return THEME["muted"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Entreprise",
        orientation="h",
        x=df["Indice"],
        y=df["Ratio"],
        marker_color=[_couleur(lib) for lib in df["Ratio"]],
        marker_line=dict(width=0),
        text=[f"{v:,.0f}".replace(",", " ") for v in df["Indice"]],
        textposition="outside",
        textfont=dict(size=10.5, color=THEME["ink"]),
        hovertemplate="<b>%{y}</b><br>Indice : %{x:.0f} (100 = mediane)"
                      "<extra></extra>",
    ))

    fig.add_vline(x=100, line_dash="dot", line_color=CHART["cible"],
                  line_width=1.4,
                  annotation_text="Mediane secteur",
                  annotation_position="top right",
                  annotation_font=dict(size=10.5, color=THEME["muted"]))

    fig.update_layout(
        xaxis_title="Indice (100 = mediane du secteur)",
        showlegend=False,
    )
    _grille_y_seule(fig)
    # hauteur adaptative : ~26 px par ratio pour rester lisible, meme
    # avec les 18 ratios affiches (plafond elargi pour les petits
    # ecrans)
    fig = base_layout(fig, max(430, 26 * len(df) + 60))
    # Valeurs placees HORS des barres : marge droite + axe elargi de
    # 12 % pour que la barre la plus longue garde son etiquette dans
    # le conteneur (rien ne doit etre coupe).
    fig.update_layout(margin=dict(l=8, r=48, t=30, b=8))
    vmax = max(max(df["Indice"]), 0)
    vmin = min(min(df["Indice"]), 0)
    fig.update_xaxes(range=[vmin - (vmax - vmin) * 0.12,
                            vmax + (vmax - vmin) * 0.12])
    return fig


# ============================================================
# EVOLUTION MULTI-ANNEES : TOUS LES INDICATEURS SUR UN GRAPHIQUE
# ============================================================
def evolution_indicateurs_unifie(donnees_par_annee: dict, indicateurs: list):
    """Un seul graphique : evolution de tous les indicateurs, une
    couleur par courbe.

    Dynamique :
    - survol unifie : toutes les valeurs d'un exercice dans une seule
      carte blanche ;
    - legende cliquable : isoler/masquer un indicateur ;
    - boutons "Valeurs" / "Base 100" : les montants d'echelles
      differentes se comparent en base 100 (premier exercice = 100).
    """
    annees = sorted(donnees_par_annee)
    if not annees:
        return None
    from src.visualization.colors import CATEGORIES
    palette = [THEME["accent"], THEME["ok"], THEME["warn"], THEME["bad"],
               CATEGORIES["croissance"], CATEGORIES["partage_valeur"]]

    # unite adaptee : M pour les millions, k pour les milliers
    toutes_vals = [abs(v) for a in annees
                   for (_, v) in _valeurs(donnees_par_annee, a, indicateurs)
                   if v is not None]
    vmax = max(toutes_vals, default=0)
    if vmax >= 1e6:
        unite, div = "M EUR", 1e6
    elif vmax >= 1e3:
        unite, div = "k EUR", 1e3
    else:
        unite, div = "EUR", 1.0

    fig = go.Figure()
    y_abs, y_base = [], []
    n_traces = 0
    for i, (code, label) in enumerate(indicateurs):
        vals = [donnees_par_annee[a].get(code) for a in annees]
        if all(v is None for v in vals):
            continue
        col = palette[i % len(palette)]
        # courbe absolue (unite adaptee)
        abs_serie = [round(v / div, 2) if v is not None else None for v in vals]
        # courbe base 100 (premier exercice non nul = 100)
        ref = next((v for v in vals if v), None)
        base_serie = [round(v / ref * 100, 1) if (v is not None and ref) else None
                      for v in vals]
        fig.add_trace(go.Scatter(
            x=annees, y=abs_serie, mode="lines+markers", name=label,
            line=dict(color=col, width=2.5, shape="spline", smoothing=0.6),
            marker=dict(size=7, color=col,
                        line=dict(width=2, color="#FFFFFF")),
            hovertemplate="<b>%{fullData.name}</b> : %{y:,.1f} " + unite +
                          "<extra></extra>",
        ))
        y_abs.append(abs_serie)
        y_base.append(base_serie)
        n_traces += 1

    if not n_traces:
        return None

    fig.update_layout(
        xaxis_title="Exercice",
        yaxis=dict(ticksuffix=" " + unite, gridcolor=CHART["grid"]),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(size=11, color=THEME["ink"])),
        hovermode="x unified",
        # boutons dynamiques : valeurs reelles ou base 100
        updatemenus=[dict(
            type="buttons", direction="right",
            x=1, xanchor="right", y=1.14, yanchor="top",
            bgcolor="#FFFFFF", bordercolor=CHART["grid"],
            font=dict(size=11, color=THEME["ink"]),
            buttons=[
                dict(label="Valeurs", method="update",
                     args=[{"y": y_abs},
                           {"yaxis": {"ticksuffix": " " + unite,
                                      "title": {"text": ""}}}]),
                dict(label="Base 100", method="update",
                     args=[{"y": y_base},
                           {"yaxis": {"ticksuffix": "",
                                      "title": {"text":
                                                "base 100 = premier exercice"}}}]),
            ],
        )],
    )
    base_layout(fig, 430)
    # titre interne des boutons : marge haute suffisante
    fig.update_layout(margin=dict(l=8, r=8, t=52, b=8))
    return fig


def _valeurs(donnees_par_annee, annee, indicateurs):
    """Valeurs (non nulles possibles) des indicateurs d'un exercice."""
    agg = donnees_par_annee.get(annee) or {}
    return [(code, agg.get(code)) for code, _ in indicateurs]


# ============================================================
# COMPARAISON N vs N-1
# ============================================================
def comparaison_n_n1(agregats_n: dict, agregats_n1: dict,
                     agregats_exercices: dict = None):
    """Barres horizontales groupees : agregats cles N vs N-1 (en kEUR).

    agregats_exercices : dict {annee: agregats} de tous les exercices
    disponibles -> ajoute une troisieme serie, la MOYENNE des
    exercices (N et N-1 inclus).
    """
    indicateurs = [
        ("chiffre_affaires", "Chiffre d'affaires"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
        ("tresorerie", "Tresorerie"),
    ]

    labels, vals_n, vals_n1, vals_moy = [], [], [], []
    tous = list((agregats_exercices or {}).values()) or [agregats_n]
    for code, label in indicateurs:
        v_n = agregats_n.get(code, 0)
        v_n1 = agregats_n1.get(code, 0)
        if v_n or v_n1:
            labels.append(label)
            vals_n.append(v_n)
            vals_n1.append(v_n1)
            valeurs = [a.get(code) for a in tous]
            valeurs = [v for v in valeurs if v is not None]
            vals_moy.append(sum(valeurs) / len(valeurs)
                             if valeurs else None)

    if not labels:
        return None

    # Du plus grand au plus petit, N-1 en haut, N en bas
    ordre = sorted(range(len(labels)), key=lambda i: vals_n[i],
                   reverse=False)
    labels = [labels[i] for i in ordre]
    vals_n = [vals_n[i] for i in ordre]
    vals_n1 = [vals_n1[i] for i in ordre]
    vals_moy = [vals_moy[i] for i in ordre]

    def _fmt(vals):
        return [f"{v / 1000:,.0f}".replace(",", " ") if v is not None else ""
                for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Exercice N-1",
        orientation="h",
        y=labels,
        x=[v / 1000 for v in vals_n1],
        marker_color=CHART["n1"],
        marker_line=dict(width=0),
        text=_fmt(vals_n1),
        textposition="outside",
        textfont=dict(size=10, color=THEME["muted"]),
        hovertemplate="<b>%{y}</b><br>N-1 : %{x:,.0f} k\u20ac<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Moyenne des exercices",
        orientation="h",
        y=labels,
        x=[v / 1000 if v is not None else None for v in vals_moy],
        marker_color=THEME["accent2"],
        marker_line=dict(width=0),
        text=_fmt(vals_moy),
        textposition="outside",
        textfont=dict(size=10, color=THEME["muted"]),
        hovertemplate="<b>%{y}</b><br>Moyenne : %{x:,.0f} k\u20ac<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Exercice N",
        orientation="h",
        y=labels,
        x=[v / 1000 for v in vals_n],
        marker_color=CHART["n"],
        marker_line=dict(width=0),
        text=_fmt(vals_n),
        textposition="outside",
        textfont=dict(size=10, color=THEME["ink"]),
        hovertemplate="<b>%{y}</b><br>N : %{x:,.0f} k\u20ac<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        xaxis_title="k\u20ac",
        bargap=0.28,
        bargroupgap=0.04,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    x=1, xanchor="right",
                    font=dict(size=11, color=THEME["ink"])),
    )
    _grille_y_seule(fig)
    fig = base_layout(fig, 420)
    # Tout doit RENTRER dans le conteneur : la legende horizontale
    # au-dessus du trace demande une marge haute, et les valeurs
    # placees HORS des barres (cote droit) une marge droite plus un
    # axe elargi de ~12 % pour la barre la plus longue.
    fig.update_layout(margin=dict(l=8, r=48, t=44, b=8))
    xs = [v / 1000 for v in list(vals_n) + list(vals_n1)
          if v is not None]
    if xs:
        vmax = max(max(xs), 0)
        vmin = min(min(xs), 0)
        fig.update_xaxes(range=[vmin - (vmax - vmin) * 0.12,
                                vmax + (vmax - vmin) * 0.12])
    return fig
