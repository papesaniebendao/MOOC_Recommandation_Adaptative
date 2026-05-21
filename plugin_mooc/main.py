from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import sys, os

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import API_HOST, API_PORT, SEUIL_CRITIQUE, SEUIL_MODERE, GROQ_API_KEY, MOODLE_URL, MOODLE_TOKEN
from schemas.input import StudentData
from models.xgboost_model import get_predictor
from core.explainer import explain_student
from core.recommender import recommend



app = FastAPI(
    title       = "DropGuard API",
    description = "Système de détection précoce d'abandon et recommandation causale — IRD/UGB",
    version     = "2.0.0",
    docs_url    = "/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("[DropGuard] Chargement des modèles...")
    get_predictor()
    print("[DropGuard] API prête.")


@app.get("/health")
async def health_check():
    return {
        "status"       : "ok",
        "version"      : "2.0.0",
        "model"        : "XGBoost DropGuard Final (J28→J140)",
        "recommender"  : "KMeans + Groq",
        "financement"  : "IRD — UGB Saint-Louis"
    }


@app.post("/predict")
async def predict_student(student: StudentData):
    try:
        student_dict  = student.dict()
        dropout_score = get_predictor().predict(student_dict)

        if dropout_score >= SEUIL_CRITIQUE:
            niveau, emoji = "critique", "🔴"
        elif dropout_score >= SEUIL_MODERE:
            niveau, emoji = "modere", "🟠"
        else:
            niveau, emoji = "faible", "🟢"

        shap_dict, cause = explain_student(student_dict)
        prenom = student_dict.get("prenom", "Étudiant")

        # Récupérer vraies ressources Moodle si course_id disponible
        ressources_reelles = []
        course_id = student_dict.get("course_id", None)
        if course_id:
            try:
                from moodle.moodle_client import MoodleClient
                client = MoodleClient(MOODLE_URL, MOODLE_TOKEN)
                ressources_reelles = client.get_resources_by_cause(
                    int(course_id), cause
                )
            except Exception as e:
                print(f"[predict] Erreur ressources Moodle : {e}")

        rec = recommend(
            student_dict, cause, prenom,
            GROQ_API_KEY, ressources_reelles
        )

        return {
            "id_student"        : student_dict.get("id_student"),
            "dropout_score"     : float(round(float(dropout_score), 4)),
            "niveau_risque"     : niveau,
            "emoji_risque"      : emoji,
            "cause_principale"  : cause,
            "cluster_id"        : rec["cluster_id"],
            "cluster_name"      : rec["cluster_name"],
            "ressources"        : rec["activites"],
            "ressources_links"  : rec.get("ressources_links", []),
            "message_motivation": rec["message"],
            "facteurs_shap"     : {
                k: float(round(float(v), 4))
                for k, v in sorted(
                    shap_dict.items(),
                    key=lambda x: abs(float(x[1])),
                    reverse=True
                )[:5]
            },
            "cutoff_utilise"    : 28,
            "version_modele"    : "xgboost_v2_dropguard"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch")
async def predict_batch(students: List[StudentData]):

    if len(students) > 500:
        raise HTTPException(
            status_code=400,
            detail="Maximum 500 étudiants."
        )

    results = []

    for student in students:

        try:
            student_dict = student.dict()

            # ─────────────────────────────────
            # Score
            # ─────────────────────────────────
            dropout_score = get_predictor().predict(student_dict)
            dropout_score = float(dropout_score)

            # ─────────────────────────────────
            # Niveau
            # ─────────────────────────────────
            if dropout_score >= SEUIL_CRITIQUE:
                niveau, emoji = "critique", "🔴"
            elif dropout_score >= SEUIL_MODERE:
                niveau, emoji = "modere", "🟠"
            else:
                niveau, emoji = "faible", "🟢"

            # ─────────────────────────────────
            # SHAP
            # ─────────────────────────────────
            shap_dict, cause = explain_student(student_dict)

            # ─────────────────────────────────
            # Recommandation
            # ─────────────────────────────────
            prenom = str(student_dict.get("prenom", "Étudiant"))

            rec = recommend(
                student_dict,
                cause,
                prenom,
                GROQ_API_KEY
            )

            results.append({
                "id_student"        : int(student_dict.get("id_student", 0)),
                "dropout_score"     : float(round(dropout_score, 4)),
                "niveau_risque"     : niveau,
                "emoji_risque"      : emoji,
                "cause_principale"  : str(cause),

                "cluster_id"        : int(rec["cluster_id"]),
                "cluster_name"      : str(rec["cluster_name"]),

                "ressources"        : list(rec["activites"]),
                "message_motivation": str(rec["message"]),
            })

        except Exception as e:
            print(f"Erreur étudiant {student.id_student}: {e}")
            continue

    critiques = sum(
        1 for r in results
        if r["niveau_risque"] == "critique"
    )

    moderes = sum(
        1 for r in results
        if r["niveau_risque"] == "modere"
    )

    faibles = sum(
        1 for r in results
        if r["niveau_risque"] == "faible"
    )

    return {
        "total"        : len(results),
        "critiques"    : critiques,
        "moderes"      : moderes,
        "faibles"      : faibles,
        "prescriptions": results
    }


@app.get("/moodle/course/{course_id}")
async def analyze_moodle_course(course_id: int):

    try:
        from moodle.moodle_client import get_moodle_client

        client = get_moodle_client()

        students = client.get_enrolled_students(course_id)

        if not students:
            raise HTTPException(
                status_code=404,
                detail="Aucun étudiant trouvé."
            )

        results = []

        for s in students:

            profile = client.get_student_profile(
                s["id"],
                course_id
            )

            profile["code_module"]       = str(course_id)
            profile["code_presentation"] = "moodle"

            dropout_score = get_predictor().predict(profile)
            dropout_score = float(dropout_score)

            shap_dict, cause = explain_student(profile)

            prenom = s.get(
                "fullname",
                "Étudiant"
            ).split()[0]

            rec = recommend(
                profile,
                cause,
                prenom,
                GROQ_API_KEY
            )

            if dropout_score >= SEUIL_CRITIQUE:
                niveau, emoji = "critique", "🔴"
            elif dropout_score >= SEUIL_MODERE:
                niveau, emoji = "modere", "🟠"
            else:
                niveau, emoji = "faible", "🟢"

            results.append({
                "id_student"        : int(s["id"]),
                "fullname"          : str(s.get("fullname", "")),
                "dropout_score"     : float(round(dropout_score, 4)),
                "niveau_risque"     : niveau,
                "emoji_risque"      : emoji,
                "cause_principale"  : str(cause),

                "cluster_id"        : int(rec["cluster_id"]),
                "cluster_name"      : str(rec["cluster_name"]),

                "ressources"        : list(rec["activites"]),
                "message_motivation": str(rec["message"]),
            })

        results.sort(
            key=lambda x: x["dropout_score"],
            reverse=True
        )

        return {
            "course_id"    : course_id,
            "total"        : len(results),
            "critiques"    : sum(
                1 for r in results
                if r["niveau_risque"] == "critique"
            ),
            "prescriptions": results
        }

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        print(f"[ERREUR Moodle] {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )