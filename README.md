# Le Collecteur

## 1. Présentation

**Le Collecteur** est une application Python (FastAPI) permettant de :
- Gérer une liste de serveurs distants (ajout, suppression, édition, liste)
- Se connecter en SSH à ces serveurs (clé privée ou mot de passe)
- Exécuter des scripts shell à distance et récupérer les logs
- Interface web moderne (HTML/Jinja2, notifications, tableau de bord, navigation rapide)
- Historique détaillé des exécutions
- Préparer l'intégration avec Centreon (à venir)

---

## 2. Installation & Lancement

### Prérequis
- Python 3.8+
- AlmaLinux 8 (ou tout Linux compatible)
- Accès SSH aux serveurs cibles

### Installation des dépendances

```bash
python -m venv venv
# Sous Windows
.\venv\Scripts\activate
# Sous Linux/Mac
source venv/bin/activate

pip install fastapi uvicorn[standard] sqlalchemy aiosqlite databases paramiko jinja2 aiofiles python-multipart
```

### Lancement de l'API

```bash
uvicorn main:app --reload
```

L'API est accessible sur :  
http://127.0.0.1:8000  
La documentation interactive (Swagger UI) :  
http://127.0.0.1:8000/docs

---

## 3. Structure des fichiers

- `main.py` : Application FastAPI, endpoints API et web
- `models.py` : Modèle SQLAlchemy pour les serveurs et les logs
- `database.py` : Initialisation de la base SQLite
- `templates/` : Fichiers HTML Jinja2 pour l'interface web
- `static/` : Fichiers statiques (CSS, images)

---

## 4. Fonctionnalités de l'API et de l'interface web

### 4.1. Interface web moderne

- **Tableau de bord** :
  - Nombre de serveurs, nombre d'exécutions, derniers logs
  - Navigation rapide vers la gestion des serveurs et l'historique
- **Notifications** :
  - Messages de succès ou d'erreur après chaque action (ajout, édition, suppression, exécution)
  - Affichage moderne et coloré
- **Navigation** :
  - Liens directs entre toutes les pages principales (tableau de bord, gestion, historique, édition)
- **Responsive design** :
  - Affichage adapté sur mobile et ordinateur
- **Style moderne** :
  - Fond dégradé, cartes arrondies, boutons stylés, tableaux interactifs

### 4.2. Gestion des serveurs

#### Ajouter un serveur

- **Via l'API** :
  - **POST /serveurs/**  
    Payload JSON :
    ```json
    {
      "nom": "ServeurTest",
      "adresse_ip": "192.168.1.10",
      "utilisateur_ssh": "root",
      "port_ssh": 22,
      "chemin_cle_privee": "C:\\Users\\INET\\.ssh\\id_rsa", // ou null
      "mot_de_passe": null // ou "votre_mot_de_passe"
    }
    ```
- **Via l'interface web** :
  - Formulaire en haut de la page [http://127.0.0.1:8000/serveurs_html](http://127.0.0.1:8000/serveurs_html)

#### Lister les serveurs

- **GET /serveurs/** (API)
- **Page web** : [http://127.0.0.1:8000/serveurs_html](http://127.0.0.1:8000/serveurs_html)

#### Supprimer un serveur

- **DELETE /serveurs/{serveur_id}** (API)
- **Bouton "Supprimer"** dans l'interface web

#### Éditer un serveur

- **Via l'interface web** :
  - Bouton "Éditer" → formulaire pré-rempli
  - Modifie et enregistre

---

### 4.3. Exécution de scripts à distance

- **POST /serveurs/{serveur_id}/executer_script** (API)
  - Payload JSON :
    ```json
    {
      "script": "echo Hello World"
    }
    ```
- **Via l'interface web** :
  - Champ "Exécuter" pour chaque serveur
  - Résultat affiché sous le tableau après exécution

---

### 4.4. Historique des exécutions

- **Chaque exécution est historisée** (date, script, stdout, stderr, erreur)
- **Lien "Historique"** pour chaque serveur
- **Page dédiée** avec tous les détails des exécutions passées

---

## 5. Réinitialisation de la base de données

Pour repartir de zéro, supprime le fichier `collecteur.db` dans le dossier du projet :
```powershell
del collecteur.db
```
ou
```bash
rm collecteur.db
```
Relance ensuite l'application.

---

## 6. Tests

- Utilise l'interface Swagger UI (`/docs`) pour tester tous les endpoints API.
- Utilise l'interface web pour toutes les opérations courantes.
- Tu peux ajouter, éditer, supprimer des serveurs, exécuter des scripts, consulter l'historique, et naviguer facilement.

---

## 7. Sécurité

- Les mots de passe et chemins de clés privées sont stockés en clair dans la base SQLite (à sécuriser pour la production).
- L'API et l'interface web sont protégées par une authentification (login/mot de passe).

---

## 8. Déploiement avec Docker

1. Construire l'image Docker :

```bash
docker build -t le-collecteur .
```

2. Lancer le conteneur :

```bash
docker run -d -p 8000:8000 --name collecteur le-collecteur
```

- L'application sera accessible sur http://localhost:8000
- **Persistance de la base de données** :
  Pour conserver la base de données même après arrêt/suppression du conteneur, monte un volume sur `/app` :
  ```bash
  docker run -d -p 8000:8000 -v $(pwd):/app --name collecteur le-collecteur
  ```
  (Sous Windows, adapte la syntaxe du chemin si besoin)
- **Arrêter le conteneur** :
  ```bash
  docker stop collecteur
  ```
- **Supprimer le conteneur** :
  ```bash
  docker rm collecteur
  ```
- **Changer le port** :
  Modifie le mapping `-p` (ex : `-p 8080:8000` pour accéder sur http://localhost:8080)

### Utilisation de Docker Compose (optionnel)

Pour gérer la persistance et la configuration plus facilement, tu peux créer un fichier `docker-compose.yml` :

```yaml
version: '3.8'
services:
  collecteur:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app
    environment:
      - TZ=Europe/Paris
    restart: unless-stopped
```

- Lance avec :
  ```bash
  docker-compose up -d
  ```
- Les données seront persistées dans le dossier `./data` sur ta machine.

### Conseils sécurité production
- Change la clé secrète de session dans `main.py` (paramètre `SessionMiddleware`)
- Utilise un reverse proxy (Nginx, Traefik) pour gérer HTTPS
- Gère les variables sensibles (mot de passe admin, etc.) via variables d'environnement ou fichiers secrets

---

## 9. Planification de tâches (exécution automatique de scripts)

- Accès via le menu « Tâches planifiées » sur toutes les pages
- Formulaire pour planifier un script sur un serveur à une date/heure donnée, avec récurrence possible (quotidienne, hebdomadaire)
- Les tâches sont exécutées automatiquement par le collecteur (scheduler intégré)
- Chaque exécution génère un log (visible dans l'historique du serveur)
- En cas d'échec automatique, une notification visuelle s'affiche sur le dashboard et un badge rouge apparaît sur le menu « Tâches planifiées  »

---

*Ce fichier sera mis à jour à chaque évolution du projet.* 