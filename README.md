# Projet 13 - Agent ouvertures d'echecs

POC local pour un agent IA d'entrainement aux ouvertures d'echecs.

## Prerequis

- Docker et Docker Compose
- uv

## Backend

Lancer l'API en local :

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

L'Opening Explorer Lichess demande une authentification. Renseigner
`LICHESS_TOKEN` dans l'environnement si l'API repond `401`.

Evaluer une position avec Stockfish :

```bash
curl "http://localhost:8000/api/v1/evaluate/rnbqkbnr%2Fpppppppp%2F8%2F8%2F8%2F8%2FPPPPPPPP%2FRNBQKBNR%20w%20KQkq%20-%200%201"
```

Charger le jeu de donnees d'ouvertures dans Milvus :

```bash
docker compose up -d milvus
uv run python -m backend.scripts.load_openings
```

Rechercher du contexte d'ouverture :

```bash
curl "http://localhost:8000/api/v1/vector-search?opening=sicilienne"
```

Rechercher des videos explicatives YouTube :

```bash
curl "http://localhost:8000/api/v1/videos/Defense%20sicilienne"
```

Renseigner `YOUTUBE_API_KEY` dans `.env` avant d'appeler cet endpoint.

## Docker

```bash
docker compose up --build
```

L'API est exposee sur `http://localhost:${API_PORT:-8000}`.
