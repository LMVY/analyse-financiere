"""Valide le resultat d'une extraction. Sert de porte AVANT les agregats.

Principes :
- Aucune dependance a Agregats (pas de risque circulaire, pas de crash en cascade).
- Retourne un statut + des raisons, pas seulement un score.
- Tous les seuils sont des constantes ajustables.
- Tolere les deux formats de donnees : {"poste": 500} et {"poste": {"valeur": 500, ...}}
  (futur modele avec provenance).
"""

from dataclasses import dataclass, field, asdict

# --------------------------------------------------------------------------
# Constantes ajustables
# --------------------------------------------------------------------------
SEUIL_ACCEPTATION = 60

POSTES_EXCELLENT = 40
POSTES_BON = 20
POSTES_MIN = 10
POINTS_POSTES_MAX = 40
POINTS_POSTES_BON = 25
POINTS_POSTES_MIN = 10

MIN_POSTES_PAR_COTE = 5
POINTS_BILAN_COMPLET = 20

ECART_OK_PCT = 1.0
ECART_TOLERE_PCT = 5.0
POINTS_EQUILIBRE_OK = 30
POINTS_EQUILIBRE_TOLERE = 15

MIN_POSTES_CR = 3
POINTS_CR_PRESENT = 10

CLES_TOTAL_ACTIF = ("total_actif", "total_general_actif", "total_actif_net", "BJ")
CLES_TOTAL_PASSIF = ("total_passif", "total_general_passif", "total_passif_net", "EE")
CLES_CA = ("chiffre_affaires", "chiffre_affaires_net", "ca", "FL")


@dataclass
class ResultatValidation:
    score: int = 0
    statut: str = "vide"
    acceptable: bool = False
    problemes: list = field(default_factory=list)
    avertissements: list = field(default_factory=list)
    nb_postes: int = 0
    nb_actif: int = 0
    nb_passif: int = 0
    nb_cr: int = 0
    equilibre_ecart_pct: float | None = None
    equilibre_methode: str | None = None

    def to_dict(self):
        return asdict(self)


def _val(x):
    if isinstance(x, dict):
        x = x.get("valeur")
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _section(data, nom):
    sec = data.get(nom) if isinstance(data, dict) else None
    return sec if isinstance(sec, dict) else {}


def _chercher(section, cles):
    for c in cles:
        if c in section:
            v = _val(section[c])
            if v is not None:
                return v
    return None


def _somme_postes(section, cles_total):
    total = 0.0
    n = 0
    for k, v in section.items():
        if k in cles_total or str(k).lower().startswith("total"):
            continue
        x = _val(v)
        if x is not None:
            total += x
            n += 1
    return total if n else None


def _calcul_equilibre(actif, passif):
    ta = _chercher(actif, CLES_TOTAL_ACTIF)
    tp = _chercher(passif, CLES_TOTAL_PASSIF)
    methode = "totaux"
    if ta is None or tp is None:
        ta = _somme_postes(actif, CLES_TOTAL_ACTIF)
        tp = _somme_postes(passif, CLES_TOTAL_PASSIF)
        methode = "somme_postes"
    if not ta or not tp:
        return None, None
    ecart = abs(ta - tp) / max(abs(ta), abs(tp)) * 100
    return ecart, methode


def scorer_extraction(data, parser_utilise: str = "") -> ResultatValidation:
    r = ResultatValidation()

    if not data or not isinstance(data, dict):
        r.problemes.append("Resultat vide ou invalide")
        return r

    actif = _section(data, "actif")
    passif = _section(data, "passif")
    cr = _section(data, "compte_resultat")

    r.nb_actif, r.nb_passif, r.nb_cr = len(actif), len(passif), len(cr)
    r.nb_postes = r.nb_actif + r.nb_passif + r.nb_cr

    if r.nb_postes == 0:
        r.problemes.append("Aucun poste extrait")
        return r

    if r.nb_postes >= POSTES_EXCELLENT:
        r.score += POINTS_POSTES_MAX
    elif r.nb_postes >= POSTES_BON:
        r.score += POINTS_POSTES_BON
    elif r.nb_postes >= POSTES_MIN:
        r.score += POINTS_POSTES_MIN
    else:
        r.problemes.append(f"Trop peu de postes ({r.nb_postes})")

    bilan_complet = r.nb_actif >= MIN_POSTES_PAR_COTE and r.nb_passif >= MIN_POSTES_PAR_COTE
    if bilan_complet:
        r.score += POINTS_BILAN_COMPLET
    else:
        r.problemes.append(f"Bilan incomplet (actif={r.nb_actif}, passif={r.nb_passif})")

    desequilibre = False
    ecart, methode = _calcul_equilibre(actif, passif)
    r.equilibre_ecart_pct, r.equilibre_methode = ecart, methode
    if ecart is None:
        r.problemes.append("Equilibre non verifiable")
    elif ecart < ECART_OK_PCT:
        r.score += POINTS_EQUILIBRE_OK
    elif ecart < ECART_TOLERE_PCT:
        r.score += POINTS_EQUILIBRE_TOLERE
    else:
        desequilibre = True
        r.problemes.append(f"Bilan desequilibre ({ecart:.1f} %)")
    if methode == "somme_postes":
        r.avertissements.append("Equilibre estime par somme des postes")

    if r.nb_cr >= MIN_POSTES_CR:
        r.score += POINTS_CR_PRESENT
        ca = _chercher(cr, CLES_CA)
        if not ca:
            r.avertissements.append("CA nul ou absent (normal pour holding/SCI)")
    else:
        r.problemes.append(f"Compte de resultat absent ({r.nb_cr} postes)")

    if r.nb_postes < POSTES_MIN or not bilan_complet:
        r.statut = "incomplet"
    elif desequilibre:
        r.statut = "desequilibre"
    else:
        r.statut = "ok"

    r.acceptable = r.statut == "ok" and r.score >= SEUIL_ACCEPTATION
    return r
