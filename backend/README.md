# Smart Elderly Monitoring System — Backend

Backend FastAPI pour le système de télésurveillance des personnes âgées (Smart Elderly Monitoring System).

Ce socle technique constitue la **Phase 0** du projet : configuration de l'infrastructure, gestion asynchrone PostgreSQL, broker Mosquitto MQTT, architecture en couches, vérification de l'état de santé et chaîne de qualité (linters, typage statique et tests automatisés).

---

## 1. Prérequis

* **Système d'exploitation** : Windows 10/11 (ou Linux / macOS)
* **Python** : 3.12.x (vérifier avec `py -3.12 --version`)
* **Docker Desktop** : avec Docker Compose v2 actif
* **Git** : installé et configuré

---

## 2. Installation & Configuration Locale

Ouvrez un terminal Windows PowerShell :

```powershell
# Cloner le repository si ce n'est pas déjà fait
git clone https://github.com/selmahacii/hackdotIA.git
cd hackdotIA\backend

# Créer l'environnement virtuel avec Python 3.12
py -3.12 -m venv .venv

# Activer l'environnement virtuel
.\.venv\Scripts\Activate.ps1

# Mettre à jour pip et les outils de packaging
python -m pip install --upgrade pip setuptools wheel

# Installer les dépendances du projet
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Vérifier la cohérence des dépendances
pip check
```

---

## 3. Configuration de l'environnement (.env)

Copiez le fichier `.env.example` en `.env` :

```powershell
Copy-Item .env.example .env
```

> **Note importante sur le port PostgreSQL** :
> Si votre machine exécute déjà une instance locale Windows de PostgreSQL sur le port `5432`, Docker compose mappe PostgreSQL sur le port hôte `5433` (`5433:5432`) pour éviter tout conflit.
> La variable `DATABASE_URL` dans `.env` est configurée par défaut avec :
> `postgresql+asyncpg://elderly:elderly@localhost:5433/elderly`

---

## 4. Démarrage de l'infrastructure Docker

Démarrez les services de base de données PostgreSQL 16 et le broker MQTT Eclipse Mosquitto :

```powershell
# Démarrer les services en arrière-plan
docker compose up -d postgres mosquitto

# Vérifier l'état des conteneurs
docker compose ps
```

---

## 5. Migrations de base de données (Alembic)

Vérifiez l'état d'Alembic :

```powershell
alembic current
alembic heads
```

---

## 6. Lancement du serveur FastAPI

Lancez l'application en mode développement local :

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

L'API est alors accessible sur :
* Swagger UI : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* ReDoc : [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 7. Endpoints de Santé & Disponibilité

### Health Check (liveness)
Vérifie que le serveur web répond :
```powershell
curl http://127.0.0.1:8000/api/v1/health
```
Réponse attendue (HTTP 200) :
```json
{
  "status": "ok"
}
```

### Readiness Check
Vérifie que la connexion avec PostgreSQL est active :
```powershell
curl http://127.0.0.1:8000/api/v1/ready
```
Réponse attendue lorsque la base est connectée (HTTP 200) :
```json
{
  "status": "ready",
  "database": "connected"
}
```
Si PostgreSQL est indisponible (HTTP 503) :
```json
{
  "status": "not ready",
  "database": "disconnected"
}
```

---

## 8. Tests Automatisés & Qualité de Code

Exécutez la suite de tests et les contrôles de conformité :

```powershell
# Lancer les tests unitaires et d'intégration
pytest -v

# Lancer les tests avec couverture de code
pytest --cov=app --cov-report=term-missing

# Vérifier le style et les règles de linting avec Ruff
ruff check app tests

# Vérifier le formatage avec Black
black --check app tests

# Contrôler le typage statique strict avec Mypy
mypy app tests
```
