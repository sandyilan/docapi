import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:8001/search"
TENANT_ID = 1

CASES_PATH = Path("docs/eval_cases.jsonl")
DETAILS_PATH = Path("docs/eval_runs/day34_retrieval.jsonl")
SUMMARY_PATH = Path("docs/eval_runs/day34_retrieval_summary.json")

DOCUMENT_IDS = {
    "01_database_indexes.pdf": 107,
    "02_postgresql_vectors.pdf": 108,
    "03_rag_workflow.pdf": 109,
    "04_tenant_isolation.pdf": 110,
    "05_document_chunking.pdf": 111,
}


def read_json_response(raw_body: bytes):
    text = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


def search_question(question: str):
    payload = {
        "tenant_id": TENANT_ID,
        "query": question,
    }
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=900) as response:
            return response.status, read_json_response(response.read())
    except HTTPError as error:
        return error.code, read_json_response(error.read())
    except (URLError, TimeoutError, OSError) as error:
        return None, {"error": str(error)}


def main():
    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    answerable_count = 0
    relevant_found_count = 0
    reciprocal_rank_total = 0.0
    unanswerable_count = 0
    unanswerable_with_results = 0
    api_errors = 0

    DETAILS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with DETAILS_PATH.open("w", encoding="utf-8") as output_file:
        for number, case in enumerate(cases, start=1):
            status_code, body = search_question(case["question"])
            results = body.get("results", []) if isinstance(body, dict) else []

            expected_document = case["source_document"]
            expected_document_id = (
                DOCUMENT_IDS.get(expected_document)
                if expected_document is not None
                else None
            )

            reciprocal_rank = None
            relevant_rank = None
            recall_at_5 = None

            if status_code != 200:
                api_errors += 1

            if expected_document_id is None:
                unanswerable_count += 1
                if results:
                    unanswerable_with_results += 1
            else:
                answerable_count += 1
                for rank, result in enumerate(results[:5], start=1):
                    if result.get("document_id") == expected_document_id:
                        relevant_rank = rank
                        break

                recall_at_5 = relevant_rank is not None
                reciprocal_rank = (
                    1 / relevant_rank if relevant_rank is not None else 0.0
                )

                if recall_at_5:
                    relevant_found_count += 1
                reciprocal_rank_total += reciprocal_rank

            detail = {
                "case_number": number,
                "question": case["question"],
                "expected_source_document": expected_document,
                "expected_document_id": expected_document_id,
                "status_code": status_code,
                "relevant_rank": relevant_rank,
                "recall_at_5": recall_at_5,
                "reciprocal_rank": reciprocal_rank,
                "retrieved_chunks": results,
                "error": body.get("error") if isinstance(body, dict) else None,
            }

            output_file.write(json.dumps(detail, ensure_ascii=False) + "\n")
            output_file.flush()

            print(
                f"{number}/{len(cases)} "
                f"status={status_code} relevant_rank={relevant_rank}",
                flush=True,
            )

    summary = {
        "total_cases": len(cases),
        "answerable_cases": answerable_count,
        "recall_at_5": (
            round(relevant_found_count / answerable_count, 3)
            if answerable_count
            else None
        ),
        "mrr": (
            round(reciprocal_rank_total / answerable_count, 3)
            if answerable_count
            else None
        ),
        "unanswerable_cases": unanswerable_count,
        "unanswerable_cases_with_results": unanswerable_with_results,
        "search_api_errors": api_errors,
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"Saved per-case retrieval results to {DETAILS_PATH}")
    print(f"Saved metrics summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()