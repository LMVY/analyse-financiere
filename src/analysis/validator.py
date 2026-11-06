"""Validateur de coherence des donnees comptables et des ratios.

39 tests repartis en 6 niveaux :
- Niveau 1 (6) : validations de base ;
- Niveau 2 (12) : validations comptables ;
- Niveau 2b (4) : coherence economique (ordre des marges, EBITDA vs CA,
  resultat net vs EBITDA, VA vs CA) ;
- Niveau 2c (10) : controles complementaires (equilibre N-1, structure de
  l'actif, details des totaux du passif, chaine du resultat, signes,
  continuite N vs N-1) ;
- Niveau 2d (4) : controles d'enrichissement (charges sociales,
  dotations, FDR, couverture des interets, position vs mediane) ;
- Niveau 3 (3) : coherence sectorielle - identifie clairement, ratio par
  ratio, les valeurs incompatibles avec le secteur detecte (hors domaine
  Q1/Q3 elargi, ratios normalement non pertinents pour le secteur).

Les niveaux OK / WARN / ERREUR suivent le meme code couleur que le
reste de l'application : vert / ambre / rouge.
"""

class Validator:
    """Valide la coherence des donnees et des ratios."""

    def __init__(self, agregats: dict, ratios: dict, data_brute: dict = None,
                 secteur_code: str = None, secteurs_config: dict = None,
                 data_n1: dict = None):
        self.agregats = agregats
        self.ratios = ratios
        self.data = data_brute or {}
        self.secteur_code = secteur_code
        self.secteurs = secteurs_config or {}
        self.data_n1 = data_n1 or {}
        self.rapport = []
        self.erreurs = 0
        self.avertissements = 0
        self.succes = 0

    def _add(self, niveau, test, message, details=""):
        self.rapport.append({
            "niveau": niveau,
            "test": test,
            "message": message,
            "details": details,
        })
        if niveau == "OK":
            self.succes += 1
        elif niveau == "WARN":
            self.avertissements += 1
        elif niveau == "ERREUR":
            self.erreurs += 1

    def _check_egalite(self, nom_test, valeur1, valeur2, tolerance_pct=1.0,
                       label1="Calcule", label2="Declare"):
        """Test generique : valeur1 ≈ valeur2."""
        if valeur1 is None or valeur2 is None:
            self._add("WARN", nom_test, "Donnees manquantes")
            return
        ecart = abs(valeur1 - valeur2)
        ref = max(abs(valeur1), abs(valeur2), 1)
        pct = (ecart / ref) * 100

        if pct < tolerance_pct:
            self._add("OK", nom_test, f"{label1} = {label2} = {valeur1:,.0f}")
        elif pct < 5:
            self._add("WARN", nom_test, f"Ecart faible ({pct:.2f}%)",
                      f"{label1}={valeur1:,.0f}, {label2}={valeur2:,.0f}")
        else:
            self._add("ERREUR", nom_test, f"Ecart IMPORTANT ({pct:.2f}%)",
                      f"{label1}={valeur1:,.0f}, {label2}={valeur2:,.0f}")

    def validate_all(self) -> dict:
        # === NIVEAU 1 : BASE ===
        self._test_equilibre_bilan()
        self._test_coherence_resultat()
        self._test_coherence_ebitda()
        self._test_coherence_tresorerie()
        self._test_dupont()
        self._test_bornes_ratios()

        # === NIVEAU 2 : COMPTABLE ===
        self._test_cp_par_passif()
        self._test_cp_par_actif()
        self._test_bfr_formule()
        self._test_fdr_formule()
        self._test_tresorerie_nette_formule()
        self._test_dette_nette_formule()
        self._test_va_formule()
        self._test_ebe_formule()
        self._test_caf_formule()
        self._test_charges_personnel_va()
        self._test_variation_n_n1()
        self._test_analyse_verticale()

        # === NIVEAU 2B : COHERENCE ECONOMIQUE ===
        self._test_ordre_marges()
        self._test_ebitda_ca()
        self._test_rn_ebitda()
        self._test_va_ca()

        # === NIVEAU 2C : CONTROLES COMPLEMENTAIRES ===
        self._test_equilibre_bilan_n1()
        self._test_structure_actif()
        self._test_detail_dettes()
        self._test_detail_capitaux_propres()
        self._test_resultat_courant()
        self._test_resultat_net_chaine()
        self._test_signes_bilan()
        self._test_continuite_n_n1()
        self._test_dettes_financieres_incluses()
        self._test_capital_vs_cp()

        # === NIVEAU 2D : CONTROLES D'ENRICHISSEMENT ===
        self._test_charges_sociales_salaires()
        self._test_dotations_immobilisations()
        self._test_fdr_positif()
        self._test_couverture_interets_ebe()

        # === NIVEAU 3 : COHERENCE SECTORIELLE ===
        if self.secteur_code and self.secteurs.get(self.secteur_code):
            self._test_plausibilite_sectorielle()
            self._test_ratios_desactives()
            self._test_position_mediane_secteur()

        return {
            "rapport": self.rapport,
            "stats": {
                "succes": self.succes,
                "avertissements": self.avertissements,
                "erreurs": self.erreurs,
                "total": len(self.rapport),
            },
        }

    # ============================================================
    # NIVEAU 1 : BASE
    # ============================================================

    def _test_equilibre_bilan(self):
        ta = self.agregats.get("total_actif", 0)
        tp = self.agregats.get("total_passif", 0)
        if ta == 0 or tp == 0:
            self._add("WARN", "1. Equilibre bilan", "Total actif/passif non extrait")
            return
        self._check_egalite("1. Equilibre bilan", ta, tp, 1.0, "Actif", "Passif")

    def _test_coherence_resultat(self):
        cr = self.data.get("compte_resultat", {})
        total_produits = cr.get("total_produits", 0)
        total_charges = cr.get("total_charges", 0)
        rn = self.agregats.get("resultat_net", 0)
        if total_produits == 0 or total_charges == 0:
            self._add("WARN", "2. Coherence resultat", "Total produits/charges non extrait")
            return
        self._check_egalite("2. Coherence resultat", total_produits - total_charges, rn,
                            1.0, "Produits-Charges", "Resultat net")

    def _test_coherence_ebitda(self):
        ebitda = self.agregats.get("ebitda", 0)
        ebit = self.agregats.get("ebit", 0)
        dot = self.agregats.get("dotations", 0)
        if ebitda == 0:
            self._add("WARN", "3. Coherence EBITDA", "EBITDA non calcule")
            return
        self._check_egalite("3. Coherence EBITDA", ebit + dot, ebitda, 1.0,
                            "EBIT+Dot", "EBITDA")

    def _test_coherence_tresorerie(self):
        tn = self.agregats.get("tresorerie_nette", 0)
        treso = self.agregats.get("tresorerie", 0)
        bfr = self.agregats.get("bfr", 0)
        fdr = self.agregats.get("fdr", 0)
        if treso == 0:
            self._add("WARN", "4. Coherence tresorerie", "Tresorerie non extraite")
            return
        # Si le BFR est superieur au FDR, l'ecart est structurel (normal)
        if bfr > fdr:
            self._add("OK", "4. Coherence tresorerie",
                      "BFR > FDR : ecart structurel normal",
                      f"FDR={fdr:,.0f}, BFR={bfr:,.0f}, Treso. nette={tn:,.0f}")
            return
        ecart_pct = abs(tn - treso) / abs(treso) * 100
        if ecart_pct < 50:
            self._add("OK", "4. Coherence tresorerie",
                      f"Tresorerie nette proche de tresorerie ({ecart_pct:.1f}%)")
        else:
            self._add("WARN", "4. Coherence tresorerie",
                      f"Ecart de {ecart_pct:.1f}%",
                      f"Nette={tn:,.0f}, Tresorerie={treso:,.0f}")

    def _test_dupont(self):
        """Identite Banque de France du partage de la valeur :

        EBE = VA (+ subventions) - charges de personnel - impots et
        taxes  =>  taux de marge = 100 - part personnel - part Etat.
        Les petites divergences (transferts, subventions non prises en
        compte) sont admises.
        """
        rent = self.ratios.get("rentabilite", {})
        part = self.ratios.get("partage_valeur", {})
        taux_marge = rent.get("taux_marge")
        perso = part.get("repartition_personnel")
        etat = part.get("repartition_etat")
        if None in (taux_marge, perso, etat):
            self._add("WARN", "5. Verification partage de la valeur",
                      "Donnees insuffisantes")
            return
        attendu = 100 - perso - etat
        self._check_egalite("5. Verification partage de la valeur",
                            attendu, taux_marge, 20.0,
                            "100 - personnel - Etat", "taux de marge")

    def _test_bornes_ratios(self):
        bornes = {
            "croissance_ca": (-100, 500), "croissance_va": (-100, 500),
            "taux_valeur_ajoutee": (0, 100),
            "taux_marge": (-100, 100),
            "taux_excedent_brut_global": (-100, 100),
            "rentabilite_financiere_capitaux_propres": (-100, 300),
            "rentabilite_brute_capital_exploitation": (-100, 300),
            "rendement_capital_exploitation": (0, 1000),
            "dso": (0, 365), "dpo": (0, 365),
            "poids_bfr_exploitation": (-365, 365),
            "gearing": (0, 1000), "dette_nette_fonds_propres": (-1000, 1000),
            "cout_apparent_endettement": (0, 50), "poids_interets_ebg": (0, 500),
            "repartition_personnel": (0, 150), "repartition_etat": (0, 100),
            "repartition_preteurs": (0, 100),
        }
        anomalies = 0
        for cat, ratio_dict in self.ratios.items():
            for nom, val in ratio_dict.items():
                if val is None or nom not in bornes:
                    continue
                mini, maxi = bornes[nom]
                if val < mini or val > maxi:
                    anomalies += 1
        if anomalies == 0:
            self._add("OK", "6. Bornes des ratios", "Tous les ratios sont plausibles")
        else:
            self._add("WARN", "6. Bornes des ratios", f"{anomalies} ratios hors bornes")

    # ============================================================
    # NIVEAU 2 : COMPTABLE
    # ============================================================

    def _test_cp_par_passif(self):
        cp = self.agregats.get("capitaux_propres", 0)
        tp = self.agregats.get("total_passif", 0)
        td = self.agregats.get("total_dettes", 0)
        if tp == 0 or td == 0:
            self._add("WARN", "7. CP = Passif - Dettes", "Donnees insuffisantes")
            return
        self._check_egalite("7. CP = Passif - Dettes", tp - td, cp, 5.0,
                            "Passif-Dettes", "CP")

    def _test_cp_par_actif(self):
        cp = self.agregats.get("capitaux_propres", 0)
        ta = self.agregats.get("total_actif", 0)
        td = self.agregats.get("total_dettes", 0)
        if ta == 0 or td == 0:
            self._add("WARN", "8. CP = Actif - Dettes", "Donnees insuffisantes")
            return
        self._check_egalite("8. CP = Actif - Dettes", ta - td, cp, 5.0,
                            "Actif-Dettes", "CP")

    def _test_bfr_formule(self):
        bfr = self.agregats.get("bfr", 0)
        stocks = self.agregats.get("total_stocks", 0)
        creances = self.agregats.get("total_creances", 0)
        df = self.agregats.get("dettes_fournisseurs", 0)
        if bfr == 0:
            self._add("WARN", "9. BFR = Stocks + Creances - DF", "BFR non calcule")
            return
        self._check_egalite("9. BFR = Stocks + Creances - DF",
                            stocks + creances - df, bfr, 1.0,
                            "Stocks+Creances-DF", "BFR")

    def _test_fdr_formule(self):
        fdr = self.agregats.get("fdr", 0)
        rs = self.agregats.get("ressources_stables", 0)
        ai = self.agregats.get("actif_immobilise", 0)
        if fdr == 0:
            self._add("WARN", "10. FDR = Ressources - Actif immo", "FDR non calcule")
            return
        self._check_egalite("10. FDR = Ressources - Actif immo",
                            rs - ai, fdr, 1.0,
                            "Ressources-ActifImmo", "FDR")

    def _test_tresorerie_nette_formule(self):
        tn = self.agregats.get("tresorerie_nette", 0)
        fdr = self.agregats.get("fdr", 0)
        bfr = self.agregats.get("bfr", 0)
        if fdr == 0 and bfr == 0:
            self._add("WARN", "11. Tresorerie nette = FDR - BFR", "Donnees insuffisantes")
            return
        self._check_egalite("11. Tresorerie nette = FDR - BFR",
                            fdr - bfr, tn, 1.0, "FDR-BFR", "Treso. nette")

    def _test_dette_nette_formule(self):
        dn = self.agregats.get("dette_nette", 0)
        df = self.agregats.get("dettes_financieres", 0)
        treso = self.agregats.get("tresorerie", 0)
        if df == 0:
            self._add("WARN", "12. Dette nette = Dettes fin - Treso", "Donnees insuffisantes")
            return
        self._check_egalite("12. Dette nette = Dettes fin - Treso",
                            df - treso, dn, 1.0, "Dettes fin-Treso", "Dette nette")

    def _test_va_formule(self):
        va = self.agregats.get("valeur_ajoutee", 0)
        marge_com = self.agregats.get("marge_commerciale", 0)
        prod = self.agregats.get("production_exercice", 0)
        conso = self.agregats.get("consommations_tiers", 0)
        if va == 0:
            self._add("WARN", "13. VA = Marge com + Prod - Conso", "VA non calculee")
            return
        self._check_egalite("13. VA = Marge com + Prod - Conso",
                            marge_com + prod - conso, va, 1.0,
                            "Formule", "VA")

    def _test_ebe_formule(self):
        ebe = self.agregats.get("ebe", 0)
        va = self.agregats.get("valeur_ajoutee", 0)
        cr = self.data.get("compte_resultat", {})
        subv = cr.get("subventions_exploitation", 0)
        impots = cr.get("impots_taxes", 0)
        perso = cr.get("charges_personnel", 0)
        if ebe == 0:
            self._add("WARN", "14. EBE = VA + Subv - Impots - Perso", "EBE non calcule")
            return
        self._check_egalite("14. EBE = VA + Subv - Impots - Perso",
                            va + subv - impots - perso, ebe, 1.0,
                            "Formule", "EBE")

    def _test_caf_formule(self):
        caf = self.agregats.get("caf", 0)
        rn = self.agregats.get("resultat_net", 0)
        dot = self.agregats.get("dotations", 0)
        if caf == 0:
            self._add("WARN", "15. CAF = Resultat net + Dotations", "CAF non calculee")
            return
        self._check_egalite("15. CAF = Resultat net + Dotations",
                            rn + dot, caf, 1.0, "RN+Dot", "CAF")

    def _test_charges_personnel_va(self):
        charges_perso = self.data.get("compte_resultat", {}).get("charges_personnel", 0)
        va = self.agregats.get("valeur_ajoutee", 0)
        if va == 0:
            self._add("WARN", "16. Charges personnel / VA < 100%", "VA non calculee")
            return
        ratio = charges_perso / va * 100
        if ratio < 80:
            self._add("OK", "16. Charges personnel / VA < 100%",
                      f"Ratio sain : {ratio:.1f}%")
        elif ratio < 100:
            self._add("WARN", "16. Charges personnel / VA < 100%",
                      f"Ratio eleve : {ratio:.1f}%")
        else:
            self._add("ERREUR", "16. Charges personnel / VA < 100%",
                      f"Ratio CRITIQUE : {ratio:.1f}% (VA insuffisante)")

    def _test_variation_n_n1(self):
        """Verifie que les variations N vs N-1 ne sont pas aberrantes."""
        croissance = self.ratios.get("croissance", {})
        anomalies = 0
        for nom, val in croissance.items():
            if val is None:
                continue
            if abs(val) > 100:
                anomalies += 1

        if not croissance:
            self._add("WARN", "17. Variation N vs N-1", "Croissance non calculee")
        elif anomalies == 0:
            self._add("OK", "17. Variation N vs N-1", "Variations plausibles (< 100%)")
        else:
            self._add("WARN", "17. Variation N vs N-1",
                      f"{anomalies} variation(s) > 100%")

    def _test_analyse_verticale(self):
        """Verifie que les postes ne depassent pas le total."""
        ta = self.agregats.get("total_actif", 0)
        if ta == 0:
            self._add("WARN", "18. Analyse verticale", "Total actif non disponible")
            return

        actif = self.data.get("actif", {})
        anomalies = 0
        for code, val in actif.items():
            if val and val > ta * 1.05:
                anomalies += 1

        if anomalies == 0:
            self._add("OK", "18. Analyse verticale", "Aucun poste ne depasse le total")
        else:
            self._add("WARN", "18. Analyse verticale",
                      f"{anomalies} poste(s) depassent le total actif")

    # ============================================================
    # NIVEAU 2B : COHERENCE ECONOMIQUE
    # ============================================================

    def _val_ratio(self, nom):
        """Valeur d'un ratio, quelle que soit sa categorie."""
        for cat_dict in (self.ratios or {}).values():
            if isinstance(cat_dict, dict) and nom in cat_dict:
                return cat_dict.get(nom)
        return None

    def _test_ordre_marges(self):
        """19. Enchainement economique : CA >= VA >= EBE (aux subventions pres)."""
        ca = self.agregats.get("chiffre_affaires")
        va = self.agregats.get("valeur_ajoutee")
        ebe = self.agregats.get("ebe")
        subv = (self.data.get("compte_resultat") or {}).get(
            "subventions_exploitation") or 0
        if not ca or not va or ebe is None:
            self._add("WARN", "19. Enchainement CA, VA, EBE",
                      "Donnees insuffisantes")
            return
        anomalies = []
        if va > ca * 1.05:
            anomalies.append(f"VA ({va:,.0f}) superieure au CA ({ca:,.0f})")
        if ebe > va + subv + 0.02 * max(abs(va), 1):
            anomalies.append(
                f"EBE ({ebe:,.0f}) superieur a VA + subventions "
                f"({va + subv:,.0f})")
        if anomalies:
            self._add("WARN", "19. Enchainement CA, VA, EBE",
                      " ; ".join(anomalies),
                      "Ordre attendu : CA >= VA >= EBE (aux subventions "
                      "d'exploitation pres)")
        else:
            self._add("OK", "19. Enchainement CA, VA, EBE",
                      "CA >= VA >= EBE : enchainement coherent")

    def _test_ebitda_ca(self):
        """L'EBITDA ne peut depasser le chiffre d'affaires."""
        ca = self.agregats.get("chiffre_affaires", 0)
        eb = self.agregats.get("ebitda", 0)
        if not ca or eb == 0:
            self._add("WARN", "20. EBITDA vs CA", "Donnees insuffisantes")
            return
        marge = eb / ca * 100
        if marge > 100:
            self._add("ERREUR", "20. EBITDA vs CA",
                      f"EBITDA ({eb:,.0f}) superieur au CA ({ca:,.0f}) : "
                      "incoherence de perimetre",
                      "Verifier que l'EBITDA et le CA couvrent le meme perimetre")
        elif marge > 60:
            self._add("WARN", "20. EBITDA vs CA",
                      f"Marge EBITDA de {marge:.0f}% : atypique, verifier "
                      "le perimetre des montants extraits")
        else:
            self._add("OK", "20. EBITDA vs CA",
                      f"Marge EBITDA de {marge:.1f}% (plausible)")

    def _test_rn_ebitda(self):
        """Un resultat net tres superieur a l'EBITDA est suspect."""
        rn = self.agregats.get("resultat_net", 0)
        eb = self.agregats.get("ebitda", 0)
        if eb == 0:
            self._add("WARN", "21. Resultat net vs EBITDA", "Donnees insuffisantes")
            return
        if eb > 0 and rn > eb * 1.3:
            self._add("WARN", "21. Resultat net vs EBITDA",
                      f"Resultat net ({rn:,.0f}) tres superieur a l'EBITDA "
                      f"({eb:,.0f}) : verifier les produits exceptionnels "
                      "ou l'affectation du resultat")
        else:
            self._add("OK", "21. Resultat net vs EBITDA",
                      "Resultat net coherent avec l'EBITDA")

    def _test_va_ca(self):
        """La valeur ajoutee doit rester dans un rapport plausible au CA."""
        va = self.agregats.get("valeur_ajoutee", 0)
        ca = self.agregats.get("chiffre_affaires", 0)
        if not ca or va == 0:
            self._add("WARN", "22. VA vs CA", "Donnees insuffisantes")
            return
        taux = va / ca * 100
        if taux > 100:
            self._add("ERREUR", "22. VA vs CA",
                      f"VA ({va:,.0f}) superieure au CA ({ca:,.0f}) : "
                      "incoherence de perimetre")
        elif taux < 5:
            self._add("WARN", "22. VA vs CA",
                      f"VA = {taux:.1f}% du CA : tres faible, verifier "
                      "les consommations externes")
        else:
            self._add("OK", "22. VA vs CA",
                      f"VA = {taux:.0f}% du CA (plausible)")

    # ============================================================
    # NIVEAU 2C : CONTROLES COMPLEMENTAIRES
    # ============================================================

    def _test_equilibre_bilan_n1(self):
        """L'exercice precedent doit aussi etre equilibre."""
        if not self.data_n1:
            self._add("WARN", "23. Equilibre bilan N-1",
                      "Exercice N-1 non fourni")
            return
        ta = (self.data_n1.get("actif") or {}).get("total_actif")
        tp = (self.data_n1.get("passif") or {}).get("total_passif")
        if not ta or not tp:
            self._add("WARN", "23. Equilibre bilan N-1",
                      "Totaux N-1 non extraits")
            return
        self._check_egalite("23. Equilibre bilan N-1", ta, tp, 1.0,
                            "Actif N-1", "Passif N-1")

    def _test_structure_actif(self):
        """Actif immobilise + actif circulant = total actif."""
        a = self.data.get("actif") or {}
        ta = a.get("total_actif") or self.agregats.get("total_actif")
        circulant = a.get("total_actif_circulant")
        ai = self.agregats.get("actif_immobilise")
        if not ta or not circulant or ai is None:
            self._add("WARN", "24. Structure de l'actif",
                      "Donnees insuffisantes")
            return
        self._check_egalite("24. Structure de l'actif", ai + circulant, ta,
                            5.0, "Immo+Circulant", "Total actif")

    def _test_detail_dettes(self):
        """Somme des dettes detaillees = total des dettes.

        Inclut les avances et acomptes recus et les produits constates
        d'avance : dans la presentation fiscale comme classique, ils
        font partie du bloc des dettes.
        """
        p = self.data.get("passif") or {}
        composantes = ("dettes_financieres", "emprunts_obligataires",
                       "emprunts_dettes_financieres_divers",
                       "dettes_fournisseurs", "dettes_fiscales_sociales",
                       "dettes_immobilisations", "autres_dettes",
                       "avances_acomptes_recus", "produits_constates_avance")
        somme = sum(p.get(c) or 0 for c in composantes)
        total = p.get("total_dettes") or self.agregats.get("total_dettes")
        if not somme or not total:
            self._add("WARN", "25. Detail des dettes", "Donnees insuffisantes")
            return
        self._check_egalite("25. Detail des dettes", somme, total, 5.0,
                            "Somme detaillee", "Total dettes")

    def _test_detail_capitaux_propres(self):
        """Somme des composantes des capitaux propres = total CP."""
        p = self.data.get("passif") or {}
        composantes = ("capital_social", "primes_emission", "reserve_legale",
                       "reserves_statutaires", "reserves_reglementees",
                       "autres_reserves", "report_a_nouveau",
                       "resultat_exercice", "subventions_investissement",
                       "provisions_reglementees")
        somme = sum(p.get(c) or 0 for c in composantes)
        total = p.get("total_capitaux_propres") \
            or self.agregats.get("capitaux_propres")
        if not somme or not total:
            self._add("WARN", "26. Detail des capitaux propres",
                      "Donnees insuffisantes")
            return
        self._check_egalite("26. Detail des capitaux propres", somme, total,
                            5.0, "Somme detaillee", "Total capitaux propres")

    def _test_resultat_courant(self):
        """Resultat courant = resultat d'exploitation + resultat financier."""
        cr = self.data.get("compte_resultat") or {}
        rex = cr.get("resultat_exploitation")
        rf = cr.get("resultat_financier")
        rc = cr.get("resultat_courant")
        if None in (rex, rf, rc):
            self._add("WARN", "27. Resultat courant = REX + RF",
                      "Donnees insuffisantes")
            return
        self._check_egalite("27. Resultat courant = REX + RF", rex + rf, rc,
                            5.0, "REX+RF", "Resultat courant")

    def _test_resultat_net_chaine(self):
        """Resultat net = courant + exceptionnel - impots - participation."""
        cr = self.data.get("compte_resultat") or {}
        pieces = ("resultat_courant", "resultat_exceptionnel",
                  "impots_benefices", "participation_salaries")
        if any(cr.get(c) is None for c in pieces):
            self._add("WARN", "28. Chaine du resultat net",
                      "Donnees insuffisantes")
            return
        attendu = (cr["resultat_courant"] + cr["resultat_exceptionnel"]
                   - cr["impots_benefices"] - cr["participation_salaries"])
        self._check_egalite("28. Chaine du resultat net", attendu,
                            self.agregats.get("resultat_net"), 5.0,
                            "Courant+Excep-Impots", "Resultat net")

    def _test_signes_bilan(self):
        """Stocks, creances et tresorerie negatifs : montants aberrants."""
        a = self.data.get("actif") or {}
        negatifs = []
        for nom in ("total_stocks", "total_creances", "disponibilites",
                    "valeurs_mobilieres_placement", "immobilisations_incorporelles"):
            v = a.get(nom)
            if v is not None and v < 0:
                negatifs.append(nom.replace("_", " "))
        if not negatifs:
            self._add("OK", "29. Signes du bilan",
                      "Aucun poste d'actif negatif")
        else:
            self._add("ERREUR", "29. Signes du bilan",
                      f"{len(negatifs)} poste(s) d'actif negatif(s) : "
                      + ", ".join(negatifs),
                      "Un poste d'actif negatif est generalement un probleme "
                      "d'extraction (signe ou parenthese mal lu) ou une "
                      "provision non identifiee.")

    def _test_continuite_n_n1(self):
        """Variation du total actif entre N-1 et N : mutation de perimetre ?"""
        if not self.data_n1:
            self._add("WARN", "30. Continuite N vs N-1",
                      "Exercice N-1 non fourni")
            return
        ta_n = self.agregats.get("total_actif")
        ta_n1 = (self.data_n1.get("actif") or {}).get("total_actif")
        if not ta_n or not ta_n1:
            self._add("WARN", "30. Continuite N vs N-1", "Totaux insuffisants")
            return
        variation = (ta_n - ta_n1) / abs(ta_n1) * 100
        if abs(variation) > 200:
            self._add("WARN", "30. Continuite N vs N-1",
                      f"Total actif : {variation:+.0f} % d'une annee "
                      "sur l'autre",
                      "Variation majeure : verifier le perimetre, une "
                      "fusion/restructuration ou une erreur d'exercice.")
        else:
            self._add("OK", "30. Continuite N vs N-1",
                      f"Variation du total actif : {variation:+.0f} % "
                      "(plausible)")

    def _test_dettes_financieres_incluses(self):
        """Les dettes financieres font partie du total des dettes."""
        df = self.agregats.get("dettes_financieres")
        td = self.agregats.get("total_dettes")
        if not df or not td:
            self._add("WARN", "31. Dettes financieres incluses",
                      "Donnees insuffisantes")
            return
        if df > td * 1.02:
            self._add("ERREUR", "31. Dettes financieres incluses",
                      f"Dettes financieres ({df:,.0f}) superieures au total "
                      f"des dettes ({td:,.0f})",
                      "Le total des dettes semble incomplet ou les dettes "
                      "financieres sont double-comptees.")
        else:
            self._add("OK", "31. Dettes financieres incluses",
                      f"Dettes financieres = {df / td * 100:.0f} % du "
                      "total des dettes")

    def _test_capital_vs_cp(self):
        """Capitaux propres inferieurs au capital social : pertes accumulees."""
        p = self.data.get("passif") or {}
        capital = p.get("capital_social")
        cp = self.agregats.get("capitaux_propres")
        if not capital or cp is None:
            self._add("WARN", "32. Capital vs capitaux propres",
                      "Donnees insuffisantes")
            return
        if cp < capital * 0.5:
            self._add("WARN", "32. Capital vs capitaux propres",
                      f"Capitaux propres ({cp:,.0f}) tres inferieurs au "
                      f"capital social ({capital:,.0f})",
                      "Des pertes accumulees ou une distribution "
                      "exceptionnelle ont entame la situation nette : "
                      "point de vigilance patrimonial.")
        else:
            self._add("OK", "32. Capital vs capitaux propres",
                      "Situation nette superieure a la moitie du capital")

    # ============================================================
    # NIVEAU 2D : CONTROLES D'ENRICHISSEMENT (33-36)
    # ============================================================
    def _test_charges_sociales_salaires(self):
        """35. Charges sociales / salaires : structure usuelle 25-65 %."""
        salaires = self.agregats.get("salaires_traitements")
        charges = self.agregats.get("charges_sociales")
        if not salaires or salaires <= 0 or charges is None:
            self._add("WARN", "33. Charges sociales / salaires",
                      "Donnees manquantes")
            return
        taux = charges / salaires * 100
        if 25 <= taux <= 65:
            self._add("OK", "33. Charges sociales / salaires",
                      f"Structure usuelle ({taux:.0f} % des salaires)")
        else:
            self._add("WARN", "33. Charges sociales / salaires",
                      f"Structure atypique ({taux:.0f} % des salaires) - "
                      "verifier la ventilation salaires / charges sociales")

    def _test_dotations_immobilisations(self):
        """36. Taux d'amortissement apparent : dotations / actif immobilise."""
        dotations = self.agregats.get("dotations")
        immo = self.agregats.get("actif_immobilise")
        if not immo or immo <= 0 or dotations is None:
            self._add("WARN", "34. Dotations / actif immobilise",
                      "Donnees manquantes")
            return
        taux = dotations / immo * 100
        if 0.5 <= taux <= 40:
            self._add("OK", "34. Dotations / actif immobilise",
                      f"Taux d'amortissement plausible ({taux:.0f} %)")
        else:
            self._add("WARN", "34. Dotations / actif immobilise",
                      f"Taux d'amortissement atypique ({taux:.0f} %) - "
                      "sous-valorisation des dotations ou actif tres recent")

    def _test_fdr_positif(self):
        """37. Fonds de roulement : les ressources stables couvrent-elles
        l'actif immobilise ?"""
        fdr = self.agregats.get("fdr")
        if fdr is None:
            self._add("WARN", "35. Fonds de roulement", "Donnees manquantes")
            return
        if fdr >= 0:
            self._add("OK", "35. Fonds de roulement",
                      f"Ressources stables suffisantes (FDR = {fdr:,.0f})")
        else:
            self._add("WARN", "35. Fonds de roulement",
                      f"FDR negatif ({fdr:,.0f}) - l'actif immobilise n'est "
                      "pas couvert par les ressources stables")

    def _test_couverture_interets_ebe(self):
        """39. L'EBE couvre-t-il la charge d'interets (au moins 3 fois) ?"""
        ebe = self.agregats.get("ebe")
        interets = self.agregats.get("interets_charges_assimilees")
        if ebe is None or not interets:
            self._add("WARN", "36. Couverture des interets par l'EBE",
                      "Donnees manquantes")
            return
        couverture = ebe / interets
        if couverture >= 3:
            self._add("OK", "36. Couverture des interets par l'EBE",
                      f"Charge financiere bien couverte ({couverture:.1f}x)")
        elif couverture >= 1:
            self._add("WARN", "36. Couverture des interets par l'EBE",
                      f"Couverture juste ({couverture:.1f}x) - la marge "
                      "d'exploitation absorbe difficilement les interets")
        else:
            self._add("ERREUR", "36. Couverture des interets par l'EBE",
                      f"Interets non couverts par l'EBE ({couverture:.1f}x)")

    def _test_position_mediane_secteur(self):
        """38. Position globale vs mediane du secteur : combien de ratios
        font mieux que la moitie des entreprises du secteur ?"""
        refs = (self.secteurs.get(self.secteur_code) or {}).get("ratios") or {}
        au_dessus, total = 0, 0
        for cat, ratio_dict in self.ratios.items():
            for nom, val in ratio_dict.items():
                med = (refs.get(nom) or {}).get("mediane")
                if val is None or med is None:
                    continue
                total += 1
                # sens de lecture du ratio (baisse_bien : plus bas = mieux)
                baisse = nom in ("dso", "dpo", "poids_bfr_exploitation",
                                 "gearing", "dette_nette_fonds_propres",
                                 "cout_apparent_endettement",
                                 "poids_interets_ebg", "repartition_personnel",
                                 "repartition_etat", "repartition_preteurs")
                meilleur = val <= med if baisse else val >= med
                if meilleur:
                    au_dessus += 1
        if not total:
            self._add("WARN", "39. Position vs mediane du secteur",
                      "Aucun ratio comparable au secteur")
            return
        part = au_dessus / total * 100
        if part >= 50:
            self._add("OK", "39. Position vs mediane du secteur",
                      f"{au_dessus} ratios sur {total} font mieux que la "
                      f"mediane du secteur ({part:.0f} %)")
        else:
            self._add("WARN", "39. Position vs mediane du secteur",
                      f"Seuls {au_dessus} ratios sur {total} font mieux que "
                      f"la mediane du secteur ({part:.0f} %)")

    # ============================================================
    # NIVEAU 3 : COHERENCE SECTORIELLE
    # ============================================================

    def _test_plausibilite_sectorielle(self):
        """Identifie, ratio par ratio, les valeurs incompatibles avec le secteur.

        Une valeur situee au-dela de 2 ecarts interquartiles du domaine
        sectoriel est signalee en vigilance ; au-dela de 4, en incoherence.
        Chaque ratio en dehors du domaine genere une entree dediee :
        l'incoherence est nommee, chiffree et comparee au secteur.
        """
        info = self.secteurs.get(self.secteur_code) or {}
        label = info.get("label", self.secteur_code)
        refs = info.get("ratios") or {}
        nom_test = f"37. Plausibilite sectorielle ({label})"
        anomalies = 0

        for nom, ref in refs.items():
            val = self._val_ratio(nom)
            if val is None:
                continue
            q1, med, q3 = ref.get("q1"), ref.get("mediane"), ref.get("q3")
            if q1 is None or q3 is None:
                continue
            iqr = q3 - q1
            if iqr <= 0:
                continue
            bas, haut = q1 - 2 * iqr, q3 + 2 * iqr
            if bas <= val <= haut:
                continue
            anomalies += 1
            grave = val < q1 - 4 * iqr or val > q3 + 4 * iqr
            niveau = "ERREUR" if grave else "WARN"
            self._add(niveau, nom_test,
                      f"{nom.replace('_', ' ')} = {val:,.2f} : hors du "
                      f"domaine sectoriel [{q1:,.2f} ; {q3:,.2f}] "
                      f"(mediane {med:,.2f})",
                      f"Domaine plausible pour le secteur {label} : "
                      f"[{bas:,.2f} ; {haut:,.2f}] - Q1={q1:,.2f}, "
                      f"mediane={med:,.2f}, Q3={q3:,.2f}. Verifier la "
                      f"valeur extraite, le perimetre ou la pertinence du "
                      f"secteur detecte.")

        if anomalies == 0:
            self._add("OK", nom_test,
                      "Toutes les valeurs situees dans le domaine plausible "
                      f"du secteur {label}")

    def _test_ratios_desactives(self):
        """Signale les valeurs significatives sur des ratios non pertinents.

        Certains ratios sont desactives par secteur (ex: rotation des
        stocks pour les services) : une valeur elevee sur un de ces
        ratios indique soit une erreur d'extraction, soit un mauvais
        secteur detecte.
        """
        info = self.secteurs.get(self.secteur_code) or {}
        label = info.get("label", self.secteur_code)
        desactives = info.get("ratios_desactives") or []
        nom_test = f"38. Ratios non pertinents ({label})"
        seuils = {"dpo": 5, "dso": 5}
        anomalies = 0

        for nom in desactives:
            val = self._val_ratio(nom)
            if val is None:
                continue
            seuil = seuils.get(nom, 0.5)
            if abs(val) > seuil:
                anomalies += 1
                self._add("WARN", nom_test,
                          f"{nom.replace('_', ' ')} = {val:,.2f} alors que "
                          f"ce ratio est desactive pour le secteur {label}",
                          "Ce ratio est normalement non pertinent pour ce "
                          "secteur : verifier la detection du secteur ou "
                          "les donnees extraites.")

        if anomalies == 0:
            if desactives:
                self._add("OK", nom_test,
                          f"Aucune valeur significative sur les "
                          f"{len(desactives)} ratio(s) non pertinents du "
                          f"secteur {label}")
            else:
                self._add("OK", nom_test,
                          f"Aucun ratio desactive pour le secteur {label}")
