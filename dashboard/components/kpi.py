"""Composants KPI reutilisables (cards custom stylisees)."""
import streamlit as st

def kpi_card(label, valeur, delta_pct=None, unite="EUR", icone="💰", inverse=False, couleur=None):
    """Card KPI stylisee avec ombre, bordure coloree, icone.

    Args:
        label: titre du KPI
        valeur: valeur numerique
        delta_pct: variation en % (optionnel)
        unite: "EUR" ou "%" ou ""
        icone: emoji
        inverse: si True, une baisse est bonne
        couleur: couleur de la bordure (auto si None)
    """
    # Format valeur
    if unite == "EUR":
        texte = f"{valeur:,.0f} €".replace(",", " ")
    elif unite == "%":
        texte = f"{valeur:.2f} %"
    else:
        texte = f"{valeur:,.2f}"

    # Couleur de la bordure
    if couleur is None:
        if delta_pct is None:
            couleur = "#3498db"
        else:
            positif = delta_pct > 0
            if inverse:
                positif = not positif
            couleur = "#27ae60" if positif else "#e74c3c"

    # Delta
    delta_html = ""
    if delta_pct is not None:
        signe = "+" if delta_pct > 0 else ""
        classe = "kpi-delta-pos" if delta_pct > 0 else "kpi-delta-neg"
        if inverse:
            classe = "kpi-delta-neg" if delta_pct > 0 else "kpi-delta-pos"
        fleche = "↗" if delta_pct > 0 else "↘"
        delta_html = f'<div class="kpi-delta {classe}">{fleche} {signe}{delta_pct:.1f}%</div>'

    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: {couleur};">
        <div class="kpi-label">{icone} {label}</div>
        <div class="kpi-value">{texte}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def score_card(score, titre="Score global", methode="standard"):
    """Affiche le score dans une card centree."""
    color = get_score_color(score)
    emoji = get_score_emoji(score)
    label = get_score_label(score)

    label_methode = "🏭 Sectoriel" if methode == "sectorielle" else "📐 Standard"

    st.markdown(f"""
    <div style="background: white; padding: 2rem; border-radius: 16px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08); text-align: center;">
        <div style="color: #7f8c8d; font-size: 0.85rem; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 1px;">
            {titre}
        </div>
        <div style="font-size: 4rem; font-weight: 800; color: {color};
                    line-height: 1; margin: 1rem 0;">
            {score:.0f}
        </div>
        <div style="font-size: 1rem; font-weight: 600; color: {color}; margin-bottom: 0.5rem;">
            {emoji} {label}
        </div>
        <div style="font-size: 0.75rem; color: #7f8c8d;">
            {label_methode}
        </div>
    </div>
    """, unsafe_allow_html=True)

def score_bar(categorie, score):
    """Barre de score coloree inline."""
    color = get_score_color(score)
    emoji = get_score_emoji(score)
    label = categorie.replace("_", " ").title()

    st.markdown(f"""
    <div style="margin-bottom: 0.75rem;">
        <div style="display: flex; justify-content: space-between;
                    margin-bottom: 0.25rem; font-size: 0.85rem;">
            <span style="color: #2c3e50; font-weight: 500;">{emoji} {label}</span>
            <span style="color: {color}; font-weight: 700;">{score:.0f}/100</span>
        </div>
        <div class="score-bar-container">
            <div class="score-bar-fill" style="width: {score}%; background: {color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def alerte_banner(niveau, message):
    """Bandeau d'alerte stylise."""
    classes = {
        "critique": "alerte-critique",
        "warning": "alerte-warning",
        "info": "alerte-info",
        "succes": "alerte-succes",
    }
    icones = {"critique": "🚨", "warning": "⚠️", "info": "ℹ️", "succes": "✅"}
    classe = classes.get(niveau, "alerte-info")
    icone = icones.get(niveau, "ℹ️")

    st.markdown(
        f'<div class="alerte-box {classe}">{icone} {message}</div>',
        unsafe_allow_html=True,
    )

def section_header(titre, icone="📊", sous_titre=None):
    """En-tete de section."""
    st.markdown(f"### {icone} {titre}")
    if sous_titre:
        st.caption(sous_titre)
