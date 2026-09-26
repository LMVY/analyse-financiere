"""Genere un PDF de test avec un bilan et un compte de resultat fictifs."""
import fitz  # PyMuPDF
from pathlib import Path

# Donnees fictives d'une entreprise
data = {
    "BILAN ACTIF": [
        ("Immobilisations incorporelles", "50 000", "45 000"),
        ("Immobilisations corporelles", "250 000", "230 000"),
        ("Immobilisations financieres", "30 000", "30 000"),
        ("Stocks et en-cours", "80 000", "70 000"),
        ("Creances clients", "120 000", "110 000"),
        ("Autres creances", "15 000", "12 000"),
        ("Disponibilites", "50 000", "40 000"),
        ("TOTAL ACTIF", "595 000", "537 000"),
    ],
    "BILAN PASSIF": [
        ("Capital social", "100 000", "100 000"),
        ("Reserves", "150 000", "120 000"),
        ("Resultat de l'exercice", "45 000", "30 000"),
        ("Emprunts et dettes aupres des etablissements de credit", "200 000", "220 000"),
        ("Dettes fournisseurs", "80 000", "55 000"),
        ("Dettes fiscales et sociales", "20 000", "12 000"),
        ("TOTAL PASSIF", "595 000", "537 000"),
    ],
    "COMPTE DE RESULTAT": [
        ("Chiffre d'affaires", "800 000", "720 000"),
        ("Achats consommes", "450 000", "410 000"),
        ("Charges externes", "80 000", "75 000"),
        ("Charges de personnel", "150 000", "140 000"),
        ("Impots et taxes", "20 000", "18 000"),
        ("Dotations aux amortissements", "30 000", "28 000"),
        ("Resultat d'exploitation", "70 000", "49 000"),
        ("Charges financieres", "15 000", "12 000"),
        ("Resultat courant avant impots", "55 000", "37 000"),
        ("Impots sur les benefices", "10 000", "7 000"),
        ("Resultat net", "45 000", "30 000"),
    ],
}


def create_pdf(output_path: str = "data/raw/bilan_test.pdf"):
    doc = fitz.open()
    page = doc.new_page()

    # Configuration
    fontsize = 10
    line_height = 15
    y = 50
    x = 50

    # Titre
    page.insert_text((x, y), "ENTREPRISE EXEMPLE SAS", fontsize=14, fontname="helv")
    y += 20
    page.insert_text((x, y), "Bilan et Compte de Resultat - Exercice 2024", fontsize=11, fontname="helv")
    y += 30

    # Pour chaque section
    for section_title, lignes in data.items():
        page.insert_text((x, y), section_title, fontsize=11, fontname="helv")
        y += line_height + 3

        # En-tetes
        page.insert_text((x, y), "Poste", fontsize=fontsize, fontname="helv")
        page.insert_text((x + 320, y), "2024", fontsize=fontsize, fontname="helv")
        page.insert_text((x + 400, y), "2023", fontsize=fontsize, fontname="helv")
        y += line_height

        # Lignes
        for poste, val_2024, val_2023 in lignes:
            page.insert_text((x, y), poste, fontsize=fontsize, fontname="helv")
            page.insert_text((x + 320, y), val_2024, fontsize=fontsize, fontname="helv")
            page.insert_text((x + 400, y), val_2023, fontsize=fontsize, fontname="helv")
            y += line_height

        y += 10

    # Creer le dossier si necessaire
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"PDF cree : {output_path}")


if __name__ == "__main__":
    create_pdf()
