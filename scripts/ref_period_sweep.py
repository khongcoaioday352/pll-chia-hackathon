"""Post hoc input-reference-period sensitivity of frozen candidate programs.

Both agent and baseline programs are altered only in ref_period_ns. These
investigator-created variants are NOT fresh model-authored tests or PVT data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mutants import prepare
from scripts.replay_summary import FROZEN_RTL_SHA256
from verify import RTL_FILES, run, validate


PERIODS_NS = (30, 40, 50)  # Fixed before the new experiment.


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=pathlib.Path, required=True)
    parser.add_argument("--summary", type=pathlib.Path,
                        default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    rtl, output = args.rtl.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output must be a new or empty directory")
    hashes = {name: sha(rtl / name) for name in RTL_FILES}
    if hashes != FROZEN_RTL_SHA256:
        parser.error("RTL does not match the published GF180 snapshot")
    saved = json.loads(args.summary.read_text())
    labels = [f"{group}_{i}" for group in ("baseline", "agent") for i in range(3)]
    if set(saved["tests"]) != set(labels):
        parser.error("expected exactly three archived agent and baseline tests")
    output.mkdir(parents=True, exist_ok=True)
    sources = prepare(rtl, output / "sources")
    if set(saved["mutants"]) != set(sources) - {"original"}:
        parser.error("fault definitions differ from the frozen run")
    report = {
        "classification": "Post hoc input reference period sweep of investigator-modified frozen tests; not new agent output or PVT",
        "rtl_sha256": hashes,
        "source_summary_sha256": sha(args.summary),
        "periods_ns": list(PERIODS_NS),
        "cases": {},
    }
    for period in PERIODS_NS:
        tests = {}
        for label in labels:
            candidate = dict(saved["tests"][label]["candidate"])
            candidate["ref_period_ns"] = period
            candidate = validate(candidate)
            statuses = {fault: run(source, candidate, output / f"period_{period}" /
                        label / fault)["status"] for fault, source in sources.items()}
            valid = statuses["original"] == "pass"
            tests[label] = {
                "candidate": candidate,
                "original_pass": valid,
                "detected": sorted(fault for fault in saved["mutants"]
                                   if valid and statuses[fault] == "fail"),
                "statuses": statuses,
            }
        case = {"tests": tests, "tool_errors": sorted(
            f"{label}/{fault}" for label, row in tests.items()
            for fault, status in row["statuses"].items()
            if status not in ("pass", "fail"))}
        for group in ("agent", "baseline"):
            rows = [tests[f"{group}_{i}"] for i in range(3)]
            case[group + "_original_valid"] = sum(row["original_pass"] for row in rows)
            case[group + "_detected_union"] = sorted({fault for row in rows
                                                     for fault in row["detected"]})
        report["cases"][str(period)] = case
        (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{period} ns: agent valid {case['agent_original_valid']}/3, "
              f"detected {len(case['agent_detected_union'])}/4; "
              f"baseline valid {case['baseline_original_valid']}/3, "
              f"detected {len(case['baseline_detected_union'])}/4; "
              f"tool errors {len(case['tool_errors'])}", flush=True)
    nominal = report["cases"]["40"]["tests"]
    report["nominal_matches_frozen_run"] = all(
        nominal[label]["statuses"] == saved["tests"][label]["statuses"]
        and nominal[label]["original_pass"] == saved["tests"][label]["original_pass"]
        for label in labels)
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("40 ns saved result:", "MATCH" if report["nominal_matches_frozen_run"] else "DIFF")
    if not report["nominal_matches_frozen_run"] or any(
            case["tool_errors"] for case in report["cases"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
