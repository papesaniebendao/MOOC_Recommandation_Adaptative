# core/recommender.py
# DropGuard — Moteur de Recommandation Causale v2.0
# Features cumulatives + récentes + tendance

import joblib
import json
import os
import pandas as pd
import numpy as np
from groq import Groq

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")

# ── Singletons ──
_kmeans    = None
_scaler    = None
_df_recomm = None
_templates = None
_feat_cluster = None

def _load_assets():
    global _kmeans, _scaler, _df_recomm, _templates, _feat_cluster
    if _kmeans is None:
        _kmeans    = joblib.load(os.path.join(MODELS_DIR, "kmeans_model.joblib"))
        _scaler    = joblib.load(os.path.join(MODELS_DIR, "scaler_kmeans.joblib"))
        _df_recomm = pd.read_csv(os.path.join(MODELS_DIR, "recommendation_table.csv"))
        with open(os.path.join(MODELS_DIR, "message_templates.json"), encoding="utf-8") as f:
            _templates = json.load(f)
        with open(os.path.join(MODELS_DIR, "features_cluster.json")) as f:
            _feat_cluster = json.load(f)
    return _kmeans, _scaler, _df_recomm, _templates, _feat_cluster

CLUSTER_NAMES = {
    0: "Engagés Modérés",
    1: "À Risque Critique",
    2: "Bien Engagés",
    3: "Hyper Engagés"
}

NOMS_ACTIVITES = {
    'forumng'     : 'Forum de discussion',
    'quiz'        : 'Quiz de révision',
    'oucontent'   : 'Contenus du cours',
    'resource'    : 'Ressources complémentaires',
    'ouwiki'      : 'Wiki collaboratif',
    'ouelluminate': 'Sessions en ligne',
    'homepage'    : "Page d'accueil du cours",
    'subpage'     : 'Sous-pages du cours',
    'url'         : 'Liens externes',
    'glossary'    : 'Glossaire',
}

def get_cluster(student_dict: dict) -> tuple:
    kmeans, scaler, _, _, feat_cluster = _load_assets()
    features = [float(student_dict.get(f, 0) or 0)
                for f in feat_cluster]
    X = scaler.transform([features])
    cluster_id = int(kmeans.predict(X)[0])
    return cluster_id, CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}")

def get_recommendations(cluster_id: int, cause: str) -> list:
    _, _, df_recomm, _, _ = _load_assets()
    row = df_recomm[
        (df_recomm['cluster']    == cluster_id) &
        (df_recomm['cause_shap'] == cause)
    ]
    if row.empty:
        return ['Forum de discussion', 'Contenus du cours',
                'Ressources complémentaires']
    row = row.iloc[0]
    acts = [row['activite_1'], row['activite_2'], row['activite_3']]
    return [NOMS_ACTIVITES.get(a, a) for a in acts if a]

def generate_message(prenom, cluster_name, cause_desc,
                     activites, conseil, groq_api_key):
    try:
        client = Groq(api_key=groq_api_key)
        prompt = f"""Tu es un tuteur bienveillant dans une plateforme MOOC.
Écris un message court (3-4 phrases) et encourageant pour {prenom}.
Profil : {cluster_name} | Cause : {cause_desc}
Conseil : {conseil}
Activités recommandées : {', '.join(activites)}

Contraintes : commence par "Bonjour {prenom},",
maximum 4 phrases, ton chaleureux,
NE PAS mentionner de score ou risque."""

        response = client.chat.completions.create(
            model       = "llama-3.1-8b-instant",
            messages    = [{"role":"user","content":prompt}],
            max_tokens  = 200,
            temperature = 0.7
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Bonjour {prenom}, {conseil} 💪"

def recommend(student_dict: dict, cause: str,
              prenom: str = "Étudiant",
              groq_api_key: str = "",
              ressources_reelles: list = []) -> dict:
    _load_assets()
    _, _, df_recomm, templates, _ = _load_assets()

    cluster_id, cluster_name = get_cluster(student_dict)
    conseil    = templates.get(cause, {}).get('conseil', '')
    cause_desc = templates.get(cause, {}).get('description', cause)

    # Utiliser vraies ressources si disponibles
    if ressources_reelles:
        activites = [r['name'] for r in ressources_reelles]
        activites_pour_groq = activites
        ressources_links = [
            {
                'name': r['name'],
                'url' : r.get('url', ''),
                'type': r['type']
            }
            for r in ressources_reelles
        ]
    else:
        activites = get_recommendations(cluster_id, cause)
        activites_pour_groq = activites
        ressources_links = []

    message = generate_message(
        prenom, cluster_name, cause_desc,
        activites_pour_groq, conseil, groq_api_key
    )

    return {
        'cluster_id'     : cluster_id,
        'cluster_name'   : cluster_name,
        'activites'      : activites,
        'ressources_links': ressources_links,
        'message'        : message,
    }