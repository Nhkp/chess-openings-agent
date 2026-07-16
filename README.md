# Projet 13 - Agent ouvertures d'echecs

POC local pour un agent IA d'entrainement aux ouvertures d'echecs.

## Services

- `frontend` : Angular + ngx-chess-board, expose sur `http://localhost:${FRONTEND_PORT:-4200}`
- `api` : FastAPI, expose sur `http://localhost:${API_PORT:-8000}`
- `mongodb` : historisation des interactions de l'agent IA
- `milvus`, `etcd`, `minio` : recherche vectorielle et stockage persistant
- `seed-openings` : charge le petit corpus d'ouvertures dans Milvus au demarrage

## Prerequis

- Docker et Docker Compose
- uv
- Node.js 20 si vous lancez Angular hors Docker

## Configuration

```bash
cp .env.example .env
```

Renseigner les secrets utiles dans `.env` :

- `LICHESS_TOKEN` pour l'Opening Explorer Lichess
- `YOUTUBE_API_KEY` pour l'API YouTube Data v3

Les variables `MONGODB_URI`, `MONGODB_DATABASE` et
`MONGODB_EVENTS_COLLECTION` pilotent l'historique agent. Les valeurs de
`.env.example` fonctionnent avec Docker Compose.

`EMBEDDING_MODEL` identifie le modele d'embedding utilise pour indexer les
chunks d'ouvertures dans Milvus. La valeur par defaut reste legere pour le POC.

## Demarrage Docker

```bash
docker compose up --build
```

Ouvrir ensuite `http://localhost:4200`.

Le premier demarrage peut etre long car l'image Milvus est volumineuse. Si le
chargement du corpus echoue parce que Milvus n'est pas encore pret, relancer :

```bash
docker compose run --rm seed-openings
```

## Backend local

```bash
uv sync --locked
uv run uvicorn backend.app.main:app --reload
```

Verifier le service :

```bash
curl http://localhost:8000/api/v1/healthcheck
```

Interroger les coups theoriques Lichess pour une FEN :

```bash
curl --get "http://localhost:8000/api/v1/moves" \
  --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

Evaluer une position avec Stockfish :

```bash
curl --get "http://localhost:8000/api/v1/evaluate" \
  --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

Demander une recommandation unifiee a l'agent LangGraph :

```bash
curl --get "http://localhost:8000/api/v1/coach" \
  --data-urlencode "fen=rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2" \
  --data-urlencode "opening=Defense sicilienne"
```

## Donnees vectorielles

Preprocesser les sources Wikichess et generer les chunks :

```bash
uv run python -m backend.scripts.preprocess_wikichess
```

Charger ou recharger le jeu de donnees d'ouvertures :

```bash
docker compose up -d milvus
uv run python -m backend.scripts.load_openings
```

Rechercher du contexte :

```bash
curl "http://localhost:8000/api/v1/vector-search?opening=sicilienne"
```

## Historique agent

Les analyses de position, recherches de contexte et recherches de videos sont
journalisees dans MongoDB. Consulter les derniers evenements :

```bash
curl "http://localhost:8000/api/v1/history?limit=20"
```

## Videos

```bash
curl --get "http://localhost:8000/api/v1/videos" \
  --data-urlencode "opening=Defense sicilienne"
```

Renseigner `YOUTUBE_API_KEY` dans `.env` avant d'appeler cet endpoint.

## Postman

Une collection Postman est disponible dans
[docs/postman/Projet_13_API.postman_collection.json](docs/postman/Projet_13_API.postman_collection.json).
Importer aussi l'environnement local
[docs/postman/Projet_13_Local.postman_environment.json](docs/postman/Projet_13_Local.postman_environment.json).

Demarrer le stack avant de lancer les requetes :

```bash
docker compose up --build
```

Dans Postman, selectionner l'environnement `Projet 13 - Local`, puis lancer les
requetes dans cet ordre :

1. `Healthcheck`
2. `Moves by FEN`
3. `Evaluate by FEN`
4. `Coach recommendation`
5. `Vector search`
6. `Videos`
7. `History`

Le dossier `Backend direct` cible `http://localhost:8000`. Le dossier
`Via frontend proxy` cible `http://localhost:4200` pour verifier nginx.

## Frontend local

```bash
cd frontend
npm ci
npm start
```

Le proxy Angular redirige `/api` vers `http://localhost:8000`.

## Tests et CI

Le plan de couverture est detaille dans [docs/testing-plan.md](docs/testing-plan.md).

```bash
uv run coverage run -m unittest discover -s backend/tests
uv run coverage report
cd frontend
npm run test:ci
```

GitHub Actions execute les tests backend et frontend sur chaque pull request et
sur les pushes vers `main`.

## Depannage

- `ng: not found` pendant le build Docker : verifier que le Dockerfile frontend lance `npm ci --include=dev`.
- `Not Found` depuis le frontend sur `/api/v1/...` : verifier que nginx preserve l'URI avec `proxy_pass http://$api_upstream$request_uri;`.
- `YouTube search requires YOUTUBE_API_KEY` : renseigner `YOUTUBE_API_KEY` dans `.env`.
- Erreur d'authentification Lichess : renseigner `LICHESS_TOKEN` dans `.env`.
- `No binary for ChromeHeadless` en local : installer Chrome ou definir `CHROME_BIN`; la CI GitHub le configure automatiquement.
- Milvus peut etre lent au premier demarrage; relancer `docker compose run --rm seed-openings` si le chargement initial echoue.

## Scenario de demo

Le scenario pas-a-pas est disponible dans [docs/demo-scenario.md](docs/demo-scenario.md).

## Note systeme

La note client sur l'architecture, les benefices, les limites et la faisabilite
economique est disponible dans [docs/system-note.md](docs/system-note.md).

La note de conception du systeme avance d'analyse video demande au step 7 est
disponible dans [docs/video-analysis-system-note.md](docs/video-analysis-system-note.md).

Le statut case par case de la fiche d'autoevaluation est disponible dans
[docs/autoevaluation-status.md](docs/autoevaluation-status.md).

## Positions de demo

- Position initiale : `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- Sicilienne apres `1.e4 c5` : `rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2`
- Espagnole apres `1.e4 e5 2.Nf3 Nc6 3.Bb5` : `r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`
- Italienne apres `1.e4 e5 2.Nf3 Nc6 3.Bc4` : `r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`

## Volumes

MongoDB, Milvus, MinIO et etcd utilisent des volumes Docker nommes :

```bash
docker volume ls | grep projet_13
docker volume inspect projet_13_mongodb-data
docker volume inspect projet_13_milvus-data
```

Pour tester la persistance, recreer les conteneurs sans supprimer les volumes :

```bash
docker compose down
docker compose up --build
```

Utiliser `docker compose down -v` uniquement pour repartir d'une base vide.
