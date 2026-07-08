# Projet 13 - Agent ouvertures d'echecs

POC local pour un agent IA d'entrainement aux ouvertures d'echecs.

## Services

- `frontend` : Angular + ngx-chess-board, expose sur `http://localhost:${FRONTEND_PORT:-4200}`
- `api` : FastAPI, expose sur `http://localhost:${API_PORT:-8000}`
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
curl "http://localhost:8000/api/v1/moves/rnbqkbnr%2Fpppppppp%2F8%2F8%2F8%2F8%2FPPPPPPPP%2FRNBQKBNR%20w%20KQkq%20-%200%201"
```

Evaluer une position avec Stockfish :

```bash
curl "http://localhost:8000/api/v1/evaluate/rnbqkbnr%2Fpppppppp%2F8%2F8%2F8%2F8%2FPPPPPPPP%2FRNBQKBNR%20w%20KQkq%20-%200%201"
```

## Donnees vectorielles

Charger ou recharger le jeu de donnees d'ouvertures :

```bash
docker compose up -d milvus
uv run python -m backend.scripts.load_openings
```

Rechercher du contexte :

```bash
curl "http://localhost:8000/api/v1/vector-search?opening=sicilienne"
```

## Videos

```bash
curl "http://localhost:8000/api/v1/videos/Defense%20sicilienne"
```

Renseigner `YOUTUBE_API_KEY` dans `.env` avant d'appeler cet endpoint.

## Frontend local

```bash
cd frontend
npm ci
npm start
```

Le proxy Angular redirige `/api` vers `http://localhost:8000`.

## Positions de demo

- Position initiale : `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- Sicilienne apres `1.e4 c5` : `rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2`
- Espagnole apres `1.e4 e5 2.Nf3 Nc6 3.Bb5` : `r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`
- Italienne apres `1.e4 e5 2.Nf3 Nc6 3.Bc4` : `r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`

## Volumes

Milvus, MinIO et etcd utilisent des volumes Docker nommes :

```bash
docker volume ls | grep projet_13
docker volume inspect projet_13_milvus-data
```

Pour tester la persistance, recreer les conteneurs sans supprimer les volumes :

```bash
docker compose down
docker compose up --build
```

Utiliser `docker compose down -v` uniquement pour repartir d'une base vide.
