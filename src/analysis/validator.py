"""Validateur de coherence des donnees comptables et des ratios.

18 tests repartis en 2 niveaux :
- Niveau 1 (6) : validations de base
- Niveau 2 (12) : validations comptables
"""
from typing import Optional


class Validator:
    """Valide la coherence des donnees et des ratios."""

    def __init__(self, agregats: dict, ratios: dict, data_brute: dict = None):
        self.agregats = agregats
        self.ratios = ratios
        self.data = data_brute or {}
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
                      f"BFR > FDR : ecart structurel normal",
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
        roe = self.ratios.get("rentabilite", {}).get("roe")
        marge = self.ratios.get("rentabilite", {}).get("marge_nette")
        rotation = self.ratios.get("gestion_activite", {}).get("rotation_actif")
        # Levier Dupont = Total actif / Capitaux propres (et non Total dettes / CP)
        ta = self.agregats.get("total_actif", 0)
        cp = self.agregats.get("capitaux_propres", 0)
        if None in (roe, marge, rotation) or cp == 0 or ta == 0:
            self._add("WARN", "5. Verification Dupont", "Donnees insuffisantes")
            return
        levier_dupont = ta / cp
        # Formule : ROE = marge (deja en %) x rotation x levier
        roe_calc = marge * rotation * levier_dupont
        self._check_egalite("5. Verification Dupont", roe_calc, roe, 15.0,
                            "Dupont", "ROE")

    def _test_bornes_ratios(self):
        bornes = {
            "current_ratio": (0, 10), "quick_ratio": (0, 10), "cash_ratio": (0, 5),
            "gearing": (0, 1000), "levier_financier": (0, 2000),
            "marge_nette": (-100, 100), "marge_brute": (-100, 100),
            "roe": (-100, 200), "roa": (-50, 100),
            "dso": (0, 365), "dpo": (0, 365), "dsi": (0, 365),
            "autonomie_financiere": (-100, 100), "ratio_solvabilite": (0, 1000),
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


if __name__ == "__main__":
    from src.extraction.bilan_parser import BilanParser
    from src.analysis.agregats import Agregats
    from src.analysis.ratios import Ratios

    parser = BilanParser("data/raw/bilan_annee2.pdf")
    data = parser.parse_simple(force_ocr=False)
    parser_cr = BilanParser("data/raw/compte_resultat_annee2.pdf")
    data_cr = parser_cr.parse_simple(force_ocr=False)
    data["compte_resultat"] = data_cr.get("compte_resultat", {})

    agg = Agregats(data)
    agregats = agg.compute_all()
    r = Ratios(agregats)
    ratios = r.compute_all()

    v = Validator(agregats, ratios, data)
    rapport = v.validate_all()

    print("=" * 70)
    print("RAPPORT DE VALIDATION - 18 TESTS")
    print("=" * 70)
    print()

    for item in rapport["rapport"]:
        sym = {"OK": "[OK]  ", "WARN": "[WARN]", "ERREUR": "[ERR] "}[item["niveau"]]
        print(f"{sym} {item['test']:40s} : {item['message']}")
        if item["details"]:
            print(f"            {item['details']}")

    print()
    print("=" * 70)
    s = rapport["stats"]
    print(f"RESULTATS : {s['succes']} OK | {s['avertissements']} WARN | {s['erreurs']} ERREUR")
    print("=" * 70)
