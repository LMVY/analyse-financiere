# Analyse financiere - Entreprises francaises (PCG)

Outil d'analyse financiere et de scoring credit pour entreprises francaises,
base sur le Plan Comptable General (PCG).

## Objectif

Permettre a un analyste credit d'evaluer la sante financiere d'une entreprise
a partir de ses documents comptables (bilan + compte de resultat), avec un
score de risque parametrable et contextualise par secteur.

## Architecture

```
PDF (natif ou scanne) / image            Excel (.xlsx / .xlsm)
        |                                          |
        v                                          v
Mistral Document AI                     Lecteur Excel (src/extraction/excel_parser.py)
(ocr.process + annotation JSON)        codes DGFiP (liasse fiscale) ou libelles
   |  schema construit depuis           normalises, matches contre le meme
   |  config/pcg_referentiel.yaml       referentiel PCG ; colonnes N / N-1
   |  extrait : 127 postes comptables   deduites des en-tetes d'exercices
   |  (N et N-1) + raison sociale, SIREN, code NAF
   |                                          |
   +-------------> Service d'extraction unifie
                   (src/extraction/service.py : un seul appel, quel que
                    soit le format, -> Extraction {data, meta, source})
                       |
                       v
Format standard {"actif": {...}, "passif": {...}, "compte_resultat": {...}}
                       |
                       v
controle_extraction (qualite, equilibre bilan)
                       |
                       v
PORTE AVANT ANALYSE : de TROIS a HUIT exercices fiscaux complets.
Un exercice complet = bilan (actif ET passif) + compte de resultat ;
les exercices incomplets sont ecartes (message de detail), au-dela de
huit seuls les plus recents sont analyses, et sous trois complets
l'analyse est bloquee.
                       |
                       v
Agregats (SIG, structure financiere, tresorerie)
   |
   v
Ratios (6 categories, 33 ratios)
   |
   v
Scoring : sectoriel (Q1/mediane/Q3 du secteur) ou standard (seuils fixes).
Concordance stricte avec la configuration EFFECTIVE (defaut ou page
Parametrage) : ratios_actifs, poids des ratios, poids des categories
du profil d'analyse ; audit automatise dans tests/test_concordance_scoring.py

BASE DU SCORE (Options du dashboard, src/scoring/modes.py) :
- "Derniere annee + tendance" (defaut) : le score porte sur
  l'exercice N, ajuste par la trajectoire des ratios (N compare a
  la moyenne des exercices, au sens favorable de chaque ratio ;
  bande morte de +/- 2 % ; au plus +/- 5 points par categorie,
  scores bornes [0 ; 100], global recalcule avec les poids du profil) ;
- "Moyenne des exercices" : le score porte sur la moyenne
  arithmetique de chaque ratio sur tous les exercices fournis
  (meme regle que la colonne "Moyenne") ; le jeu de ratios actifs
  et les poids restent ceux de la configuration effective.

   |
   v
Dashboard Streamlit + Rapport PDF (synthese redigee, nuances, methodologie)
```

## Structure

```
config/
  pcg_referentiel.yaml    # postes PCG + libelles (source du schema Document AI)
  ratios_config.yaml      # 33 ratios : seuils, sens, poids
  secteurs_config.yaml    # 8 secteurs : quartiles par ratio + ratios desactives
  profils.yaml            # profils d'analyse (court/moyen/long terme)
dashboard/
  app.py                  # launcher (onglets Analyse / Paramétrage)
  _analyse_body.py        # analyse : import, scores, graphiques
  _admin_body.py          # paramétrage : configuration (accessible a tous)
src/
  extraction/
    service.py             # service unifie : un appel -> Extraction (data, meta, source)
    mistral_docai.py        # client Mistral Document AI (annotation JSON)
    excel_parser.py         # lecteur Excel (.xlsx/.xlsm) -> format standard
    controle_extraction.py  # validation de l'extraction (score, equilibre)
  analysis/
    agregats.py           # soldes intermediaires de gestion, BFR, FDR...
    ratios.py             # 6 categories, 33 ratios
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
tests/
  test_excel_parser.py         # tests du lecteur Excel (genere ses fixtures)
  test_concordance_scoring.py  # audit : agregats, ratios, scores, config, sectoriel
```

## Stack technique

| Composant | Outil |
|-----------|-------|
| Extraction PDF/image | Mistral Document AI (annotation JSON, OCR integre) |
| Extraction Excel | openpyxl (libelles matches contre le referentiel PCG) |
| Analyse | pandas, numpy |
| Interface | Streamlit |
| Graphiques | Plotly (palette centralisee) |
| Rapport PDF | reportlab |
| Configuration | YAML |

## Installation

```bash
conda activate finance  # ou tout env python 3.11+
pip install mistralai streamlit plotly pandas numpy pyyaml python-dotenv reportlab openpyxl

cp .env.example .env   # puis renseigner MISTRAL_API_KEY
```

MISTRAL_API_KEY n'est necessaire que pour les PDF et images ; les
fichiers Excel sont lus localement, sans appel API.

## Utilisation

```bash
# Dashboard
streamlit run dashboard/app.py

# Extraction en ligne de commande (test, tout format supporte)
python -m src.extraction.service chemin/vers/document.pdf|.xlsx|.jpg
python -m src.extraction.excel_parser chemin/vers/bilan.xlsx

# Tests du lecteur Excel et du service (genere ses propres classeurs de test)
python tests/test_excel_parser.py

# Audit de concordance du scoring (ratios, poids, profil, sectoriel)
python tests/test_concordance_scoring.py
```

L'analyse exige entre trois et huit exercices fiscaux complets : un
exercice complet = un bilan (actif + passif) et un compte de resultat,
quel que soit le format (PDF, image, Excel, ou une liasse qui porte
deux exercices). Trois complets minimum (sinon blocage avec le detail
des manques par exercice) ; au-dela de huit, seuls les huit exercices
les plus recents sont analyses. L'annee de chaque exercice est lue
dans le nom de fichier (ex : `bilan_2024.pdf`) ou, pour les fichiers
Excel, dans les en-tetes de colonnes ; a defaut, les exercices sont
etiquetes N / N-1.
Le code NAF/APE extrait du document determine le secteur ; il peut
aussi etre saisi manuellement dans les Options.

## Limites connues

- Les references sectorielles (quartiles) sont des approximations de
  sources publiques (INSEE, Banque de France) : a ajuster par secteur.
- Le lecteur Excel s'appuie sur des heuristiques (libelles normalises,
  colonnes N / N-1 deduites des en-tetes ou de la convention francais
  "exercice le plus recent a gauche") : les classeurs tres atypiques
  peuvent demander une mise en forme avant import. Les liasses fiscales
  DGFiP exportees en Excel (codes AA a HN) sont quant a elles lues via
  ces codes, plus fiables que les libelles.
- Les scores sont indicatifs et ne constituent ni un audit ni un
  avis financier (voir la section Methode et limites du rapport PDF).
