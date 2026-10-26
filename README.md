# Sutura

MVP PWA d’alertes communautaires de quartier à Dakar, avec API Flask.

## Démarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Ouvrir `http://localhost:5000`. En mode debug, le code OTP de développement est affiché dans l’interface (`1234` pendant les tests).

Si le port 5000 est occupé sur macOS (souvent par AirPlay Receiver), utiliser un autre port :

```bash
PORT=5001 python run.py
```

Puis ouvrir `http://localhost:5001`.

## Backoffice

Le numéro administrateur est défini par `ADMIN_TELEPHONE` (par défaut en local : `+221770000000`). Connectez-vous d’abord à l’application avec ce numéro, puis ouvrez `/admin`. Configurez impérativement cette variable dans chaque environnement déployé.

## Tests

```bash
pytest tests/backend -q
npm install
npm test
```

Importer également `tests/backend/postman/Sutura.postman_collection.json` dans Postman, sélectionner l’environnement local fourni et lancer la collection dans l’ordre. Le script mémorise automatiquement le jeton et l’identifiant de l’alerte.

Les spécifications se trouvent dans [docs/specifications-fonctionnelles.md](docs/specifications-fonctionnelles.md) et [docs/specifications-techniques.md](docs/specifications-techniques.md).
