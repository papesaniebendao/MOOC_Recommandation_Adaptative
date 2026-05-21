# 🛡️ DropGuard v2.0 — Guide d'installation et de déploiement

**Système prescriptif de détection précoce de l'abandon dans les MOOCs**  
IRD / UGB Saint-Louis — 2026

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation — Scénario 1 : Moodle existant](#scénario-1--moodle-existant)
4. [Installation — Scénario 2 : Démo rapide avec Docker](#scénario-2--démo-rapide-avec-docker)
5. [Configuration](#configuration)
6. [Lancer le système](#lancer-le-système)
7. [Utilisation](#utilisation)
8. [Architecture technique](#architecture-technique)

---

## Vue d'ensemble

DropGuard est un plugin Moodle qui détecte automatiquement les étudiants à risque d'abandon et génère des recommandations personnalisées.

```
Chaque nuit :
Moodle → Collecte données → API Python → XGBoost + SHAP + KMeans + Groq
→ Score de risque + Cause + Recommandations → Bloc étudiant + Rapport enseignant
```

**Composants :**
- `plugin/dropguard_v2.0_IRD.zip` — Plugin PHP à installer sur Moodle
- `api/` — API FastAPI Python (le cerveau du système)
- `docker/` — Environnement Docker pour démo rapide

---

## Prérequis

### Pour l'API FastAPI
- Python 3.11 ou supérieur
- pip

### Pour Moodle
- Moodle 4.0 ou supérieur
- PHP 8.1 ou supérieur

### Pour la démo Docker
- Docker Desktop installé
- Docker Compose

---

## Scénario 1 — Moodle existant

### Étape 1 — Installer le plugin Moodle

1. Connectez-vous à votre Moodle en tant qu'administrateur
2. Allez dans **Administration du site → Plugins → Installer des plugins**
3. Uploadez le fichier `plugin/dropguard_v2.0_IRD.zip`
4. Cliquez **Installer**
5. Suivez les instructions d'installation
6. Le plugin crée automatiquement les tables nécessaires

### Étape 2 — Installer l'API FastAPI

```bash
# Aller dans le dossier API
cd api/plugin_mooc

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
# Éditer config.py avec vos paramètres
```

### Étape 3 — Configurer config.py

Ouvrez `api/plugin_mooc/config.py` et modifiez :

```python
# URL de votre Moodle
MOODLE_URL = "https://votre-moodle.ugb.edu.sn"

# Token API Moodle (voir étape 4)
MOODLE_TOKEN = "votre_token_ici"

# Clé API Groq (obtenir sur console.groq.com)
GROQ_API_KEY = "votre_cle_groq_ici"
```

### Étape 4 — Créer le token Moodle

1. Allez dans **Administration → Plugins → Services web → Tokens**
2. Créez un token pour le service "DropGuard Service"
3. Copiez le token dans `config.py`

### Étape 5 — Configurer le service web Moodle

Allez dans **Administration → Plugins → Services web → Services externes**  
Ajoutez les fonctions suivantes au service DropGuard :
```
core_webservice_get_site_info
core_enrol_get_enrolled_users
core_user_get_users_by_field
gradereport_user_get_grade_items
core_message_send_messages
core_course_get_contents
```

### Étape 6 — Configurer DropGuard dans Moodle

Depuis MySQL ou MariaDB :
```sql
INSERT INTO mdl_block_dropguard_config 
(api_url, seuil_critique, seuil_modere, cutoff_days, actif, timecreated, timemodified)
VALUES 
('http://adresse-serveur-api:8000', 0.70, 0.50, 28, 1, UNIX_TIMESTAMP(), UNIX_TIMESTAMP());
```

---

## Scénario 2 — Démo rapide avec Docker

### Étape 1 — Lancer Moodle

```bash
cd docker/
docker compose up -d
```

Attendez 2-3 minutes. Moodle sera disponible sur `http://localhost:8080`  
Login : `admin` / Mot de passe : `Admin1234!`

### Étape 2 — Lancer l'API

```bash
cd api/plugin_mooc
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Étape 3 — Installer le plugin

```bash
docker cp plugin/dropguard_v2.0_IRD.zip moodle_app:/var/www/html/blocks/

docker exec -it moodle_app bash -c "
cd /var/www/html/blocks && 
unzip -o dropguard_v2.0_IRD.zip && 
chown -R www-data:www-data dropguard
"

docker exec -it moodle_app bash -c "
php /var/www/html/admin/cli/upgrade.php --non-interactive
"
```

### Étape 4 — Configurer la base

```bash
docker exec -it moodle_db mysql -u moodle -pmoodle_pass moodle -e "
INSERT INTO mdl_block_dropguard_config 
(api_url, seuil_critique, seuil_modere, cutoff_days, actif, timecreated, timemodified)
VALUES 
('http://host.docker.internal:8000', 0.70, 0.50, 28, 1, UNIX_TIMESTAMP(), UNIX_TIMESTAMP());
"
```

---

## Lancer le système

### Lancer l'API FastAPI

```bash
cd api/plugin_mooc
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Vérifier : `http://localhost:8000/health`

### Lancer le cron manuellement (test)

```bash
# Avec Docker
docker exec -it moodle_app bash -c "php /var/www/html/admin/cli/scheduled_task.php --execute='\block_dropguard\task\analyse_students'"

# Sans Docker (Moodle natif)
php /var/www/html/admin/cli/scheduled_task.php --execute='\block_dropguard\task\analyse_students'
```

### Cron automatique

Le cron tourne automatiquement chaque nuit à 2h.  
Pour activer le cron Moodle sur votre serveur :

```bash
# Ajouter dans crontab
* * * * * /usr/bin/php /var/www/html/admin/cli/cron.php
```

---

## Utilisation

### Côté étudiant

L'étudiant voit dans son cours :
- Son message de motivation personnalisé (généré par Groq)
- 3 ressources recommandées avec liens cliquables
- Mis à jour automatiquement chaque nuit

### Côté enseignant

L'enseignant accède au rapport via le bloc DropGuard :
- Tableau de tous les étudiants avec scores et niveaux
- Cause principale du risque pour chaque étudiant
- Liens cliquables vers les ressources recommandées
- Bouton **Notifier** pour envoyer un message personnalisé

### Workflow enseignant

```
1. Voir le rapport → identifier les étudiants critiques
2. Cliquer "Notifier" sur un étudiant
3. Lire le message suggéré par l'IA
4. Modifier avec ses propres mots
5. Cliquer "Envoyer le message"
6. L'étudiant reçoit la notification dans Moodle
```

---

## Architecture technique

```
┌─────────────────────────────────────────────┐
│              Moodle 4.4                     │
│  Étudiant → Logs → Cron (2h) → API         │
└──────────────────────┬──────────────────────┘
                       │ POST /predict
┌──────────────────────▼──────────────────────┐
│           API FastAPI (Python)              │
│  XGBoost → Score     (AUC 0.8908)          │
│  SHAP    → Cause     (4 causes)            │
│  KMeans  → Cluster   (4 profils)           │
│  Groq    → Message   (Llama3-8b)           │
└──────────────────────┬──────────────────────┘
                       │ JSON résultat
┌──────────────────────▼──────────────────────┐
│         Base de données Moodle              │
│  block_dropguard_results                    │
│  Score · Niveau · Cause · Ressources        │
└──────────┬───────────────────┬──────────────┘
           │                   │
   ┌───────▼──────┐   ┌────────▼────────┐
   │ Vue Étudiant │   │ Vue Enseignant  │
   │ Message+Liens│   │ Rapport complet │
   └──────────────┘   └─────────────────┘
```

### Modèle XGBoost

- Dataset : OULAD (32 593 étudiants, Open University UK)
- Features : 85 (cumulatives + récentes 14j + tendance)
- Cutoffs couverts : J28 → J140
- AUC-ROC : 0.8908 (test set)
- Validation : GroupKFold 5 folds (sans overlap étudiant)

### Clusters comportementaux (KMeans K=4)

| Cluster | Nom | Taux abandon |
|---------|-----|-------------|
| 0 | Engagés Modérés | 16.9% |
| 1 | À Risque Critique | 69.1% |
| 2 | Bien Engagés | 23.6% |
| 3 | Hyper Engagés | 10.7% |

### Causes identifiées par SHAP

| Cause | Description | Ressources recommandées |
|-------|-------------|------------------------|
| inactivite | Absence prolongée | Pages courtes, contenus |
| difficulte_academique | Mauvaises notes | Quiz, exercices |
| surcharge | Trop de crédits | Pages essentielles |
| desengagement_module | Peu d'interactions | Forums, discussions |

---

## Variables d'environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `MOODLE_URL` | URL de votre Moodle | `https://moodle.ugb.edu.sn` |
| `MOODLE_TOKEN` | Token API Moodle | `9d5cf986...` |
| `GROQ_API_KEY` | Clé API Groq | `gsk_...` |

---

## Support

Projet développé dans le cadre d'un Master en Informatique  
Financé par l'IRD — Université Gaston Berger, Saint-Louis, Sénégal  
Contact : ndaopapesaniebe3@gmail.com

---

*DropGuard v2.0 — Mai 2026*
