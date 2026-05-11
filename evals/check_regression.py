"""Compare fresh eval results against the committed baseline and fail on regression."""

import json
import sys
from pathlib import Path
from typing import Any


def _compute_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    retrieval = [r for r in results if r["query_type"] in ("factual", "multi_hop")]
    oos = [r for r in results if r["query_type"] == "out_of_scope"]

    retrieval_processed = sum(1 for r in retrieval if r["error"] is None)
    retrieval_matched = sum(1 for r in retrieval if r["matched"])
    retrieval_returned = sum(
        1 for r in retrieval if r["error"] is None and r["num_returned"] > 0
    )
    oos_processed = sum(1 for r in oos if r["error"] is None)
    oos_matched = sum(1 for r in oos if r["matched"])

    return {
        "retrieval_recall": retrieval_matched / retrieval_processed
        if retrieval_processed
        else 0.0,
        "coverage": retrieval_returned / retrieval_processed
        if retrieval_processed
        else 0.0,
        "abstention_rate": oos_matched / oos_processed if oos_processed else 0.0,
    }


def main() -> int:
    evals_dir = Path(__file__).parent
    baseline: list[dict[str, Any]] = json.loads(
        (evals_dir / "baseline.json").read_text()
    )
    current: list[dict[str, Any]] = json.loads((evals_dir / "results.json").read_text())

    baseline_metrics = _compute_metrics(baseline)
    current_metrics = _compute_metrics(current)

    print(f"{'Metric':<22} {'Baseline':>10} {'Current':>10}")
    print("-" * 44)

    regressions: list[str] = []
    for metric in baseline_metrics:
        b = baseline_metrics[metric]
        c = current_metrics[metric]
        flag = "  REGRESSION" if c < b else ""
        print(f"{metric:<22} {b:>10.3f} {c:>10.3f}{flag}")
        if c < b:
            regressions.append(metric)

    print()
    if regressions:
        print(
            f"Gate FAILED — {len(regressions)} regression(s): {', '.join(regressions)}"
        )
        return 1

    print("Gate PASSED — no regressions detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
