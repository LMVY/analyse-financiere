"""Calcul des ratios financiers - 6 categories, 35 ratios.

Chaque ratio est calcule a partir des agregats intermediaires.
Retourne une valeur numerique (float) ou None si non calculable.

Categories :
    - liquidite (6)
    - endettement (7)
    - rentabilite (7)
    - croissance (5)
    - gestion_activite (6)
    - risque_solvabilite (4)
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
            "croissance": self._croissance(),
            "gestion_activite": self._gestion_activite(),
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
        caf = self._get("caf")

        actif_circulant = stocks + creances + tresorerie

        return {
            "current_ratio": self._safe_div(actif_circulant, dettes_ct),
            "quick_ratio": self._safe_div(creances + tresorerie, dettes_ct),
            "cash_ratio": self._safe_div(tresorerie, dettes_ct),
            "liquidite_immediate": self._safe_div(tresorerie, dettes_fin_ct),
            "tresorerie_ca": self._safe_pct(tresorerie, ca),
            "couverture_caf_dette": self._safe_pct(caf, dettes_fin_ct),
        }

    # ============================================================
    # 2. ENDETTEMENT (7 ratios)
    # ============================================================
    def _endettement(self) -> dict:
        cp = self._get("capitaux_propres")
        df = self._get("dettes_financieres")
        td = self._get("total_dettes")
        ebitda = self._get("ebitda")
        tresorerie = self._get("tresorerie")
        caf = self._get("caf")
        total_passif = self._get("total_passif")
        rs = self._get("ressources_stables")
        ai = self._get("actif_immobilise")

        return {
            "gearing": self._safe_pct(df, cp),
            "levier_financier": self._safe_pct(td, cp),
            "dette_nette_ebitda": self._safe_div(df - tresorerie, ebitda),
            "dette_nette_fonds_propres": self._safe_pct(df - tresorerie, cp),
            "capacite_desendettement": self._safe_div(df, caf),
            "autonomie_financiere": self._safe_pct(cp, total_passif),
            "equilibre_financier": self._safe_div(rs, ai),
        }

    # ============================================================
    # 3. RENTABILITE (7 ratios)
    # ============================================================
    def _rentabilite(self) -> dict:
        ca = self._get("chiffre_affaires")
        rn = self._get("resultat_net")
        ebit = self._get("ebit")
        ebitda = self._get("ebitda")
        cp = self._get("capitaux_propres")
        total_actif = self._get("total_actif")
        cap_employes = self._get("capitaux_employes")
        achats = self._get("achats")  # agrege par Agregats

        return {
            "marge_brute": self._safe_pct(ca - achats, ca),
            "marge_ebitda": self._safe_pct(ebitda, ca),
            "marge_operationnelle": self._safe_pct(ebit, ca),
            "marge_nette": self._safe_pct(rn, ca),
            "roe": self._safe_pct(rn, cp),
            "roa": self._safe_pct(rn, total_actif),
            "roce": self._safe_pct(ebit, cap_employes),
        }

    # ============================================================
    # 4. CROISSANCE (5 ratios - remplis plus tard)
    # ============================================================
    def _croissance(self) -> dict:
        return {
            "croissance_ca": None,
            "croissance_ebitda": None,
            "croissance_resultat_net": None,
            "croissance_capitaux_propres": None,
            "tcac_ca_3ans": None,
        }

    # ============================================================
    # 5. GESTION / ACTIVITE (6 ratios)
    # ============================================================
    def _gestion_activite(self) -> dict:
        ca = self._get("chiffre_affaires")
        stocks = self._get("total_stocks")
        df = self._get("dettes_fournisseurs")
        achats = self._get("achats")  # agrege par Agregats
        total_actif = self._get("total_actif")
        ai = self._get("actif_immobilise")

        dsi = self._safe_div(stocks * 365, achats)
        dpo = self._safe_div(df * 365, achats)

        ccc = None
        if dsi is not None and dpo is not None:
            ccc = dsi - dpo

        return {
            "dsi": dsi,
            "dpo": dpo,
            "rotation_stocks": self._safe_div(ca, stocks),
            "rotation_actif": self._safe_div(ca, total_actif),
            "rotation_immobilisations": self._safe_div(ca, ai),
            "cycle_conversion_tresorerie": ccc,
        }

    # ============================================================
    # 6. RISQUE / SOLVABILITE (4 ratios)
    # ============================================================
    def _risque_solvabilite(self) -> dict:
        cp = self._get("capitaux_propres")
        td = self._get("total_dettes")
        total_actif = self._get("total_actif")
        stocks = self._get("total_stocks")
        creances = self._get("total_creances")
        tresorerie = self._get("tresorerie")
        dettes_fourn = self._get("dettes_fournisseurs")
        ebe = self._get("ebe")

        charges_fin = self._get("interets_charges_assimilees") + self._get("charges_cessions_vmp")

        couv_frais_fin = None
        if charges_fin and charges_fin > 0 and ebe is not None:
            couv_frais_fin = ebe / charges_fin

        return {
            "ratio_solvabilite": self._safe_pct(cp, td),
            "ratio_couverture_dettes": self._safe_div(total_actif, td),
            "ratio_liquidite_large": self._safe_div(
                stocks + creances + tresorerie, dettes_fourn
            ),
            "couverture_frais_financiers": couv_frais_fin,
        }


if __name__ == "__main__":
    test = {
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
        "capitaux_employes": 301278,
        "ressources_stables": 301278,
        "interets_charges_assimilees": 15000,
        "achats_matieres": 40582,
        "achats_marchandises": 56,
    }

    r = Ratios(test)
    for cat, ratios in r.compute_all().items():
        print(f"--- {cat.upper()} ---")
        for nom, val in ratios.items():
            if val is None:
                print(f"  {nom:35s} : N/A")
            elif isinstance(val, float) and abs(val) < 100:
                print(f"  {nom:35s} : {val:>10.2f}")
            else:
                print(f"  {nom:35s} : {val:>10,.0f}")
        print()
