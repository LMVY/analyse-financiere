# Analyse financiere - Entreprises francaises (PCG)

Outil d'analyse financiere et de scoring credit pour entreprises francaises,
base sur le Plan Comptable General (PCG).

## Objectif

Permettre a un analyste credit d'evaluer la sante financiere d'une entreprise
a partir de ses documents comptables (bilan + compte de resultat), avec un
score de risque parametrable et contextualise par secteur.

## Architecture

```
PDF (natif ou scanne) / image
   |
   v
Mistral Document AI (ocr.process + annotation JSON)
   |  schema construit depuis config/pcg_referentiel.yaml
   |  extrait : 126 postes comptables (N et N-1) + raison sociale, SIREN, code NAF
   v
Format standard {"actif": {...}, "passif": {...}, "compte_resultat": {...}}
   |
   v
controle_extraction (qualite, equilibre bilan) -- porte avant l'analyse
   |
   v
Agregats (SIG, structure financiere, tresorerie)
   |
   v
Ratios (6 categories, 35 ratios)
   |
   v
Scoring : sectoriel (Q1/mediane/Q3 du secteur) ou standard (seuils fixes)
   |
   v
Dashboard Streamlit + Rapport PDF (synthese redigee, nuances, methodologie)
```

## Structure

```
config/
  pcg_referentiel.yaml    # postes PCG + libelles (source du schema Document AI)
  ratios_config.yaml      # 35 ratios : seuils, sens, poids
  secteurs_config.yaml    # 8 secteurs : quartiles par ratio + ratios desactives
  profils.yaml            # profils d'analyse (court/moyen/long terme)
dashboard/
  app.py                  # launcher (onglets Analyse / Admin)
  _analyse_body.py        # analyse : import, scores, graphiques
  _admin_body.py          # admin : configuration utilisateur
src/
  extraction/
    mistral_docai.py        # client Mistral Document AI (annotation JSON)
    controle_extraction.py  # validation de l'extraction (score, equilibre)
  analysis/
    agregats.py           # soldes intermediaires de gestion, BFR, FDR...
    ratios.py             # 6 categories, 35 ratios
    filter_ratios.py      # filtrage selon nombre d'exercices
    historique.py         # tendances multi-exercices
    validator.py          # controles de coherence comptable
  scoring/
    score.py              # scoring standard (profils ponderables)
    sector_scorer.py      # scoring sectoriel + detection NAF
    alerts.py             # alertes automatiques
    config_loader.py      # chargement YAML
  visualization/
    colors.py             # palette centrale (source unique)
    charts.py             # benchmark sectoriel, evolution multi-annees
  reporting/
    pdf_report.py         # rapport PDF complet et nuance
data/
  cache_mistral/          # cache des extractions (gitignore)
  raw/                    # documents sources (gitignore)
```

## Stack technique

| Composant | Outil |
|-----------|-------|
| Extraction | Mistral Document AI (annotation JSON, OCR integre) |
| Analyse | pandas, numpy |
| Interface | Streamlit |
| Graphiques | Plotly (palette centralisee) |
| Rapport PDF | reportlab |
| Configuration | YAML |

## Installation

```bash
conda activate finance  # ou tout env python 3.11+
pip install mistralai streamlit plotly pandas numpy pyyaml python-dotenv reportlab

cp .env.example .env   # puis renseigner MISTRAL_API_KEY
```

## Utilisation

```bash
# Dashboard
streamlit run dashboard/app.py

# Extraction en ligne de commande (test)
python -m src.extraction.mistral_docai chemin/vers/bilan.pdf
```

L'annee de chaque exercice est lue dans le nom de fichier (ex :
`bilan_2024.pdf`) ; a defaut, les exercices sont etiquetes N / N-1.
Le code NAF/APE extrait du document determine le secteur ; il peut
aussi etre saisi manuellement dans les Options.

## Limites connues

- Les references sectorielles (quartiles) sont des approximations de
  sources publiques (INSEE, Banque de France) : a ajuster par secteur.
- Les scores sont indicatifs et ne constituent ni un audit ni un
  avis financier (voir la section Methode et limites du rapport PDF).
