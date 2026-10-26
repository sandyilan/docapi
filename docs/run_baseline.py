import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "docs" / "eval_cases.jsonl"
OUTPUT_DIR = ROOT / "docs" / "eval_runs"
API_URL = "http://127.0.0.1:8001/ask"
TENANT_ID = 1
PROMPT_VERSION = "ask_v2"


def read_json_response(raw_body: bytes):
    text = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


def main():
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_name = f"baseline_{commit_hash[:7]}"
    results_path = OUTPUT_DIR / f"{run_name}.jsonl"
    summary_path = OUTPUT_DIR / f"{run_name}_summary.json"

    successes = 0
    errors = 0
    latencies = []

    print(f"Baseline commit: {commit_hash}")

    with results_path.open("w", encoding="utf-8") as output_file:
        for number, case in enumerate(cases, start=1):
            payload = {
                "tenant_id": TENANT_ID,
                "question": case["question"],
            }
            request = Request(
                API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            started = time.perf_counter()
            status_code = None

            try:
                with urlopen(request, timeout=900) as response:
                    status_code = response.status
                    body = read_json_response(response.read())
            except HTTPError as error:
                status_code = error.code
                body = read_json_response(error.read())
            except (URLError, TimeoutError, OSError) as error:
                body = {"error": str(error)}

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            latencies.append(latency_ms)

            if status_code == 200:
                successes += 1
            else:
                errors += 1

            result = {
                "case_number": number,
                "git_commit": commit_hash,
                "prompt_version": PROMPT_VERSION,
                "question": case["question"],
                "expected_answer": case["expected_answer"],
                "expected_source_document": case["source_document"],
                "status_code": status_code,
                "answer": body.get("answer"),
                "retrieved_chunks": body.get("sources", []),
                "latency_ms": latency_ms,
                "error": body.get("error") or body.get("detail"),
            }

            output_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            output_file.flush()

            print(
                f"{number}/{len(cases)} "
                f"status={status_code} latency_ms={latency_ms}",
                flush=True,
            )

    summary = {
        "git_commit": commit_hash,
        "prompt_version": PROMPT_VERSION,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "successful_responses": successes,
        "api_errors": errors,
        "average_latency_ms": (
            round(sum(latencies) / len(latencies), 2)
            if latencies
            else None
        ),
        "results_file": str(results_path.relative_to(ROOT)),
    }

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"Saved baseline results to {results_path}")


if __name__ == "__main__":
    main()