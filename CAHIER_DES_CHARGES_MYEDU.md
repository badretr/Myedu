# Cahier des charges - Myedu

## 1. Présentation du projet

Myedu est une plateforme web de gestion scolaire développée avec Django. Elle centralise les services destinés à un établissement d'enseignement : gestion des utilisateurs, scolarité, notes, absences, emploi du temps, paiements, messagerie interne et demandes de documents administratifs.

L'application vise trois objectifs principaux :

1. Simplifier le suivi administratif et pédagogique.
2. Donner aux étudiants un espace personnel de consultation.
3. Fournir à l'administration des outils de pilotage et de publication.

## 2. Périmètre fonctionnel

Le périmètre couvre les modules suivants :

- Authentification et gestion des comptes.
- Gestion des classes, inscriptions et années académiques.
- Gestion des matières, semestres, notes et absences.
- Consultation et dépôt d'emplois du temps.
- Messagerie interne et publication d'actualités.
- Suggestions anonymes ou nominatives.
- Suivi financier par tranches de paiement.
- Demande de documents administratifs en ligne.
- Administration générale via l'interface Django Admin.

## 3. Acteurs et rôles

### 3.1 Administrateur

- Crée, modifie et supprime les comptes.
- Gère les classes, les matières, les inscriptions et les semestres.
- Saisit ou supervise les notes, absences, paiements et demandes de documents.
- Publie des actualités et consulte les suggestions.

### 3.2 Enseignant

- Consulte les classes et matières qui lui sont affectées.
- Saisit ou met à jour les notes.
- Peut envoyer des messages liés à une classe.

### 3.3 Étudiant

- Consulte son profil, sa carte étudiant et son matricule.
- Consulte ses notes, absences, emploi du temps et solde.
- Reçoit les messages de sa classe et les actualités publiques.
- Dépose des demandes de documents administratifs.
- Envoie des suggestions.

### 3.4 Parent

- Accède aux actualités publiques et aux informations disponibles selon les droits définis.

## 4. Besoins fonctionnels détaillés

### 4.1 Accueil et actualités

- Afficher une page d'accueil publique.
- Publier des actualités visibles par tous ou réservées selon la configuration.
- Permettre la suppression d'une actualité par un utilisateur autorisé.

### 4.2 Authentification et comptes

- Connexion et déconnexion des utilisateurs.
- Consultation du profil personnel.
- Création, édition et suppression des utilisateurs par un administrateur.
- Gestion des attributs de compte : rôle, téléphone, adresse, photo, date de naissance, nationalité.

### 4.3 Gestion académique

- Créer et gérer les années académiques, avec une seule année courante à la fois.
- Créer et gérer les classes, spécialités, cycles et groupes.
- Affecter un étudiant à une classe via une inscription unique.
- Générer et afficher un matricule unique.
- Gérer les sous-groupes.
- Créer et gérer les matières, enseignants affectés, coefficients et volumes horaires.
- Créer les semestres et associer les dates de début et de fin.

### 4.4 Notes et résultats

- Saisir les notes par étudiant, matière et semestre.
- Prendre en charge les composantes CC, DS, Examen et Contrôle.
- Calculer une moyenne pondérée à partir des notes disponibles.
- Éviter les doublons pour une combinaison étudiant-matière-semestre.

### 4.5 Absences

- Enregistrer les absences par étudiant, matière et date.
- Indiquer la durée en heures.
- Marquer une absence comme justifiée ou non.
- Ajouter un motif de justification.

### 4.6 Emploi du temps

- Importer un emploi du temps au format image.
- Associer un emploi du temps à une classe.
- Conserver une date de version et la date d'import.
- Afficher l'emploi du temps correspondant à l'utilisateur connecté.

### 4.7 Messagerie interne

- Créer des messages avec titre, contenu et éventuellement pièce jointe.
- Envoyer un message à une classe précise ou à tous les destinataires.
- Suivre les messages lus et non lus.

### 4.8 Suggestions

- Permettre aux utilisateurs d'envoyer une suggestion.
- Classer la suggestion par catégorie et sous-catégorie.
- Gérer l'anonymat de l'expéditeur.
- Suivre l'état de traitement de la suggestion.

### 4.9 Suivi financier

- Afficher le solde de l'étudiant.
- Gérer les tranches de paiement par inscription.
- Suivre le montant demandé, payé et restant.
- Indiquer les dates d'échéance et de paiement.
- Calculer automatiquement si une tranche est soldée.

### 4.10 Documents administratifs

- Permettre la demande de documents en ligne.
- Gérer les types de documents : carte étudiant, certificat d'inscription, attestation de présence, attestation de réussite, relevé de notes.
- Suivre le statut de traitement : en attente, en traitement, prêt, livré, rejeté.
- Ajouter des notes administratives à la demande.

## 5. Modèle de données cible

Les entités principales du système sont :

- Utilisateur personnalisé.
- Année académique.
- Classe.
- Inscription étudiant.
- Matière.
- Semestre.
- Note.
- Absence.
- Emploi du temps.
- Actualité.
- Message.
- Suggestion.
- Tranche de paiement.
- Demande de document.

## 6. Exigences non fonctionnelles

### 6.1 Sécurité

- Authentification obligatoire pour les pages privées.
- Contrôle d'accès par rôle.
- Protection des données personnelles.
- Gestion sécurisée des fichiers téléversés.

### 6.2 Performance

- Temps de réponse rapide pour les consultations courantes.
- Pagination des listes volumineuses si nécessaire.
- Optimisation des requêtes liées aux notes, absences et messages.

### 6.3 Maintenabilité

- Architecture modulaire par application Django.
- Séparation claire entre présentation, logique métier et données.
- Code compatible avec les évolutions futures du référentiel scolaire.

### 6.4 Expérience utilisateur

- Interface claire, responsive et adaptée aux mobiles.
- Navigation simple par profil utilisateur.
- Lisibilité forte des données administratives et académiques.

## 7. Interfaces principales

- Page d'accueil publique.
- Tableau de bord utilisateur.
- Profil et carte étudiant.
- Liste des messages et détail d'un message.
- Formulaire de suggestion.
- Page des notes et absences.
- Emploi du temps.
- Suivi des paiements.
- Formulaire de demande de document.
- Interface d'administration des classes et utilisateurs.

## 8. Contraintes techniques

- Backend basé sur Django.
- Base de données relationnelle, SQLite en développement et PostgreSQL en production.
- Stockage des médias pour les photos, pièces jointes et emplois du temps.
- Utilisation de Bootstrap et de CSS personnalisé côté interface.

## 9. Critères d'acceptation

Le projet sera considéré comme conforme si :

- Un utilisateur peut se connecter selon son rôle.
- Un administrateur peut gérer les comptes, classes et inscriptions.
- Les notes, absences et paiements sont consultables et cohérents.
- Les étudiants peuvent consulter leur espace personnel et envoyer une demande de document.
- La messagerie, les actualités et les suggestions fonctionnent correctement.
- Les fichiers téléversés sont affichés et associés au bon objet métier.

## 10. Livrables attendus

- Code source de l'application Django.
- Base de données de développement et scripts de migration.
- Documentation d'installation et d'utilisation.
- Cahier des charges fonctionnel.
- Interface web prête pour test utilisateur.

## 11. Hypothèses et limites

- Le document est rédigé à partir de l'état actuel du dépôt.
- Certains droits d'accès peuvent être affinés dans l'implémentation des vues et formulaires.
- Le système suppose une gestion centralisée par établissement.

## 12. Conclusion

Myedu répond à un besoin de digitalisation complète de la vie scolaire. Le projet couvre les usages administratifs, académiques et de communication essentiels pour un établissement, avec une structure modulaire qui permet d'ajouter des fonctions complémentaires par la suite.