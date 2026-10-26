import json
import re
from pathlib import Path

from ollama import chat


RESULTS_PATH = Path("docs/eval_runs/day32_results.jsonl")
SCORES_PATH = Path("docs/eval_runs/day33_scores.jsonl")
SUMMARY_PATH = Path("docs/eval_runs/day33_summary.json")
JUDGE_MODEL = "qwen2.5:1.5b"

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does",
    "for", "from", "how", "in", "is", "it", "of", "on", "or", "should",
    "that", "the", "their", "they", "this", "to", "what", "when", "where",
    "which", "why", "with",
}

ABSTENTION_PHRASES = (
    "couldn't find",
    "could not find",
    "do not say",
    "does not say",
    "not stated",
    "not specified",
    "not specify",
    "not in the documents",
    "don't know",
    "cannot determine",
    "can't determine",
)


def words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def indicates_abstention(text):
    text = (text or "").lower()
    return any(phrase in text for phrase in ABSTENTION_PHRASES)


def key_fact_match(expected, answer, source_document):
    if not answer:
        return 0

    if source_document is None:
        return int(indicates_abstention(answer))

    expected_normalized = " ".join(words(expected))
    answer_normalized = " ".join(words(answer))
    return int(bool(expected_normalized) and expected_normalized in answer_normalized)


def keyword_score(expected, answer, source_document):
    if not answer:
        return 0.0

    if source_document is None:
        return float(indicates_abstention(answer))

    expected_keywords = {
        word
        for word in words(expected)
        if len(word) > 2 and word not in STOP_WORDS
    }
    if not expected_keywords:
        return 0.0

    answer_words = set(words(answer))
    present = expected_keywords & answer_words
    return round(len(present) / len(expected_keywords), 3)


def judge_answer(question, expected, answer, source_document):
    prompt_data = {
        "question": question,
        "expected_answer": expected,
        "answer": answer,
        "expected_source_document": source_document,
    }

    response = chat(
        model=JUDGE_MODEL,
        format="json",
        messages=[
            {
                "role": "system",
                "content": (
                    "Evaluate the answer against the expected answer. "
                    "Give score 1.0 if it is correct, 0.5 if partly correct, "
                    "and 0.0 if incorrect, unsupported, or empty. If the expected "
                    "source document is null, reward an honest abstention and "
                    "penalize invented facts. Return JSON with a numeric score "
                    "from 0.0 to 1.0 and a short rationale."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt_data, ensure_ascii=False),
            },
        ],
    )

    result = json.loads(response.message.content)
    score = max(0.0, min(1.0, float(result["score"])))
    return score, str(result.get("rationale", ""))


def main():
    rows = [
        json.loads(line)
        for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    scores = []

    with SCORES_PATH.open("w", encoding="utf-8") as output_file:
        for number, row in enumerate(rows, start=1):
            answer = row.get("answer") or ""
            expected = row.get("expected_answer") or ""
            source_document = row.get("expected_source_document")

            exact_match = key_fact_match(expected, answer, source_document)
            keywords = keyword_score(expected, answer, source_document)

            judge_score = None
            judge_rationale = None
            judge_error = None

            if row.get("status_code") == 200 and answer:
                try:
                    judge_score, judge_rationale = judge_answer(
                        row["question"],
                        expected,
                        answer,
                        source_document,
                    )
                except Exception as error:
                    judge_error = str(error)

            scored_row = {
                "case_number": row["case_number"],
                "question": row["question"],
                "status_code": row.get("status_code"),
                "exact_key_fact_match": exact_match,
                "keyword_presence": keywords,
                "llm_judge_score": judge_score,
                "llm_judge_rationale": judge_rationale,
                "llm_judge_error": judge_error,
            }

            scores.append(scored_row)
            output_file.write(json.dumps(scored_row, ensure_ascii=False) + "\n")
            output_file.flush()

            print(f"{number}/{len(rows)} scored", flush=True)

    judge_values = [
        row["llm_judge_score"]
        for row in scores
        if row["llm_judge_score"] is not None
    ]

    summary = {
        "cases": len(scores),
        "exact_key_fact_matches": sum(
            row["exact_key_fact_match"] for row in scores
        ),
        "average_keyword_presence": round(
            sum(row["keyword_presence"] for row in scores) / len(scores), 3
        ) if scores else None,
        "average_llm_judge_score": round(
            sum(judge_values) / len(judge_values), 3
        ) if judge_values else None,
        "llm_judge_scored_cases": len(judge_values),
        "api_errors": sum(
            row["status_code"] != 200 for row in scores
        ),
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"Saved per-case scores to {SCORES_PATH}")
    print(f"Saved summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()