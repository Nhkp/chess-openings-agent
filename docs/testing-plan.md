# Test Coverage Plan

Target: keep backend and frontend coverage above 80% in CI.

## Backend

- Tooling: `coverage.py` with `unittest`.
- Gate: `pyproject.toml` sets `fail_under = 80`.
- Command:

```bash
uv run coverage run -m unittest discover -s backend/tests
uv run coverage report
```

Current focus:

- service-level tests for FEN validation, Lichess formatting, Milvus search, and YouTube formatting
- route-level tests for FastAPI error mapping
- seeder tests for Milvus startup retry behavior
- E5 encoder tests with a fake model: prefixes, normalization, model reuse, invalid output, and safe seeding failures
- MongoDB history tests for event writes, unavailable store handling, and history route formatting

Run the real CPU model check separately (downloads weights on first use):

```bash
uv run python -m backend.scripts.check_embeddings
```

It verifies normalized 384-dimensional vectors and top-3 retrieval for French and
English opening queries. The regular unit suite never downloads model weights.

Next useful backend tests:

- Stockfish success path with a fake UCI engine
- Lichess HTTP error variants for `429` and malformed JSON
- Milvus missing collection path

## Frontend

- Tooling: Angular Karma + `karma-coverage`.
- Gate: `frontend/karma.conf.js` requires 80% globally for statements, branches, functions, and lines.
- Command:

```bash
cd frontend
npm run test:ci
```

Current focus:

- `ChessAgentService` HTTP request tests
- `AppComponent` state transitions for position analysis, resource loading, errors, reset, and tracking helpers

Next useful frontend tests:

- template-level rendering for move/context/video cards
- disabled/loading button states
- e2e smoke test once a browser runner is available locally

## CI

GitHub Actions runs backend and frontend as separate jobs on every push to `main` and on pull requests.
