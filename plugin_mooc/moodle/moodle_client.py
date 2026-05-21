
import requests
import json
from typing import List, Dict, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MOODLE_URL, MOODLE_TOKEN

class MoodleClient:
    """
    Client pour l'API REST Moodle.
    Récupère les données des étudiants depuis Moodle
    et envoie les résultats du plugin.
    """

    def __init__(self, url: str = None, token: str = None):
        self.base_url = (url or MOODLE_URL).rstrip('/')
        self.token    = token or MOODLE_TOKEN
        self.api_url  = f"{self.base_url}/webservice/rest/server.php"

    def _call(self, function: str, params: dict = {}) -> dict:
        """Appel générique à l'API REST Moodle."""
        payload = {
            'wstoken'        : self.token,
            'wsfunction'     : function,
            'moodlewsrestformat': 'json',
            **params
        }
        try:
            response = requests.post(self.api_url, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'exception' in data:
                raise ValueError(f"Moodle API error: {data.get('message', 'Unknown')}")
            return data
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Impossible de contacter Moodle: {self.base_url}")

    def get_enrolled_students(self, course_id: int) -> List[dict]:
        """
        Récupère la liste des étudiants inscrits à un cours.
        Fonction Moodle : core_enrol_get_enrolled_users
        """
        data = self._call(
            'core_enrol_get_enrolled_users',
            {'courseid': course_id}
        )
        students = []
        for user in data:
            # Garder uniquement les étudiants (pas les profs)
            roles = [r.get('shortname') for r in user.get('roles', [])]
            if 'student' in roles or not roles:
                students.append({
                    'id'       : user.get('id'),
                    'username' : user.get('username'),
                    'fullname' : user.get('fullname'),
                    'email'    : user.get('email'),
                })
        return students

    def get_student_logs(
        self,
        course_id : int,
        user_id   : int,
        date_from : Optional[int] = None
    ) -> List[dict]:
        """
        Récupère les logs d'activité d'un étudiant dans un cours.
        Fonction Moodle : core_user_get_course_user_profiles (simplifié)
        """
        params = {
            'courseid' : course_id,
            'userid'   : user_id,
        }
        if date_from:
            params['datefrom'] = date_from

        # Note: En production, utiliser report_log ou get_logs
        # selon la version Moodle et les permissions
        try:
            data = self._call('core_completion_get_activities_completion_status', params)
            return data.get('statuses', [])
        except:
            return []

    def get_student_grades(self, course_id: int, user_id: int) -> dict:
        """
        Récupère les notes d'un étudiant.
        Fonction Moodle : gradereport_user_get_grade_items
        """
        try:
            data = self._call(
                'gradereport_user_get_grade_items',
                {'courseid': course_id, 'userid': user_id}
            )
            items     = data.get('usergrades', [{}])[0].get('gradeitems', [])
            scores    = [float(item.get('percentageformatted', '0').replace('%','').strip() or 0)
                         for item in items if item.get('percentageformatted')]
            avg_score = sum(scores) / len(scores) if scores else None
            return {
                'avg_score'               : avg_score,
                'num_submitted_assessments': len(scores)
            }
        except:
            return {'avg_score': None, 'num_submitted_assessments': 0}

    def get_student_profile(self, user_id: int, course_id: int) -> dict:
        """
        Récupère le profil complet d'un étudiant.
        Combine logs + notes + profil utilisateur.
        """
        try:
            profile_data = self._call(
                'core_user_get_users_by_field',
                {'field': 'id', 'values[0]': user_id}
            )
            user = profile_data[0] if profile_data else {}
        except:
            user = {}

        grades = self.get_student_grades(course_id, user_id)

        return {
            'id_student'               : user_id,
            'fullname'                 : user.get('fullname', ''),
            'email'                    : user.get('email', ''),
            'avg_score'                : grades.get('avg_score'),
            'num_submitted_assessments': grades.get('num_submitted_assessments', 0),
            'studied_credits'          : 60.0,  # À récupérer selon config Moodle
        }

    def send_notification(
        self,
        user_id : int,
        subject : str,
        message : str
    ) -> bool:
        """
        Envoie une notification à un étudiant via Moodle.
        Fonction Moodle : core_message_send_messages
        """
        try:
            self._call(
                'core_message_send_messages',
                {
                    'messages[0][touserid]' : user_id,
                    'messages[0][text]'     : message,
                    'messages[0][textformat]': 0,
                    'messages[0][subject]'  : subject,
                }
            )
            return True
        except Exception as e:
            print(f"Erreur notification: {e}")
            return False

    def test_connection(self) -> bool:
        """Teste la connexion à Moodle."""
        try:
            data = self._call('core_webservice_get_site_info')
            print(f"[MoodleClient] Connecté à : {data.get('sitename', 'Moodle')}")
            print(f"[MoodleClient] Version    : {data.get('release', '?')}")
            return True
        except Exception as e:
            print(f"[MoodleClient] Connexion échouée : {e}")
            return False
        
    def get_course_resources(self, course_id: int) -> list:
        """
        Récupère toutes les ressources d'un cours Moodle.
        Retourne une liste structurée par type.
        """
        try:
            data = self._call('core_course_get_contents',
                            {'courseid': course_id})
            resources = []
            for section in data:
                for mod in section.get('modules', []):
                    # Ignorer Announcements (forum système)
                    if mod.get('name') == 'Announcements':
                        continue
                    resources.append({
                        'id'      : mod['id'],
                        'name'    : mod['name'],
                        'type'    : mod['modname'],
                        'url'     : mod.get('url', ''),
                        'section' : section['name'],
                    })
            return resources
        except Exception as e:
            print(f"[MoodleClient] Erreur get_course_resources: {e}")
            return []

    def get_resources_by_cause(
        self, course_id: int, cause: str
    ) -> list:
        """
        Filtre les ressources selon la cause SHAP.
        Retourne les 3 ressources les plus pertinentes.
        """
        all_resources = self.get_course_resources(course_id)

        # Mapping cause → types de ressources prioritaires
        CAUSE_PRIORITY = {
            'inactivite': ['page', 'url', 'forum'],
            'difficulte_academique': ['quiz', 'page', 'forum'],
            'surcharge': ['page', 'url'],
            'desengagement_module': ['forum', 'quiz', 'page'],
        }

        priority_types = CAUSE_PRIORITY.get(
            cause, ['page', 'forum', 'quiz']
        )

        # Trier par priorité
        sorted_resources = []
        for ptype in priority_types:
            matching = [r for r in all_resources
                        if r['type'] == ptype]
            sorted_resources.extend(matching)

        # Ajouter le reste
        for r in all_resources:
            if r not in sorted_resources:
                sorted_resources.append(r)

        return sorted_resources[:3]


# Instance singleton
_client_instance = None

def get_moodle_client() -> MoodleClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = MoodleClient()
    return _client_instance 
    

