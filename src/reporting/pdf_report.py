"""Generation de rapport PDF avec scores et graphiques."""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors

    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)

def fmt_euro(v):
    """Formate un nombre en euros."""
    if v is None:
        return "N/A"
    return f"{v:,.0f} EUR".replace(",", " ")

def fmt_pct(v):
    """Formate un pourcentage."""
    if v is None:
        return "N/A"
    return f"{v:.1f}%"

def get_risk_color(score):
    """Couleur selon le score."""
    if score >= 75:
        return colors.HexColor("#27ae60")  # Vert
    elif score >= 60:
        return colors.HexColor("#2980b9")  # Bleu
    elif score >= 45:
        return colors.HexColor("#f39c12")  # Orange
    elif score >= 30:
        return colors.HexColor("#e67e22")  # Orange fonce
    else:
        return colors.HexColor("#e74c3c")  # Rouge

def get_risk_label(score):
    """Label selon le score."""
    if score >= 75:
        return "Risque faible - Acceptation recommandee"
    elif score >= 60:
        return "Risque modere - Acceptation avec garanties"
    elif score >= 45:
        return "Risque eleve - Analyse approfondie requise"
    elif score >= 30:
        return "Risque tres eleve - Acceptation deconseillee"
    else:
        return "Risque critique - Refus"

def generate_pdf_report(
    result: dict,
    agregats: dict,
    validation: dict = None,
    alertes: list = None,
    company_name: str = "Entreprise",
    secteur_label: str = None,
    figures: dict = None,
) -> bytes:
    """Genere un rapport PDF complet.

    Args:
        result: dict retourne par Scorer.compute_all()
        agregats: dict retourne par Agregats.compute_all()
        validation: dict retourne par Validator.validate_all()
        alertes: liste d'alertes (dicts)
        company_name: nom de l'entreprise
        secteur_label: nom du secteur
        figures: dict de figures Plotly (radar, waterfall) a convertir en images

    Returns:
        bytes du PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=22, textColor=colors.HexColor("#2c3e50"),
        spaceAfter=20, alignment=TA_CENTER,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=colors.HexColor("#2c3e50"),
        spaceAfter=10, spaceBefore=15,
    )
    normal = styles["Normal"]

    story = []

    # ============================================================
    # PAGE 1 : SYNTHESE
    # ============================================================
    story.append(Paragraph("Rapport d'analyse financiere", title_style))
    story.append(Paragraph(f"<b>{company_name}</b>", styles["Heading2"]))
    if secteur_label:
        story.append(Paragraph(f"Secteur : {secteur_label}", normal))
    story.append(Paragraph(
        f"Date : {datetime.now().strftime('%d/%m/%Y')}",
        normal
    ))
    story.append(Spacer(1, 0.5*cm))

    # Score global
    score = result.get("score_global", 0)
    color = get_risk_color(score)
    label = get_risk_label(score)

    score_data = [
        ["Score global", f"{score}/100"],
        ["Recommandation", label],
    ]
    score_table = Table(score_data, colWidths=[5*cm, 11*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("TEXTCOLOR", (1, 0), (1, 0), color),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5*cm))

    # Agregats cles
    story.append(Paragraph("Agregats cles", h2_style))
    agr_data = [["Indicateur", "Valeur"]]
    for code, label_a in [
        ("chiffre_affaires", "Chiffre d'affaires"),
        ("valeur_ajoutee", "Valeur ajoutee"),
        ("ebitda", "EBITDA"),
        ("resultat_net", "Resultat net"),
        ("capitaux_propres", "Capitaux propres"),
        ("total_dettes", "Total dettes"),
        ("tresorerie", "Tresorerie"),
    ]:
        v = agregats.get(code, 0)
        agr_data.append([label_a, fmt_euro(v)])

    agr_table = Table(agr_data, colWidths=[8*cm, 8*cm])
    agr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(agr_table)
    story.append(PageBreak())

    # ============================================================
    # PAGE 2 : SCORES PAR CATEGORIE
    # ============================================================
    story.append(Paragraph("Scores par categorie", h2_style))
    story.append(Spacer(1, 0.3*cm))

    cat_data = [["Categorie", "Score", "Niveau"]]
    for cat, sc in result.get("scores_categories", {}).items():
        if sc is None:
            continue
        cat_label = cat.replace("_", " ").title()
        if sc >= 75:
            niveau = "Excellent"
        elif sc >= 60:
            niveau = "Bon"
        elif sc >= 45:
            niveau = "Moyen"
        elif sc >= 30:
            niveau = "Faible"
        else:
            niveau = "Critique"
        cat_data.append([cat_label, f"{sc:.1f}/100", niveau])

    cat_table = Table(cat_data, colWidths=[7*cm, 4*cm, 5*cm])
    cat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cat_table)

    # Alertes
    if alertes:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Alertes detectees", h2_style))
        for alerte in alertes:
            niveau = alerte.get("niveau", "info")
            msg = alerte.get("message", "")
            couleur = {
                "critique": "#e74c3c",
                "warning": "#f39c12",
                "info": "#3498db",
            }.get(niveau, "#95a5a6")
            story.append(Paragraph(
                f'<font color="{couleur}">[{niveau.upper()}]</font> {msg}',
                normal
            ))

    # Validation
    if validation:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Validation des donnees", h2_style))
        stats = validation.get("stats", {})
        val_data = [
            ["Tests reussis", f"{stats.get('succes', 0)}/{stats.get('total', 0)}"],
            ["Avertissements", str(stats.get("avertissements", 0))],
            ["Erreurs", str(stats.get("erreurs", 0))],
        ]
        val_table = Table(val_data, colWidths=[8*cm, 8*cm])
        val_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(val_table)

    # Build
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

if __name__ == "__main__":
    print("Module pdf_report.py OK")
