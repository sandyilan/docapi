import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "docs" / "eval_runs"
V1_SUMMARY = EVAL_DIR / "baseline_d8ecbb8_summary.json"


def main() -> None:
    if not V1_SUMMARY.exists():
        raise FileNotFoundError(
            f"Could not find the ask_v1 baseline summary: {V1_SUMMARY}"
        )

    # Run all 30 /ask cases. This writes a commit-specific JSONL file and summary.
    subprocess.run(
        [sys.executable, str(ROOT / "docs" / "run_baseline.py")],
        cwd=ROOT,
        check=True,
    )

    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    current_summary_path = EVAL_DIR / f"baseline_{commit_hash[:7]}_summary.json"
    if not current_summary_path.exists():
        raise FileNotFoundError(
            f"The current run did not create its summary: {current_summary_path}"
        )

    before = json.loads(V1_SUMMARY.read_text(encoding="utf-8"))
    after = json.loads(current_summary_path.read_text(encoding="utf-8"))

    old_latency = before.get("average_latency_ms")
    new_latency = after.get("average_latency_ms")
    latency_change_percent = None
    if old_latency and new_latency is not None:
        latency_change_percent = round(
            (new_latency - old_latency) / old_latency * 100,
            2,
        )

    comparison = {
        "baseline_prompt_version": before.get("prompt_version"),
        "new_prompt_version": after.get("prompt_version"),
        "baseline_commit": before.get("git_commit"),
        "new_commit": after.get("git_commit"),
        "cases": after.get("total_cases"),
        "baseline_successful_responses": before.get("successful_responses"),
        "new_successful_responses": after.get("successful_responses"),
        "baseline_api_errors": before.get("api_errors"),
        "new_api_errors": after.get("api_errors"),
        "baseline_average_latency_ms": old_latency,
        "new_average_latency_ms": new_latency,
        "latency_change_percent": latency_change_percent,
        "new_results_file": after.get("results_file"),
    }

    comparison_path = EVAL_DIR / f"day40_comparison_{commit_hash[:7]}.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nPhase 4 baseline comparison:")
    print(json.dumps(comparison, indent=2))
    print(f"\nSaved comparison to {comparison_path}")


if __name__ == "__main__":
    main()