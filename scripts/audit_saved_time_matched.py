"""Compare a saved lab run to the published time-matched per-test matrix.

No Icarus, CHIA, or Gemini invocation is needed. A PASS here checks the saved
JSON and does NOT constitute a new independent RTL simulation.
"""
from __future__ import annotations

import argparse
import json
import pathlib


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=pathlib.Path, required=True,
                        help="Saved results/.../time_matched/summary.json or its directory")
    parser.add_argument("--expected", type=pathlib.Path, default=pathlib.Path(
                        "evidence/time_matched_public_replay_matrix.json"))
    parser.add_argument("--output", type=pathlib.Path,
                        help="Optional new JSON audit record; never overwrites an existing file")
    args = parser.parse_args()
    source = args.run / "summary.json" if args.run.is_dir() else args.run
    measured = json.loads(source.read_text())
    published = json.loads(args.expected.read_text())
    checks = {
        "source_summary_sha256": measured["source_summary_sha256"] ==
            published["source_summary_sha256"],
        "rtl_sha256": measured["rtl_sha256"] == published["rtl_sha256"],
        "baseline_observe_ns": measured["baseline_observe_ns"] ==
            published["baseline_observe_ns"],
        "suite_names": set(measured["results"]) == set(published["suites"]),
    }
    status_count = 0
    for suite_name, suite in measured["results"].items():
        expected = published["suites"].get(suite_name)
        if expected is None:
            checks[f"{suite_name}/exists"] = False
            continue
        checks[f"{suite_name}/mutants"] = suite["mutants"] == expected["mutants"]
        checks[f"{suite_name}/test_names"] = set(suite["tests"]) == set(expected["tests"])
        for name, row in suite["tests"].items():
            prior = expected["tests"].get(name)
            if prior is None:
                checks[f"{suite_name}/{name}/exists"] = False
                continue
            checks[f"{suite_name}/{name}/original_pass"] = (
                row["original_pass"] == prior["original_pass"])
            checks[f"{suite_name}/{name}/detected"] = (
                sorted(row["detected"]) == sorted(prior["detected"]))
            keys = set(row["statuses"]) | set(prior["statuses"])
            for fault in sorted(keys):
                checks[f"{suite_name}/{name}/{fault}"] = (
                    row["statuses"].get(fault) == prior["statuses"].get(fault))
                status_count += 1
    success = all(checks.values())
    record = {"classification": "Saved JSON status audit; no simulator or model call",
              "source": str(source), "published": str(args.expected),
              "all_match": success, "status_cells_checked": status_count,
              "different_fields": [name for name, matched in checks.items() if not matched]}
    if args.output:
        if args.output.exists():
            parser.error("output exists; keep prior audits immutable")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + "\n")
    print("Saved time-matched matrix:", "MATCH" if success else "DIFF",
          f"({status_count} status cells checked)")
    if not success:
        print("Differences:", record["different_fields"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
