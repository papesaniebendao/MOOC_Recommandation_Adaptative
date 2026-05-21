
from pydantic import BaseModel
from typing import List, Dict, Optional

class PrescriptionOutput(BaseModel):
    """Format de sortie standardisé du plugin."""

    # Identifiants
    id_student         : int
    code_module        : str
    code_presentation  : str

    # Score de risque
    dropout_score      : float
    niveau_risque      : str   # critique / modere / faible
    emoji_risque       : str   # 🔴 / 🟠 / 🟢

    # Diagnostic
    cause_principale   : str
    cause_label        : str
    facteurs_shap      : Dict[str, float]

    # Prescription
    action             : str
    intervention       : str
    ressources         : List[str]
    urgence            : int   # 1, 2, 3

    # Données étudiant résumées
    donnees_etudiant   : Dict[str, float]

    # Métadonnées
    cutoff_utilise     : int = 42
    version_modele     : str = "xgboost_v1"


class BatchOutput(BaseModel):
    """Format de sortie pour une liste d'étudiants."""
    total             : int
    critiques         : int
    moderes           : int
    faibles           : int
    prescriptions     : List[PrescriptionOutput]
