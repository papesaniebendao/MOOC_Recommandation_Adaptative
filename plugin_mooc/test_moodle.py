import requests

# Configuration de la requête vers l'API de prédiction
url = 'http://localhost:8000/predict'
payload = {
    'id_student': 3,
    'code_module': 'MOODLE_2',
    'code_presentation': '2026J',
    'prenom': 'Pape',
    'course_id': 2,
    'total_clicks': 0.0,
    'total_days_active': 0.0,
    'avg_clicks_per_day': 0.0,
    'last_activity_day': 0.0,
    'total_span_days': 0.0,
    'clicks_recent': 0.0,
    'days_active_recent': 0.0,
    'tendance_activite': 0.0,
    'jours_inactivite': 15.0,
    'cutoff_day': 15.0,
    'avg_score': 0.0,
    'studied_credits': 60.0
}

# Envoi de la requête POST
r = requests.post(url, json=payload)
res = r.json()

# Affichage des résultats formatés
print('Score     :', res.get('dropout_score'))
print('Cause     :', res.get('cause_principale'))
print('Ressources:')

for resource in res.get('ressources_links', []):
    print(f"  [{resource['type']}] {resource['name']}")

message = res.get('message_motivation', '')
print('Message   :', message[:150])
