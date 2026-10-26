import json
from datetime import datetime, timezone
from pathlib import Path

from structlog.contextvars import get_contextvars


USAGE_FILE = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "eval_runs"
    / "usage.jsonl"
)


def record_usage(
    *,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    prompt_version: str,
) -> None:
    now = datetime.now(timezone.utc)
    context = get_contextvars()

    record = {
        "timestamp_utc": now.isoformat(),
        "date_utc": now.date().isoformat(),
        "request_id": context.get("request_id"),
        "provider": "ollama_local",
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": int(prompt_tokens or 0),
        "output_tokens": int(completion_tokens or 0),
        "estimated_cost_usd": 0.0,
    }

    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")