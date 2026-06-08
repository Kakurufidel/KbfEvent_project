# Event Management System V1

Application web de gestion d'événements permettant aux organisateurs de créer des événements, gérer les invités, et suivre les RSVP.

## Fonctionnalités

- Authentification des organisateurs (email + mot de passe)
- CRUD complet des événements
- Gestion des invités avec import manuel
- RSVP public par token unique
- Tableau de bord avec statistiques
- Export CSV et Excel
- Support multilingue (français, anglais, swahili)

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-depot>
cd event_management_v1
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Créer la base de données PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE event_management_db;"
```

### 5. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer le fichier `.env` avec vos informations.

### 6. Appliquer les migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Créer les fichiers de traduction

```bash
python manage.py makemessages -l fr -l en -l sw
python manage.py compilemessages
```

### 8. Créer un superutilisateur (optionnel)

```bash
python manage.py createsuperuser
```

### 9. Lancer le serveur

```bash
python manage.py runserver
```

## Structure du projet

```
event_management_v1/
├── manage.py
├── requirements.txt
├── .env
├── event_management/       # Configuration Django
├── apps/
│   ├── authentication/     # Gestion des utilisateurs
│   ├── events/            # Gestion des événements
│   └── guests/            # Gestion des invités
├── templates/             # Templates Bootstrap 5
├── static/                # Fichiers statiques
└── media/                 # Uploads
```

## Technologies

- Django 5.0+
- PostgreSQL
- Bootstrap 5
- Pillow (gestion d'images)
- openpyxl (export Excel)
