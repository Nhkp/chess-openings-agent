from fastapi import FastAPI


app = FastAPI(title="FFE Chess Openings Agent", version="0.1.0")


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
