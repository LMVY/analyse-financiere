"""Calcul des agregats intermediaires (14 blocs).

Ces agregats sont calcules UNE FOIS puis reutilises par tous les ratios.
Cela evite les incoherences entre ratios qui utilisent le meme agregat.

Reference : Plan Comptable General francais (PCG) - Soldes Intermediaires de Gestion
"""


class Agregats:
    """Calcule les agregats intermediaires a partir des postes bruts."""

    def __init__(self, data: dict):
        """data = {"actif": {...}, "passif": {...}, "compte_resultat": {...}}"""
        self.actif = data.get("actif", {})
        self.passif = data.get("passif", {})
        self.cr = data.get("compte_resultat", {})
        self.resultats = {}

    def _get(self, section: str, code: str, default: float = 0.0) -> float:
        """Recupere une valeur avec une valeur par defaut."""
        source = {"actif": self.actif, "passif": self.passif, "cr": self.cr}[section]
        return source.get(code, default)

    def compute_all(self) -> dict:
        """Calcule tous les agregats et les stocke dans self.resultats."""
        self._compute_sig()
        self._compute_structure()
        self._compute_tresorerie()
        return self.resultats

    # ============================================================
    # SOLDES INTERMEDIAIRES DE GESTION (SIG)
    # ============================================================
    def _compute_sig(self):
        # Marge commerciale
        ventes_march = self._get("cr", "ventes_marchandises")
        achats_march = self._get("cr", "achats_marchandises")
        var_stocks_march = self._get("cr", "variation_stocks_marchandises")
        self.resultats["marge_commerciale"] = ventes_march - achats_march + var_stocks_march

        # Production de l'exercice
        prod_biens = self._get("cr", "production_vendue_biens")
        prod_services = self._get("cr", "production_vendue_services")
        prod_stockee = self._get("cr", "production_stockee")
        prod_immob = self._get("cr", "production_immobilisee")
        self.resultats["production_exercice"] = (
            prod_biens + prod_services + prod_stockee + prod_immob
        )

        # Chiffre d'affaires
        ca = self._get("cr", "chiffre_affaires")
        if ca == 0:
            ca = prod_biens + prod_services + ventes_march
        self.resultats["chiffre_affaires"] = ca

        # Consommations en provenance de tiers
        achats_mat = self._get("cr", "achats_matieres")
        var_stocks_mat = self._get("cr", "variation_stocks_matieres")
        autres_achats = self._get("cr", "autres_achats_charges_externes")
        consommations = achats_mat + var_stocks_mat + autres_achats
        self.resultats["consommations_tiers"] = consommations

        # Valeur ajoutee (VA)
        # Base SIG = marge commerciale + production ; si le compte de
        # resultat ne fournit que le chiffre d'affaires global (pas de
        # ventilation ventes/production), la VA part de ce CA.
        base_sig = self.resultats["marge_commerciale"] + self.resultats["production_exercice"]
        if base_sig == 0 and ca > 0:
            base_sig = ca
        self.resultats["valeur_ajoutee"] = base_sig - consommations

        # EBE (Excedent Brut d'Exploitation)
        subventions = self._get("cr", "subventions_exploitation")
        impots_taxes = self._get("cr", "impots_taxes")

        # Charges personnel : DGFiP separe salaires et charges sociales
        charges_perso = self._get("cr", "charges_personnel")
        if charges_perso == 0:
            charges_perso = (self._get("cr", "salaires_traitements")
                             + self._get("cr", "charges_sociales"))
        self.resultats["charges_personnel"] = charges_perso

        self.resultats["ebe"] = (
            self.resultats["valeur_ajoutee"]
            + subventions
            - impots_taxes
            - charges_perso
        )

        # EBIT (Resultat d'exploitation)
        ebit = self._get("cr", "resultat_exploitation")
        self.resultats["ebit"] = ebit

        # Dotations aux amortissements
        dotations = self._get("cr", "dotations_amortissements_immob")
        dotations += self._get("cr", "dotations_depreciations_immob")
        dotations += self._get("cr", "dotations_depreciations_actif_circulant")
        dotations += self._get("cr", "dotations_provisions_risques")
        self.resultats["dotations"] = dotations

        # EBITDA
        self.resultats["ebitda"] = ebit + dotations

        # Resultat net
        self.resultats["resultat_net"] = self._get("cr", "resultat_net")

        # CAF (approximation : Resultat net + Dotations)
        self.resultats["caf"] = self.resultats["resultat_net"] + dotations

        # --- Exposer les postes bruts necessaires aux ratios ---
        for k in [
            "achats_matieres", "achats_marchandises",
            "variation_stocks_matieres", "variation_stocks_marchandises",
            "salaires_traitements", "charges_sociales",
            "interets_charges_assimilees", "charges_cessions_vmp",
            "total_charges_financieres",
            "impots_taxes", "subventions_exploitation",
            "ventes_marchandises", "production_vendue_services",
            "production_vendue_biens", "production_stockee",
            "production_immobilisee", "autres_achats_charges_externes",
        ]:
            self.resultats[k] = self._get("cr", k)

        # Achats agreges (utilises par marge_brute + DPO + DSI)
        self.resultats["achats"] = (
            self.resultats["achats_matieres"] + self.resultats["achats_marchandises"]
        )
        # Achats CONSOMMES (biens + charges externes) : denominateur des
        # durees de rotation (DPO, DSI, CCC). Une societe de services
        # n'achete presque pas de biens : ses dettes fournisseurs
        # proviennent des charges externes (sous-traitance, prestations).
        # Sans elles, le DPO explose (denominateur denombrable en
        # milliers d'euros) et le score est fausse.
        self.resultats["achats_consommes"] = (
            self.resultats["achats"] + autres_achats
        )

    # ============================================================
    # STRUCTURE FINANCIERE
    # ============================================================
    def _compute_structure(self):
        # Capitaux propres : PREFERER le total explicite s'il existe
        cp = self._get("passif", "total_capitaux_propres")

        if cp == 0:
            # Sinon, calculer par somme des composants
            capital = self._get("passif", "capital_social")
            primes = self._get("passif", "primes_emission")
            reserve_legale = self._get("passif", "reserve_legale")
            reserves_statutaires = self._get("passif", "reserves_statutaires")
            reserves_reglementees = self._get("passif", "reserves_reglementees")
            autres_reserves = self._get("passif", "autres_reserves")
            report = self._get("passif", "report_a_nouveau")
            resultat = self._get("passif", "resultat_exercice")
            subventions = self._get("passif", "subventions_investissement")
            provisions_regl = self._get("passif", "provisions_reglementees")

            cp = (
                capital + primes + reserve_legale + reserves_statutaires
                + reserves_reglementees + autres_reserves + report + resultat
                + subventions + provisions_regl
            )

        self.resultats["capitaux_propres"] = cp

        # Dettes financieres : somme des composantes (emprunts obligataires,
        # etablissements de credit, emprunts et dettes financieres divers) ;
        # le total explicite sert de repli
        dettes_fin = (self._get("passif", "dettes_financieres")
                      + self._get("passif", "emprunts_obligataires")
                      + self._get("passif", "emprunts_dettes_financieres_divers"))
        if dettes_fin == 0:
            dettes_fin = self._get("passif", "total_dettes_financieres")
        self.resultats["dettes_financieres"] = dettes_fin

        # Dettes fournisseurs
        self.resultats["dettes_fournisseurs"] = self._get("passif", "dettes_fournisseurs")

        # Total dettes : PREFERER le total explicite (code EC du DGFiP)
        total_dettes = self._get("passif", "total_dettes")
        if total_dettes == 0:
            # Sinon, calculer par somme
            dettes_codes = [
                "dettes_financieres", "total_dettes_financieres",
                "dettes_fournisseurs", "dettes_fiscales_sociales",
                "dettes_immobilisations", "autres_dettes",
                "avances_acomptes_recus", "emprunts_obligataires",
                "provisions_risques", "provisions_charges",
                "produits_constates_avance",
            ]
            for code in dettes_codes:
                total_dettes += self._get("passif", code)
        self.resultats["total_dettes"] = total_dettes

        # Capitaux employes
        self.resultats["capitaux_employes"] = cp + dettes_fin

        # Actif immobilise
        self.resultats["actif_immobilise"] = self._get("actif", "actif_immobilise")

        # Ressources stables (approximation : capitaux propres + dettes financieres)
        self.resultats["ressources_stables"] = cp + dettes_fin

        # Totaux du bilan (recuperes directement du parser). La liasse
        # fiscale n'a pas de ligne "Total stocks" ni "Total creances" :
        # a defaut de total explicite, sommer les composantes.
        self.resultats["total_actif"] = self._get("actif", "total_actif")
        self.resultats["total_passif"] = self._get("passif", "total_passif")
        self.resultats["total_stocks"] = self._get("actif", "total_stocks")
        if self.resultats["total_stocks"] == 0:
            self.resultats["total_stocks"] = (
                self._get("actif", "matieres_premieres")
                + self._get("actif", "en_cours_production_biens")
                + self._get("actif", "en_cours_production_services")
                + self._get("actif", "produits_intermediaires")
                + self._get("actif", "stocks_marchandises")
                + self._get("actif", "avances_commandes")
            )
        self.resultats["total_creances"] = self._get("actif", "total_creances")
        if self.resultats["total_creances"] == 0:
            self.resultats["total_creances"] = (
                self._get("actif", "creances_clients")
                + self._get("actif", "autres_creances")
                + self._get("actif", "creances_rattachees_participations")
            )
        self.resultats["dettes_fiscales_sociales"] = self._get("passif", "dettes_fiscales_sociales")
        # Postes bruts du bilan requis par les formules Banque de
        # France (delais de reglement, avances nettees). Les liasses
        # simplifiees ne detaille pas les creances clients : repli
        # sur le total des creances (approximation documentee).
        creances_clients = self._get("actif", "creances_clients")
        if creances_clients == 0:
            creances_clients = self._get("actif", "total_creances")
        self.resultats["creances_clients"] = creances_clients
        self.resultats["avances_commandes"] = self._get("actif", "avances_commandes")
        self.resultats["avances_acomptes_recus"] = self._get("passif", "avances_acomptes_recus")
        self.resultats["disponibilites"] = self._get("actif", "disponibilites")
        self.resultats["valeurs_mobilieres_placement"] = self._get(
            "actif", "valeurs_mobilieres_placement")
        self.resultats["actif_circulant"] = (
            self.resultats["total_stocks"]
            + self.resultats["total_creances"]
            + self._get("actif", "disponibilites")
            + self._get("actif", "valeurs_mobilieres_placement")
        )
        self.resultats["passif_circulant"] = (
            self.resultats["dettes_fournisseurs"]
            + self.resultats["dettes_fiscales_sociales"]
            + self._get("passif", "autres_dettes")
            + self._get("passif", "produits_constates_avance")
        )

        # BFR
        stocks = self.resultats["total_stocks"]
        creances = self.resultats["total_creances"]
        df = self.resultats["dettes_fournisseurs"]
        self.resultats["bfr"] = stocks + creances - df

        # FDR
        self.resultats["fdr"] = self.resultats["ressources_stables"] - self.resultats["actif_immobilise"]

        # Actif economique
        self.resultats["actif_economique"] = self.resultats["actif_immobilise"] + self.resultats["bfr"]

        # Fallback capitaux propres : Total passif - Total dettes
        if self.resultats.get("capitaux_propres", 0) == 0:
            total_passif = self._get("passif", "total_passif")
            total_dettes = self.resultats.get("total_dettes", 0)
            if total_passif > 0 and total_dettes > 0:
                self.resultats["capitaux_propres"] = total_passif - total_dettes

    # ============================================================
    # TRESORERIE
    # ============================================================
    def _compute_tresorerie(self):
        # Tresorerie
        dispo = self._get("actif", "disponibilites")
        vmp = self._get("actif", "valeurs_mobilieres_placement")
        tresorerie = dispo + vmp
        self.resultats["tresorerie"] = tresorerie

        # Tresorerie nette
        self.resultats["tresorerie_nette"] = self.resultats["fdr"] - self.resultats["bfr"]

        # Dette nette
        self.resultats["dette_nette"] = (
            self.resultats["dettes_financieres"] - tresorerie
        )
