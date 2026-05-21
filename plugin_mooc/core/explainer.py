# core/explainer.py
# DropGuard — SHAP Explainer v2.0

import shap
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.xgboost_model import get_predictor

_explainer_instance = None

def get_explainer():
    global _explainer_instance
    if _explainer_instance is None:
        _explainer_instance = shap.TreeExplainer(
            get_predictor().model
        )
    return _explainer_instance

CAUSE_GROUPS = {
    'inactivite': [
        'jours_inactivite', 'last_activity_day',
        'days_active_recent', 'tendance_activite',
        'total_days_active', 'clicks_recent',
        'avg_clicks_per_day'
    ],
    'difficulte_academique': [
        'avg_score', 'TMA', 'CMA',
        'num_submitted_assessments'
    ],
    'surcharge': ['studied_credits'],
    'desengagement_module': [
        'forumng', 'quiz', 'oucontent', 'resource',
        'ouwiki', 'forumng_recent', 'quiz_recent',
        'oucontent_recent'
    ]
}

def explain_student(student_dict: dict) -> Tuple[Dict, str]:
    predictor = get_predictor()
    explainer = get_explainer()

    X = pd.DataFrame([student_dict])
    for feat in predictor.feature_names:
        if feat not in X.columns:
            X[feat] = 0.0
    X = X[predictor.feature_names].fillna(0)

    shap_vals = explainer.shap_values(X)[0]
    shap_dict = dict(zip(predictor.feature_names, shap_vals))

    # Identifier cause principale
    scores = {}
    for cause, feats in CAUSE_GROUPS.items():
        scores[cause] = sum(
            shap_dict.get(f, 0) for f in feats
            if shap_dict.get(f, 0) > 0
        )
    cause = max(scores, key=scores.get) \
            if sum(scores.values()) > 0 else 'inactivite'

    return shap_dict, cause