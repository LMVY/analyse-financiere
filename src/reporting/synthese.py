"""Moteur de contenu du rapport PDF.

Fournit des blocs COURTS et FACTUELLES, chiffres a l'appui, que la
mise en page assemble en structure d'avis :

- avis_global        : le verdict en 2-3 phrases ;
- points_cles        : les chiffres de la bande d'ouverture ;
- faits_structures   : trois listes de faits courts : appuis,
                       vigilances, alertes ;
- resume_categorie   : une lecture factuelle d'une categorie ;
- texte_dynamique    : la trajectoire N vs N-1 ;
- lecture_croisee    : ce que la trajectoire confirme ou nuance ;
- conditions_lecture : fiabilite et limites du dossier.

Regle editoriale : chaque affirmation est portee par un chiffre, les
phrases restent courtes, aucun remplissage.
"""
from src.reporting.glossaire import (
    CAT_DESCRIPTIONS, label_categorie, label_ratio, get_score_label,
)
from src.visualization.colors import get_score_verdict

# ============================================================
# FORMATAGE ET OUTILS
# ============================================================
def variation(v_n, v_n1):
    """Variation en % entre deux exercices (None si non calculable)."""
    if v_n is None or v_n1 is None or abs(v_n1) < 1e-9:
        return None
    return (v_n - v_n1) / abs(v_n1) * 100


def fmt_euro(v):
    if v is None:
        return "N/A"
    return f"{v:,.0f} EUR".replace(",", " ")


def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v:.1f} %"


def fmt_ratio_val(v):
    """Valeur de ratio formatee (unite selon le ratio)."""
    if v is None:
        return "n/d"
    if abs(v) >= 100:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ")


def marge_ebitda(agregats):
    """Marge d'EBITDA en % a partir des agregats (None si non calculable)."""
    ca = agregats.get("chiffre_affaires")
    eb = agregats.get("ebitda")
    if not ca or eb is None:
        return None
    return eb / ca * 100


def ratios_extremes(details, cat):
    """Ratios au meilleur et au moins bon score d'une categorie."""
    items = [(n, d) for n, d in (details or {}).items()
             if d.get("categorie") == cat and d.get("score") is not None]
    if not items:
        return None, None
    items.sort(key=lambda kv: kv[1]["score"], reverse=True)
    return items[0], items[-1]


# ============================================================
# AVIS GLOBAL
# ============================================================
def avis_global(result):
    """Le verdict en 2-3 phrases : score, contraste, porte."""
    score = result.get("score_global")
    if score is None:
        return ("Le score global n'a pas pu etre calcule : les donnees "
                "disponibles sont insuffisantes pour fonder une opinion. "
                "Les sections factuelles restent informatives, mais "
                "aucune conclusion ne doit en etre tiree sans completer "
                "les donnees manquantes.")
    details = result.get("details") or {}
    n_ratios = len([d for d in details.values()
                    if d.get("score") is not None])
    texte = (f"Score global : {score:.0f} / 100 sur {n_ratios} ratios "
             f"evalues - {get_score_verdict(score).lower()}. ")
    cats = {k: v for k, v in result.get("scores_categories", {}).items()
            if v is not None}
    if cats:
        best_c = max(cats, key=cats.get)
        weak_c = min(cats, key=cats.get)
        ecart = cats[best_c] - cats[weak_c]
        if ecart >= 25:
            texte += (f"Profil contraste : {ecart:.0f} points separent "
                      f"{label_categorie(best_c).lower()} "
                      f"({cats[best_c]:.0f}) de "
                      f"{label_categorie(weak_c).lower()} "
                      f"({cats[weak_c]:.0f}) - le score moyen ne doit "
                      f"pas masquer cet ecart.")
        elif ecart <= 12:
            texte += ("Profil homogene : les dimensions evoluent dans un "
                      "corridor etroit, un point isole ne fausse pas la "
                      "lecture d'ensemble.")
        else:
            texte += ("Le score moyen resume des dimensions de niveaux "
                      "differents : la lecture par dimension (section "
                      "Analyse par dimension) prime sur le chiffre global.")
    return texte


# ============================================================
# POINTS CLES : chiffres de la bande d'ouverture
# ============================================================
def points_cles(result, agregats, agregats_n1, alertes,
                ref_moyennes=None):
    """Faits majeurs chiffres pour la bande d'ouverture du rapport.

    Retourne une liste de dicts {label, valeur, note, couleur} :
    - label   : intitule court de l'indicateur ;
    - valeur  : fait chiffre principal (texte deja formate) ;
    - note    : precision de lecture (facultative, '' sinon) ;
    - couleur : couleur d'accent.

    En mode "moyenne", la dynamique d'activite compare l'exercice N a
    ref_moyennes (moyenne des agregats sur les exercices fournis) au
    lieu de l'exercice N-1.
    """
    from src.visualization.colors import THEME, get_score_gradient

    faits = []
    score = result.get("score_global")
    base = result.get("base_scoring")
    cats = {k: v for k, v in result.get("scores_categories", {}).items()
            if v is not None}

    # 1. Score global
    if score is not None:
        faits.append({
            "label": "Score global",
            "valeur": f"{score:.0f} / 100",
            "note": get_score_verdict(score),
            "couleur": get_score_gradient(score),
        })

    # 2. Dimension la plus solide / la plus fragile
    if cats:
        best_c = max(cats, key=cats.get)
        faits.append({
            "label": "Point fort",
            "valeur": f"{cats[best_c]:.0f}",
            "note": label_categorie(best_c).lower(),
            "couleur": THEME["ok"],
        })
        weak_c = min(cats, key=cats.get)
        faits.append({
            "label": "Point fragile",
            "valeur": f"{cats[weak_c]:.0f}",
            "note": label_categorie(weak_c).lower(),
            "couleur": (THEME["bad"] if cats[weak_c] < 40
                        else THEME["warn"]),
        })

    # 3. Dynamique d'activite : N vs moyenne (mode moyenne) ou N-1
    if base == "moyenne" and ref_moyennes:
        d_ca = variation(agregats.get("chiffre_affaires"),
                         ref_moyennes.get("chiffre_affaires"))
        if d_ca is not None:
            faits.append({
                "label": "Activite (CA)",
                "valeur": f"{d_ca:+.1f} %",
                "note": "vs moyenne",
                "couleur": THEME["ok"] if d_ca >= 0 else THEME["bad"],
            })
    elif agregats_n1:
        d_ca = variation(agregats.get("chiffre_affaires"),
                         agregats_n1.get("chiffre_affaires"))
        if d_ca is not None:
            faits.append({
                "label": "Activite (CA)",
                "valeur": f"{d_ca:+.1f} %",
                "note": "vs N-1",
                "couleur": THEME["ok"] if d_ca >= 0 else THEME["bad"],
            })

    # 4. Alertes
    n_crit = sum(1 for a in (alertes or [])
                 if a.get("niveau") == "critique")
    n_warn = sum(1 for a in (alertes or [])
                 if a.get("niveau") == "warning")
    if n_crit:
        faits.append({
            "label": "Alertes critiques",
            "valeur": str(n_crit),
            "note": "a lever avant decision",
            "couleur": THEME["bad"],
        })
    elif alertes:
        faits.append({
            "label": "Points d'attention",
            "valeur": str(n_warn),
            "note": "aucune alerte critique",
            "couleur": THEME["warn"],
        })
    else:
        faits.append({
            "label": "Alertes",
            "valeur": "0",
            "note": "aucune alerte declenchee",
            "couleur": THEME["ok"],
        })

    return faits


# ============================================================
# FAITS STRUCTURES : appuis / vigilances / alertes
# ============================================================
def _fait_ratio(nom, det, mediane=None):
    """Un fait court, chiffre : 'Delai clients : 42 j (mediane 57) - 75/100'."""
    texte = f"<b>{label_ratio(nom)}</b> : {fmt_ratio_val(det.get('valeur'))}"
    if mediane is not None:
        texte += f" (mediane secteur {fmt_ratio_val(mediane)})"
    texte += f" - {det.get('score', 0):.0f} / 100"
    return texte


def faits_structures(result, alertes, medianes_secteur=None):
    """Trois listes de faits courts, tries par score.

    Retourne {"appuis": [...], "vigilances": [...], "alertes": [...]}
    ou chaque element est une phrase courte, chiffree. Les faits
    reposent sur les ratios notes ; les alertes reprennent les
    messages du detecteur, telles quelles.
    """
    from src.visualization.colors import THEME

    details = result.get("details") or {}
    cats = {k: v for k, v in result.get("scores_categories", {}).items()
            if v is not None}
    medianes = medianes_secteur or {}

    appuis, vigilances = [], []
    for cat, sc in sorted(cats.items(), key=lambda kv: kv[1], reverse=True):
        best, worst = ratios_extremes(details, cat)
        if sc >= 55:
            if best:
                appuis.append(
                    f"<b>{label_categorie(cat)}</b> ({sc:.0f} / 100) : "
                    + _fait_ratio(best[0], best[1],
                                  medianes.get(best[0])))
        else:
            if worst:
                vigilances.append(
                    f"<b>{label_categorie(cat)}</b> ({sc:.0f} / 100) : "
                    + _fait_ratio(worst[0], worst[1],
                                  medianes.get(worst[0])))

    alertes_faits = []
    for a in sorted((alertes or []),
                    key=lambda x: {"critique": 0, "warning": 1}.get(
                        x.get("niveau"), 2)):
        alertes_faits.append(a.get("message", ""))

    if not appuis:
        appuis.append("Aucune dimension n'atteint le niveau de confort "
                      "(55 / 100) : le score ne dispose pas de point "
                      "d'appui net.")
    if not vigilances and cats:
        vigilances.append("Toutes les dimensions evaluees sont au-dessus "
                          "du niveau de confort (55 / 100).")
    if not alertes_faits:
        alertes_faits.append(
            "Aucune alerte automatique declenchee - les risques hors "
            "perimetre (garanties, contentieux, dependance commerciale) "
            "ne sont pas couverts par ces regles.")

    return {"appuis": appuis, "vigilances": vigilances,
            "alertes": alertes_faits}


# ============================================================
# LECTURE D'UNE CATEGORIE
# ============================================================
def resume_categorie(cat, sc, details, medianes_secteur=None):
    """Lecture factuelle d'une categorie : niveau + extreme + ecart type."""
    details = details or {}
    medianes = medianes_secteur or {}
    best, worst = ratios_extremes(details, cat)
    niveau = get_score_label(sc)

    morceaux = [f"Niveau {niveau.lower()} ({sc:.0f} / 100)"]
    if best:
        morceaux.append(f"meilleur ratio : {label_ratio(best[0])} a "
                        f"{fmt_ratio_val(best[1].get('valeur'))} "
                        f"({best[1]['score']:.0f} / 100)")
    if worst and worst[0] != best[0]:
        morceaux.append(f"plus penalise : {label_ratio(worst[0])} a "
                        f"{fmt_ratio_val(worst[1].get('valeur'))} "
                        f"({worst[1]['score']:.0f} / 100)")
    return " - ".join(morceaux) + "."


# ============================================================
# DYNAMIQUE N vs N-1
# ============================================================
def texte_dynamique(agregats, agregats_n1):
    """Dynamique N vs N-1 : activite, marge, structure, avec nuances."""
    if not agregats_n1:
        return ("Aucun exercice anterieur n'a ete fourni : la dynamique "
                "de l'entreprise ne peut pas etre evaluee. L'analyse se "
                "limite a une photographie de l'exercice N ; un "
                "historique de deux ou trois exercices permettrait de "
                "distinguer une tendance de fond d'un evenement "
                "ponctuel.")

    ca, ca1 = agregats.get("chiffre_affaires"), agregats_n1.get("chiffre_affaires")
    eb, eb1 = agregats.get("ebitda"), agregats_n1.get("ebitda")
    rn, rn1 = agregats.get("resultat_net"), agregats_n1.get("resultat_net")
    cp, cp1 = agregats.get("capitaux_propres"), agregats_n1.get("capitaux_propres")
    dt, dt1 = agregats.get("total_dettes"), agregats_n1.get("total_dettes")

    phrases = []
    d_ca = variation(ca, ca1)
    if d_ca is not None:
        sens = "progresse" if d_ca >= 0 else "recule"
        phrases.append(f"le chiffre d'affaires {sens} de {abs(d_ca):.1f} % "
                       f"pour atteindre {fmt_euro(ca)}")
    d_eb = variation(eb, eb1)
    if d_eb is not None:
        phrases.append(f"l'EBITDA evolue de {d_eb:+.1f} % ({fmt_euro(eb)})")
    d_rn = variation(rn, rn1)
    if d_rn is not None:
        if rn is not None and rn < 0:
            phrases.append(f"le resultat net reste negatif ({fmt_euro(rn)}, "
                           f"variation de {d_rn:+.1f} %)")
        else:
            phrases.append(f"le resultat net varie de {d_rn:+.1f} % "
                           f"({fmt_euro(rn)})")

    texte = ""
    if phrases:
        texte = "Sur l'exercice, " + ", ".join(phrases) + ". "

    # Marge operationnelle en points de pourcentage
    marge_n = marge_ebitda(agregats)
    marge_1 = marge_ebitda(agregats_n1)
    if marge_n is not None and marge_1 is not None and abs(marge_n - marge_1) >= 0.5:
        diff = marge_n - marge_1
        lecture = ("un signe d'amelioration de la rentabilite operationnelle "
                   "si la conjoncture le confirme"
                   if diff > 0 else
                   "le signe d'une pression sur la rentabilite operationnelle "
                   "(couts, prix ou mix)")
        texte += (f"La marge d'EBITDA passe de {marge_1:.1f} % a "
                  f"{marge_n:.1f} % ({diff:+.1f} points), {lecture}. ")

    # Structure financiere
    morceaux = []
    d_cp = variation(cp, cp1)
    if d_cp is not None:
        sens = "se renforcent" if d_cp >= 0 else "diminuent"
        morceaux.append(f"les capitaux propres {sens} de {abs(d_cp):.1f} %")
    d_dt = variation(dt, dt1)
    if d_dt is not None:
        sens = "s'allege" if d_dt < 0 else "augmente"
        morceaux.append(f"l'endettement total {sens} de {abs(d_dt):.1f} %")
    if morceaux:
        texte += "Cote structure, " + " et ".join(morceaux) + ". "

    texte += ("Ces variations ne portent que sur un exercice : elles ne "
              "constituent pas une tendance de fond. Il convient de les "
              "recouper avec l'historique des exercices disponibles dans le "
              "rapport avant toute conclusion.")
    return texte


# ============================================================
# LECTURE CROISEE : niveau (scores) x trajectoire (variations)
# ============================================================
def lecture_croisee(cats, agregats, agregats_n1):
    """Croise le niveau constate et la trajectoire de l'exercice.

    Pour chaque dimension ou l'information existe des deux cotes,
    indique si la dynamique confirme, nuance ou contredit le score.
    Retourne None si le croisement n'est pas calculable.
    """
    if not agregats_n1 or not cats:
        return None

    morceaux = []

    # --- Rentabilite vs marge d'EBITDA ---
    marge_n = marge_ebitda(agregats)
    marge_1 = marge_ebitda(agregats_n1)
    if "rentabilite" in cats and marge_n is not None and marge_1 is not None:
        diff = marge_n - marge_1
        s = cats["rentabilite"]
        if abs(diff) >= 0.5:
            if s >= 55 and diff > 0:
                morceaux.append(
                    f"la rentabilite bien notee ({s:.0f}/100) est confirmee "
                    f"par une marge d'EBITDA en progression ({diff:+.1f} "
                    f"points) : le niveau et la trajectoire vont dans le "
                    f"meme sens")
            elif s < 55 and diff < 0:
                morceaux.append(
                    f"la rentabilite en retrait ({s:.0f}/100) se double "
                    f"d'une marge d'EBITDA en recul ({diff:+.1f} points) : "
                    f"il ne s'agit pas d'un accident de calcul mais d'une "
                    f"pression qui s'installe")
            elif s >= 55 and diff < 0:
                morceaux.append(
                    f"la rentabilite reste bien notee ({s:.0f}/100) mais sa "
                    f"marge d'EBITDA recule ({diff:+.1f} points) : le niveau "
                    f"est encore satisfaisant, sa trajectoire appelle une "
                    f"attention avant le prochain exercice")
            else:
                morceaux.append(
                    f"la rentabilite reste en retrait ({s:.0f}/100) alors "
                    f"que la marge d'EBITDA remonte ({diff:+.1f} points) : "
                    f"l'amelioration est encore trop recente ou trop faible "
                    f"pour redresser le score")

    # --- Croissance vs chiffre d'affaires ---
    d_ca = variation(agregats.get("chiffre_affaires"),
                     agregats_n1.get("chiffre_affaires"))
    if "croissance" in cats and d_ca is not None:
        s = cats["croissance"]
        if d_ca >= 5 and s < 55:
            morceaux.append(
                f"l'activite progresse nettement ({d_ca:+.1f} %) alors que "
                f"la croissance reste modrement notee ({s:.0f}/100) : "
                f"verifier la regularite et la qualite de cette progression "
                f"(mix, prix, volume)")
        elif d_ca < 0 and s >= 55:
            morceaux.append(
                f"le recul d'activite ({d_ca:+.1f} %) nuance le score de "
                f"croissance ({s:.0f}/100), fonde sur des references "
                f"structurelles plus larges qu'un seul exercice")
        elif d_ca < -10 and s < 55:
            morceaux.append(
                f"la contraction de l'activite ({d_ca:+.1f} %) est coherente "
                f"avec le score de croissance faible ({s:.0f}/100) : la "
                f"difficulte est visible des deux cotes de la lecture")

    # --- Endettement vs structure de financement ---
    d_dt = variation(agregats.get("total_dettes"),
                     agregats_n1.get("total_dettes"))
    d_cp = variation(agregats.get("capitaux_propres"),
                     agregats_n1.get("capitaux_propres"))
    if "endettement" in cats:
        s = cats["endettement"]
        if s < 55 and d_dt is not None and d_dt > 10:
            morceaux.append(
                f"l'endettement mal note ({s:.0f}/100) se degrade egalement "
                f"dans les faits (dette totale +{d_dt:.1f} %) : la structure "
                f"de financement se tend sur l'exercice, ce qui rend le "
                f"point prioritaire")
        elif s >= 55 and d_dt is not None and d_dt > 15:
            morceaux.append(
                f"le score d'endettement reste acceptable ({s:.0f}/100) mais "
                f"la dette totale progresse de {d_dt:+.1f} % : le confort "
                f"actuel ne doit pas faire oublier cette derive a suivre "
                f"au prochain exercice")
        elif s < 55 and d_cp is not None and d_cp < 0:
            morceaux.append(
                f"la faiblesse d'endettement notee ({s:.0f}/100) est "
                f"coherente avec des capitaux propres en recul "
                f"({d_cp:+.1f} %) : le bilan se fragilise par sa base")

    if not morceaux:
        return None

    return ("En croisant le niveau et la trajectoire : "
            + " ; ".join(morceaux)
            + ". Ces recoupements portent sur deux exercices seulement : "
              "ils orientent la lecture, ils ne la figent pas.")


# ============================================================
# CONDITIONS DE LECTURE
# ============================================================
def conditions_lecture(validation=None, agregats_n1=None):
    """Fiabilite des donnees et limites du dossier, en un paragraphe."""
    texte = ""
    if validation:
        stats = validation.get("stats", {})
        err = stats.get("erreurs", 0)
        warn = stats.get("avertissements", 0)
        if err:
            texte += (f"{err} controle(s) de coherence sont en erreur : "
                      "certaines donnees sont incoherentes et la fiabilite "
                      "des ratios calcules s'en trouve degradee. ")
        elif warn:
            texte += (f"{warn} avertissement(s) de coherence ont ete releves "
                      "sans bloquer l'analyse ; les montants concernes sont a "
                      "verifier. ")
        else:
            texte += ("Tous les controles de coherence ont ete passes avec "
                      "succes. ")
    texte += ("La synthese repose sur les elements comptables extraits des "
              "documents fournis pour l'exercice N"
              + (" et l'exercice N-1" if agregats_n1 else "")
              + ". Elle ne tient compte ni des elements hors bilan, ni des "
              "engagements eventuels, ni de l'actualite de l'entreprise. "
              "Les scores et seuils sont indicatifs et doivent etre resitues "
              "dans le contexte du dossier avant toute decision "
              "d'engagement. Le glossaire en annexe detaille la definition "
              "et le mode de lecture de chaque ratio cite.")
    return texte
