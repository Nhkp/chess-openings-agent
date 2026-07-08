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

## Docker

```bash
docker compose up --build
```

L'API est exposee sur `http://localhost:${API_PORT:-8000}`.
