# MOOC Dropout Prediction Plugin
### Système de prédiction précoce de l'abandon et recommandations prescriptives
**Financé par l'IRD (Institut de Recherche pour le Développement) — UGB Saint-Louis**

---

## Architecture

```
plugin_mooc/
├── main.py                    # API FastAPI
├── app.py                     # Dashboard Streamlit
├── config.py                  # Configuration
├── requirements.txt
├── models/
│   └── xgboost_model.py       # Modèle XGBoost (AUC=0.863)
├── core/
│   ├── feature_engineering.py # Calcul features depuis logs Moodle
│   ├── explainer.py           # SHAP
│   └── prescriptor.py         # Moteur prescriptif
├── schemas/
│   ├── input.py               # Format entrée JSON
│   └── output.py              # Format sortie JSON
└── moodle/
    └── moodle_client.py       # Client API REST Moodle
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancement API

```bash
cd plugin_mooc
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Lancement Dashboard

```bash
streamlit run app.py
```

## Endpoints API

| Endpoint | Méthode | Description |
|---|---|---|
| /predict | POST | Prédiction pour 1 étudiant |
| /predict/batch | POST | Prédiction pour N étudiants |
| /moodle/course/{id} | GET | Analyser un cours Moodle |
| /health | GET | Santé de l'API |
| /docs | GET | Documentation Swagger |

## Résultats scientifiques

- XGBoost : AUC=0.863, Recall=71%, Wilcoxon p=0.002
- Cutoff optimal : Jour 28 (-1.2% AUC, +14 jours d'intervention)
- 7 profils d'abandon identifiés via SHAP + K-Means
- Moteur prescriptif : 4 causes x 3 niveaux = 12 interventions ciblées