"""Generation du rapport PDF : assemblage et mise en page.

RAPPORT PROFESSIONNEL D'ANALYSE CREDIT - refonte complete.

Langage visuel :
- bandeau d'identite pleine largeur en tete de chaque page (accent
  sur les pages internes, bandeau epais sur la couverture) ;
- sections en bandes teintees : numero accent + titre capitales +
  barre accent a gauche ;
- le contenu vit dans des BOITES : chaque bloc a un en-tete de boite
  (libelle capitales sur fond teinte) et un corps borde ;
- les chiffres majeurs forment une BANDE sous l'avis : valeur en
  grand, libelle au-dessus, note au-dessous, filets encre ;
- tableaux : en-tete discret, filet encre sous l'en-tete, hairlines,
  chiffres alignes a droite, aucun trait vertical ;
- statuts en badges (pastilles teintes) : couleurs reservees au sens.

Structure du fond (avis -> faits -> dimensions -> references) :
  1. Avis et points cles      : avis chiffre, bande de chiffres,
                                forces / vigilances en regard,
                                dynamique et lecture croisee ;
  2. Perimetre et fiabilite   : identification, controles, conditions
                                de lecture ;
  3. Profil de risque         : radar, niveaux par categorie ;
  4. Construction du score    : contributions ratio par ratio ;
  5. Indicateurs cles         : N vs N-1 ;
  6. Analyse par dimension    : une sous-section par categorie, sa
                                lecture et ses ratios ;
  7. Synthese des ratios      : tableau de reference complet ;
  8. Controles de coherence   : audit comptable detaille ;
  Annexes A / B               : glossaire, methode et limites.
"""
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

from src.reporting.glossaire import (
    CAT_LABELS, GLOSSAIRE, label_categorie, label_ratio,
)
from src.reporting.synthese import (
    avis_global, points_cles, faits_structures, resume_categorie,
    texte_dynamique, lecture_croisee, conditions_lecture,
    variation, fmt_euro,
)
from src.reporting.charts_pdf import (
    chart_radar_categories, chart_scores_categories,
    chart_comparaison_n_n1, chart_contributions_categories,
    fig_vers_image,
)
from src.visualization.colors import (
    THEME, get_score_gradient, get_score_verdict,
)

INDICATEURS_CLES = [
    ("chiffre_affaires", "Chiffre d'affaires", False),
    ("valeur_ajoutee", "Valeur ajoutee", False),
    ("ebitda", "EBITDA", False),
    ("resultat_net", "Resultat net", False),
    ("capitaux_propres", "Capitaux propres", False),
    ("total_dettes", "Total dettes", True),
    ("tresorerie", "Tresorerie", False),
]

LARGEUR_UTILE = 17 * cm  # A4 (21 cm) - marges (2 x 2 cm)

# ============================================================
# TYPOGRAPHIE : DejaVu Sans embarquee (livree avec matplotlib),
# repli Helvetica si indisponible
# ============================================================
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _charger_polices():
    global FONT, FONT_BOLD
    try:
        import os
        import matplotlib
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        ttf = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(ttf, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(ttf, "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily(
            "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
            italic="DejaVu", boldItalic="DejaVu-Bold")
        FONT, FONT_BOLD = "DejaVu", "DejaVu-Bold"
    except Exception:
        FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"


_charger_polices()


# ============================================================
# OUTILS DE MISE EN PAGE
# ============================================================
def _hex(h):
    return colors.HexColor(h)


def _tint(hex_color, fraction=0.10):
    """Couleur eclaircie : fraction de la couleur mixee au blanc."""
    c = colors.HexColor(hex_color)
    return colors.Color(
        1.0 + (c.red - 1.0) * fraction,
        1.0 + (c.green - 1.0) * fraction,
        1.0 + (c.blue - 1.0) * fraction,
    )


def get_risk_label(score):
    """Recommandation nuancee selon le score (meme bareme que le dashboard)."""
    if score is None:
        return "Non evaluable"
    if score >= 70:
        return "Risque faible - poursuite du dossier recommandee"
    if score >= 40:
        return "Risque modere - vigilance et suivi recommandes"
    return "Risque eleve - analyse approfondie requise"


def _table_base(col_widths=None, header_bg=None):
    """Style commun des tables : en-tete discret a libelles
    capitales, filet fort encre SOUS l'en-tete, hairlines entre les
    lignes - pas de grille verticale."""
    return [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg or colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), _hex(THEME["muted"])),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 6.8),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, _hex(THEME["ink"])),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, _hex("#F1F5F9")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]


def _section_titre(texte, style):
    """Bandeau de section : barre accent a gauche, numero accent,
    titre en capitales, fond legerement teinte."""
    m = texte.split(".", 1)
    num = ""
    if len(m) == 2 and len(m[0].strip()) <= 2 and m[0].strip().isalnum():
        num, texte = m[0].strip(), m[1].strip()
    para = Paragraph(
        (f"<font color='{THEME['accent']}'><b>{num}.</b></font> "
         if num else "")
        + f"<b>{texte.upper()}</b>", style)
    return Table(
        [[para]],
        colWidths=[LARGEUR_UTILE],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _hex(THEME["bg"])),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, _hex(THEME["accent"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )


def _boite(titre, contenu, couleur=None, largeur=LARGEUR_UTILE):
    """Boite structuree : en-tete capitales sur fond teinte, corps
    borde. contenu : flowable ou liste de flowables."""
    couleur = couleur or THEME["ink"]
    if not isinstance(contenu, (list, tuple)):
        contenu = [contenu]
    head = Paragraph(
        f"<font color='{couleur}' size='7'><b>{titre.upper()}</b></font>",
        ParagraphStyle("boite-titre", leading=10, fontName=FONT_BOLD))
    t = Table([[head], [list(contenu)]], colWidths=[largeur])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _tint(couleur, 0.07)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, _hex(THEME["line"])),
        ("BOX", (0, 0), (-1, -1), 0.75, _hex(THEME["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    return t


def _boites_cote_a_cote(titre_g, contenu_g, col_g,
                        titre_d, contenu_d, col_d):
    """Deux boites de meme largeur sur une ligne, separees d'un espace."""
    gap = 0.6 * cm
    w = (LARGEUR_UTILE - gap) / 2
    b_g = _boite(titre_g, contenu_g, col_g, largeur=w)
    b_d = _boite(titre_d, contenu_d, col_d, largeur=w)
    t = Table([[b_g, "", b_d]], colWidths=[w, gap, w])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _puces(items, style):
    """Liste a puces compacte : une puce par fait, phrases courtes."""
    return [Paragraph(f"&bull;&nbsp;&nbsp;{t}", style) for t in items]


def _badge(libelle, couleur_hex, largeur=2.4 * cm):
    """Badge de statut : pastille teintee, texte colore en gras."""
    cell = Paragraph(
        f"<font color='{couleur_hex}' size='7'><b>{libelle.upper()}</b></font>",
        ParagraphStyle("badge", leading=10, alignment=TA_CENTER,
                       fontName=FONT_BOLD),
    )
    return Table([[cell]], colWidths=[largeur],
                 style=TableStyle([
                     ("BACKGROUND", (0, 0), (-1, -1), _tint(couleur_hex, 0.12)),
                     ("BOX", (0, 0), (-1, -1), 0.4, _tint(couleur_hex, 0.35)),
                     ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                     ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                     ("LEFTPADDING", (0, 0), (-1, -1), 2),
                     ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                 ]))


def _bande_chiffres(faits):
    """Bande des chiffres majeurs : filet encre en tete, valeurs en
    grand colorees, notes discretes, hairlines de separation."""
    faits = faits[:5]
    n = len(faits)
    if not n:
        return None
    lab_style = ParagraphStyle(
        "chiffre-l", fontName=FONT_BOLD, fontSize=6.3, leading=8.5,
        textColor=_hex(THEME["muted"]))
    val_style = ParagraphStyle(
        "chiffre-v", fontName=FONT_BOLD, fontSize=13.5, leading=17,
        spaceBefore=2, spaceAfter=1)
    note_style = ParagraphStyle(
        "chiffre-n", fontName=FONT, fontSize=7, leading=9.5,
        textColor=_hex(THEME["muted"]))

    ligne_label, ligne_val, ligne_note = [], [], []
    for f in faits:
        ligne_label.append(Paragraph(f["label"].upper(), lab_style))
        ligne_val.append(Paragraph(
            f"<font color='{f['couleur']}'>{f['valeur']}</font>", val_style))
        ligne_note.append(Paragraph(f.get("note", "") or " ", note_style))

    w = LARGEUR_UTILE / n
    t = Table([ligne_label, ligne_val, ligne_note],
              colWidths=[w] * n)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, _hex(THEME["ink"])),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, _hex(THEME["line"])),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, _hex(THEME["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 2), (-1, 2), 1),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _fiche_identite(entrees):
    """Grille d'identification : libelle muet + valeur encre,
    cellules separees par des hairlines."""
    lab_style = ParagraphStyle(
        "fiche-l", fontName=FONT_BOLD, fontSize=6.3, leading=8.5,
        textColor=_hex(THEME["muted"]))
    val_style = ParagraphStyle(
        "fiche-v", fontName=FONT_BOLD, fontSize=9.2, leading=12,
        textColor=_hex(THEME["ink"]))
    ranges = []
    for i in range(0, len(entrees), 3):
        trio = list(entrees[i:i + 3])
        while len(trio) < 3:
            trio.append(("", ""))
        ranges.append([[Paragraph(k.upper(), lab_style),
                        Paragraph(v, val_style)] for k, v in trio])
    n = len(ranges[0])
    t = Table(ranges, colWidths=[LARGEUR_UTILE / n] * n,
              hAlign="LEFT")
    style = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _hex(THEME["line"])),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, _hex(THEME["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t


def _sommaire(items, style):
    """Sommaire : sections numerotees puis annexes, une par ligne."""
    if not items:
        return None
    rows = [Paragraph(
        f"<font color='{THEME['accent']}'><b>{n}.</b></font>  "
        f"<b>{nom}</b>", style) for n, nom in items]
    table = Table([[r] for r in rows], colWidths=[LARGEUR_UTILE])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _footer_factory(company_name, entete=True):
    date_fr = datetime.now().strftime("%d/%m/%Y")
    nom = (company_name if len(company_name) <= 48
           else company_name[:45].rstrip() + "...")

    def _footer(canvas, doc):
        canvas.saveState()
        # bandeau d'identite : filet accent en tete de page interne
        if entete:
            canvas.setFillColor(_hex(THEME["accent"]))
            canvas.rect(0, A4[1] - 0.22 * cm, A4[0], 0.22 * cm,
                        stroke=0, fill=1)
            canvas.setFont(FONT_BOLD, 7.5)
            canvas.setFillColor(_hex(THEME["ink"]))
            canvas.drawString(2 * cm, A4[1] - 1.25 * cm,
                              nom.upper())
            canvas.setFont(FONT, 7.5)
            canvas.setFillColor(_hex(THEME["muted"]))
            canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.25 * cm,
                                   "Rapport d'analyse financiere")
            canvas.setStrokeColor(_hex(THEME["line"]))
            canvas.setLineWidth(0.6)
            canvas.line(2 * cm, A4[1] - 1.45 * cm,
                        A4[0] - 2 * cm, A4[1] - 1.45 * cm)
        # Pied de page : filet, signature FINVIEW accent, entreprise
        canvas.setStrokeColor(_hex(THEME["line"]))
        canvas.setLineWidth(0.6)
        canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
        canvas.setFont(FONT_BOLD, 7.5)
        canvas.setFillColor(_hex(THEME["accent"]))
        canvas.drawString(2 * cm, 1.07 * cm, "FINVIEW")
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(_hex(THEME["muted"]))
        canvas.drawString(2 * cm + 46, 1.07 * cm,
                          f"{nom} - {date_fr}")
        canvas.restoreState()

    return _footer


def _decor_couverture(canvas, doc):
    """Bandeau pleine largeur de la couverture : accent epais, FINVIEW
    et intitule en blanc. Trace sur le canvas (pleine page)."""
    canvas.saveState()
    bande_h = 3.2 * cm
    canvas.setFillColor(_hex(THEME["accent"]))
    canvas.rect(0, A4[1] - bande_h, A4[0], bande_h, stroke=0, fill=1)
    # filet fin sous le bandeau, encre
    canvas.setFillColor(_hex(THEME["ink"]))
    canvas.rect(0, A4[1] - bande_h - 0.08 * cm, A4[0], 0.08 * cm,
                stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 13)
    canvas.drawString(2 * cm, A4[1] - 1.35 * cm, "FINVIEW")
    canvas.setFont(FONT, 9.5)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.28 * cm,
                           "RAPPORT D'ANALYSE FINANCIERE")
    canvas.setFont(FONT, 8)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.85 * cm,
                           "Analyse de sante financiere et de risque de credit")
    # pied de couverture : mention confidentielle + date
    canvas.setStrokeColor(_hex(THEME["line"]))
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.setFont(FONT, 7)
    canvas.setFillColor(_hex(THEME["muted"]))
    canvas.drawString(2 * cm, 1.07 * cm,
                      "Document confidentiel - reserve a l'analyse interne. "
                      "Ne constitue ni un audit, ni un avis financier.")
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(_hex(THEME["accent"]))
    canvas.drawRightString(A4[0] - 2 * cm, 1.07 * cm,
                           datetime.now().strftime("%d/%m/%Y"))
    canvas.restoreState()


class _CanvasNumerote(pdfcanvas.Canvas):
    """Canvas a deux passes : pagination "Page X / N" en pied de page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages_sauvees = []

    def showPage(self):
        self._pages_sauvees.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages_sauvees)
        for etat in self._pages_sauvees:
            self.__dict__.update(etat)
            self.setFont(FONT_BOLD, 7.5)
            self.setFillColor(_hex(THEME["ink"]))
            # la couverture n'est pas paginee
            if self._pageNumber > 1:
                self.drawRightString(A4[0] - 2 * cm, 1.07 * cm,
                                     f"Page {self._pageNumber} / {total}")
            super().showPage()
        super().save()


# ============================================================
# DOCUMENT
# ============================================================
def generate_pdf_report(
    result: dict,
    agregats: dict,
    validation: dict = None,
    alertes: list = None,
    company_name: str = "Entreprise",
    secteur_label: str = None,
    agregats_n1: dict = None,
    poids_categories: dict = None,
    historique: dict = None,
    medianes_secteur: dict = None,
    config_ratios: dict = None,
    agregats_exercices: dict = None,
) -> bytes:
    """Genere le rapport PDF professionnel d'analyse credit.

    Args:
        result: dict retourne par Scorer/SectorScorer (compute_all)
        agregats: dict Agregats.compute_all() de l'exercice N
        validation: dict Validator.validate_all()
        alertes: liste d'alertes (dicts niveau/message)
        company_name: nom de l'entreprise
        secteur_label: libelle du secteur
        agregats_n1: agregats de l'exercice precedent (variations)
        poids_categories: poids des categories du profil d'analyse
        historique: sortie de calculer_historique() - moyenne de chaque
            ratio sur tous les exercices fournis
        medianes_secteur: {nom_ratio: mediane du secteur}
        config_ratios: {nom_ratio: {"categorie":..., "poids":...}} -
            l'integralite des ratios configures ; le tableau de
            reference affiche tous les ratios actifs (n/d si non
            notes), aligne sur le dashboard.
        agregats_exercices: {annee: agregats} de tous les exercices
            fournis - sert de base de comparaison en mode "moyenne"
            (indicateurs cles et bande de chiffres).

    Returns:
        bytes du PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title=f"Rapport d'analyse financiere - {company_name}",
        author="FinView",
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontName=FONT_BOLD, fontSize=10.5, leading=14,
        textColor=_hex(THEME["ink"]),
        spaceAfter=0, spaceBefore=0,
    )
    body_style = ParagraphStyle(
        "Body", parent=normal, fontName=FONT,
        fontSize=9.2, leading=13.8, alignment=TA_JUSTIFY,
        spaceAfter=6, textColor=_hex(THEME["ink"]),
    )
    puce_style = ParagraphStyle(
        "Puce", parent=normal, fontName=FONT,
        fontSize=8.6, leading=12.5, leftIndent=10, firstLineIndent=-10,
        spaceAfter=3.5, textColor=_hex(THEME["ink"]),
    )
    small_style = ParagraphStyle(
        "Small", parent=normal, fontName=FONT,
        fontSize=8.2, leading=11.5, textColor=_hex(THEME["muted"]),
        spaceAfter=4,
    )
    caption_style = ParagraphStyle(
        "Caption", parent=normal, fontName=FONT, fontSize=8,
        leading=10.5, textColor=_hex(THEME["muted"]),
        alignment=TA_CENTER, spaceBefore=2, spaceAfter=6,
    )
    _num_graphique = [0]

    def _legende(titre):
        """Legende numerotee sous un graphique."""
        _num_graphique[0] += 1
        return Paragraph(
            f"<i>Graphique {_num_graphique[0]} - {titre}</i>",
            caption_style)

    score = result.get("score_global") or 0
    methode = result.get("methode")
    details = result.get("details") or {}
    couleur_score_hex = get_score_gradient(score)
    date_fr = datetime.now().strftime("%d/%m/%Y")
    n_ratios_eval = len([d for d in details.values()
                         if d.get("score") is not None])
    cats_scores = {k: v for k, v in
                   (result.get("scores_categories") or {}).items()
                   if v is not None}
    has_scores_cfg = bool(result.get("scores_categories"))
    has_cats = bool(cats_scores)
    has_details = bool(details)
    has_glossaire = has_details and any(nom in GLOSSAIRE for nom in details)
    medianes = medianes_secteur or {}
    # base du score (Options du dashboard) : exercice N ajuste par la
    # trajectoire (defaut) ou moyenne des exercices
    _base = result.get("base_scoring")
    base_label = ("Moyenne des exercices" if _base == "moyenne"
                  else "Derniere annee + tendance" if _base == "tendance"
                  else "Derniere annee")
    valeur_col = "Valeur (moy.)" if _base == "moyenne" else "Valeur N"
    # moyennes des agregats sur les exercices fournis (base de
    # comparison en mode moyenne ; N inclus, meme regle que la
    # colonne "Moyenne" des ratios)
    _moyennes_agregats = {}
    for _a in (agregats_exercices or {}).values():
        if not isinstance(_a, dict):
            continue
        for _code, _l, _i in INDICATEURS_CLES:
            _v = _a.get(_code)
            if _v is not None:
                _moyennes_agregats.setdefault(_code, []).append(_v)
    _moyennes_agregats = {c: sum(v) / len(v)
                          for c, v in _moyennes_agregats.items()}
    story = []

    # -------- sections actives : sommaire et numerotation --------
    _sections_actives = [
        ("1. Avis et points cles", True),
        ("2. Perimetre et fiabilite des donnees", True),
        ("3. Profil de risque", has_scores_cfg),
        ("4. Construction du score", has_scores_cfg),
        ("5. Indicateurs cles", True),
        ("6. Analyse par dimension", has_cats),
        ("7. Synthese des ratios scores", has_details),
        ("8. Controles de coherence des donnees", bool(validation)),
        ("A. Annexe - Glossaire des ratios", has_glossaire),
        ("B. Annexe - Methode et limites", True),
    ]
    _items_sommaire = [
        (s.split(".", 1)[0], s.split(".", 1)[1].strip())
        for s, actif in _sections_actives if actif
    ]
    _sections_demandees = {s for s, actif in _sections_actives if actif}
    _compteur_section = [0]

    def section(texte, premier=None, page_break=False):
        """Titre de section numerote, colle a son premier element."""
        actif = texte in _sections_demandees or texte.startswith("A.") \
            or texte.startswith("B.")
        if not actif:
            return
        _compteur_section[0] += 1
        num, titre = texte.split(".", 1)
        titre = _section_titre(f"{num.strip()}.{titre.strip()}", h2_style)
        bloc = [Spacer(1, 0.5 * cm)]
        if premier is not None:
            bloc.append(KeepTogether([titre, Spacer(1, 0.22 * cm),
                                      premier]))
        else:
            bloc += [titre, Spacer(1, 0.22 * cm)]
        if page_break:
            story.append(PageBreak())
        story.extend(bloc)

    # ============================================================
    # COUVERTURE
    # ============================================================
    # panneau avis : score + verdict + recommandation, fond teinte
    panneau = Table([[
        Paragraph(
            f"<font color='{couleur_score_hex}' size='40'><b>"
            f"{score:.0f}</b></font>"
            f"<font color='{couleur_score_hex}' size='16'><b>"
            f" /100</b></font><br/><br/>"
            f"<font color='{THEME['muted']}' size='7'><b>"
            f"SCORE GLOBAL</b></font>",
            ParagraphStyle("avis-score", leading=46,
                           fontName=FONT_BOLD)),
        [Paragraph(
            f"<font color='{couleur_score_hex}' size='14'><b>"
            f"{get_score_verdict(score)}</b></font>",
            ParagraphStyle("avis-verdict", leading=18,
                           fontName=FONT_BOLD)),
         Paragraph(
             f"<font color='{THEME['ink']}' size='9.8'>"
             f"{get_risk_label(score)}</font>",
             ParagraphStyle("avis-reco", leading=14,
                            fontName=FONT)),
         Paragraph(
             f"<font color='{THEME['muted']}' size='7.6'>"
             f"Methode "
             f"{'sectorielle' if methode == 'sectorielle' else 'standard'}"
             f" - base : {base_label.lower()}"
             f" - barreme identique au dashboard (confort au-dela de 70, "
             f"vigilance de 40 a 70)</font>",
             ParagraphStyle("avis-meta", leading=10.5, fontName=FONT,
                            spaceBefore=4))],
    ]], colWidths=[5.4 * cm, LARGEUR_UTILE - 5.4 * cm])
    panneau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _tint(couleur_score_hex, 0.06)),
        ("BOX", (0, 0), (-1, -1), 0.75, _hex(THEME["line"])),
        ("LINEAFTER", (0, 0), (0, 0), 0.6, _hex(THEME["line"])),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, _hex(couleur_score_hex)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (0, 0), 16),
        ("LEFTPADDING", (1, 0), (1, 0), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    cover_inner = [
        [Spacer(1, 2.5 * cm)],      # claire le bandeau trace sur le canvas
        [Paragraph(
            f"<font color='{THEME['ink']}' size='25'><b>"
            f"{company_name}</b></font>",
            ParagraphStyle("nom", leading=30, fontName=FONT_BOLD))],
        [Spacer(1, 0.4 * cm)],
        [Paragraph(
            f"<font color='{THEME['muted']}' size='7'><b>AVIS</b></font>",
            ParagraphStyle("avis-l", leading=9, fontName=FONT_BOLD))],
        [Spacer(1, 0.12 * cm)],
        [panneau],
        [Spacer(1, 0.35 * cm)],
    ]
    cover_inner += [
        [Spacer(1, 2.6 * cm)],
        [_fiche_identite([
            ("Entreprise", company_name),
            ("Secteur", secteur_label or "Non determine"),
            ("Methode", "Sectorielle" if methode == "sectorielle"
             else "Standard"),
            ("Ratios evalues", str(n_ratios_eval)),
            ("Periode", "Exercices N et N-1" if agregats_n1
             else "Exercice N"),
            ("Genere le", date_fr),
        ])],
    ]

    cover = Table([[Table(cover_inner, colWidths=[LARGEUR_UTILE])]],
                  colWidths=[LARGEUR_UTILE])
    cover.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(cover)
    story.append(PageBreak())

    # ============================================================
    # SOMMAIRE
    # ============================================================
    story.append(_section_titre("SOMMAIRE", h2_style))
    story.append(Spacer(1, 0.3 * cm))
    sommaire_style = ParagraphStyle(
        "Sommaire", parent=normal, fontName=FONT,
        fontSize=10, leading=15, textColor=_hex(THEME["ink"]),
    )
    som_table = _sommaire(_items_sommaire, sommaire_style)
    if som_table:
        story.append(som_table)
    story.append(PageBreak())

    # ============================================================
    # 1. AVIS ET POINTS CLES
    # ============================================================
    faits = faits_structures(result, alertes, medianes)
    section("1. Avis et points cles",
            _boite("Avis", Paragraph(avis_global(result), body_style),
                   couleur=couleur_score_hex))

    bande = _bande_chiffres(points_cles(
        result, agregats, agregats_n1, alertes,
        ref_moyennes=(_moyennes_agregats
                      if _base == "moyenne" else None)))
    if bande:
        story.append(Spacer(1, 0.25 * cm))
        story.append(bande)

    # ajustement de tendance : les points gagnes ou perdus par la
    # trajectoire des ratios (mode derniere annee + tendance)
    ajust = result.get("ajustement_tendance") or {}
    if ajust:
        morceaux = ", ".join(
            f"{label_categorie(c)} {v:+.1f}" for c, v in ajust.items())
        story.append(Paragraph(
            f"Ajustement de tendance (exercice N compare a la moyenne des "
            f"exercices, au plus +/- 5 points par categorie) : {morceaux}.",
            small_style))

    # forces / vigilances en regard, alertes dessous
    story.append(Spacer(1, 0.3 * cm))
    appuis = _puces(faits["appuis"], puce_style)
    vigil = _puces(faits["vigilances"], puce_style)
    story.append(_boites_cote_a_cote(
        "Points d'appui", appuis, THEME["ok"],
        "Points de vigilance", vigil, THEME["warn"]))

    if alertes:
        story.append(Spacer(1, 0.25 * cm))
        story.append(_boite("Alertes - priment sur le score chiffre",
                            _puces(faits["alertes"], puce_style),
                            THEME["bad"]))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_boite("Dynamique de l'exercice",
                        Paragraph(texte_dynamique(agregats, agregats_n1),
                                  body_style),
                        THEME["accent"]))
    croisee = lecture_croisee(cats_scores, agregats, agregats_n1)
    if croisee:
        story.append(Spacer(1, 0.25 * cm))
        story.append(_boite("Lecture croisee : niveau x trajectoire",
                            Paragraph(croisee, body_style)))

    # ============================================================
    # 2. PERIMETRE ET FIABILITE DES DONNEES
    # ============================================================
    fiche = _fiche_identite([
        ("Entreprise", company_name),
        ("Secteur", secteur_label or "Non determine"),
        ("Methode de scoring",
         "Sectorielle" if methode == "sectorielle" else "Standard"),
        ("Base du score", base_label),
        ("Ratios evalues", str(n_ratios_eval)),
        ("Periode analysee",
         "Exercices N et N-1" if agregats_n1 else "Exercice N"),
        ("Genere le", date_fr),
    ])
    section("2. Perimetre et fiabilite des donnees",
            _boite("Identification", fiche))

    if validation:
        stats = validation.get("stats", {})
        resume = Table([[
            _badge(f"{stats.get('succes', 0)}/{stats.get('total', 0)} "
                   "CONTROLES REUSSIS", THEME["ok"], 4.9 * cm),
            _badge(f"{stats.get('avertissements', 0)} VIGILANCES",
                   THEME["warn"], 4.9 * cm),
            _badge(f"{stats.get('erreurs', 0)} INCOHERENCES",
                   THEME["bad"], 4.9 * cm),
        ]], colWidths=[5.6 * cm, 5.6 * cm, 5.6 * cm])
        resume.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(Spacer(1, 0.25 * cm))
        story.append(_boite("Fiabilite des donnees", resume,
                           THEME["bad"] if stats.get("erreurs")
                           else THEME["ink"]))
        if stats.get("erreurs"):
            story.append(Paragraph(
                f"{stats['erreurs']} controle(s) en erreur : les valeurs "
                "concernees sont detaillees en section Controles et doivent "
                "etre verifiees avant d'exploiter le rapport.",
                ParagraphStyle("alert-err", parent=body_style,
                               textColor=_hex(THEME["bad"]))))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_boite("Conditions de lecture",
                        Paragraph(conditions_lecture(validation,
                                                     agregats_n1),
                                  body_style),
                        THEME["muted"]))

    # ============================================================
    # 3. PROFIL DE RISQUE : radar + barres + categories
    # ============================================================
    if has_scores_cfg:
        try:
            fig_radar = chart_radar_categories(result["scores_categories"])
        except Exception:
            fig_radar = None
        try:
            fig_bars = chart_scores_categories(result["scores_categories"])
        except Exception:
            fig_bars = None
        blocs = []
        if fig_radar:
            blocs.append(fig_vers_image(fig_radar, 7.5))
        if fig_bars:
            blocs.append(fig_vers_image(fig_bars, 8.1))
        if blocs:
            graphe = (Table([blocs], colWidths=[8.3 * cm, 8.3 * cm])
                      if len(blocs) == 2 else blocs[0])
            section("3. Profil de risque", graphe)
            story.append(_legende(
                "Profil par categorie et niveau de chaque categorie"))
            story.append(Paragraph(
                "Bareme identique au dashboard : vert au-dela de 70, ambre "
                "de 40 a 70, rouge en dessous. Le detail des ratios de "
                "chaque dimension suit en section Analyse par dimension.",
                small_style))
        else:
            section("3. Profil de risque")

    if has_cats:
        cat_data = [["Categorie", "Score", "Niveau", "Lecture"]]
        cat_colors = []
        tri = sorted(cats_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (cat, sc) in enumerate(tri, start=1):
            if sc >= 70:
                lecture = ("Niveau satisfaisant au regard des references "
                           "retenues : cette dimension soutient clairement "
                           "le score global.")
                badge_txt, badge_col = "SOLIDE", THEME["ok"]
            elif sc >= 40:
                lecture = ("Niveau intermediaire : a surveiller selon "
                           "l'horizon d'analyse ; ce n'est pas une "
                           "defaillance constatee mais un signal a "
                           "documenter.")
                badge_txt, badge_col = "A SURVEILLER", THEME["warn"]
            else:
                lecture = ("Point de vigilance prioritaire du dossier : "
                           "le niveau observe s'ecarte nettement des "
                           "references et doit etre explique avant "
                           "decision.")
                badge_txt, badge_col = "FRAGILE", THEME["bad"]
            cat_data.append([
                Paragraph(f"<b>{label_categorie(cat)}</b>",
                          ParagraphStyle(f"cat{i}", parent=small_style,
                                         fontName=FONT_BOLD,
                                         textColor=_hex(THEME["ink"]))),
                Paragraph(
                    f"<font color='{get_score_gradient(sc)}'><b>"
                    f"{sc:.0f} / 100</b></font>",
                    ParagraphStyle(f"sc{i}", parent=small_style,
                                   alignment=TA_CENTER)),
                _badge(badge_txt, badge_col, 2.6 * cm),
                Paragraph(lecture, small_style),
            ])
            cat_colors.append(("BACKGROUND", (1, i), (1, i),
                               _tint(get_score_gradient(sc), 0.08)))
        cat_table = Table(cat_data,
                          colWidths=[4.2 * cm, 2.4 * cm, 2.9 * cm, 7.5 * cm],
                          repeatRows=1)
        cat_table.setStyle(TableStyle(_table_base() + cat_colors + [
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ]))
        if not has_scores_cfg:
            section("3. Profil de risque", cat_table)
        else:
            story.append(Spacer(1, 0.3 * cm))
            story.append(cat_table)

    # ============================================================
    # 4. CONSTRUCTION DU SCORE : contributions par categorie
    # ============================================================
    if has_scores_cfg:
        # Tableau : poids du profil, score et contribution en points.
        # Contribution = score de la categorie x poids du profil,
        # normalise : la somme des contributions vaut le score global.
        _poids_cfg4 = poids_categories or {}
        _poids_eff4 = {c: _poids_cfg4.get(c) for c in cats_scores
                       if _poids_cfg4.get(c)}
        if not _poids_eff4:
            _poids_eff4 = {c: 1.0 for c in cats_scores}
        _total_p4 = sum(_poids_eff4.values()) or 1.0
        cons_data = [["Categorie", "Poids dans le profil",
                      "Score / 100", "Contribution"]]
        cons_styles = []
        contribs = {}
        tri4 = sorted(cats_scores, key=lambda c: cats_scores[c],
                      reverse=True)
        for i, cat in enumerate(tri4, start=1):
            pcts = _poids_eff4.get(cat, 0) / _total_p4 * 100
            sc = cats_scores[cat]
            contrib = sc * _poids_eff4.get(cat, 0) / _total_p4
            contribs[cat] = contrib
            cons_data.append([
                label_categorie(cat),
                f"{pcts:.0f} %",
                f"{sc:.0f}",
                f"+{contrib:.1f} pts",
            ])
            cons_styles.append(("TEXTCOLOR", (2, i), (2, i),
                                _hex(get_score_gradient(sc))))
            cons_styles.append(("FONTNAME", (2, i), (2, i), FONT_BOLD))
            cons_styles.append(("BACKGROUND", (2, i), (2, i),
                               _tint(get_score_gradient(sc), 0.09)))
            cons_styles.append(("FONTNAME", (3, i), (3, i), FONT_BOLD))
        _tot_i = len(cons_data)
        _global_calc = sum(contribs.values())
        cons_data.append(["TOTAL - SCORE GLOBAL", "100 %", "-",
                          f"{_global_calc:.0f} / 100"])
        cons_styles.append(("FONTNAME", (0, _tot_i), (-1, _tot_i),
                            FONT_BOLD))
        cons_styles.append(("BACKGROUND", (0, _tot_i), (-1, _tot_i),
                           _hex(THEME["bg"])))
        cons_styles.append(("LINEABOVE", (0, _tot_i), (-1, _tot_i),
                            0.8, _hex(THEME["ink"])))
        cons_table = Table(cons_data,
                           colWidths=[6.2 * cm, 3.6 * cm, 3.4 * cm,
                                      3.8 * cm],
                           repeatRows=1)
        cons_table.setStyle(TableStyle(_table_base() + cons_styles + [
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ]))

        # Methode de construction, expliquee pas a pas : niveau ratio,
        # niveau categorie, score global, base retenue.
        expl_style = ParagraphStyle(
            "expl-score", fontName=FONT, fontSize=8.2, leading=11.4,
            textColor=_hex(THEME["ink"]), spaceBefore=2, spaceAfter=2)
        if methode == "sectorielle":
            txt_ratio = (
                "<b>1. Score de chaque ratio (0 a 100).</b> Methode "
                "sectorielle : la valeur retenue est comparee a la "
                "distribution du secteur (Q1, mediane, Q3), au sens "
                "favorable du ratio - 0 a 40 en deca de Q1, 40 a 60 "
                "entre Q1 et la mediane, 60 a 80 entre la mediane et "
                "Q3, 80 a 100 au-dela ; si le secteur ne fournit pas "
                "de reference pour le ratio, repli sur la grille de "
                "seuils fixes de la configuration.")
        else:
            txt_ratio = (
                "<b>1. Score de chaque ratio (0 a 100).</b> Methode "
                "standard : la valeur retenue est interpolee sur la "
                "grille de seuils fixes de la configuration (paliers "
                "de 20 points de 0 a 100), au sens favorable du "
                "ratio.")
        if _base == "tendance":
            txt_base = (
                "<b>4. Base du score : derniere annee + tendance.</b> "
                "Le score porte sur l'exercice N, ajuste par la "
                "trajectoire de chaque ratio (N compare a la moyenne "
                "des exercices, au sens favorable ; bande morte de "
                "+/- 2 % ; au plus +/- 5 points par categorie, "
                "scores bornes 0-100).")
        elif _base == "moyenne":
            txt_base = (
                "<b>4. Base du score : moyenne des exercices.</b> "
                "Chaque ratio est evalue sur sa moyenne arithmetique "
                "sur tous les exercices fournis (meme regle que la "
                "colonne Moyenne des sections 6 et 7).")
        else:
            txt_base = (
                "<b>4. Base du score : derniere annee.</b> Chaque "
                "ratio est evalue sur le seul exercice N.")
        expl_score = _boite("Comment se construit le score", [
            Paragraph(txt_ratio, expl_style),
            Paragraph(
                "<b>2. Score de chaque categorie (0 a 100).</b> "
                "Moyenne ponderee des scores des ratios actifs de la "
                "categorie, chaque ratio pesant selon le poids "
                "declare dans la configuration effective.", expl_style),
            Paragraph(
                "<b>3. Score global (0 a 100).</b> Somme des "
                "contributions du tableau ci-dessus : contribution "
                "d'une categorie = score de la categorie x poids du "
                "profil d'analyse (normalise, la somme vaut le score "
                "global).", expl_style),
            Paragraph(txt_base, expl_style),
            Paragraph(
                "Le detail ratio par ratio - valeurs, references "
                "sectorielles, scores et poids - figure en section 6 "
                "(par dimension) et en section 7 (synthese).",
                ParagraphStyle("expl-ref", fontName=FONT, fontSize=7.5,
                               leading=10, textColor=_hex(THEME["muted"]),
                               spaceBefore=4)),
        ])

        fig_contrib = None
        try:
            fig_contrib = chart_contributions_categories(
                result["scores_categories"], poids_categories)
        except Exception:
            fig_contrib = None
        if fig_contrib:
            section("4. Construction du score",
                    fig_vers_image(fig_contrib, 15.5))
            story.append(_legende(
                "Contribution des categories au score global"))
            story.append(Spacer(1, 0.15 * cm))
            story.append(cons_table)
            story.append(Paragraph(
                "Contribution d'une categorie = score de la categorie x "
                "poids du profil d'analyse, normalise : la somme des "
                "contributions vaut le score global. Les poids sont ceux "
                "du profil configure ; une categorie non ponderee n'entre "
                "pas dans le calcul.", small_style))
            story.append(Spacer(1, 0.25 * cm))
            story.append(expl_score)
        else:
            section("4. Construction du score", cons_table)
            story.append(Spacer(1, 0.25 * cm))
            story.append(expl_score)

    # ============================================================
    # 5. INDICATEURS CLES : N vs N-1 (ou N vs moyenne en mode moyenne)
    # ============================================================
    _mode_moy = (_base == "moyenne" and bool(_moyennes_agregats))
    if _mode_moy:
        ind_data = [["Indicateur", "Exercice N", "Exercice N-1",
                     "Moyenne ex.", "Variation"]]
        _w_ind = [6.2 * cm, 3.4 * cm, 3.4 * cm, 2.6 * cm, 1.4 * cm]
    else:
        ind_data = [["Indicateur", "Exercice N", "Exercice N-1",
                     "Variation"]]
        _w_ind = [7 * cm, 4 * cm, 4 * cm, 1.5 * cm]
    delta_styles = []
    for i, (code, label, inverse) in enumerate(INDICATEURS_CLES, start=1):
        v_n = agregats.get(code)
        v_n1 = (agregats_n1 or {}).get(code)
        v_ref = _moyennes_agregats.get(code) if _mode_moy else v_n1
        d = variation(v_n, v_ref)
        d_txt = "n/d" if d is None else f"{d:+.1f} %"
        ligne = [label, fmt_euro(v_n), fmt_euro(v_n1)]
        if _mode_moy:
            ligne.append(fmt_euro(v_ref))
        ligne.append(d_txt)
        ind_data.append(ligne)
        if d is not None:
            positif = d > 0 if not inverse else d < 0
            c = _hex(THEME["ok"] if positif else THEME["bad"])
            delta_styles.append(("TEXTCOLOR", (-1, i), (-1, i), c))
            delta_styles.append(("FONTNAME", (-1, i), (-1, i), FONT_BOLD))
            delta_styles.append(
                ("BACKGROUND", (-1, i), (-1, i),
                 _tint(THEME["ok"] if positif else THEME["bad"], 0.09)))

    ind_table = Table(ind_data, colWidths=_w_ind, repeatRows=1)
    ind_table.setStyle(TableStyle(_table_base() + delta_styles + [
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    if _mode_moy:
        note_ind = Paragraph(
            "En mode moyenne des exercices, la variation compare "
            "l'exercice N a la moyenne des exercices (N inclus) : elle "
            "mesure l'ecart du dernier exercice au niveau moyen de la "
            "periode analyse. Une variation favorable n'est pas "
            "necessairement une amelioration : elle se lit au regard du "
            "sens de l'indicateur (une hausse des dettes est "
            "defavorable).", small_style)
    elif not agregats_n1:
        note_ind = Paragraph(
            "Exercice N-1 non fourni : les variations ne sont pas "
            "calculees.", small_style)
    else:
        note_ind = Paragraph(
            "Une variation favorable n'est pas necessairement une "
            "amelioration : elle se lit au regard du sens de "
            "l'indicateur (une hausse des dettes est defavorable). La "
            "colonne est coloree en consequence.", small_style)
    section("5. Indicateurs cles", ind_table)
    story.append(note_ind)

    if agregats_n1:
        try:
            fig_cmp = chart_comparaison_n_n1(agregats, agregats_n1)
            if fig_cmp:
                story.append(Spacer(1, 0.3 * cm))
                story.append(fig_vers_image(fig_cmp, 15.5))
                story.append(_legende(
                    "Indicateurs cles : exercices N et N-1"))
        except Exception:
            pass

    # ============================================================
    # 6. ANALYSE PAR DIMENSION : une sous-section par categorie
    # ============================================================
    if has_cats:
        intro = Paragraph(
            f"Chaque dimension est lue individuellement : son niveau, son "
            f"ratio le plus porteur et le plus penalise, puis son tableau "
            f"de ratios (valeur retenue pour le score - {base_label.lower()} "
            f"- mediane du secteur et score sur 100). Les dimensions sont "
            f"classees par niveau decroissant."
            + (" En mode derniere annee + tendance, le score de chaque "
               "categorie integre l'ajustement de trajectoire (au plus "
               "+/- 5 points)." if _base == "tendance" else ""),
            body_style)
        section("6. Analyse par dimension", intro)

        _sc_cats = result.get("scores_categories") or {}
        for cat in sorted(_sc_cats,
                          key=lambda c: (_sc_cats[c] is not None,
                                         _sc_cats[c] or 0),
                          reverse=True):
            sc = _sc_cats[cat]
            if sc is None:
                continue
            sc_hex = get_score_gradient(sc)
            # en-tete de dimension : nom + badge de niveau
            if sc >= 70:
                badge_txt, badge_col = "SOLIDE", THEME["ok"]
            elif sc >= 40:
                badge_txt, badge_col = "A SURVEILLER", THEME["warn"]
            else:
                badge_txt, badge_col = "FRAGILE", THEME["bad"]
            entete = Table([[
                Paragraph(f"<b>{label_categorie(cat).upper()}</b>"
                          f" &nbsp;<font color='{sc_hex}' size='8'>"
                          f"<b>{sc:.0f} / 100</b></font>",
                          ParagraphStyle("dim-t", fontName=FONT_BOLD,
                                         fontSize=10, leading=13,
                                         textColor=_hex(THEME["ink"]))),
                _badge(badge_txt, badge_col, 2.6 * cm),
            ]], colWidths=[LARGEUR_UTILE - 2.6 * cm, 2.6 * cm])
            entete.setStyle(TableStyle([
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, _hex(THEME["line"])),
                ("LINEBEFORE", (0, 0), (0, 0), 2.5, sc_hex),
                ("LEFTPADDING", (0, 0), (0, 0), 9),
                ("LEFTPADDING", (1, 0), (1, 0), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            lecture = Paragraph(resume_categorie(cat, sc, details, medianes),
                                small_style)

            # tableau des ratios de la dimension : configures + notes
            lignes_cat = {n: d for n, d in details.items()
                          if d.get("categorie") == cat}
            if config_ratios:
                for nom, info in config_ratios.items():
                    if info.get("categorie") == cat and \
                            nom not in lignes_cat:
                        lignes_cat[nom] = {"score": None, "valeur": None,
                                           "poids": (info or {}).get(
                                               "poids", 0)}
            cell_style = ParagraphStyle(
                "cell-lab", fontName=FONT, fontSize=8.5, leading=10.6,
                textColor=_hex(THEME["ink"]))
            dim_data = [["Ratio", valeur_col, "Med. secteur",
                         "Score / 100", "Poids"]]
            dim_colors = []
            items = sorted(lignes_cat.items(),
                           key=lambda kv: (kv[1].get("score") is None,
                                           -(kv[1].get("score") or 0)))
            for i, (nom, det) in enumerate(items, start=1):
                v = det.get("valeur")
                s = det.get("score")
                med = medianes.get(nom)
                dim_data.append([
                    Paragraph(label_ratio(nom), cell_style),
                    f"{v:,.2f}".replace(",", " ") if v is not None else "n/d",
                    f"{med:,.2f}".replace(",", " ")
                    if med is not None else "-",
                    f"{s:.0f}" if s is not None else "n/d",
                    f"{det.get('poids', 0):.2f}",
                ])
                if s is not None:
                    dim_colors.append(("TEXTCOLOR", (3, i), (3, i),
                                       _hex(get_score_gradient(s))))
                    dim_colors.append(("FONTNAME", (3, i), (3, i),
                                       FONT_BOLD))
            dim_table = Table(dim_data, repeatRows=1,
                              colWidths=[6.6 * cm, 2.9 * cm, 2.9 * cm,
                                         2.6 * cm, 2.0 * cm])
            dim_table.setStyle(TableStyle(_table_base() + dim_colors + [
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "CENTER"),
            ]))
            story.append(Spacer(1, 0.32 * cm))
            story.append(KeepTogether([entete, lecture, dim_table]))

    # ============================================================
    # 7. SYNTHESE DES RATIOS SCORES : tableau de reference
    # ============================================================
    if has_details:
        historique = historique or {}
        rat_data = [["Categorie", "Ratio", valeur_col, "Moyenne",
                     "Med. secteur", "Score", "Poids"]]
        rat_colors = []
        cell_style = ParagraphStyle(
            "cell-lab", fontName=FONT, fontSize=8.5, leading=10.6,
            textColor=_hex(THEME["ink"]))
        _sc_cats = result.get("scores_categories") or {}
        _ordre_cats = {c: i for i, c in enumerate(sorted(
            _sc_cats,
            key=lambda c: (_sc_cats[c] is not None, _sc_cats[c] or 0),
            reverse=True))}
        _lignes_items = list(details.items())
        if config_ratios:
            _deja = set(details.keys())
            for nom, info in config_ratios.items():
                if nom in _deja:
                    continue
                _lignes_items.append((nom, {
                    "score": None, "valeur": None,
                    "poids": (info or {}).get("poids", 0),
                    "categorie": (info or {}).get("categorie", "autre"),
                }))
        lignes = sorted(
            _lignes_items,
            key=lambda kv: (
                _ordre_cats.get(kv[1].get("categorie", ""), 99),
                kv[1].get("score") is None,
                -(kv[1].get("score") or 0),
            ),
        )
        for i, (nom, det) in enumerate(lignes, start=1):
            val = det.get("valeur")
            s = det.get("score")
            cat = det.get("categorie", "autre")
            moy = (historique.get(nom) or {}).get("moyenne")
            med = medianes.get(nom)
            rat_data.append([
                Paragraph(label_categorie(cat), cell_style),
                Paragraph(label_ratio(nom), cell_style),
                f"{val:,.2f}".replace(",", " ")
                if val is not None else "n/d",
                f"{moy:,.2f}".replace(",", " ")
                if moy is not None else "n/d",
                f"{med:,.2f}".replace(",", " ") if med is not None else "-",
                f"{s:.0f}" if s is not None else "n/d",
                f"{det.get('poids', 0):.2f}",
            ])
            if val is not None:
                rat_colors.append(("FONTNAME", (2, i), (2, i), FONT_BOLD))
                rat_colors.append(("TEXTCOLOR", (2, i), (2, i),
                                   _hex(THEME["ink"])))
            if s is not None:
                rat_colors.append(("TEXTCOLOR", (5, i), (5, i),
                                   _hex(get_score_gradient(s))))
                rat_colors.append(("FONTNAME", (5, i), (5, i),
                                   FONT_BOLD))
                rat_colors.append(("BACKGROUND", (5, i), (5, i),
                                   _tint(get_score_gradient(s), 0.09)))
        rat_table = Table(
            rat_data, repeatRows=1,
            colWidths=[3.4 * cm, 4.2 * cm, 2.4 * cm, 2.0 * cm, 2.0 * cm,
                       1.2 * cm, 1.6 * cm])
        rat_table.setStyle(TableStyle(_table_base() + rat_colors + [
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (5, 1), (5, -1), "CENTER"),
        ]))
        section("7. Synthese des ratios scores", rat_table)
        story.append(Paragraph(
            "Tableau de reference : valeurs dans leur unite de calcul, "
            "moyenne arithmetique sur tous les exercices fournis (meme "
            "regle que le dashboard), mediane du secteur de reference. "
            f"La colonne {valeur_col} est la valeur retenue pour le score "
            f"({base_label.lower()}). Un tiret signale l'absence de "
            "reference sectorielle pour le ratio.", small_style))

    # ============================================================
    # 8. CONTROLES DE COHERENCE
    # ============================================================
    if validation:
        stats = validation.get("stats", {})
        resume_rows = [[
            _badge(f"{stats.get('succes', 0)}/{stats.get('total', 0)} "
                   "CONTROLES REUSSIS", THEME["ok"], 4.9 * cm),
            _badge(f"{stats.get('avertissements', 0)} VIGILANCES",
                   THEME["warn"], 4.9 * cm),
            _badge(f"{stats.get('erreurs', 0)} INCOHERENCES",
                   THEME["bad"], 4.9 * cm),
        ]]
        resume = Table(resume_rows,
                       colWidths=[5.6 * cm, 5.6 * cm, 5.6 * cm])
        resume.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        section("8. Controles de coherence des donnees", resume)

        rapport = validation.get("rapport", [])
        if rapport:
            niveaux_pdf = {
                "OK": (THEME["ok"], "Reussi"),
                "WARN": (THEME["warn"], "Vigilance"),
                "ERREUR": (THEME["bad"], "Incoherence"),
            }
            ct_data = [["Statut", "Controle", "Observation"]]
            ct_styles = []
            for i, item in enumerate(rapport, start=1):
                niveau = item.get("niveau", "INFO")
                col, lib = niveaux_pdf.get(niveau, (THEME["muted"], niveau))
                msg = item.get("message", "")
                det = item.get("details") or ""
                texte = msg + (f"<br/><i>{det}</i>" if det else "")
                ct_data.append([
                    _badge(lib, col, 2.0 * cm),
                    Paragraph(item.get("test", ""), small_style),
                    Paragraph(texte, small_style),
                ])
                ct_styles.append(("VALIGN", (0, i), (-1, i), "TOP"))
            ct_table = Table(ct_data, repeatRows=1,
                             colWidths=[2.4 * cm, 4.8 * cm, 9.8 * cm])
            ct_table.setStyle(TableStyle(_table_base() + ct_styles))
            story.append(Spacer(1, 0.25 * cm))
            story.append(ct_table)

    # ============================================================
    # ANNEXE A - GLOSSAIRE DES RATIOS
    # ============================================================
    if has_glossaire:
        present = {}
        for nom, det in details.items():
            present.setdefault(det.get("categorie", "autre"), []).append(nom)
        ordre = ([c for c in CAT_LABELS if c in present]
                 + [c for c in present if c not in CAT_LABELS])
        if any(nom in GLOSSAIRE for noms in present.values()
               for nom in noms):
            section("A. Annexe - Glossaire des ratios",
                    Paragraph(
                        "Definitions et mode de lecture des ratios "
                        "utilises dans ce rapport. Le sens favorable "
                        "indique la direction jugee positive : pour la "
                        "plupart des ratios une valeur elevee est "
                        "favorable, pour les ratios de dette et de "
                        "delais une valeur basse l'est. Les reperes "
                        "cites sont generiques : le niveau pertinent "
                        "depend du secteur, de la taille et de "
                        "l'horizon d'analyse.", body_style),
                    page_break=True)
            for cat in ordre:
                g_data = [["Ratio", "Definition", "Mode de lecture"]]
                for nom in sorted(present.get(cat, [])):
                    def_, lect_ = GLOSSAIRE.get(nom, ("", ""))
                    if not def_:
                        continue
                    g_data.append([
                        Paragraph(f"<b>{label_ratio(nom)}</b>",
                                  small_style),
                        Paragraph(def_, small_style),
                        Paragraph(lect_, small_style),
                    ])
                if len(g_data) < 2:
                    continue
                g_table = Table(g_data, repeatRows=1,
                                colWidths=[3.4 * cm, 6.2 * cm, 7.4 * cm])
                g_table.setStyle(TableStyle(_table_base() + [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(Spacer(1, 0.15 * cm))
                story.append(_sous_bloc_annexe(label_categorie(cat)))
                story.append(g_table)

    # ============================================================
    # ANNEXE B - METHODE ET LIMITES
    # ============================================================
    mentions = [
        "Ce rapport est genere automatiquement a partir des documents "
        "comptables fournis (extraction par Mistral Document AI pour les "
        "PDF et images, ou par le lecteur Excel integre pour les "
        "classeurs ; normalisation PCG). Les montants restent ceux "
        "figurant dans les documents.",
        "Le score global resulte d'une moyenne ponderee de ratios par "
        "categorie. Selon la base choisie, il porte sur l'exercice N "
        "ajuste par la trajectoire des ratios (N compare a la moyenne des "
        "exercices, au plus +/- 5 points par categorie) ou directement "
        "sur la moyenne des exercices. Les seuils ou references "
        "sectorielles sont indicatifs (sources publiques : INSEE, Banque "
        "de France) et doivent etre ajustees au contexte du dossier.",
        "La synthese croise le niveau constate (scores par categorie) et "
        "la trajectoire de l'exercice (variations N vs N-1) : les deux ne "
        "se substituent pas l'un a l'autre et seuls des exercices "
        "multiples permettent une tendance.",
        "Ce document constitue une aide a l'analyse : il ne remplace ni "
        "l'expertise d'un analyste, ni un audit comptable, ni un avis "
        "financier ou juridique.",
        f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}.",
    ]
    section("B. Annexe - Methode et limites",
            Paragraph(mentions[0], small_style))
    for m in mentions[1:]:
        story.append(Paragraph(m, small_style))

    doc.build(story,
              onFirstPage=_decor_couverture,
              onLaterPages=_footer_factory(company_name),
              canvasmaker=_CanvasNumerote)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _sous_bloc_annexe(titre):
    """Sous-titre d'annexe : carre accent + titre gras."""
    return Paragraph(
        f"<font color='{THEME['accent']}'>&#9632;</font> <b>{titre}</b>",
        ParagraphStyle("annexe-h3", fontName=FONT_BOLD, fontSize=9.6,
                       leading=13, textColor=_hex(THEME["ink"]),
                       spaceBefore=10, spaceAfter=4))
