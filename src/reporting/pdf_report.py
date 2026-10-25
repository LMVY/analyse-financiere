"""Generation de rapport PDF : synthese financee, complete et nuancee.

Palette et bareme de scores importes de src.visualization.colors
(source unique). Le rapport presente :
- une synthese redigee (forces, faiblesses, dynamique, vigilances) ;
- les indicateurs cles N vs N-1 avec variations ;
- l'analyse par categorie et le detail des ratios scores ;
- les alertes, les controles de coherence et la methodologie.
"""
from io import BytesIO
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image as RLImage,
)

from src.visualization.colors import (
    THEME, get_score_color, get_score_label, get_score_verdict,
)

CAT_LABELS = {
    "liquidite": "Liquidite",
    "endettement": "Endettement",
    "rentabilite": "Rentabilite",
    "croissance": "Croissance",
    "gestion_activite": "Gestion de l'activite",
    "risque_solvabilite": "Risque et solvabilite",
}

INDICATEURS_CLES = [
    ("chiffre_affaires", "Chiffre d'affaires", False),
    ("valeur_ajoutee", "Valeur ajoutee", False),
    ("ebitda", "EBITDA", False),
    ("resultat_net", "Resultat net", False),
    ("capitaux_propres", "Capitaux propres", False),
    ("total_dettes", "Total dettes", True),
    ("tresorerie", "Tresorerie", False),
]


def fmt_euro(v):
    if v is None:
        return "N/A"
    return f"{v:,.0f} EUR".replace(",", " ")


def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v:.1f} %"


def _hex(h):
    return colors.HexColor(h)


def get_risk_label(score):
    """Recommandation nuancee selon le score (meme bareme que le dashboard)."""
    if score is None:
        return "Non evaluable"
    if score >= 70:
        return "Risque faible - poursuite du dossier recommandee"
    if score >= 40:
        return "Risque modere - vigilance et suivi recommandes"
    return "Risque eleve - analyse approfondie requise"


def _variation(v_n, v_n1):
    """Variation en % entre deux exercices (None si non calculable)."""
    if v_n is None or v_n1 is None or abs(v_n1) < 1e-9:
        return None
    return (v_n - v_n1) / abs(v_n1) * 100


# ============================================================
# GRAPHIQUES (matplotlib, palette centrale)
# ============================================================
def _style_mpl():
    """Theme matplotlib aligne sur src.visualization.colors."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "text.color": THEME["ink"],
        "axes.edgecolor": THEME["line"],
        "axes.labelcolor": THEME["muted"],
        "xtick.color": THEME["muted"],
        "ytick.color": THEME["muted"],
        "axes.grid": True,
        "grid.color": THEME["line"],
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _fig_vers_image(fig, width_cm):
    """Figure matplotlib -> Image reportlab de la largeur donnee."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight",
                 facecolor="white")
    plt.close(fig)
    buf.seek(0)
    from PIL import Image as PILImage
    with PILImage.open(buf) as img:
        px_w, px_h = img.size
    buf.seek(0)
    hauteur = width_cm * px_h / px_w
    return RLImage(buf, width=width_cm * cm, height=hauteur * cm)


def _chart_radar_categories(scores_categories):
    """Radar des scores par categorie (0-100)."""
    cats = [(c, v) for c, v in scores_categories.items() if v is not None]
    if not cats:
        return None
    _style_mpl()
    labels = [_label_categorie(c) for c, _ in cats]
    vals = [v for _, v in cats]
    n = len(cats)
    angles = [i / n * 2 * np.pi for i in range(n)]
    vals_c = vals + [vals[0]]
    angles_c = angles + [angles[0]]
    labels_c = labels + [labels[0]]

    fig, ax = plt.subplots(figsize=(4.2, 3.9),
                           subplot_kw=dict(polar=True))
    ax.plot(angles_c, vals_c, color=THEME["accent"], linewidth=2)
    ax.fill(angles_c, vals_c, color=THEME["accent"], alpha=0.18)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=6.5, color=THEME["muted"])
    ax.grid(color=THEME["line"], linewidth=0.6)
    ax.spines["polar"].set_color(THEME["line"])
    ax.set_title("Scores par categorie (/100)",
                 fontsize=10, color=THEME["ink"], pad=14)
    return fig


def _chart_scores_categories(scores_categories):
    """Barres horizontales des scores par categorie, colorees par niveau."""
    cats = sorted([(v, c) for c, v in scores_categories.items() if v is not None])
    if not cats:
        return None
    _style_mpl()
    labels = [_label_categorie(c) for _, c in cats]
    vals = [v for v, _ in cats]
    couleurs = [get_score_color(v) for v in vals]

    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    bars = ax.barh(labels, vals, color=couleurs, height=0.62)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 1.5, b.get_y() + b.get_height() / 2,
                f"{v:.0f}", va="center", fontsize=8.5, color=THEME["ink"])
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title("Niveau de chaque categorie", fontsize=10,
                 color=THEME["ink"], pad=10)
    ax.grid(axis="y", visible=False)
    return fig


def _chart_comparaison_n_n1(agregats_n, agregats_n1):
    """Barres groupees des agregats cles N vs N-1 (kEUR)."""
    _style_mpl()
    indicateurs = [
        ("chiffre_affaires", "Chiffre d'affaires"),
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
    ax.barh(y - h / 2, vn, height=h, color=THEME["accent"], label="Exercice N")
    ax.barh(y + h / 2, vn1, height=h, color="#94A3B8", label="Exercice N-1")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("kEUR", fontsize=8.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.set_title("Agregats cles : exercice N vs exercice N-1 (kEUR)",
                 fontsize=10.5, color=THEME["ink"], pad=10)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def _label_categorie(cat):
    return CAT_LABELS.get(cat, cat.replace("_", " ").title())


def _synthese_redigee(result, agregats, agregats_n1, alertes):
    """Paragraphes de synthese : verdict, forces, faiblesses, dynamique.

    Le texte evite les verdicts binaires : chaque affirmation est
    reliee aux categories et aux alertes qui la fondent.
    """
    score = result.get("score_global")
    cats = {k: v for k, v in result.get("scores_categories", {}).items()
            if v is not None}
    paragraphes = []

    # Verdict
    if score is None:
        paragraphes.append("Le score global n'a pas pu etre calcule : "
                          "les donnees disponibles sont insuffisantes pour "
                          "fonder une opinion solide.")
    else:
        intro = {
            "solide": ("Le profil financier global apparait solide au regard "
                       "des references retenues, sans que cela dispense d'une "
                       "lecture attentive des points de vigilance ci-dessous."),
            "surveiller": ("Le profil financier global se situe dans une zone "
                           "intermediaire : la situation ne presente pas de "
                           "signal critique isole, mais plusieurs dimensions "
                           "appellent une surveillance rapprochee."),
            "fragile": ("Le profil financier global est fragilise : plusieurs "
                        "dimensions du score se situent sous le seuil de "
                        "vigilance et doivent etre documentees avant toute "
                        "decision."),
        }.get("solide" if score >= 70 else
              "surveiller" if score >= 40 else "fragile")
        paragraphes.append(f"Score global : {score:.0f}/100. {intro}")

    # Forces et faiblesses
    if cats:
        tri = sorted(cats.items(), key=lambda x: x[1], reverse=True)
        forces = [f"{_label_categorie(c)} ({v:.0f}/100)"
                  for c, v in tri[:2] if v >= 55]
        faiblesses = [f"{_label_categorie(c)} ({v:.0f}/100)"
                      for c, v in tri[-2:] if v < 55]
        if forces:
            paragraphes.append(
                "Points d'appui : " + ", ".join(forces) +
                ". Ces dimensions soutiennent le score global et peuvent "
                "servir de base de discussion.")
        if faiblesses:
            paragraphes.append(
                "Points de vigilance : " + ", ".join(faiblesses) +
                ". Ils pesent sur le score et meritent une analyse "
                "complementaire avant conclusion definitive.")

    # Dynamique
    if agregats_n1:
        d_ca = _variation(agregats.get("chiffre_affaires"),
                          agregats_n1.get("chiffre_affaires"))
        d_rn = _variation(agregats.get("resultat_net"),
                          agregats_n1.get("resultat_net"))
        morceaux = []
        if d_ca is not None:
            morceaux.append(
                f"l'activite evolue de {d_ca:+.1f} % "
                f"(" + ("progression" if d_ca >= 0 else "recul") + ")")
        if d_rn is not None:
            morceaux.append(
                f"le resultat net varie de {d_rn:+.1f} %")
        if morceaux:
            paragraphes.append(
                "Dynamique sur un exercice : " + " et ".join(morceaux) +
                ". Une seule annee de recul ne permet pas d'identifier une "
                "tendance de fond ; l'historique doit etre consolide.")

    # Alertes
    n_crit = sum(1 for a in (alertes or []) if a.get("niveau") == "critique")
    n_warn = sum(1 for a in (alertes or []) if a.get("niveau") == "warning")
    if n_crit:
        paragraphes.append(
            f"{n_crit} alerte(s) critique(s) figurent dans le rapport : "
            "elles doivent etre levees ou expliques avant toute decision.")
    elif n_warn:
        paragraphes.append(
            f"{n_warn} point(s) d'attention (non critiques) sont listes "
            "en fin de rapport.")
    else:
        paragraphes.append(
            "Aucune alerte automatique n'a ete declenchee par les regles "
            "de controle ; cela ne garantit pas l'absence de risque.")

    # Methode
    methode = result.get("methode")
    if methode == "sectorielle":
        paragraphes.append(
            "Methode de scoring : sectorielle. Les ratios sont compares aux "
            "references du secteur (quartiles Q1 / mediane / Q3), ce qui "
            "contextualise l'analyse mais reste sensible a la qualite des "
            "references sectorielles.")
    else:
        paragraphes.append(
            "Methode de scoring : standard (seuils fixes). Aucune reference "
            "sectorielle n'a ete appliquee ; les seuils generiques peuvent "
            "sous ou sur-estimer le risque selon le secteur d'activite.")

    return paragraphes


def _table_base(col_widths, header_bg=None):
    """Style commun des tables."""
    return [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg or _hex(THEME["ink"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, _hex(THEME["line"])),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]


def _footer_factory(company_name):
    date_fr = datetime.now().strftime("%d/%m/%Y")

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(_hex(THEME["line"]))
        canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_hex(THEME["muted"]))
        canvas.drawString(2 * cm, 1.0 * cm,
                          f"Analyse financiere - {company_name} - {date_fr}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm,
                               f"Page {doc.page}")
        canvas.restoreState()

    return _footer


def generate_pdf_report(
    result: dict,
    agregats: dict,
    validation: dict = None,
    alertes: list = None,
    company_name: str = "Entreprise",
    secteur_label: str = None,
    figures: dict = None,
    agregats_n1: dict = None,
) -> bytes:
    """Genere un rapport PDF complet et nuance.

    Args:
        result: dict retourne par Scorer/SectorScorer (compute_all)
        agregats: dict Agregats.compute_all() de l'exercice N
        validation: dict Validator.validate_all()
        alertes: liste d'alertes (dicts niveau/message)
        company_name: nom de l'entreprise
        secteur_label: libelle du secteur
        figures: inutilise (compatibilite)
        agregats_n1: agregats de l'exercice precedent (variations)

    Returns:
        bytes du PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Rapport d'analyse financiere - {company_name}",
        author="Analyse financiere",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=22, textColor=_hex(THEME["ink"]),
        spaceAfter=6, alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=_hex(THEME["muted"]),
        alignment=TA_CENTER, spaceAfter=24,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, textColor=_hex(THEME["ink"]),
        spaceAfter=8, spaceBefore=16,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=15, alignment=TA_JUSTIFY,
        spaceAfter=8, textColor=_hex(THEME["ink"]),
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=8.5, leading=12, textColor=_hex(THEME["muted"]),
        spaceAfter=4,
    )

    score = result.get("score_global") or 0
    methode = result.get("methode")
    story = []

    # ============================================================
    # PAGE 1 : SYNTHESE
    # ============================================================
    story.append(Paragraph("Rapport d'analyse financiere", title_style))
    meta = f"<b>{company_name}</b>"
    if secteur_label:
        meta += f" - Secteur : {secteur_label}"
    meta += (f" - Methode : "
             f"{'sectorielle' if methode == 'sectorielle' else 'standard'}")
    story.append(Paragraph(meta, subtitle_style))

    couleur_score = _hex(get_score_color(score))

    score_data = [
        [Paragraph("<b>Score global</b>", styles["Normal"]),
         Paragraph(f"<b>{score:.0f}/100</b>",
                   ParagraphStyle("s", parent=styles["Normal"],
                                  textColor=couleur_score, fontSize=16))],
        [Paragraph("<b>Verdict</b>", styles["Normal"]),
         Paragraph(get_score_verdict(score), styles["Normal"])],
        [Paragraph("<b>Recommandation</b>", styles["Normal"]),
         Paragraph(get_risk_label(score), styles["Normal"])],
    ]
    score_table = Table(score_data, colWidths=[5 * cm, 11 * cm])
    score_style = _table_base(col_widths=None)
    score_table.setStyle(TableStyle(score_style + [
        ("BACKGROUND", (0, 0), (0, -1), _hex(THEME["bg"])),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("FONTSIZE", (1, 1), (1, -1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Synthese", h2_style))
    for p in _synthese_redigee(result, agregats, agregats_n1, alertes):
        story.append(Paragraph(p, body_style))

    # ============================================================
    # VUE D'ENSEMBLE : radar + barres des categories
    # ============================================================
    if result.get("scores_categories"):
        fig_radar = None
        fig_bars = None
        try:
            fig_radar = _chart_radar_categories(result.get("scores_categories", {}))
        except Exception:
            fig_radar = None
        try:
            fig_bars = _chart_scores_categories(result.get("scores_categories", {}))
        except Exception:
            fig_bars = None

        blocs = []
        if fig_radar:
            blocs.append(_fig_vers_image(fig_radar, 7.6))
        if fig_bars:
            blocs.append(_fig_vers_image(fig_bars, 8.2))
        if blocs:
            story.append(Paragraph("Vue d'ensemble du score", h2_style))
            if len(blocs) == 2:
                story.append(Table([blocs], colWidths=[8.4 * cm, 8.4 * cm]))
            else:
                story.append(blocs[0])
            story.append(Paragraph(
                "A gauche : profil par categorie (plus la surface est grande, "
                "plus la categorie soutient le score). A droite : niveau de "
                "chaque categorie sur 100.", small_style))

    # ============================================================
    # INDICATEURS CLES N vs N-1
    # ============================================================
    story.append(Paragraph("Indicateurs cles", h2_style))
    ind_data = [["Indicateur", "Exercice N", "Exercice N-1", "Variation"]]
    delta_styles = []
    for i, (code, label, inverse) in enumerate(INDICATEURS_CLES, start=1):
        v_n = agregats.get(code)
        v_n1 = (agregats_n1 or {}).get(code)
        d = _variation(v_n, v_n1)
        if d is None:
            d_txt = "n/d"
        else:
            d_txt = f"{d:+.1f} %"
        ind_data.append([label, fmt_euro(v_n), fmt_euro(v_n1), d_txt])
        if d is not None:
            positif = d > 0 if not inverse else d < 0
            c = _hex(THEME["ok"] if positif else THEME["bad"])
            delta_styles.append(("TEXTCOLOR", (3, i), (3, i), c))

    ind_table = Table(ind_data, colWidths=[7 * cm, 4 * cm, 4 * cm, 1.5 * cm])
    ind_table.setStyle(TableStyle(_table_base(None) + delta_styles + [
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(ind_table)

    if not agregats_n1:
        story.append(Paragraph(
            "Exercice N-1 non fourni : les variations ne sont pas calculees.",
            small_style))

    # Graphique de comparaison N vs N-1
    if agregats_n1:
        try:
            fig_cmp = _chart_comparaison_n_n1(agregats, agregats_n1)
            if fig_cmp:
                story.append(Spacer(1, 0.3 * cm))
                story.append(_fig_vers_image(fig_cmp, 15.5))
        except Exception:
            pass

    # ============================================================
    # ANALYSE PAR CATEGORIE
    # ============================================================
    cats = {k: v for k, v in result.get("scores_categories", {}).items()
            if v is not None}
    if cats:
        story.append(Paragraph("Analyse par categorie", h2_style))
        cat_data = [["Categorie", "Score", "Niveau", "Lecture"]]
        cat_colors = []
        tri = sorted(cats.items(), key=lambda x: x[1], reverse=True)
        for i, (cat, sc) in enumerate(tri, start=1):
            lecture = {
                True: "Dimension qui soutient le score global.",
            }
            if sc >= 70:
                lecture = "Niveau satisfaisant au regard des references retenues."
            elif sc >= 40:
                lecture = ("Niveau intermediaire : a surveiller selon "
                          "l'horizon d'analyse.")
            else:
                lecture = "Point de vigilance prioritaire du dossier."
            cat_data.append([
                _label_categorie(cat),
                f"{sc:.0f}/100",
                get_score_label(sc),
                Paragraph(lecture, small_style),
            ])
            cat_colors.append(("TEXTCOLOR", (1, i), (1, i),
                               _hex(get_score_color(sc))))

        cat_table = Table(cat_data, colWidths=[4.5 * cm, 2 * cm, 2.5 * cm, 7 * cm])
        cat_table.setStyle(TableStyle(_table_base(None) + cat_colors + [
            ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ]))
        story.append(cat_table)

    # ============================================================
    # DETAIL DES RATIOS SCORES
    # ============================================================
    details = result.get("details", {})
    if details:
        story.append(Paragraph("Detail des ratios scores", h2_style))
        rat_data = [["Categorie", "Ratio", "Valeur", "Score", "Poids"]]
        rat_colors = []
        lignes = sorted(
            details.items(),
            key=lambda kv: (kv[1].get("categorie", ""), -(kv[1].get("score") or 0)),
        )
        for i, (nom, det) in enumerate(lignes, start=1):
            val = det.get("valeur")
            sc = det.get("score")
            cat = det.get("categorie", "autre")
            val_txt = f"{val:,.2f}".replace(",", " ") if val is not None else "n/d"
            rat_data.append([
                _label_categorie(cat),
                nom.replace("_", " "),
                val_txt,
                f"{sc:.0f}" if sc is not None else "n/d",
                f"{det.get('poids', 0):.2f}",
            ])
            if sc is not None:
                rat_colors.append(("TEXTCOLOR", (3, i), (3, i),
                                   _hex(get_score_color(sc))))

        rat_table = Table(rat_data,
                          colWidths=[4.5 * cm, 5.5 * cm, 3 * cm, 1.5 * cm, 1.5 * cm])
        rat_table.setStyle(TableStyle(_table_base(None) + rat_colors + [
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(rat_table)
        story.append(Paragraph(
            "Les valeurs sont exprimees dans leur unite de calcul "
            "(pourcentage, jours ou coefficient selon le ratio).",
            small_style))

    # ============================================================
    # ALERTES
    # ============================================================
    if alertes:
        story.append(Paragraph("Alertes et points d'attention", h2_style))
        al_data = [["Niveau", "Message"]]
        for a in alertes:
            niveau = a.get("niveau", "info")
            msg = a.get("message", "")
            couleur = {
                "critique": THEME["bad"],
                "warning": THEME["warn"],
                "info": THEME["accent"],
            }.get(niveau, THEME["muted"])
            al_data.append([
                Paragraph(f"<b>{niveau.upper()}</b>",
                          ParagraphStyle("al", parent=small_style,
                                         textColor=_hex(couleur))),
                Paragraph(msg, small_style),
            ])
        al_table = Table(al_data, colWidths=[2.5 * cm, 13.5 * cm])
        al_table.setStyle(TableStyle(_table_base(None) + [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(al_table)

    # ============================================================
    # CONTROLES DE COHERENCE
    # ============================================================
    if validation:
        story.append(Paragraph("Controles de coherence des donnees", h2_style))
        stats = validation.get("stats", {})
        val_data = [
            ["Controles reussis", f"{stats.get('succes', 0)}/{stats.get('total', 0)}"],
            ["Avertissements", str(stats.get('avertissements', 0))],
            ["Erreurs", str(stats.get('erreurs', 0))],
        ]
        val_table = Table(val_data, colWidths=[8 * cm, 8 * cm])
        val_table.setStyle(TableStyle(_table_base(None) + [
            ("BACKGROUND", (0, 0), (0, -1), _hex(THEME["bg"])),
        ]))
        story.append(val_table)

        rapport = validation.get("rapport", [])
        if rapport:
            story.append(Spacer(1, 0.3 * cm))
            for item in rapport:
                story.append(Paragraph(
                    f"- <b>{item['test']}</b> : {item['message']}",
                    small_style))

    # ============================================================
    # METHODOLOGIE ET MENTIONS
    # ============================================================
    story.append(Paragraph("Methode et limites", h2_style))
    mentions = [
        "Ce rapport est genere automatiquement a partir des documents "
        "comptables fournis (extraction par Mistral Document AI, normalisation "
        "PCG). Les montants restent ceux figurant dans les documents.",
        "Le score global resulte d'une moyenne ponderee de ratios par "
        "categorie. Les seuils ou references sectorielles sont indicatifs "
        "(sources publiques : INSEE, Banque de France) et doivent etre "
        "ajustees au contexte du dossier.",
        "Ce document constitue une aide a l'analyse : il ne remplace ni "
        "l'expertise d'un analyste, ni un audit comptable, ni un avis "
        "financier ou juridique.",
        f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}.",
    ]
    for m in mentions:
        story.append(Paragraph(m, small_style))

    doc.build(story, onFirstPage=_footer_factory(company_name),
              onLaterPages=_footer_factory(company_name))
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
