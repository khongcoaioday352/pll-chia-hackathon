"""Replay the original three tests plus the later agent reset test.

Post hoc coverage analysis. The reset goal and fault suite were chosen with
knowledge of earlier outcomes: never call this a blind evaluation. Compare
with both the original 3-test baseline and a 4-test human-reset control.
The live run must have been generated on the same pinned RTL and contain
the exact frozen agent-authored reset candidate shipped in examples/.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.audit_test_budget import budget
from scripts.replay_summary import FROZEN_RTL_SHA256
from scripts.stress_suite import FAULTS
from scripts.time_matched_baseline import evaluate, make_stress_sources
from verify import RTL_FILES, run, validate


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    p.add_argument("--published", type=pathlib.Path,
                   default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    p.add_argument("--prior-matrix", type=pathlib.Path,
                   default=pathlib.Path("evidence/stress_public_replay_matrix.json"))
    p.add_argument("--time-matched-matrix", type=pathlib.Path,
                   default=pathlib.Path("evidence/time_matched_public_replay_matrix.json"))
    p.add_argument("--live", type=pathlib.Path, required=True,
                   help="Completed live run directory, containing summary.json")
    p.add_argument("--output", type=pathlib.Path, required=True)
    args = p.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    rtl, out = args.rtl.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        p.error("output must be new or empty")
    rtl_hash = {name: sha(rtl / name) for name in RTL_FILES}
    if rtl_hash != FROZEN_RTL_SHA256:
        p.error("RTL differs from the pinned original source")

    prior = json.loads(args.published.read_text())
    old = json.loads(args.prior_matrix.read_text())
    old_matched = json.loads(args.time_matched_matrix.read_text())
    frozen = json.loads((root / "examples/live_reset_phase_agent2.json").read_text())
    human = json.loads((root / "examples/phase1_reset_program.json").read_text())
    if old["rtl_sha256"] != rtl_hash or old["mutants"] != list(FAULTS):
        p.error("prior published stress matrix differs from RTL or fault catalog")
    if (old_matched["rtl_sha256"] != rtl_hash or
            old_matched["suites"]["stress_post_hoc"]["mutants"] != list(FAULTS)):
        p.error("published time-matched matrix differs from RTL or fault catalog")
    expected_labels = {f"agent_{i}" for i in range(3)} | {f"baseline_{i}" for i in range(3)}
    if set(prior["tests"]) != expected_labels or set(old["tests"]) != expected_labels:
        p.error("expected exactly the six frozen original proposals")
    candidates = {name: validate(prior["tests"][name]["candidate"])
                  for name in sorted(expected_labels)}
    candidates["agent_later_reset"] = validate(frozen)
    candidates["human_later_reset"] = validate(human)
    # This sensitivity check was constructed AFTER seeing the results. Match
    # nominal simulated nanoseconds for each of the original three families.
    # It does not equalize CPU time, assertion strength, or search effort.
    old_targets = [budget(candidates[name])["simulated_time_ns"] for name in
                   ("agent_0", "agent_2", "agent_1")]
    baseline_offsets = (30, 60, 20)
    baseline_slopes = (2, 2, 6)
    observed = []
    for i, target in enumerate(old_targets):
        numerator = target - baseline_offsets[i]
        if numerator % baseline_slopes[i]:
            p.error("baseline observation length cannot match agent time exactly")
        window = numerator // baseline_slopes[i]
        matched = copy.deepcopy(candidates[f"baseline_{i}"])
        matched["observe_ns"] = window
        matched = validate(matched)
        if budget(matched)["simulated_time_ns"] != target:
            p.error("time-matched baseline duration differs from agent duration")
        candidates[f"baseline_matched_{i}"] = matched
        observed.append(window)
    if observed != old_matched["baseline_observe_ns"]:
        p.error("time-matched baseline windows differ from published audit")
    human_time = budget(candidates["human_later_reset"])["simulated_time_ns"]
    new_time = budget(candidates["agent_later_reset"])["simulated_time_ns"]
    matched_human = copy.deepcopy(candidates["human_later_reset"])
    measurements = [step for step in matched_human["steps"] if step["op"] == "measure"]
    difference = new_time - human_time
    if difference < 0 or not measurements:
        p.error("human reset observation windows cannot match agent time")
    per_window, remainder = divmod(difference, len(measurements))
    for index, step in enumerate(measurements):
        step["ns"] += per_window + (index < remainder)
    candidates["human_reset_matched"] = validate(matched_human)
    if budget(candidates["human_reset_matched"])["simulated_time_ns"] != new_time:
        p.error("time-matched human reset duration differs from agent duration")

    live_path = args.live / "summary.json" if args.live.is_dir() else args.live
    live = json.loads(live_path.read_text())
    row = live["tests"]["agent_2"]
    if (not live["complete_comparable_run"] or live["rtl_sha256"] != rtl_hash
            or live["evaluation_faults"] != list(FAULTS)
            or live["completed_agent_rounds"] != 3
            or live["tests"]["agent_1"]["development"]["original_pass"] is not False
            or validate(row["candidate"]) != candidates["agent_later_reset"]
            or row["development"]["original_pass"] is not True
            or row["reference_original"] != {"30": "pass", "50": "pass"}):
        p.error("live source, candidate, or original-RTL checks differ")

    sources = make_stress_sources(rtl, out / "sources")
    report = evaluate(candidates, sources, out / "runs")
    prior_matches = all(
        report["tests"][name]["statuses"] == old["tests"][name]["statuses"]
        and sorted(report["tests"][name]["detected"]) == sorted(old["tests"][name]["detected"])
        for name in sorted(expected_labels))
    matched_prior = old_matched["suites"]["stress_post_hoc"]["tests"]
    matched_prior_matches = all(
        report["tests"][f"baseline_matched_{i}"]["statuses"] ==
        matched_prior[f"baseline_{i}"]["statuses"]
        for i in range(3))
    live_matches = (report["tests"]["agent_later_reset"]["statuses"] ==
                    live["tests"]["agent_2"]["evaluation"]["statuses"])
    reference = {str(period): run(
        sources["original"], validate({**frozen, "ref_period_ns": period}),
        out / "reference_runs" / str(period))["status"] for period in (30, 50)}

    def aggregate(names: list[str]) -> dict:
        rows = [report["tests"][name] for name in names]
        return {"tests": names, "valid": sum(row["original_pass"] for row in rows),
                "detected": sorted({fault for row in rows for fault in row["detected"]}),
                "simulated_time_ns": sum(budget(candidates[name])["simulated_time_ns"]
                                         for name in names)}

    groups = {"original_agent_three": aggregate([f"agent_{i}" for i in range(3)]),
              "combined_agent_four": aggregate([f"agent_{i}" for i in range(3)]
                                               + ["agent_later_reset"]),
              "original_baseline_three": aggregate([f"baseline_{i}" for i in range(3)]),
              "baseline_with_human_reset_four": aggregate(
                  [f"baseline_{i}" for i in range(3)] + ["human_later_reset"]),
              "time_matched_baseline_four": aggregate(
                  [f"baseline_matched_{i}" for i in range(3)]
                  + ["human_reset_matched"])}
    if (groups["combined_agent_four"]["simulated_time_ns"] !=
            groups["time_matched_baseline_four"]["simulated_time_ns"]):
        p.error("four-test simulated-time budgets differ")
    result = {"classification": "post hoc combined coverage; human-guided reset goal; not blind",
              "rtl_sha256": rtl_hash, "faults": list(FAULTS),
              "published_summary_sha256": sha(args.published),
              "live_summary_sha256": sha(live_path),
              "published_matrix_match": prior_matches,
              "published_time_matched_matrix_match": matched_prior_matches,
              "live_agent_2_matrix_match": live_matches,
              "later_agent_reference_original": reference,
              "groups": groups, "tests": report["tests"],
              "tool_errors": report["tool_errors"]}
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    for name, group in groups.items():
        print(f"{name}: {group['valid']}/{len(group['tests'])} valid, "
              f"{len(group['detected'])}/{len(FAULTS)} detected, "
              f"{group['simulated_time_ns']} simulated ns")
    print("Prior matrix:", "MATCH" if prior_matches else "DIFF",
          "| matched matrix:", "MATCH" if matched_prior_matches else "DIFF",
          "| live reset matrix:", "MATCH" if live_matches else "DIFF",
          "| ref 30/50:", reference, "| tool errors:", report["tool_errors"])
    print("Detailed summary:", out / "summary.json")
    if (not prior_matches or not matched_prior_matches or not live_matches
            or report["tool_errors"]
            or reference != {"30": "pass", "50": "pass"}):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
