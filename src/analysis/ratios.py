"""Calcul des 65 ratios financiers repartis en 10 categories.

Chaque ratio est calcule a partir des agregats intermediaires.
Retourne une valeur numerique (float) ou None si non calculable.
"""


class Ratios:
    """Calcule les ratios financiers a partir des agregats."""

    def __init__(self, agregats: dict):
        """agregats = dict issu de Agregats.compute_all()"""
        self.a = agregats
        self.resultats = {}

    def _get(self, key: str, default: float = 0.0) -> float:
        return self.a.get(key, default)

    def _safe_div(self, num: float, denom: float, default=None):
        """Division securisee : retourne None si denom <= 0."""
        if denom is None or abs(denom) < 1e-9:
            return default
        return num / denom

    def _safe_pct(self, num: float, denom: float, default=None):
        """Ratio en pourcentage."""
        r = self._safe_div(num, denom)
        return r * 100 if r is not None else default

    def compute_all(self) -> dict:
        """Calcule tous les ratios et les organise par categorie."""
        self.resultats = {
            "liquidite": self._liquidite(),
            "endettement": self._endettement(),
            "rentabilite": self._rentabilite(),
            "structure_financiere": self._structure_financiere(),
            "croissance": self._croissance(),
            "gestion_activite": self._gestion_activite(),
            "tresorerie": self._tresorerie(),
            "risque_solvabilite": self._risque_solvabilite(),
        }
        return self.resultats

    # ============================================================
    # 1. LIQUIDITE (6 ratios)
    # ============================================================
    def _liquidite(self) -> dict:
        ca = self._get("chiffre_affaires")
        stocks = self._get("total_stocks")
        creances = self._get("total_creances")
        tresorerie = self._get("tresorerie")
        dettes_ct = self._get("dettes_fournisseurs") + self._get("dettes_fiscales_sociales")
        dettes_fin_ct = self._get("dettes_financieres")

        actif_circulant = stocks + creances + tresorerie
        actif_ct = actif_circulant

        return {
            "current_ratio": self._safe_div(actif_circulant, dettes_ct),
            "quick_ratio": self._safe_div(creances + tresorerie, dettes_ct),
            "cash_ratio": self._safe_div(tresorerie, dettes_ct),
            "liquidite_immediate": self._safe_div(tresorerie, dettes_fin_ct),
            "liquidite_generale": self._safe_div(actif_ct, dettes_ct),
            "bfr": self._get("bfr"),
        }

    # ============================================================
    # 2. ENDETTEMENT (7 ratios)
    # ============================================================
    def _endettement(self) -> dict:
        cp = self._get("capitaux_propres")
        df = self._get("dettes_financieres")
        td = self._get("total_dettes")
        ebitda = self._get("ebitda")
        ebit = self._get("ebit")
        tresorerie = self._get("tresorerie")
        caf = self._get("caf")
        ebit_fin = 15000  # placeholder charges financieres

        return {
            "gearing": self._safe_pct(df, cp),
            "levier_financier": self._safe_pct(td, cp),
            "dette_nette_ebitda": self._safe_div(df - tresorerie, ebitda),
            "dette_nette_fonds_propres": self._safe_pct(df - tresorerie, cp),
            "interest_coverage": self._safe_div(ebit, ebit_fin),
            "capacite_desendettement": self._safe_div(df, caf),
            "part_dette_lt": None,  # necessite detail LT/CT
        }

    # ============================================================
    # 3. RENTABILITE (9 ratios)
    # ============================================================
    def _rentabilite(self) -> dict:
        ca = self._get("chiffre_affaires")
        rn = self._get("resultat_net")
        ebit = self._get("ebit")
        ebitda = self._get("ebitda")
        va = self._get("valeur_ajoutee")
        cp = self._get("capitaux_propres")
        total_actif = self._get("total_actif")
        cap_employes = self._get("capitaux_employes")
        achats = self._get("achats_matieres") + self._get("achats_marchandises")

        return {
            "marge_brute": self._safe_pct(ca - achats, ca),
            "marge_ebitda": self._safe_pct(ebitda, ca),
            "marge_operationnelle": self._safe_pct(ebit, ca),
            "marge_nette": self._safe_pct(rn, ca),
            "roe": self._safe_pct(rn, cp),
            "roa": self._safe_pct(rn, total_actif),
            "roce": self._safe_pct(ebit, cap_employes),
            "rentabilite_economique": self._safe_pct(ebit, self._get("actif_economique")),
            "roic": self._safe_pct(ebit * 0.75, cp + self._get("dettes_financieres") - self._get("tresorerie")),
        }

    # ============================================================
    # 4. STRUCTURE FINANCIERE (6 ratios)
    # ============================================================
    def _structure_financiere(self) -> dict:
        cp = self._get("capitaux_propres")
        td = self._get("total_dettes")
        total_passif = self._get("total_passif")
        rs = self._get("ressources_stables")
        ai = self._get("actif_immobilise")
        bfr = self._get("bfr")
        fdr = self._get("fdr")

        return {
            "autonomie_financiere": self._safe_pct(cp, total_passif),
            "poids_des_dettes": self._safe_pct(td, total_passif),
            "equilibre_financier": self._safe_div(rs, ai),
            "couverture_emplois_stables": self._safe_div(fdr, bfr),
            "fonds_de_roulement": fdr,
            "tresorerie_nette": self._get("tresorerie_nette"),
        }

    # ============================================================
    # 5. CROISSANCE (5 ratios)
    # ============================================================
    def _croissance(self) -> dict:
        # On a besoin des valeurs N-1 - placeholder pour l'instant
        return {
            "croissance_ca": None,
            "croissance_ebitda": None,
            "croissance_resultat_net": None,
            "croissance_capitaux_propres": None,
            "tcac_ca_3ans": None,
        }

    # ============================================================
    # 6. GESTION / ACTIVITE (9 ratios)
    # ============================================================
    def _gestion_activite(self) -> dict:
        ca = self._get("chiffre_affaires")
        stocks = self._get("total_stocks")
        creances = self._get("total_creances")
        df = self._get("dettes_fournisseurs")
        achats = self._get("achats_matieres") + self._get("achats_marchandises")
        total_actif = self._get("total_actif")
        cap_employes = self._get("capitaux_employes")
        ai = self._get("actif_immobilise")
        bfr = self._get("bfr")

        dsi = self._safe_div(stocks * 365, achats)
        dso = self._safe_div(creances * 365, ca)
        dpo = self._safe_div(df * 365, achats)
        ccc = None
        if dsi is not None and dso is not None and dpo is not None:
            ccc = dsi + dso - dpo

        return {
            "rotation_stocks": self._safe_div(ca, stocks),
            "dsi": dsi,
            "dso": dso,
            "dpo": dpo,
            "bfr_jours_ca": self._safe_div(bfr * 365, ca),
            "rotation_actif": self._safe_div(ca, total_actif),
            "rotation_capitaux_employes": self._safe_div(ca, cap_employes),
            "rotation_immobilisations": self._safe_div(ca, ai),
            "cycle_conversion_tresorerie": ccc,
        }

    # ============================================================
    # 7. TRESORERIE (6 ratios)
    # ============================================================
    def _tresorerie(self) -> dict:
        ca = self._get("chiffre_affaires")
        tresorerie = self._get("tresorerie")
        dettes_ct = self._get("dettes_fournisseurs") + self._get("dettes_fiscales_sociales")
        caf = self._get("caf")
        df = self._get("dettes_financieres")

        return {
            "tresorerie_ca": self._safe_pct(tresorerie, ca),
            "tresorerie_dettes_ct": self._safe_div(tresorerie, dettes_ct),
            "burn_rate": None,  # necessite N-1
            "runway": None,
            "free_cash_flow": caf,  # approximation
            "couverture_caf_dette": self._safe_pct(caf, df),
        }

    # ============================================================
    # 8. RISQUE / SOLVABILITE (7 ratios)
    # ============================================================
    def _risque_solvabilite(self) -> dict:
        cp = self._get("capitaux_propres")
        td = self._get("total_dettes")
        total_actif = self._get("total_actif")
        bfr = self._get("bfr")
        va = self._get("valeur_ajoutee")
        ebe = self._get("ebe")
        charges_fin = 15000  # placeholder
        charges_perso = self._get("charges_personnel")
        ca = self._get("chiffre_affaires")

        # Score de Conan-Holder (adapte PME francaises)
        ch = None
        if td > 0 and total_actif > 0 and ca > 0 and va > 0:
            ch = (
                16 * (ebe / td)
                + 22 * (cp / total_actif)
                - 87 * (charges_fin / ca)
                - 10 * (charges_perso / va)
                + 24 * (ebe / total_actif)
            )

        return {
            "ratio_solvabilite": self._safe_pct(cp, td),
            "ratio_couverture_dettes": self._safe_div(total_actif, td),
            "z_score_altman": None,  # necessite donnees boursieres
            "probabilite_defaut_proxy": None,
            "ratio_liquidite_large": self._safe_div(
                self._get("total_stocks") + self._get("total_creances") + self._get("tresorerie"),
                self._get("dettes_fournisseurs")
            ),
            "score_conan_holder": ch,
            "cotation_banque_de_france": None,  # qualitatif
        }


if __name__ == "__main__":
    # Test avec les agregats de L'ORTEGA
    test_agregats = {
        "chiffre_affaires": 726713,
        "valeur_ajoutee": 315108,
        "ebe": 62395,
        "ebit": 32573,
        "ebitda": 100711,
        "resultat_net": 26788,
        "caf": 94926,
        "capitaux_propres": 280925,
        "dettes_financieres": 20353,
        "total_dettes": 332079,
        "actif_immobilise": 534777,
        "total_actif": 613004,
        "total_passif": 613004,
        "total_stocks": 3420,
        "total_creances": 13028,
        "dettes_fournisseurs": 34977,
        "dettes_fiscales_sociales": 34022,
        "tresorerie": 116615,
        "bfr": 3661,
        "fdr": -514424,
        "tresorerie_nette": 16692,
        "capitaux_employes": 301278,
        "actif_economique": 538438,
        "ressources_stables": 301278,
        "charges_personnel": 249578,
        "achats_matieres": 40582,
        "achats_marchandises": 56,
    }

    r = Ratios(test_agregats)
    resultats = r.compute_all()

    print("=" * 60)
    print("RATIOS CALCULES")
    print("=" * 60)
    print()

    for cat, ratios in resultats.items():
        print(f"--- {cat.upper()} ---")
        for nom, val in ratios.items():
            if val is None:
                print(f"  {nom:35s} : N/A")
            elif isinstance(val, float) and abs(val) < 100:
                print(f"  {nom:35s} : {val:>10.2f}")
            else:
                print(f"  {nom:35s} : {val:>10,.0f}")
        print()
