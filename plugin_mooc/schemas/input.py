from pydantic import BaseModel, Field
from typing import Optional

class StudentData(BaseModel):
    """
    Format d'entrée DropGuard v2.0
    Features cumulatives + récentes + dérivées
    """
    # Identifiants
    id_student        : int   = Field(..., description="ID unique étudiant")
    code_module       : str   = Field(..., description="Code module")
    code_presentation : str   = Field(..., description="Code présentation")
    prenom            : str   = Field("Étudiant", description="Prénom étudiant")

    # Features cumulatives (J1 → Aujourd'hui)
    total_clicks               : float = Field(0.0)
    total_days_active          : float = Field(0.0)
    avg_clicks_per_day         : float = Field(0.0)
    last_activity_day          : float = Field(0.0)
    total_span_days            : float = Field(0.0)
    avg_score                  : float = Field(0.0)
    num_submitted_assessments  : float = Field(0.0)
    studied_credits            : float = Field(60.0)
    TMA                        : Optional[float] = Field(0.0)
    CMA                        : Optional[float] = Field(0.0)

    # Features récentes (14 derniers jours)
    clicks_recent              : float = Field(0.0)
    days_active_recent         : float = Field(0.0)

    # Features dérivées
    tendance_activite          : float = Field(0.0)
    jours_inactivite           : float = Field(0.0)
    cutoff_day                 : float = Field(28.0)

    # Activités VLE cumulatives
    forumng                    : float = Field(0.0)
    quiz                       : float = Field(0.0)
    oucontent                  : float = Field(0.0)
    resource                   : float = Field(0.0)
    ouwiki                     : float = Field(0.0)
    ouelluminate               : float = Field(0.0)
    homepage                   : float = Field(0.0)
    subpage                    : float = Field(0.0)
    url                        : float = Field(0.0)
    glossary                   : float = Field(0.0)

    # Activités VLE récentes (14 derniers jours)
    forumng_recent             : float = Field(0.0)
    quiz_recent                : float = Field(0.0)
    oucontent_recent           : float = Field(0.0)
    resource_recent            : float = Field(0.0)
    ouwiki_recent              : float = Field(0.0)
    ouelluminate_recent        : float = Field(0.0)
    homepage_recent            : float = Field(0.0)
    subpage_recent             : float = Field(0.0)
    url_recent                 : float = Field(0.0)
    glossary_recent            : float = Field(0.0)

    # Variables catégorielles optionnelles
    imd_band                   : Optional[str] = Field(None)
    highest_education          : Optional[str] = Field(None)
    age_band                   : Optional[str] = Field(None)
    region                     : Optional[str] = Field(None)
    gender                     : Optional[str] = Field(None)
    
    course_id                  : Optional[int] = Field(None, description="ID du cours Moodle")
    moodle_url                 : Optional[str] = Field(None, description="URL Moodle")

    class Config:
        json_schema_extra = {
            "example": {
                "id_student"        : 3,
                "code_module"       : "MOODLE_2",
                "code_presentation" : "2026J",
                "prenom"            : "Pape",
                "total_clicks"      : 45.0,
                "total_days_active" : 5.0,
                "avg_clicks_per_day": 9.0,
                "last_activity_day" : 12.0,
                "total_span_days"   : 12.0,
                "clicks_recent"     : 10.0,
                "days_active_recent": 3.0,
                "tendance_activite" : 0.22,
                "jours_inactivite"  : 2.0,
                "cutoff_day"        : 14.0,
                "avg_score"         : 52.0,
                "studied_credits"   : 60.0,
                "course_id"         : 123,
                "moodle_url"        : "https://moodle.example.com"
            }
        }