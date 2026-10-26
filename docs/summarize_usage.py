import json
from collections import defaultdict
from pathlib import Path


USAGE_PATH = Path("docs/eval_runs/usage.jsonl")
SUMMARY_PATH = Path("docs/eval_runs/usage_summary.json")


def main():
    records = [
        json.loads(line)
        for line in USAGE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    request_totals = {}

    for record in records:
        date = record["date_utc"]
        request_id = record.get("request_id") or "unknown"
        key = (date, request_id)

        totals = request_totals.setdefault(
            key,
            {
                "date_utc": date,
                "request_id": request_id,
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
        )

        totals["model_calls"] += 1
        totals["input_tokens"] += record["input_tokens"]
        totals["output_tokens"] += record["output_tokens"]
        totals["estimated_cost_usd"] += record["estimated_cost_usd"]

    daily_totals = defaultdict(
        lambda: {
            "date_utc": None,
            "requests": 0,
            "model_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
    )

    for totals in request_totals.values():
        daily = daily_totals[totals["date_utc"]]
        daily["date_utc"] = totals["date_utc"]
        daily["requests"] += 1
        daily["model_calls"] += totals["model_calls"]
        daily["input_tokens"] += totals["input_tokens"]
        daily["output_tokens"] += totals["output_tokens"]
        daily["estimated_cost_usd"] += totals["estimated_cost_usd"]

    summary = {
        "per_request": sorted(
            request_totals.values(),
            key=lambda item: (item["date_utc"], item["request_id"]),
        ),
        "daily_totals": sorted(
            daily_totals.values(),
            key=lambda item: item["date_utc"],
        ),
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"Saved usage summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()