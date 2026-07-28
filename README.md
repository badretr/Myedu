# Myedu - Plateforme de Gestion Scolaire

Application web moderne developpee avec Django pour la gestion d'un etablissement scolaire.

## Fonctionnalites

- **Accueil** : Fil d'actualites visible par tous
- **Carte etudiant** : Carte numerique avec matricule
- **Messages** : Messagerie interne par classe
- **Suggestions** : Systeme de suggestions anonymes
- **Absences** : Suivi detaille par semestre et matiere
- **Resultats** : Notes avec CC, DS, Examen par semestre
- **Emploi du temps** : Planning hebdomadaire colore
- **Mon Groupe** : Infos classe et sous-groupe
- **Mon Solde** : Etat des paiements par tranche
- **Documents** : Demande de documents administratifs en ligne
- **Admin** : Gestion des comptes, classes, notes, paiements

## Installation rapide

### 1. Installer Python 3.10+ et pip

### 2. Lancer le setup automatique
```
setup.bat
```

### Ou manuellement :
```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Acces

- Application : http://127.0.0.1:8000
- Admin Django : http://127.0.0.1:8000/admin

## Compte par defaut (apres setup.bat)

- Username: `admin`
- Password: `admin123`

## Roles utilisateurs

| Role | Acces |
|------|-------|
| admin | Tout (gestion comptes, classes, notes...) |
| teacher | Saisie notes, envoi messages |
| student | Consultation notes, absences, documents |
| parent | Actualites publiques |

## Technologies

- **Backend** : Django 5.x
- **Base de donnees** : PostgreSQL
- **Frontend** : Bootstrap 5 + Font Awesome 6
- **Style** : CSS custom avec palette Indigo/Teal moderne
