"""Selectionne la bonne valeur pour chaque poste comptable.

Logique :
- Bilan : preferer 'net' > 'net_n1' > 'brut'
- Compte de resultat : preferer 'net' > 'brut' > 'amort'
"""


class ColumnSelector:
    """Selectionne la bonne colonne selon la section."""

    PRIORITES = {
        "actif": ["net", "net_n1", "net_n2", "brut"],
        "passif": ["net", "net_n1", "net_n2", "brut"],
        "compte_resultat": ["net", "brut", "net_n1", "net_n2", "amort"],
    }

    def __init__(self, section: str):
        self.section = section
        self.priorites = self.PRIORITES.get(section, ["net", "brut", "amort"])

    def select(self, montants: dict) -> float:
        if not montants:
            return 0.0
        for col in self.priorites:
            if col in montants:
                return montants[col]
        return next(iter(montants.values()))

    def select_all(self, data: dict) -> dict:
        result = {}
        for code, info in data.items():
            montants = info.get("montants", {})
            result[code] = self.select(montants)
        return result


if __name__ == "__main__":
    selector_actif = ColumnSelector("actif")
    selector_cr = ColumnSelector("compte_resultat")

    test = {"brut": 1000, "amort": 200, "net": 800, "net_n1": 750}
    print("Bilan (actif)        :", selector_actif.select(test))
    print("Compte de resultat   :", selector_cr.select(test))
    print()
    print("Une seule valeur     :", selector_actif.select({"brut": 5000}))
    print("Vide                 :", selector_actif.select({}))
