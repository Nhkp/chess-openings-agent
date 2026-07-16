# Demo Scenario

## 1. Start the stack

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:4200`.

If Milvus starts slowly and the seed job fails on first boot:

```bash
docker compose run --rm seed-openings
```

## 2. Show the chess trainer

1. Verify the board and recommendation panel are visible.
2. Click `Analyser` on the initial position.
3. Expected result:
   - Stockfish evaluation appears.
   - Best move appears.
   - Lichess may show an auth error unless `LICHESS_TOKEN` is set.

## 3. Play an opening move

1. Move the white pawn from `e2` to `e4`.
2. Move the black pawn from `c7` to `c5` if you want to demonstrate the Sicilian.
3. Click `Analyser`.
4. Explain that the current FEN is sent to FastAPI as a query parameter, then routed to Lichess and Stockfish.

## 4. Search enriched context

1. In the resources field, enter `Defense sicilienne`.
2. Click `Chercher`.
3. Expected result:
   - Milvus returns opening notes from the seeded corpus.
   - YouTube videos appear if `YOUTUBE_API_KEY` is configured.
   - Without a YouTube key, the UI shows the backend configuration error.

## 5. Show MongoDB history

1. After the position analysis and resource search, call the history endpoint.
2. Expected result:
   - MongoDB returns recent `moves`, `evaluate`, `vector_search`, or `videos` events.
   - If MongoDB is unavailable, core analysis still works but history returns a backend configuration error.

```bash
curl "http://localhost:8000/api/v1/history?limit=20"
```

## 6. API smoke checks

```bash
curl http://localhost:8000/api/v1/healthcheck
curl --get "http://localhost:8000/api/v1/moves" \
  --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
curl --get "http://localhost:8000/api/v1/evaluate" \
  --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
curl "http://localhost:8000/api/v1/vector-search?opening=sicilienne"
curl --get "http://localhost:8000/api/v1/videos" \
  --data-urlencode "opening=Defense sicilienne"
curl "http://localhost:8000/api/v1/history?limit=20"
```

## 7. Troubleshooting notes

- If resources show `Not Found`, verify the frontend nginx proxy preserves `/api/v1/...` with `proxy_pass http://$api_upstream$request_uri;`.
- If YouTube videos do not appear, check `YOUTUBE_API_KEY` in `.env`.
- If Lichess returns an auth error, check `LICHESS_TOKEN` in `.env`.
- If history is unavailable, verify the `mongodb` service and `MONGODB_URI`.
- If frontend tests fail with `No binary for ChromeHeadless`, install Chrome or define `CHROME_BIN`.
- If Milvus starts slowly, rerun `docker compose run --rm seed-openings`.

## 8. Demo FEN positions

- Initial position: `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- Sicilian after `1.e4 c5`: `rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2`
- Spanish after `1.e4 e5 2.Nf3 Nc6 3.Bb5`: `r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`
- Italian after `1.e4 e5 2.Nf3 Nc6 3.Bc4`: `r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`
