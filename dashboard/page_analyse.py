"""Page Analyse : import des documents, extraction, score, resultats.

Structure :
- afficher()             : point d'entree, appele par app.py a chaque rendu
- _initialiser_session() : etat Streamlit par defaut
- _score_resultat()      : score selon les options (secteur, profil, base)
- _zone_import()         : accueil + televersement des documents
- executer_analyse()     : extraction, fusion des exercices, controles
- afficher_resultats()   : score, KPI, onglets de detail, export PDF
"""
import sys
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.styles import injecter_analyse
from dashboard.composants import (
    T, score_color, verdict, label, kpi, score_ring, category_rows,
    radar_chart, contribution_chart, ratios_table_html,
    _CATEGORIE_CONTROLE, _ORDRE_CATEGORIES,
)

from src.extraction.service import ExtractionService
from src.extraction.excel_parser import detecter_documents
from src.extraction.controle_extraction import scorer_extraction
from src.analysis.agregats import Agregats
from src.analysis.ratios import Ratios
from src.scoring.score import Scorer, PROFILS, load_config, load_profils
from src.scoring.modes import (
    MODE_TENDANCE, MODE_MOYENNE, LABELS_MODES,
    ratios_moyens, ajustement_tendance,
)
from src.analysis.validator import Validator
from src.analysis.filter_ratios import filter_ratios, MIN_EXERCICES_ANALYSE, MAX_EXERCICES_ANALYSE
from src.analysis.historique import calculer_historique
from src.scoring.sector_scorer import SectorScorer, detect_secteur, load_secteurs
from src.visualization.charts import (
    evolution_indicateurs_unifie, comparaison_n_n1,
)
from src.reporting.pdf_report import generate_pdf_report
from src.scoring.alerts import detect_alerts
from src.analysis.historique import (
    calculer_croissance, scinder_exercices, fusionner_exercice,
)

PROFILS_EFFECTIFS = {}


def _initialiser_session():
    """Etat Streamlit par defaut (config, profils disponibles)."""
    if "analyse_faite" not in st.session_state:
        st.session_state.analyse_faite = False
    try:
        st.session_state.config_yaml = load_config()
    except Exception:
        st.session_state.config_yaml = {"poids_categories": {}}
    try:
        st.session_state.profils_dispo = load_profils()
    except Exception:
        st.session_state.profils_dispo = PROFILS

    global PROFILS_EFFECTIFS
    PROFILS_EFFECTIFS = st.session_state.get("profils_dispo", PROFILS)


def _score_resultat(profil_courant="moyen_terme"):
    """Calcule le score courant (sectoriel si secteur connu, sinon standard).

    Lecture pure de session_state : appele a la fin de l'import (pour
    que l'en-tete dispose du resultat des le premier rendu suivant
    l'analyse) puis a chaque rendu de la section Resultats, ou les
    options de secteur et de profil de l'utilisateur s'appliquent.
    """
    secteurs_dispo = {}
    try:
        secteurs_dispo = load_secteurs()
    except Exception:
        pass

    secteur_sel = st.session_state.get("secteur_sel", "Detection automatique")
    code_naf = st.session_state.get("naf_input", "")
    secteur_code = None
    secteur_label = None

    if secteur_sel and secteur_sel != "Detection automatique":
        for code, info in secteurs_dispo.items():
            if info.get("label") == secteur_sel:
                secteur_code = code
                secteur_label = info["label"]
                break
    elif code_naf:
        secteur_code = detect_secteur(code_naf)
        if secteur_code:
            secteur_label = secteurs_dispo.get(secteur_code, {}).get("label")
    elif st.session_state.get("secteur_auto_code"):
        secteur_code = st.session_state["secteur_auto_code"]
        secteur_label = secteurs_dispo.get(secteur_code, {}).get("label")

    # Base du score (Options) : exercice N + ajustement de tendance
    # (defaut) ou moyenne des exercices. Le meme moteur et la meme
    # configuration : seul le jeu de valeurs change.
    base_sel = st.session_state.get("score_base_sel",
                                    LABELS_MODES[MODE_TENDANCE])
    mode = (MODE_MOYENNE if base_sel == LABELS_MODES[MODE_MOYENNE]
            else MODE_TENDANCE)
    ratios_base = st.session_state.ratios
    if mode == MODE_MOYENNE:
        ratios_base = ratios_moyens(
            st.session_state.ratios,
            st.session_state.get("historique") or {})

    methode = "standard"
    res = None

    if secteur_code:
        try:
            _sector = SectorScorer(ratios_base, secteur=secteur_code)
            # Concordance avec le scoring standard : le score sectoriel
            # utilise les poids de categories du profil d'analyse configure
            _poids_profil = ((PROFILS_EFFECTIFS.get(profil_courant) or {})
                             .get("poids_categories")) or {}
            res = _sector.compute_scores_by_category(
                st.session_state.config_yaml,
                poids_categories=_poids_profil)
            if res.get("score_global", 0) > 0:
                methode = "sectorielle"
            else:
                res = None
        except Exception:
            res = None

    if res is None:
        try:
            res = Scorer(ratios_base, profil=profil_courant).compute_all()
        except Exception:
            res = Scorer(ratios_base,
                         profil="moyen_terme").compute_all()
        methode = "standard"

    # Mode tendance : ajustement borne par la trajectoire des ratios
    # (N vs moyenne des exercices), scores recalculent avec les poids
    # du profil - meme pondereage que le scoring standard.
    if mode == MODE_TENDANCE:
        _poids_tend = ((PROFILS_EFFECTIFS.get(profil_courant) or {})
                       .get("poids_categories")) or {}
        res = ajustement_tendance(
            res, st.session_state.get("historique") or {},
            st.session_state.config_yaml, _poids_tend)
    res["base_scoring"] = mode

    res["methode"] = methode
    res["secteur_code"] = secteur_code
    res["secteur_label"] = secteur_label
    return res


# ============================================================
# 4. EN-TETE (rendu a chaque affichage)
# ============================================================
def _entete():
    """Bandeau titre + Options + bouton PDF : au-dessus du contenu."""
    h_left, h_opts, h_pdf = st.columns([5.2, 1.3, 2.5], vertical_alignment="center")
    with h_left:
        st.markdown("<h1>FinView</h1>", unsafe_allow_html=True)
        if st.session_state.analyse_faite:
            nom = st.session_state.get("nom_entreprise", "")
            secteur_label = st.session_state.get("secteur_auto_label")
            meta = nom
            if secteur_label:
                meta += f" &middot; Secteur : <b>{secteur_label}</b>"
            st.markdown(f"<div class='sub'>{meta}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='sub'>Deposez les documents d'au moins trois exercices complets (huit maximum) pour obtenir un score detaille.</div>",
                        unsafe_allow_html=True)

    with h_opts:
        with st.popover("Options", use_container_width=True):
            try:
                secteurs = load_secteurs()
                opts = ["Detection automatique"] + [i["label"] for i in secteurs.values()]
            except Exception:
                opts = ["Detection automatique"]
            st.selectbox("Secteur", opts, key="secteur_sel")
            st.text_input("Code NAF / APE", placeholder="Ex : 41.20A", key="naf_input")
            if st.session_state.get("naf_auto"):
                st.caption(f"Détecté dans le document : {st.session_state.naf_auto}"
                           + (f" ({st.session_state.secteur_auto_label})"
                              if st.session_state.get("secteur_auto_label") else ""))
            if st.session_state.analyse_faite:
                try:
                    keys = list(PROFILS_EFFECTIFS.keys())
                    idx = keys.index("moyen_terme") if "moyen_terme" in keys else 0
                    profil = st.selectbox("Profil d'analyse", keys, index=idx,
                                          format_func=lambda x: PROFILS_EFFECTIFS[x].get("label", x))
                except Exception:
                    profil = "moyen_terme"
                st.selectbox("Base du score",
                             list(LABELS_MODES.values()),
                             index=0, key="score_base_sel",
                             help="Dernière année + tendance : le score porte sur "
                                  "l'exercice N, ajusté par la trajectoire des ratios "
                                  "(N comparé à la moyenne des exercices, ±5 pts par "
                                  "catégorie). Moyenne des exercices : le score porte "
                                  "sur la valeur moyenne de chaque ratio.")

    with h_pdf:
        # Garde : au premier rendu qui suit l'analyse, "result" n'existe pas
        # encore (il est calcule plus bas, section Resultats) - aucun
        # bouton ce tour-ci, sans faire planter la page.
        if st.session_state.analyse_faite and st.session_state.get("result") is not None:
            # Telechargement en un clic : le PDF est calcule une seule fois
            # par configuration (signature des donnees + profil), puis cache
            import hashlib
            import json as _json

            try:
                _poids_pdf = ((PROFILS_EFFECTIFS.get(profil) or {})
                              .get("poids_categories")) or {}
            except Exception:
                _poids_pdf = {}

            # Medianes du secteur detecte (alignement PDF/dashboard : la
            # colonne "Med. secteur" existe dans les deux)
            _medianes_pdf = {}
            _code_sect_pdf = ((st.session_state.result or {}).get("secteur_code"))
            if _code_sect_pdf:
                try:
                    from src.scoring.sector_scorer import load_secteurs as _ls
                    _cfg_sect_pdf = (_ls().get(_code_sect_pdf) or {})
                    _medianes_pdf = {
                        n: (r or {}).get("mediane")
                        for n, r in (_cfg_sect_pdf.get("ratios") or {}).items()
                    }
                except Exception:
                    _medianes_pdf = {}

            # Integralite des ratios configures : le tableau de detail du
            # PDF affiche toutes les lignes comme le dashboard (n/d si non note)
            _config_ratios_pdf = {}
            try:
                _cy = st.session_state.get("config_yaml") or {}
                for _cat, _info in (_cy.get("categories") or {}).items():
                    for _nom in (_info.get("ratios_actifs") or []):
                        _config_ratios_pdf[_nom] = {
                            "categorie": _cat,
                            "poids": ((_cy.get(_cat) or {}).get(_nom) or {}).get("poids", 0),
                        }
            except Exception:
                _config_ratios_pdf = {}

            # agregats par exercice : base de comparaison du mode moyenne
            # (indicateurs cles du PDF) et element de la signature du cache
            _bilans_ch = st.session_state.get("bilans_data", [])
            _exs_ch = st.session_state.get("exercices", [])
            _agg_ex_charge = {}
            for _i, _bd in enumerate(_bilans_ch):
                try:
                    _an = (str(_exs_ch[_i].get("annee", f"N-{_i}"))
                           if _i < len(_exs_ch) else f"N-{_i}")
                    _agg_ex_charge[_an] = Agregats(_bd).compute_all()
                except Exception:
                    pass

            _charge = {
                "result": st.session_state.result,
                "agregats": st.session_state.agregats,
                "validation": st.session_state.validation,
                "alertes": st.session_state.alertes,
                "nom": st.session_state.get("nom_entreprise"),
                "secteur": (st.session_state.result or {}).get("secteur_label"),
                "n_bilans": len(st.session_state.get("bilans_data", [])),
                "poids": _poids_pdf,
                # moyennes multi-exercices affichees dans le detail des
                # ratios : une donnee qui change doit invalider le cache
                "historique": st.session_state.get("historique", {}),
                # medianes du secteur (colonne "Med. secteur" du PDF)
                "medianes_secteur": _medianes_pdf,
                # integralite des ratios configures au detail
                "config_ratios": _config_ratios_pdf,
                # agregats par exercice : comparaison du mode moyenne
                "agregats_exercices": _agg_ex_charge,
                # toute modification du code du rapport invalide le PDF en
                # cache : on ne doit jamais re-servir un rapport obsolete
                "rapport_mtime": max(
                    int(Path(str(ROOT / "src" / "reporting" / f)).stat().st_mtime)
                    for f in ("pdf_report.py", "synthese.py", "charts_pdf.py",
                              "glossaire.py")),
            }
            _sig = hashlib.sha256(
                _json.dumps(_charge, sort_keys=True, default=str,
                            ensure_ascii=False).encode()).hexdigest()[:16]

            _cache = st.session_state.get("pdf_cache") or {}
            if _cache.get("sig") != _sig:
                try:
                    _bilans = st.session_state.get("bilans_data", [])
                    _agg_n1 = (Agregats(_bilans[1]).compute_all()
                               if len(_bilans) >= 2 else None)
                    _cache = {"sig": _sig, "bytes": generate_pdf_report(
                        result=st.session_state.result,
                        agregats=st.session_state.agregats,
                        agregats_n1=_agg_n1,
                        validation=st.session_state.validation,
                        alertes=st.session_state.alertes,
                        company_name=(st.session_state.get("nom_entreprise")
                                      or "Entreprise analysee"),
                        secteur_label=(st.session_state.result or {}).get("secteur_label"),
                        poids_categories=_poids_pdf,
                        historique=st.session_state.get("historique", {}),
                        medianes_secteur=_medianes_pdf,
                        config_ratios=_config_ratios_pdf,
                        agregats_exercices=_agg_ex_charge,
                    )}
                    st.session_state.pdf_cache = _cache
                except Exception as e:
                    st.error(f"L'export a echoue : {e}")
                    _cache = {"sig": _sig, "bytes": None}
                    st.session_state.pdf_cache = _cache
            if _cache.get("bytes"):
                # pas de type="primary" : le style primaire de Streamlit
                # rend un indigo qui FONCE au survol - on style le bouton
                # nous-memes (accent, survol qui eclaircit)
                st.download_button(
                    "Télécharger le PDF", data=_cache["bytes"],
                    file_name="Rapport_Financier.pdf", mime="application/pdf",
                    use_container_width=True)


def _zone_import():
    """Accueil (hero) + televersement ; retourne les fichiers ou None."""
    zone = st.expander("Remplacer les documents") if st.session_state.analyse_faite else st.container()
    with zone:
        if not st.session_state.analyse_faite:
            st.markdown("""
    <div class="hero">
      <div class="hero-t">Analysez la sante financiere d'une entreprise</div>
      <div class="hero-s">Deposez trois exercices complets minimum, huit maximum (bilan et compte de resultat, PDF, image ou Excel) : extraction, ratios et score sont calcules automatiquement.</div>
      <div class="steps">
        <div class="step">
          <span class="step-n">1</span>
          <b>Deposez vos documents</b>
          <span class="step-s">Liasse fiscale, bilan et compte de resultat, PDF natif ou scanne, JPG, PNG ou Excel (.xlsx). Trois exercices complets minimum, huit maximum : un exercice = bilan (actif + passif) + compte de resultat.</span>
        </div>
        <div class="step">
          <span class="step-n">2</span>
          <b>Extraction automatique</b>
          <span class="step-s">Postes normalises au PCG, controles de coherence comptable et detection du secteur via le code NAF.</span>
        </div>
        <div class="step">
          <span class="step-n">3</span>
          <b>Score et vigilances</b>
          <span class="step-s">Scoring sectoriel, ratios detailles, points de vigilance et rapport PDF exportable.</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
            st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        fichiers = st.file_uploader(
            "Documents comptables (PDF, JPG, PNG ou Excel .xlsx)",
            type=["pdf", "jpg", "jpeg", "png", "xlsx", "xlsm"],
            accept_multiple_files=True, key="docs",
            label_visibility="visible" if not st.session_state.analyse_faite else "collapsed",
        )
    return fichiers


def executer_analyse(fichiers):
    """Extraction, fusion des exercices, controles de qualite."""
    files_sig = "|".join(sorted(f.name for f in fichiers))
    if st.session_state.get("files_sig") != files_sig:
        with st.status("Analyse des documents en cours...", expanded=True) as status:
            tmpdir = Path(tempfile.mkdtemp())
            paths = []
            for f in fichiers:
                p = tmpdir / f.name
                p.write_bytes(f.read())
                paths.append(str(p))

            service = ExtractionService()

            def _annee_fichier(nom):
                m = re.search(r"(20\d{2})", nom)
                return int(m.group(1)) if m else None

            # Du plus recent au plus ancien (annee dans le nom de fichier)
            fichiers_tri = sorted(zip(fichiers, paths),
                                  key=lambda x: _annee_fichier(x[0].name) or 0,
                                  reverse=True)

            extraits = []      # (nom, data_n, data_n1, annee, meta)
            controles = []
            erreurs = []

            for f, p in fichiers_tri:
                st.write(f"Extraction : {f.name}")
                try:
                    extrait = service.extraire(p)
                except Exception as e:
                    erreurs.append(f"{f.name} : {e}")
                    continue

                data_n, data_n1 = scinder_exercices(extrait.data)
                controles.append((f.name, scorer_extraction(data_n, extrait.source)))
                annee = _annee_fichier(f.name) or extrait.meta.get("annee_n")
                extraits.append((f.name, data_n, data_n1, annee, extrait.meta))

            # Fusion par exercice : les donnees N (directes) priment sur les N-1
            par_annee = {}
            for direct in (True, False):
                for nom, data_n, data_n1, annee, meta in extraits:
                    if direct:
                        cle = annee if annee else "N"
                        data = data_n
                    else:
                        cle = (annee - 1) if annee else "N-1"
                        data = data_n1
                    fusionner_exercice(par_annee, cle, data)

            # Annees numeriques du plus recent au plus ancien, puis libelles (N, N-1)
            cles = (sorted([c for c in par_annee if isinstance(c, int)], reverse=True)
                    + [c for c in par_annee if not isinstance(c, int)])
            bilans_data = [par_annee[c] for c in cles]
            exercices = [{"path": None, "nom": str(c), "type": "docai", "annee": c}
                         for c in cles]

            if controles:
                non_ok = [(n, c) for n, c in controles if c.statut != "ok"]
                for n, c in non_ok:
                    msg = c.problemes[0] if c.problemes else c.statut
                    st.warning(f"**{n}** — {c.statut} ({c.score}/100) : {msg}")
                st.session_state.controles = controles

            for e in erreurs:
                st.error(e)

            if extraits and any(a is None for _, _, _, a, _ in extraits):
                st.info("Annee non detectee dans le nom d'un fichier : "
                        "ajoutez l'annee au nom pour un historique fiable.")

            if not bilans_data:
                st.error("Aucun document exploitable apres extraction.")
                status.update(label="Echec de l'extraction", state="error")
                st.stop()

            # Porte avant analyse : de MIN_EXERCICES_ANALYSE a
            # MAX_EXERCICES_ANALYSE exercices fiscaux complets.
            # Un exercice complet = bilan (actif ET passif) + compte de
            # resultat. Les exercices incomplets (ou trop anciens) sont
            # ecartes ; sous trois complets, l'analyse est bloquee.
            def _libelle_exercice(i):
                if i < len(exercices):
                    return str(exercices[i].get("annee", f"N-{i}"))
                return f"N-{i}"

            def _manques(det):
                manq = []
                if not det["bilan"]:
                    manq.append("le bilan (actif et passif)")
                if not det["compte_resultat"]:
                    manq.append("le compte de resultat")
                return manq

            complets = []   # indices des exercices complets, du plus recent
            ecarts = []     # (libelle, raison)
            for i, bd in enumerate(bilans_data):
                det = detecter_documents(bd)
                if det["complet"]:
                    complets.append(i)
                else:
                    manq = _manques(det)
                    ecarts.append((_libelle_exercice(i),
                                   " et ".join(manq) + " manquant"
                                   + ("s" if len(manq) > 1 else "")))

            if len(complets) < MIN_EXERCICES_ANALYSE:
                st.error(f"Analyse impossible : il faut au minimum "
                         f"{MIN_EXERCICES_ANALYSE} exercices complets. "
                         "Un exercice complet = un bilan (actif et passif) "
                         "+ un compte de resultat.")
                for lib, raison in ecarts:
                    st.markdown(f"- **{lib}** : {raison}")
                st.info("Deposez les documents (PDF, image ou Excel) d'au "
                        f"moins {MIN_EXERCICES_ANALYSE} exercices complets "
                        f"(maximum {MAX_EXERCICES_ANALYSE}).")
                status.update(label="Exercices insuffisants", state="error")
                st.stop()

            # Maximum : seuls les exercices les plus recents sont analyses
            if len(complets) > MAX_EXERCICES_ANALYSE:
                for i in complets[MAX_EXERCICES_ANALYSE:]:
                    ecarts.append((_libelle_exercice(i),
                                   f"au-dela des {MAX_EXERCICES_ANALYSE} "
                                   "exercices les plus recents"))
                complets = complets[:MAX_EXERCICES_ANALYSE]

            if ecarts:
                resumes = ", ".join(f"{lib} ({raison})" for lib, raison in ecarts)
                st.info(f"Exercice(s) ecarte(s) : {resumes}. L'analyse porte "
                        f"sur les {len(complets)} exercices les plus recents.")
                bilans_data = [bilans_data[i] for i in complets]
                exercices = [exercices[i] for i in complets]

            if bilans_data:
                data_n = bilans_data[0]
                agg_n = Agregats(data_n).compute_all()
                ratios = Ratios(agg_n).compute_all()

                ratios_par_annee = {}
                for i, bd in enumerate(bilans_data):
                    try:
                        annee = str(exercices[i].get("annee", f"N-{i}")) if i < len(exercices) else f"N-{i}"
                        agg_i = Agregats(bd).compute_all()
                        ratios_par_annee[annee] = Ratios(agg_i).compute_all()
                    except Exception:
                        pass

                historique = calculer_historique(ratios_par_annee)

                if len(bilans_data) >= 2:
                    agg_n1 = Agregats(bilans_data[1]).compute_all()
                    ratios["croissance"] = {
                        "croissance_ca": calculer_croissance(agg_n.get("chiffre_affaires"), agg_n1.get("chiffre_affaires")),
                        "croissance_va": calculer_croissance(agg_n.get("valeur_ajoutee"), agg_n1.get("valeur_ajoutee")),
                    }
                ratios_f = filter_ratios(ratios, len(exercices))

                # Identification de l'entreprise : meta du document le plus recent
                meta_recent = extraits[0][4] if extraits else {}
                st.session_state.nom_entreprise = (
                    meta_recent.get("raison_sociale")
                    or Path(fichiers_tri[0][0].name).stem
                )
                naf = meta_recent.get("code_naf")
                st.session_state.naf_auto = naf
                st.session_state.secteur_auto_code = detect_secteur(naf) if naf else None
                try:
                    secteurs_cfg_val = load_secteurs()
                except Exception:
                    secteurs_cfg_val = {}
                st.session_state.secteur_auto_label = (
                    secteurs_cfg_val[st.session_state.secteur_auto_code]["label"]
                    if st.session_state.secteur_auto_code else None
                )

                # Controles de coherence, sectoriels si le secteur est connu
                st.session_state.validation = Validator(
                    agg_n, ratios_f, data_n,
                    data_n1=(bilans_data[1] if len(bilans_data) > 1 else None),
                    secteur_code=st.session_state.secteur_auto_code,
                    secteurs_config=secteurs_cfg_val).validate_all()
                st.session_state.agregats = agg_n
                st.session_state.ratios = ratios_f
                # agregats N-1 pour les alertes de variation (baisse CP...)
                _agg_n1_al = (Agregats(bilans_data[1]).compute_all()
                              if len(bilans_data) > 1 else None)
                st.session_state.alertes = detect_alerts(agg_n, ratios_f,
                                                        agregats_n1=_agg_n1_al)
                st.session_state.bilans_data = bilans_data
                st.session_state.exercices = exercices
                st.session_state.ratios_par_annee = ratios_par_annee
                st.session_state.historique = historique

                st.session_state.pop("pdf_cache", None)
                st.session_state.pop("pdf_bytes", None)
                # Le score est pre-calcule ici : l'en-tete (cache PDF,
                # resume) en a besoin des le premier rendu suivant le
                # rerun, avant que la section Resultats ne s'execute.
                st.session_state.result = _score_resultat()
                st.session_state.analyse_faite = True
                st.session_state.files_sig = files_sig
            status.update(label="Analyse terminee", state="complete")
            st.rerun()



def afficher_resultats(profil):
    """Score, KPI, onglets de detail, export PDF."""
    res = _score_resultat(profil)
    methode = res.get("methode", "standard")
    secteur_code = res.get("secteur_code")
    secteur_label = res.get("secteur_label")
    st.session_state.result = res

    # referentiels sectoriels (benchmark de l'onglet Secteur)
    secteurs_dispo = {}
    try:
        secteurs_dispo = load_secteurs()
    except Exception:
        pass

    agg = st.session_state.agregats
    score = res.get("score_global", 0) or 0
    cats = res.get("scores_categories", {})
    alertes = st.session_state.alertes
    val = st.session_state.validation
    stats = val["stats"]

    # KPI : valeurs et variations selon la base du score.
    # - mode derniere annee + tendance : valeurs de N, variation N vs N-1 ;
    # - mode moyenne : VALEURS MOYENNES des exercices, variation qui
    #   situe N par rapport a cette moyenne.
    _codes_kpi = {"ca": "chiffre_affaires", "ebitda": "ebitda",
                  "rn": "resultat_net", "cp": "capitaux_propres"}
    kpi_vals = {k: agg.get(code) for k, code in _codes_kpi.items()}
    d = {k: None for k in _codes_kpi}
    kpi_suffix = "vs N-1"
    if res.get("base_scoring") == MODE_MOYENNE:
        _moy_kpi = {}
        for code in _codes_kpi.values():
            _vals = []
            for bd in st.session_state.get("bilans_data", []):
                try:
                    v = Agregats(bd).compute_all().get(code)
                except Exception:
                    v = None
                if v:
                    _vals.append(v)
            if _vals:
                _moy_kpi[code] = sum(_vals) / len(_vals)
        kpi_vals = {k: _moy_kpi.get(code, agg.get(code))
                    for k, code in _codes_kpi.items()}
        d = {k: calculer_croissance(agg.get(code), _moy_kpi.get(code))
             for k, code in _codes_kpi.items()}
        kpi_suffix = "vs moyenne"
    elif len(st.session_state.bilans_data) >= 2:
        n1 = Agregats(st.session_state.bilans_data[1]).compute_all()
        d = {
            "ca": calculer_croissance(agg.get("chiffre_affaires"), n1.get("chiffre_affaires")),
            "ebitda": calculer_croissance(agg.get("ebitda"), n1.get("ebitda")),
            "rn": calculer_croissance(agg.get("resultat_net"), n1.get("resultat_net")),
            "cp": calculer_croissance(agg.get("capitaux_propres"), n1.get("capitaux_propres")),
        }

    n_crit = sum(1 for a in alertes if a.get("niveau") == "critique")
    n_warn = sum(1 for a in alertes if a.get("niveau") == "warning")
    resume = (f"{n_crit} alerte{'s' if n_crit > 1 else ''} critique{'s' if n_crit > 1 else ''} "
              f"et {n_warn} point{'s' if n_warn > 1 else ''} d'attention." if alertes
              else "Aucun point de vigilance detecte.")

    left, right = st.columns([6, 7], gap="large", vertical_alignment="center")
    with left:
        if methode == "sectorielle" and secteur_label:
            badge = (f'<span class="badge">Score sectoriel &middot; '
                     f'{secteur_label}</span>')
        else:
            badge = ('<span class="badge neutre">Score standard &middot; '
                     'seuils fixes</span>')
        _base = res.get("base_scoring")
        if _base == MODE_MOYENNE:
            badge_base = ('<span class="badge neutre">Base : moyenne '
                          'des exercices</span>')
        else:
            badge_base = ('<span class="badge neutre">Base : exercice N '
                          '+ tendance</span>')
        st.markdown(
            f'<div class="ring-wrap">{score_ring(score)}<div>'
            f'{badge}{badge_base}'
            f'<div class="verdict" style="color:{score_color(score)}">{verdict(score)}</div>'
            f'<div class="verdict-sub">{resume}</div>'
            f'</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            '<div class="kpi-grid">'
            + kpi("Chiffre d'affaires", kpi_vals["ca"], d["ca"], kpi_suffix)
            + kpi("EBITDA", kpi_vals["ebitda"], d["ebitda"], kpi_suffix)
            + kpi("Resultat net", kpi_vals["rn"], d["rn"], kpi_suffix)
            + kpi("Capitaux propres", kpi_vals["cp"], d["cp"], kpi_suffix)
            + "</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    tab_syn, tab_rat, tab_ctl = st.tabs(["Synthese", "Ratios", "Controles"])

    with tab_syn:
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            st.markdown('<div class="section-t">Score par categorie</div>', unsafe_allow_html=True)
            st.markdown(category_rows(cats), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="section-t">Profil de risque</div>', unsafe_allow_html=True)
            fig_radar = radar_chart(cats)
            if fig_radar:
                st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="section-t">Ce qui construit le score</div>', unsafe_allow_html=True)
        try:
            poids = PROFILS_EFFECTIFS[profil].get("poids_categories") or PROFILS_EFFECTIFS[profil].get("poids", {})
        except Exception:
            poids = {}
        # medianes du secteur : enrichissent le survol du treemap
        _medianes_syn = {}
        if secteur_code:
            _cfg_sect_syn = (secteurs_dispo.get(secteur_code) or {})
            _medianes_syn = {
                n: (r or {}).get("mediane")
                for n, r in (_cfg_sect_syn.get("ratios") or {}).items()
            }
        fig_contrib = contribution_chart(cats, poids, res.get("details", {}),
                                         medianes=_medianes_syn)
        if fig_contrib:
            st.plotly_chart(fig_contrib, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='sub'>Chaque tuile est un ratio : sa surface est "
                "proportionnelle a sa contribution au score global (score du "
                "ratio x poids dans la categorie x poids de la categorie dans "
                "le profil). Chaque categorie garde sa couleur habituelle ; "
                "l'intensite de la tuile traduit le niveau du ratio (pale = "
                "faible, soutenue = solide). Survolez pour le detail.</div>",
                unsafe_allow_html=True)
        else:
            st.info("Aucun ratio score a representer pour ce profil : "
                    "verifiez les ratios actifs dans le Parametrage.")

        if len(st.session_state.get("bilans_data", [])) >= 2:
            st.markdown('<div class="section-t">Comparaison des agregats : '
                        'N, N-1 et moyenne des exercices (EUR)</div>',
                        unsafe_allow_html=True)
            try:
                agg_n1_cmp = Agregats(st.session_state.bilans_data[1]).compute_all()
                # agregats par exercice (calcules pour les courbes) ->
                # troisieme serie : moyenne de tous les exercices
                _exs_cmp = st.session_state.get("exercices", [])
                _agg_par_ex = {}
                for _i, _bd in enumerate(st.session_state.bilans_data):
                    try:
                        _an = (str(_exs_cmp[_i].get("annee", f"N-{_i}"))
                               if _i < len(_exs_cmp) else f"N-{_i}")
                        _agg_par_ex[_an] = Agregats(_bd).compute_all()
                    except Exception:
                        pass
                fig_cmp = comparaison_n_n1(agg, agg_n1_cmp,
                                           agregats_exercices=_agg_par_ex)
                if fig_cmp:
                    st.plotly_chart(fig_cmp, use_container_width=True,
                                    config={"displayModeBar": False})
                    st.markdown(
                        "<div class='sub'>La moyenne couvre tous les "
                        "exercices disponibles (N et N-1 inclus), jusqu'a "
                        "huit.</div>", unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Comparaison indisponible : {e}")

            try:
                agregats_par_annee = {}
                _exs = st.session_state.get("exercices", [])
                for i, bd in enumerate(st.session_state.bilans_data):
                    try:
                        annee = str(_exs[i].get("annee", f"N-{i}")) if i < len(_exs) else f"N-{i}"
                        agregats_par_annee[annee] = Agregats(bd).compute_all()
                    except Exception:
                        pass

                indicateurs_evo = [
                    ("chiffre_affaires", "Chiffre d'affaires"),
                    ("ebitda", "EBITDA"),
                    ("resultat_net", "Resultat net"),
                    ("capitaux_propres", "Capitaux propres"),
                    ("total_dettes", "Total dettes"),
                    ("tresorerie", "Tresorerie"),
                ]
                # UN SEUL graphique : une couleur par indicateur, survol
                # unifie, legende cliquable, boutons Valeurs / Base 100
                fig_evo = evolution_indicateurs_unifie(
                    agregats_par_annee, indicateurs_evo)
                if fig_evo:
                    st.plotly_chart(fig_evo, use_container_width=True,
                                    config={"displayModeBar": False})
                    st.markdown(
                        "<div class='sub'>Une couleur par indicateur. "
                        "Survolez un exercice : toutes les valeurs "
                        "s'affichent ensemble ; cliquez un indicateur "
                        "dans la legende pour l'isoler ; basculez en "
                        "base 100 pour comparer des montants d'echelles "
                        "differentes.</div>",
                        unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Evolution indisponible : {e}")

    with tab_rat:
        details = res.get("details", {})
        historique = st.session_state.get("historique", {})

        # Medianes du secteur detecte : reference de comparaison de
        # chaque ratio (colonne "Med. secteur")
        medianes_sect = {}
        if secteur_code:
            try:
                _cfg_sect = (secteurs_dispo.get(secteur_code) or {})
                medianes_sect = {
                    n: (r or {}).get("mediane")
                    for n, r in (_cfg_sect.get("ratios") or {}).items()
                }
            except Exception:
                medianes_sect = {}

        if details:
            # TOUJOURS toutes les lignes configures : la vue affiche l'integralite des
            # ratios configures ; ceux non notes sur les donnees (ou
            # desactives par le secteur) apparaissent en n/d au lieu
            # de disparaitre - calcule = config = affiche
            cfg_y = st.session_state.get("config_yaml") or {}
            details_tous = dict(details)
            for cat_cfg, info_cfg in (cfg_y.get("categories") or {}).items():
                cfg_cat = cfg_y.get(cat_cfg) or {}
                for nom in (info_cfg.get("ratios_actifs") or []):
                    if nom in details_tous or nom not in cfg_cat:
                        continue
                    details_tous[nom] = {
                        "score": None, "valeur": None,
                        "poids": (cfg_cat.get(nom) or {}).get("poids", 0),
                        "categorie": cat_cfg,
                    }
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                _cats_rat = sorted({label(det.get("categorie", "autre"))
                                    for det in details_tous.values()})
                choix = st.selectbox("Categorie", ["Toutes"] + _cats_rat)
            with col_f2:
                filtre_type = st.selectbox("Type", ["Tous", "flux", "stock"])
            _html_tbl = ratios_table_html(details_tous, historique,
                                          cats_scores=cats,
                                          filtre_cat=choix,
                                          filtre_type=filtre_type,
                                          medianes=medianes_sect,
                                          valeur_label=(
                                              "Valeur (moy.)"
                                              if res.get("base_scoring") == MODE_MOYENNE
                                              else "Valeur N"))
            if _html_tbl:
                st.markdown(_html_tbl, unsafe_allow_html=True)
            else:
                st.info("Aucun ratio score pour ces filtres.")
        else:
            st.info("Aucun ratio score pour ce profil : verifiez les "
                    "ratios actifs dans le Parametrage.")

    with tab_ctl:
        # 1. Fiabilite des donnees : bandeau de compteurs en tete
        st.markdown('<div class="section-t">Fiabilit&eacute; des donn&eacute;es</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<span class="stat"><b style="color:{T["ok"]}">{stats["succes"]}/{stats["total"]}</b><span>Controles reussis</span></span>'
            f'<span class="stat"><b style="color:{T["warn"]}">{stats["avertissements"]}</b><span>Vigilances</span></span>'
            f'<span class="stat"><b style="color:{T["bad"]}">{stats["erreurs"]}</b><span>Incoherences</span></span>',
            unsafe_allow_html=True)

        if stats.get("erreurs"):
            st.markdown(
                f'<div class="alert"><span class="dot" style="background:{T["bad"]}"></span>'
                '<div><div class="alert-lvl">Incoherences detectees</div>'
                f'{stats["erreurs"]} controle(s) en erreur : les valeurs '
                'concernees sont identifiees ci-dessous et doivent etre '
                'verifiees avant d\'exploiter le rapport.</div></div>',
                unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # 2. Points de vigilance : alertes en pleine largeur
        st.markdown('<div class="section-t">Points de vigilance</div>', unsafe_allow_html=True)
        if not alertes:
            st.markdown(f'<div class="alert"><span class="dot" style="background:{T["ok"]}"></span>'
                        'Aucun risque critique identifie.</div>', unsafe_allow_html=True)
        else:
            lv = {"critique": (T["bad"], "Critique"), "warning": (T["warn"], "Attention")}
            html = ""
            for a in alertes:
                col, name = lv.get(a.get("niveau"), (T["accent"], "Information"))
                html += (f'<div class="alert"><span class="dot" style="background:{col}"></span>'
                         f'<div><div class="alert-lvl">{name}</div>{a["message"]}</div></div>')
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # --- controles regroupes par CATEGORIE DE TEST, PLEINE LARGEUR
        #     (hors des deux colonnes du haut : rien ne s'entasse d'un cote) ---
        niveaux_ctl = {
            "OK": (T["ok"], "Reussi"),
            "WARN": (T["warn"], "Vigilance"),
            "ERREUR": (T["bad"], "Incoherence"),
        }
        groupes = {}
        for item in val["rapport"]:
            m = re.match(r"(\d+)\.", item.get("test", ""))
            num = int(m.group(1)) if m else 999
            cat = _CATEGORIE_CONTROLE.get(num, "Autres controles")
            groupes.setdefault(cat, []).append(item)

        def _tint_ctl(hexc):
            return (f"color:{hexc};background:{hexc}1A")

        html_ctl = ""
        for cat in [c for c in _ORDRE_CATEGORIES if c in groupes] + \
                   [c for c in groupes if c not in _ORDRE_CATEGORIES]:
            items = groupes[cat]
            n_warn = sum(1 for i in items if i.get("niveau") == "WARN")
            n_err = sum(1 for i in items if i.get("niveau") == "ERREUR")
            if n_err:
                sum_col, sum_txt = T["bad"], f"{n_err} incoherence{'s' if n_err > 1 else ''}"
            elif n_warn:
                sum_col, sum_txt = T["warn"], f"{n_warn} vigilance{'s' if n_warn > 1 else ''}"
            else:
                sum_col, sum_txt = T["ok"], "tous reussis"
            html_ctl += (f'<div class="ctl-wrap">'
                         f'<div class="ctl-cat"><span>{cat}</span>'
                         f'<span class="ctl-sum" style="color:{sum_col}">{sum_txt}</span></div>')
            for item in items:
                col, badge = niveaux_ctl.get(item.get("niveau"),
                                             (T["muted"], "Info"))
                det = item.get("details") or ""
                det_html = f'<div class="ctl-m">{det}</div>' if det else ""
                html_ctl += (f'<div class="ctl-row">'
                             f'<span class="ctl-badge" style="{_tint_ctl(col)}">{badge}</span>'
                             f'<div><div class="ctl-t">{item["test"]}</div>'
                             f'<div class="ctl-m">{item.get("message", "")}</div>'
                             f'{det_html}</div></div>')
            html_ctl += "</div>"
        if html_ctl:
            st.markdown('<div class="section-t">Controles par categorie de test</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="ctl-grid">{html_ctl}</div>',
                        unsafe_allow_html=True)



def afficher():
    """Point d'entree de la page Analyse."""
    injecter_analyse()
    _initialiser_session()
    _entete()
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    profil = "moyen_terme"
    fichiers = _zone_import()
    if fichiers:
        files_sig = "|".join(sorted(f.name for f in fichiers))
        if st.session_state.get("files_sig") != files_sig:
            executer_analyse(fichiers)
    if st.session_state.analyse_faite:
        afficher_resultats(profil)
