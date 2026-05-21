import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Modèle final DropGuard
XGB_MODEL_PATH = os.path.join(MODELS_DIR,
                               "xgboost_dropguard_final.joblib")
FEATURE_NAMES_PATH = os.path.join(MODELS_DIR,
                                   "feature_names_final.json")
KMEANS_PATH    = os.path.join(MODELS_DIR, "kmeans_model.joblib")
SCALER_PATH    = os.path.join(MODELS_DIR, "scaler_kmeans.joblib")
RECOMM_PATH    = os.path.join(MODELS_DIR, "recommendation_table.csv")
TEMPLATES_PATH = os.path.join(MODELS_DIR, "message_templates.json")
CLUSTER_FEAT_PATH = os.path.join(MODELS_DIR, "features_cluster.json")

# Seuils de risque
SEUIL_CRITIQUE = 0.7
SEUIL_MODERE   = 0.5

# Fenêtre temporelle
WINDOW_RECENT = 14
MIN_DAYS      = 7

# Moodle
MOODLE_URL   = os.getenv("MOODLE_URL",  "http://localhost:8080")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN","9d5cf986ddae4b7c169121098b0ed632")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# API
API_HOST = "0.0.0.0"
API_PORT = 8000