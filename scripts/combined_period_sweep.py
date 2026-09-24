"""Check post hoc four-test coverage at 30, 40, and 50 ns input periods.

The input is a completed combined_coverage.py replay. This is a behavioral
reference-clock sensitivity check, NOT a transistor-level PVT sweep. Any
candidate that fails on unmodified RTL contributes zero detected faults.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.replay_summary import FROZEN_RTL_SHA256
from scripts.stress_suite import FAULTS
from scripts.time_matched_baseline import evaluate, make_stress_sources
from verify import RTL_FILES, validate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    p.add_argument("--combined", type=pathlib.Path, required=True,
                   help="Results directory (or summary.json) from combined_coverage.py")
    p.add_argument("--output", type=pathlib.Path, required=True)
    args = p.parse_args()
    summary_file = args.combined / "summary.json" if args.combined.is_dir() else args.combined
    source = json.loads(summary_file.read_text())
    rtl, out = args.rtl.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        p.error("output must be new or empty")
    actual = {name: hashlib.sha256((rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if actual != FROZEN_RTL_SHA256 or source["rtl_sha256"] != actual:
        p.error("source result and RTL must match pinned GF180 input")
    if source["faults"] != list(FAULTS) or source["tool_errors"]:
        p.error("source must be a successful seven-fault combined replay")
    for check in ("published_matrix_match", "published_time_matched_matrix_match",
                  "live_agent_2_matrix_match", "published_human_matched_matrix_match"):
        if source[check] is not True:
            p.error(f"source audit failed: {check}")
    names = {group: source["groups"][group]["tests"] for group in
             ("combined_agent_four", "time_matched_baseline_four")}
    if len(names["combined_agent_four"]) != 4 or len(names["time_matched_baseline_four"]) != 4:
        p.error("expected four agent tests and four time-matched controls")
    selected = [*names["combined_agent_four"], *names["time_matched_baseline_four"]]
    if len(selected) != len(set(selected)) or set(selected) - set(source["tests"]):
        p.error("source contains duplicate or missing candidate labels")
    candidates = {name: validate(source["tests"][name]["candidate"]) for name in selected}
    sources = make_stress_sources(rtl, out / "sources")
    report = {"classification": "post hoc behavioral input-period sensitivity; not PVT or blind",
              "source_summary_sha256": hashlib.sha256(summary_file.read_bytes()).hexdigest(),
              "rtl_sha256": actual, "faults": list(FAULTS), "groups": names, "periods": {}}
    for period in (30, 40, 50):
        changed = {name: validate({**candidate, "ref_period_ns": period})
                   for name, candidate in candidates.items()}
        scored = evaluate(changed, sources, out / "runs" / str(period))
        groups = {}
        for group, labels in names.items():
            rows = [scored["tests"][name] for name in labels]
            groups[group] = {"original_valid": sum(row["original_pass"] for row in rows),
                             "detected": sorted({fault for row in rows
                                                 for fault in row["detected"]})}
        nominal_match = (period != 40 or all(
            scored["tests"][name]["statuses"] == source["tests"][name]["statuses"]
            for name in selected))
        report["periods"][str(period)] = {"tests": scored["tests"], "groups": groups,
                                          "tool_errors": scored["tool_errors"],
                                          "nominal_matrix_match": nominal_match}
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{period} ns: ", end="")
        print("; ".join(f"{group} {row['original_valid']}/4 valid, "
                        f"{len(row['detected'])}/7 detected"
                        for group, row in groups.items()),
              "| errors:", len(scored["tool_errors"]),
              "| nominal:", "MATCH" if nominal_match else "DIFF", flush=True)
        if scored["tool_errors"] or not nominal_match:
            raise SystemExit(1)
    print("Detailed summary:", out / "summary.json")


if __name__ == "__main__":
    main()
