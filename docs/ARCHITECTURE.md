# Architecture du projet

## Vue d'ensemble

PDF / Excel / FEC
       |
       v
   DETECTION AUTOMATIQUE (bilan_parser.py)
       |
       +---> DGFiP      (dgfip_parser.py)
       +---> PDF natif  (pdfplumber_extractor.py)
       +---> PDF scan   (ocr_extractor.py)
       +---> Excel/CSV  (excel_parser.py)
       +---> FEC        (fec_parser.py)
       |
       
   DONNEES STANDARDISEES
   {actif, passif, compte_resultat}
       |
       v
   AGREGATS (24 blocs)
   - CA, VA, EBE, EBITDA
   - BFR, FDR, Tresorerie nette
       |
       v
   RATIOS (48 ratios)
   - Liquidite, Endettement
   - Rentabilite, Croissance
       |
       v
   SCORING (/100)
   - 8 categories ponderees
   - Profils predefinis
       |
       v
   DASHBOARD STREAMLIT

## Composants

### Extraction (5 formats)

| Format | Fichier | Description |
|--------|---------|-------------|
| DGFiP | src/extraction/dgfip_parser.py | Liasse fiscale 2050/2051/2052 |
| PDF Tableau | src/extraction/pdfplumber_extractor.py | Bilans edites (Sage, Cegid) |
| PDF Scan | src/extraction/ocr_extractor.py | Bilans scannes (Tesseract) |
| Excel/CSV | src/extraction/excel_parser.py | Fichiers Excel/CSV |
| FEC | src/extraction/fec_parser.py | Fichier des Ecritures Comptables |

### Analyse

| Fichier | Role |
|---------|------|
| src/analysis/agregats.py | Calcul des 24 agregats |
| src/analysis/ratios.py | Calcul des 48 ratios |
| src/analysis/validator.py | 18 tests de validation |
| src/analysis/pcg_normalizer.py | Normalisation PCG |

### Scoring

| Fichier | Role |
|---------|------|
| src/scoring/score.py | Moteur de scoring |
| src/scoring/sector_scorer.py | Comparaison sectorielle |
| config/ratios_config.yaml | Config des ratios |
| config/secteurs_config.yaml | Reference sectorielle |

## Fichiers de configuration

| Fichier | Role |
|---------|------|
| config/pcg_referentiel.yaml | 313 libelles PCG + 93 comptes |
| config/ratios_config.yaml | 48 ratios (seuils, poids, sources) |
| config/secteurs_config.yaml | 8 secteurs INSEE/BdF |
