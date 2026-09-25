# Analyse financière — Entreprises françaises (PCG)

Outil d'analyse financière et de scoring crédit pour entreprises françaises, basé sur le Plan Comptable Général (PCG).

## 🎯 Objectif

Permettre à un analyste crédit d'évaluer la santé financière d'une entreprise à partir de ses documents comptables (bilan + compte de résultat), avec un score de risque paramétrable.

## 📊 Fonctionnalités prévues

### 1. Extraction automatique
- Upload d'un PDF (bilan + compte de résultat)
- Détection du type de PDF (texte natif ou scanné)
- Extraction des postes comptables

### 2. Normalisation PCG
- Mapping des libellés vers les postes standards
- Regroupement et retraitements comptables

### 3. Ratios financiers
- **Liquidité** : current ratio, quick ratio, cash ratio
- **Endettement** : gearing, dette nette / EBITDA, interest coverage
- **Rentabilité** : marge nette, ROE, ROCE, marge EBITDA
- **Structure** : autonomie financière, BFR
- **Croissance** : croissance CA, croissance EBITDA

### 4. Score paramétrable
6 catégories pondérables :
- Croissance
- Structure financière
- Endettement
- Rentabilité
- Liquidité
- Risque financier

L'utilisateur peut ajuster les pondérations via des curseurs. Profils prédéfinis : très court terme, court terme, moyen terme, long terme.

## 🛠️ Stack technique

| Composant | Outil |
|-----------|-------|
| Extraction PDF | PyMuPDF, pdfplumber |
| OCR (PDF scannés) | OCRmyPDF + Tesseract |
| Classification postes | Règles + LLM |
| Analyse | pandas, numpy |
| Interface | Streamlit |
| Configuration | YAML |

## 📁 Structure
