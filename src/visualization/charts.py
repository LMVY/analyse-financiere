"""Graphiques Plotly pour le dashboard.

Toutes les couleurs viennent de src.visualization.colors (source unique).
"""
import plotly.graph_objects as go
import pandas as pd

from src.visualization.colors import THEME, CHART, hex_rgba


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
# BENCHMARK SECTORIEL : entreprise vs mediane du secteur
# ============================================================
def benchmark_sectoriel(ratios: dict, secteur: str, secteurs_config: dict):
    """Bar chart entreprise vs mediane du secteur (100 = mediane)."""
    if not secteur or secteur not in secteurs_config:
        return None

    ref_secteur = secteurs_config[secteur].get("ratios", {})

    data = []
    for cat, ratio_dict in ratios.items():
        for nom, val in ratio_dict.items():
            if val is None or nom not in ref_secteur:
                continue
            mediane = ref_secteur[nom].get("mediane", 0)
            idx = (val / mediane) * 100 if mediane != 0 else 0
            data.append({"Ratio": nom, "Indice": idx})

    if not data:
        return None

    df = pd.DataFrame(data).head(15)

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
# EVOLUTION MULTI-ANNEES
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
        title=dict(text=f"Evolution de {label} par exercice (EUR)",
                   font=dict(color=THEME["ink"])),
        xaxis_title="Exercice",
        yaxis_title="Euros",
    )
    return base_layout(fig, 300)


# ============================================================
# COMPARAISON N vs N-1
# ============================================================
def comparaison_n_n1(agregats_n: dict, agregats_n1: dict):
    """Barres groupees : agregats cles de l'exercice N vs N-1 (en kEUR)."""
    indicateurs = [
        ("chiffre_affaires", "Chiffre d'affaires"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
    ]

    labels, vals_n, vals_n1 = [], [], []
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
        name="Exercice N",
        x=labels,
        y=vals_n,
        marker_color=CHART["n"],
        text=[f"{v/1000:,.0f} k".replace(",", " ") for v in vals_n],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Exercice N-1",
        x=labels,
        y=vals_n1,
        marker_color=CHART["n1"],
        text=[f"{v/1000:,.0f} k".replace(",", " ") for v in vals_n1],
        textposition="outside",
    ))

    fig.update_layout(
        title=dict(text="Agregats cles : exercice N vs N-1 (kEUR)",
                   font=dict(color=THEME["ink"])),
        barmode="group",
        yaxis_title="Euros",
        legend=dict(orientation="h", y=1.1),
    )
    return base_layout(fig, 420)
