"""Post hoc test of a time-matched fixed baseline against frozen agent tests.

This sensitivity analysis adjusts only the observation durations of the three
published baseline families. It was designed after seeing the original result
and must NOT be described as a preregistered or independent evaluation.
The supplementary seven-fault suite was likewise designed after the primary
run. Simulated time is balanced on the passing original RTL, not CPU time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mutants import prepare
from scripts.audit_test_budget import budget
from scripts.replay_summary import FROZEN_RTL_SHA256
from scripts.stress_suite import FAULTS
from verify import RTL_FILES, run, validate


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_stress_sources(rtl: pathlib.Path, output: pathlib.Path) -> dict:
    paths = {}
    for label in ("original", *FAULTS):
        dst = output / label
        dst.mkdir(parents=True)
        for filename in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(rtl / filename, dst / filename)
        if label in FAULTS:
            filename, before, after = FAULTS[label]
            path = dst / filename
            data = path.read_text()
            if data.count(before) != 1:
                raise ValueError(f"fault anchor absent/ambiguous: {label}")
            path.write_text(data.replace(before, after, 1))
        paths[label] = dst
    return paths


def evaluate(candidates: dict, sources: dict, output: pathlib.Path) -> dict:
    tests = {}
    for name, candidate in candidates.items():
        outcomes = {fault: run(path, candidate, output / name / fault)["status"]
                    for fault, path in sources.items()}
        valid = outcomes["original"] == "pass"
        tests[name] = {"candidate": candidate, "original_pass": valid,
                       "statuses": outcomes,
                       "detected": [name for name in sources if name != "original"
                                    and valid and outcomes[name] == "fail"]}
    detected = {}
    for prefix in ("agent_", "baseline_"):
        selected = [row for name, row in tests.items() if name.startswith(prefix)]
        detected[prefix + "detected_union"] = sorted({fault for row in selected
                                                      for fault in row["detected"]})
        detected[prefix + "original_valid"] = sum(row["original_pass"] for row in selected)
    tool_errors = [(name, fault, status) for name, row in tests.items()
                   for fault, status in row["statuses"].items()
                   if status in ("invalid", "compile_error", "tool_error")]
    return {"tests": tests, "mutants": list(sources)[1:], "tool_errors": tool_errors,
            **detected}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    p.add_argument("--summary", type=pathlib.Path,
                   default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    p.add_argument("--expected-aggregates", type=pathlib.Path,
                   help="Check each author-reported aggregate against this independent rerun")
    p.add_argument("--expected-matrix", type=pathlib.Path,
                   help="Check every original/fault test status against the published matched-time matrix")
    p.add_argument("--output", type=pathlib.Path, required=True)
    args = p.parse_args()
    rtl, output = args.rtl.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        p.error("output must be a new or empty directory")
    hashes = {name: digest(rtl / name) for name in RTL_FILES}
    if hashes != FROZEN_RTL_SHA256:
        p.error("RTL differs from frozen measured source")
    saved = json.loads(args.summary.read_text())["tests"]
    if set(saved) != {f"agent_{i}" for i in range(3)} | {f"baseline_{i}" for i in range(3)}:
        p.error("expected the six published candidate labels")
    agent = {f"agent_{i}": validate(saved[f"agent_{i}"]["candidate"]) for i in range(3)}
    baseline = {f"baseline_{i}": validate(saved[f"baseline_{i}"]["candidate"])
                for i in range(3)}
    if [baseline[f"baseline_{i}"]["kind"] for i in range(3)] != ["disable", "dco_trim", "divider"]:
        p.error("baseline families changed")
    # Agent_0/2 each simulate 1220 ns; agent_1 simulates 4820 ns.
    # Solve each baseline family's template duration for the matched window.
    agent_time = {name: budget(row)["simulated_time_ns"] for name, row in agent.items()}
    target = [agent_time["agent_0"], agent_time["agent_2"], agent_time["agent_1"]]
    offsets = [30, 60, 20]
    coeffs = [2, 2, 6]
    observed = []
    for i in range(3):
        if (target[i] - offsets[i]) % coeffs[i]:
            p.error(f"cannot exactly match baseline_{i} duration")
        n = (target[i] - offsets[i]) // coeffs[i]
        baseline[f"baseline_{i}"]["observe_ns"] = n
        baseline[f"baseline_{i}"] = validate(baseline[f"baseline_{i}"])
        if budget(baseline[f"baseline_{i}"])["simulated_time_ns"] != target[i]:
            p.error(f"failed to match baseline_{i} duration")
        observed.append(n)
    candidates = {**agent, **baseline}
    primary = prepare(rtl, output / "primary_sources")
    stress = make_stress_sources(rtl, output / "stress_sources")
    results = {"primary": evaluate(candidates, primary, output / "primary_runs"),
               "stress_post_hoc": evaluate(candidates, stress, output / "stress_runs")}
    report = {"scope": "post hoc time-matched fixed-baseline sensitivity; not blind; not equal CPU cost",
              "rtl_sha256": hashes, "source_summary_sha256": digest(args.summary),
              "baseline_observe_ns": observed,
              "simulated_time_ns_by_test": {name: budget(candidate)["simulated_time_ns"]
                                            for name, candidate in candidates.items()},
              "results": results}
    if args.expected_aggregates:
        expected = json.loads(args.expected_aggregates.read_text())
        same = (expected["source_summary_sha256"] == report["source_summary_sha256"]
                and expected["rtl_sha256"] == hashes
                and expected["baseline_observe_ns"] == observed)
        for suite, rows in results.items():
            recorded = expected[suite]
            same = (same and recorded["fault_count"] == len(rows["mutants"])
                    and recorded["agent"]["original_valid"] == rows["agent_original_valid"]
                    and recorded["matched_baseline"]["original_valid"] == rows["baseline_original_valid"]
                    and recorded["agent"]["detected_count"] == len(rows["agent_detected_union"])
                    and recorded["matched_baseline"]["detected_count"] == len(rows["baseline_detected_union"])
                    and recorded["tool_errors"] == len(rows["tool_errors"]))
        report["author_reported_aggregates_match"] = bool(same)
    if args.expected_matrix:
        expected = json.loads(args.expected_matrix.read_text())
        same = (expected["source_summary_sha256"] == report["source_summary_sha256"]
                and expected["rtl_sha256"] == hashes
                and expected["baseline_observe_ns"] == observed
                and set(expected["suites"]) == set(results))
        for suite, rows in results.items():
            recorded = expected["suites"][suite]
            same = (same and recorded["mutants"] == rows["mutants"]
                    and set(recorded["tests"]) == set(rows["tests"])
                    and all(saved["statuses"] == rows["tests"][name]["statuses"]
                            and saved["original_pass"] == rows["tests"][name]["original_pass"]
                            and sorted(saved["detected"]) == sorted(rows["tests"][name]["detected"])
                            for name, saved in recorded["tests"].items()))
        report["published_matrix_match"] = bool(same)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    for suite, rows in results.items():
        print(f"{suite}: agent {rows['agent_original_valid']}/3 original-valid, "
              f"{len(rows['agent_detected_union'])}/{len(rows['mutants'])} detected; "
              f"matched baseline {rows['baseline_original_valid']}/3 original-valid, "
              f"{len(rows['baseline_detected_union'])}/{len(rows['mutants'])} detected; "
              f"tool errors: {len(rows['tool_errors'])}", flush=True)
    print("Baseline windows (ns):", observed, "| detailed summary:", output / "summary.json")
    if args.expected_aggregates:
        print("Author-reported aggregate replay:",
              "MATCH" if report["author_reported_aggregates_match"] else "DIFF")
        if not report["author_reported_aggregates_match"]:
            raise SystemExit(1)
    if args.expected_matrix:
        print("Published matched-time per-test matrix:",
              "MATCH" if report["published_matrix_match"] else "DIFF")
        if not report["published_matrix_match"]:
            raise SystemExit(1)
    if any(row["tool_errors"] for row in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
