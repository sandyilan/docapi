from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title=get_settings().app_name, version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
