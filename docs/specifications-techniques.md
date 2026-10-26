# Sutura — Spécifications techniques

## 1. Architecture

- Backend : Python 3.11+, Flask 3, Flask-SQLAlchemy, API JSON REST.
- Données : SQLite pour le MVP ; la couche SQLAlchemy permet une migration vers PostgreSQL.
- Frontend : PWA responsive sans framework, modules JavaScript ES, HTML sémantique, CSS mobile-first et Leaflet 1.9.4 avec tuiles OpenStreetMap.
- Authentification : OTP hashé en base, session stateless par JWT HS256.
- Médias : Pillow, conversion WebP, dimension maximale 1600 × 1600, poids maximal 200 Ko.
- Offline : service worker pour le shell applicatif et `localStorage` pour le dernier fil obtenu.

## 2. API

| Méthode | Route | Accès | Fonction |
|---|---|---|---|
| GET | `/health` | Public | Santé du service |
| GET | `/api/metadata` | Public | Catégories et quartiers |
| POST | `/api/auth/request-otp` | Public | Demande d’OTP |
| POST | `/api/auth/verify-otp` | Public | Validation et émission du JWT |
| GET/PATCH | `/api/auth/profile` | JWT | Lecture/mise à jour du profil |
| GET | `/api/alerts` | JWT | Fil filtré (`scope`, `categorie`) |
| POST | `/api/alerts` | JWT | Création JSON ou multipart |
| POST | `/api/alerts/{id}/confirm` | JWT | Confirmation unique |
| POST | `/api/alerts/{id}/resolve` | JWT auteur | Résolution |
| GET | `/api/geo/reverse` | Public | Géocodage inversé et contrôle Sénégal |
| GET | `/api/geo/search` | Public | Recherche nationale de territoires |
| GET | `/api/admin/dashboard` | JWT administrateur | Pilotage et filtres |
| PATCH | `/api/admin/alerts/{id}` | JWT administrateur | Priorité, statut et affectation |
| GET/POST | `/api/admin/groups` | JWT administrateur | Liste et création de groupes |
| PATCH/DELETE | `/api/admin/groups/{id}` | JWT administrateur | Modification/désactivation |
| GET | `/api/admin/users` | JWT administrateur | Recherche des utilisateurs |
| POST/PATCH/DELETE | `/api/admin/groups/{id}/members...` | JWT administrateur | Adhésions et lead |
| GET | `/api/work/alerts` | JWT membre | Alertes de ses groupes uniquement |
| PATCH | `/api/work/alerts/{id}` | JWT membre affecté | Avancement du traitement |

Les erreurs ont la forme `{ "error": "message" }`. Les statuts employés sont 200/201, 400, 401, 403, 404, 409 et 413.

## 3. Sécurité et production

- Utiliser un `SECRET_KEY` aléatoire injecté par secret manager et HTTPS uniquement.
- Brancher `issue_otp` sur un fournisseur SMS, ne jamais retourner l’OTP au client en production.
- Ajouter limitation de débit sur OTP et authentification, expiration/nettoyage des enregistrements OTP et journal d’audit.
- Stocker les médias dans un stockage objet avec URL signée et analyse antivirus.
- Migrer sur PostgreSQL, utiliser Alembic, désactiver le mode debug et placer Flask derrière Gunicorn/Nginx.
- Ajouter consentement, politique de confidentialité et mécanisme de suppression des données personnelles.

## 4. Structure

```text
app/                 application Flask, API, services et PWA
docs/                spécifications fonctionnelles et techniques
tests/backend/       tests pytest et collection Postman
tests/frontend/      tests unitaires du code navigateur
run.py               point d’entrée local
```
