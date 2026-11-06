"""Calcul des ratios financiers - formules de la Banque de France.

18 ratios, 5 categories. Chaque formule reprend la definition
publiee par la Banque de France dans ses "Fascicules de resultats
sectoriels" (base FIBEN) - c'est ce qui permet de comparer chaque
ratio aux quartiles sectoriels reels publies chaque annee.

Categories :
    - croissance (2)
    - rentabilite (6)
    - gestion_activite (3)
    - endettement (4)
    - partage_valeur (3)

Approximations documentees (donnees disponibles = liasse fiscale,
sans effectif ni dividendes ni montants TTC) :
    - EBG = EBE (produits financiers d'exploitation non isoles) ;
    - CAF = resultat net + dotations ;
    - capital d'exploitation = actif immobilise + BFR (creances
      d'exploitation approximees par le total des creances) ;
    - revenus repartis = VA + subventions d'exploitation ;
    - delais calcules sur des flux HT (references BdF en TTC) ;
    - jours = 360 (convention BdF).
"""


class Ratios:
    """Calcule les ratios financiers a partir des agregats."""

    def __init__(self, agregats: dict):
        """agregats = dict issu de Agregats.compute_all()"""
        self.a = agregats
        self.resultats = {}

    def _get(self, key: str, default: float = 0.0) -> float:
        return self.a.get(key, default)

    def _div_pos(self, num: float, denom: float, default=None):
        """Division BdF : None si denominateur <= 0 ou non calculable.

        "Les ratios ne sont pas calcules pour les denominateurs
        inferieurs ou egaux a zero ou indisponibles" (fascicule).
        """
        if denom is None or denom <= 1e-9:
            return default
        return num / denom

    def _pct_pos(self, num: float, denom: float, default=None):
        """Ratio en pourcentage (denominateur strictement positif)."""
        r = self._div_pos(num, denom)
        return r * 100 if r is not None else default

    def compute_all(self) -> dict:
        """Calcule tous les ratios et les organise par categorie."""
        self.resultats = {
            "croissance": self._croissance(),
            "rentabilite": self._rentabilite(),
            "gestion_activite": self._gestion_activite(),
            "endettement": self._endettement(),
            "partage_valeur": self._partage_valeur(),
        }
        return self.resultats

    # ============================================================
    # 1. CROISSANCE (2 ratios - remplis par le dashboard N vs N-1)
    # ============================================================
    def _croissance(self) -> dict:
        """Taux de variation : (N - N-1) / N-1, en %."""
        return {
            "croissance_ca": None,    # taux de variation du CAHT
            "croissance_va": None,    # taux de variation de la VA
        }

    # ============================================================
    # 2. RENTABILITE (9 ratios)
    # ============================================================
    def _rentabilite(self) -> dict:
        va = self._get("valeur_ajoutee")
        ca = self._get("chiffre_affaires")
        production = self._get("production_exercice")
        ventes_march = self._get("ventes_marchandises")
        ebe = self._get("ebe")
        caf = self._get("caf")
        cp = self._get("capitaux_propres")
        # Capital d'exploitation = immobilisations + BFRE
        # (approximation : actif immobilise + BFR, cf. docstring module)
        capital_expl = self._get("actif_immobilise") + self._get("bfr")

        # Denominateur BdF : production + ventes de marchandises. Les
        # liasses non ventilees (CA global seul) tombent a zero : le
        # CAHT est le denominateur equivalent tant qu'il n'existe pas
        # de production stockee ni immobilisee (approximation
        # documentee).
        denom_tva = production + ventes_march
        if denom_tva <= 1e-9:
            denom_tva = ca

        return {
            # Taux de valeur ajoutee = VA / (Production + Ventes marchandises)
            "taux_valeur_ajoutee": self._pct_pos(va, denom_tva),
            # Taux de marge = EBE / VA (mesure canonique BdF/INSEE ; la
            # decomposition marge commerciale / marge industrielle
            # n'est pas retenue : souvent non calculable selon le metier)
            "taux_marge": self._pct_pos(ebe, va),
            # Taux d'excedent brut global = EBG / CAHT (EBG = EBE ici)
            "taux_excedent_brut_global": self._pct_pos(ebe, ca),
            # Rentabilite financiere des capitaux propres = CAF nette / CP
            "rentabilite_financiere_capitaux_propres": self._pct_pos(caf, cp),
            # Rentabilite brute du capital d'exploitation = EBE / capital expl.
            "rentabilite_brute_capital_exploitation": self._pct_pos(
                ebe, capital_expl),
            # Rendement du capital d'exploitation = VA / capital expl.
            "rendement_capital_exploitation": self._pct_pos(va, capital_expl),
        }

    # ============================================================
    # 3. GESTION D'ACTIVITE (3 ratios - delais en jours, /360)
    # ============================================================
    def _gestion_activite(self) -> dict:
        ca = self._get("chiffre_affaires")
        bfr = self._get("bfr")
        # Delai clients : (creances clients - avances recues) / CA
        num_dso = (self._get("creances_clients")
                   - self._get("avances_acomptes_recus"))
        # Delai fournisseurs : (dettes fourn. - avances versees) /
        # (achats et charges externes)
        num_dpo = (self._get("dettes_fournisseurs")
                   - self._get("avances_commandes"))
        achats_charges = (self._get("achats_matieres")
                          + self._get("achats_marchandises")
                          + self._get("autres_achats_charges_externes"))
        return {
            "dso": self._div_pos(num_dso * 360, ca),
            "dpo": self._div_pos(num_dpo * 360, achats_charges),
            "poids_bfr_exploitation": self._div_pos(bfr * 360, ca),
        }

    # ============================================================
    # 4. ENDETTEMENT (4 ratios)
    # ============================================================
    def _endettement(self) -> dict:
        cp = self._get("capitaux_propres")
        dettes_fin = self._get("dettes_financieres")
        tresorerie = self._get("tresorerie")
        interets = self._get("interets_charges_assimilees")
        ebe = self._get("ebe")
        return {
            # Taux brut d'endettement financier = endettement / CP
            "gearing": self._pct_pos(dettes_fin, cp),
            # Taux net d'endettement = (endettement - tresorerie active) / CP
            "dette_nette_fonds_propres": self._pct_pos(
                dettes_fin - tresorerie, cp),
            # Cout apparent de l'endettement = interets / endettement
            "cout_apparent_endettement": self._pct_pos(
                interets, dettes_fin),
            # Poids des interets sur l'EBG = interets / EBG
            "poids_interets_ebg": self._pct_pos(interets, ebe),
        }

    # ============================================================
    # 5. PARTAGE DE LA VALEUR (3 ratios)
    # ============================================================
    def _partage_valeur(self) -> dict:
        # Revenus repartis ~ VA + subventions d'exploitation
        revenus = (self._get("valeur_ajoutee")
                   + self._get("subventions_exploitation"))
        return {
            "repartition_personnel": self._pct_pos(
                self._get("charges_personnel"), revenus),
            "repartition_etat": self._pct_pos(
                self._get("impots_taxes"), revenus),
            "repartition_preteurs": self._pct_pos(
                self._get("interets_charges_assimilees"), revenus),
        }
