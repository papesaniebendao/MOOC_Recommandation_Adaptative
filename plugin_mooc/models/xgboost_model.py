# models/xgboost_model.py
# DropGuard — XGBoost Predictor v2.0

import joblib
import json
import numpy as np
import pandas as pd
import os

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")

class XGBoostPredictor:
    def __init__(self):
        self.model         = None
        self.feature_names = None
        self._load_model()

    def _load_model(self):
        model_path = os.path.join(MODELS_DIR,
                                   "xgboost_dropguard_final.joblib")
        feat_path  = os.path.join(MODELS_DIR,
                                   "feature_names_final.json")
        self.model = joblib.load(model_path)
        with open(feat_path) as f:
            self.feature_names = json.load(f)
        print(f"[XGBoostPredictor] Modèle chargé — "
              f"{len(self.feature_names)} features")

    def predict(self, student_dict: dict) -> float:
        X = pd.DataFrame([student_dict])
        for feat in self.feature_names:
            if feat not in X.columns:
                X[feat] = 0.0
        X = X[self.feature_names].fillna(0)
        return float(self.model.predict_proba(X)[0][1])

_predictor_instance = None

def get_predictor() -> XGBoostPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = XGBoostPredictor()
    return _predictor_instance