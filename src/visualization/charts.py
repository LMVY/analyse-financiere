"""Graphiques Plotly pour le dashboard.

Toutes les couleurs viennent de src.visualization.colors (source unique).
"""
import plotly.graph_objects as go
from src.visualization.colors import (
    THEME, CHART, CATEGORIES,
    get_score_color, get_score_verdict, get_categorie_color, hex_rgba,
)

import pandas as pd


def base_layout(fig, height=420):
    """Habillage commun : fond transparent, grilles et polices du theme."""
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=48, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME["muted"], size=12),
    )
    fig.update_xaxes(gridcolor=CHART["grid"], zerolinecolor=CHART["grid"],
                     linecolor=CHART["grid"])
    fig.update_yaxes(gridcolor=CHART["grid"], zerolinecolor=CHART["grid"],
                     linecolor=CHART["grid"])
    return fig


# ============================================================
# 1. RADAR DES SCORES PAR CATEGORIE
# ============================================================
def radar_scores(scores_categories: dict, titre: str = "Scores par categorie"):
    """Radar chart des scores par categorie."""
    cats = []
    vals = []
    for cat, sc in scores_categories.items():
        if sc is not None:
            cats.append(cat.replace("_", " ").title())
            vals.append(sc)

    if not cats:
        return None

    # Fermer le polygone
    cats_closed = cats + [cats[0]]
    vals_closed = vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=cats_closed,
        fill="toself",
        name="Scores",
        line=dict(color=CHART["radar"], width=2),
        fillcolor=hex_rgba(CHART["radar"], 0.14),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor=CHART["grid"], linecolor=CHART["grid"]),
            angularaxis=dict(gridcolor=CHART["grid"], linecolor=CHART["grid"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        title=dict(text=titre, font=dict(color=THEME["ink"])),
    )
    return base_layout(fig, 420)


# ============================================================
# 2. WATERFALL DES CONTRIBUTIONS
# ============================================================
def waterfall_contributions(scores_categories: dict, poids: dict):
    """Barres horizontales des contributions de chaque categorie au score global."""
    data = []
    for cat, sc in scores_categories.items():
        if sc is None:
            continue
        poids_cat = poids.get(cat, 0)
        contribution = sc * poids_cat
        data.append({
            "Categorie": cat.replace("_", " ").title(),
            "Score": sc,
            "Poids": poids_cat,
            "Contribution": contribution,
        })

    if not data:
        return None

    df = pd.DataFrame(data).sort_values("Contribution", ascending=True)

    fig = go.Figure(go.Bar(
        x=df["Contribution"],
        y=df["Categorie"],
        orientation="h",
        marker=dict(color=[get_score_color(s) for s in df["Score"]]),
        text=[f"{c:.1f}" for c in df["Contribution"]],
        textposition="outside",
    ))

    fig.update_layout(
        title=dict(text="Contribution des categories au score global",
                   font=dict(color=THEME["ink"])),
        xaxis_title="Contribution (score x poids)",
        yaxis_title="",
    )
    return base_layout(fig, 420)


# ============================================================
# 3. COMPARAISON N vs N-1
# ============================================================
def comparaison_n_n1(agregats_n: dict, agregats_n1: dict):
    """Bar chart comparatif N vs N-1."""
    indicateurs = [
        ("chiffre_affaires", "CA"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
    ]

    labels = []
    vals_n = []
    vals_n1 = []

    for code, label in indicateurs:
        v_n = agregats_n.get(code, 0)
        v_n1 = agregats_n1.get(code, 0)
        if v_n or v_n1:
            labels.append(label)
            vals_n.append(v_n)
            vals_n1.append(v_n1)

    if not labels:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="N",
        x=labels,
        y=vals_n,
        marker_color=CHART["n"],
        text=[f"{v/1000:.0f} k" for v in vals_n],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="N-1",
        x=labels,
        y=vals_n1,
        marker_color=CHART["n1"],
        text=[f"{v/1000:.0f} k" for v in vals_n1],
        textposition="outside",
    ))

    fig.update_layout(
        title=dict(text="Comparaison N vs N-1", font=dict(color=THEME["ink"])),
        barmode="group",
        yaxis_title="Euros",
        legend=dict(orientation="h", y=1.1),
    )
    return base_layout(fig, 420)


# ============================================================
# 4. BENCHMARK SECTORIEL
# ============================================================
def benchmark_sectoriel(ratios: dict, secteur: str, secteurs_config: dict):
    """Bar chart entreprise vs mediane du secteur."""
    if not secteur or secteur not in secteurs_config:
        return None

    ref_secteur = secteurs_config[secteur].get("ratios", {})

    data = []
    for cat, ratio_dict in ratios.items():
        for nom, val in ratio_dict.items():
            if val is None or nom not in ref_secteur:
                continue
            ref = ref_secteur[nom]
            mediane = ref.get("mediane", 0)

            # Normaliser (100 = mediane)
            if mediane != 0:
                idx = (val / mediane) * 100
            else:
                idx = 0

            data.append({
                "Ratio": nom,
                "Entreprise": val,
                "Mediane secteur": mediane,
                "Indice": idx,
            })

    if not data:
        return None

    df = pd.DataFrame(data).head(15)  # Top 15

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Entreprise",
        x=df["Ratio"],
        y=df["Indice"],
        marker_color=[
            THEME["ok"] if i >= 100 else (THEME["warn"] if i >= 80 else THEME["bad"])
            for i in df["Indice"]
        ],
        text=[f"{v:.0f}" for v in df["Indice"]],
        textposition="outside",
    ))

    fig.add_hline(y=100, line_dash="dash", line_color=CHART["cible"],
                  annotation_text="Mediane secteur")

    fig.update_layout(
        title=dict(
            text=f"Benchmark sectoriel ({secteurs_config[secteur].get('label', secteur)})",
            font=dict(color=THEME["ink"]),
        ),
        yaxis_title="Indice (100 = mediane)",
        xaxis_tickangle=-45,
        showlegend=False,
    )
    return base_layout(fig, 450)


# ============================================================
# 5. EVOLUTION MULTI-ANNEES
# ============================================================
def evolution_multi_annees(donnees_par_annee: dict, code: str, label: str):
    """Courbe d'evolution d'un indicateur sur plusieurs annees."""
    annees = sorted(donnees_par_annee.keys())
    vals = [donnees_par_annee[a].get(code, 0) for a in annees]

    if not any(vals):
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annees,
        y=vals,
        mode="lines+markers",
        name=label,
        line=dict(color=CHART["n"], width=3),
        marker=dict(size=10, color=CHART["n"]),
    ))

    fig.update_layout(
        title=dict(text=f"Evolution de {label}", font=dict(color=THEME["ink"])),
        xaxis_title="Annee",
        yaxis_title="Euros",
    )
    return base_layout(fig, 300)


# ============================================================
# 6. JAUGE CIRCULAIRE DU SCORE GLOBAL
# ============================================================
def jauge_score(score, titre="Score global"):
    """Jauge circulaire coloree pour le score global."""
    if score is None:
        return None

    color = get_score_color(score)
    label = get_score_verdict(score)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"size": 42, "color": color}},
        title={"text": f"<b>{titre}</b><br><span style='font-size:14px;color:{color}'>{label}</span>",
               "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": THEME["muted"]},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": THEME["paper"],
            "borderwidth": 2,
            "bordercolor": THEME["line"],
            "steps": [
                {"range": [0, 40],  "color": hex_rgba(THEME["bad"], 0.12)},
                {"range": [40, 70], "color": hex_rgba(THEME["warn"], 0.12)},
                {"range": [70, 100], "color": hex_rgba(THEME["ok"], 0.12)},
            ],
            "threshold": {
                "line": {"color": THEME["ink"], "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ============================================================
# 7. KPI CARD AVEC DELTA
# ============================================================
def kpi_card_delta(valeur, delta_pct=None, label="", unite="EUR", inverse=False):
    """Retourne une figure vide (placeholder pour Streamlit metric).

    On utilise en fait st.metric cote dashboard, mais on garde
    cette fonction pour l'API uniforme.
    """
    return None


# ============================================================
# 8. RADAR AVEC COULEUR SELON MOYENNE
# ============================================================
def radar_scores_colore(scores_categories: dict, titre: str = "Scores par categorie"):
    """Radar avec couleur selon la moyenne des categories."""
    cats = []
    vals = []
    for cat, sc in scores_categories.items():
        if sc is not None:
            cats.append(cat.replace("_", " ").title())
            vals.append(sc)

    if not cats:
        return None

    moyenne = sum(vals) / len(vals)
    color = get_score_color(moyenne)

    cats_closed = cats + [cats[0]]
    vals_closed = vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=cats_closed,
        fill="toself",
        name="Scores",
        line=dict(color=color, width=2),
        fillcolor=hex_rgba(color, 0.14),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=CHART["grid"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        title=dict(
            text=f"{titre} — Moyenne : {moyenne:.1f}",
            font=dict(color=THEME["ink"]),
        ),
    )
    return base_layout(fig, 420)


# ============================================================
# 9. WATERFALL AVEC LIGNE CIBLE
# ============================================================
def waterfall_contributions_v2(scores_categories: dict, poids: dict, cible=60):
    """Waterfall avec ligne de cible."""
    data = []
    for cat, sc in scores_categories.items():
        if sc is None:
            continue
        poids_cat = poids.get(cat, 0)
        contribution = sc * poids_cat
        data.append({
            "Categorie": cat.replace("_", " ").title(),
            "Score": sc,
            "Poids": poids_cat,
            "Contribution": contribution,
        })

    if not data:
        return None

    df = pd.DataFrame(data).sort_values("Contribution", ascending=True)

    # Couleur par barre selon le score
    colors_bar = [get_score_color(s) for s in df["Score"]]

    fig = go.Figure(go.Bar(
        x=df["Contribution"],
        y=df["Categorie"],
        orientation="h",
        marker_color=colors_bar,
        text=[f"{c:.1f} (score {s:.0f})" for c, s in zip(df["Contribution"], df["Score"])],
        textposition="outside",
    ))

    # Ligne de cible (60 * poids moyen)
    fig.add_vline(
        x=cible * df["Poids"].mean(),
        line_dash="dash", line_color=CHART["cible"],
        annotation_text=f"Cible ({cible})",
        annotation_position="top right",
    )

    fig.update_layout(
        title=dict(text="Contribution des categories au score",
                   font=dict(color=THEME["ink"])),
        xaxis_title="Contribution (score x poids)",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return base_layout(fig, 420)
