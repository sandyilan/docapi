import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:8001/ask"
TENANT_ID = 1

CASES_PATH = Path("docs/eval_cases.jsonl")
RESULTS_PATH = Path("docs/eval_runs/day32_results.jsonl")


def read_json_response(raw_body: bytes):
    text = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


def main():
    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open("w", encoding="utf-8") as output_file:
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

            result = {
                "case_number": number,
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
                f"status={status_code} latency_ms={latency_ms}"
            )

    print(f"Saved results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()