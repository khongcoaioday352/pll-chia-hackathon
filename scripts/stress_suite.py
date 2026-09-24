"""Evaluate frozen CHIA proposals against an additional, post hoc fault set.

Created after observing the initial 4-fault results: this is a supplementary
stress test, NOT a blind or statistically representative held-out benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from verify import RTL_FILES, run, validate
from scripts.replay_summary import FROZEN_RTL_SHA256


FAULTS = {
    "resetb_bypassed": (
        "digital_pll.v", "assign ireset = ~resetb | ~enable;",
        "assign ireset = ~enable;"),
    "dco_mode_stuck_external": (
        "digital_pll.v", "assign itrim = (dco == 1'b0) ? otrim : ext_trim;",
        "assign itrim = ext_trim;"),
    "controller_increase_disabled": (
        "digital_pll_controller.v", "tval <= tval + 1;",
        "tval <= tval;"),
    "controller_decrease_disabled": (
        "digital_pll_controller.v", "tval <= tval - 1;",
        "tval <= tval;"),
    "controller_updates_early": (
        "digital_pll_controller.v", "if (prep == 3'b111) begin",
        "if (prep == 3'b001) begin"),
    "ring_trim_reversed": (
        "ring_osc2x13.v",
        "delay = delay_base + delay_per_bit * $itor(bcount);",
        "delay = delay_base - delay_per_bit * $itor(bcount);"),
    "phase1_held_low": (
        "ring_osc2x13.v", "clockp[1] <= (clockp[1] === 1'b0);",
        "clockp[1] <= 1'b0;"),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, required=True)
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="A completed CHIA run with frozen tests")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--expected-aggregates", type=pathlib.Path,
                    help="Optional published aggregate report to audit against")
    args = ap.parse_args()
    rtl, prior, out = args.rtl.resolve(), args.run.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("output must be a new or empty directory")
    summary = json.loads((prior / "summary.json").read_text())
    rows = summary["tests"]
    candidates = {name: validate(row["candidate"]) for name, row in rows.items()
                  if name.startswith(("baseline_", "agent_"))}
    if not any(name.startswith("baseline_") for name in candidates) or not any(
            name.startswith("agent_") for name in candidates):
        ap.error("run needs both agent and baseline tests")
    original_result = prior / "runs" / "agent_0" / "original" / "result.json"
    expected = (json.loads(original_result.read_text())["rtl_sha256"]
                if original_result.is_file() else FROZEN_RTL_SHA256)
    actual = {name: digest(rtl / name) for name in RTL_FILES}
    if actual != expected:
        ap.error("RTL hash differs from the run which generated these tests")
    for fault, (filename, before, _after) in FAULTS.items():
        if (rtl / filename).read_text().count(before) != 1:
            ap.error(f"fault {fault}: exact source anchor absent or ambiguous")
    out.mkdir(parents=True, exist_ok=True)
    sources = {}
    for label in ("original", *FAULTS):
        dst = out / "sources" / label
        dst.mkdir(parents=True)
        for filename in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(rtl / filename, dst / filename)
        if label in FAULTS:
            filename, before, after = FAULTS[label]
            path = dst / filename
            path.write_text(path.read_text().replace(before, after, 1))
        sources[label] = dst
    report = {
        "scope": "post hoc supplementary injected faults; not blind held-out",
        "rtl_sha256": actual,
        "prior_summary_sha256": digest(prior / "summary.json"),
        "mutants": list(FAULTS), "tests": {},
    }
    for label, candidate in candidates.items():
        results = {fault: run(path, candidate, out / "runs" / label / fault)
                   for fault, path in sources.items()}
        statuses = {fault: result["status"] for fault, result in results.items()}
        valid = statuses["original"] == "pass"
        detected = [fault for fault in FAULTS if valid and statuses[fault] == "fail"]
        report["tests"][label] = {"candidate": candidate, "original_pass": valid,
                                  "detected": detected, "statuses": statuses}
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    for prefix in ("baseline_", "agent_"):
        selected = {label: row for label, row in report["tests"].items()
                    if label.startswith(prefix)}
        report[prefix + "detected_union"] = sorted({fault for row in selected.values()
                                                    for fault in row["detected"]})
        report[prefix + "valid_count"] = sum(row["original_pass"]
                                             for row in selected.values())
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    for prefix in ("baseline_", "agent_"):
        print(f"{prefix}: {report[prefix+'valid_count']} valid; "
              f"{len(report[prefix+'detected_union'])}/{len(FAULTS)} detected "
              f"{report[prefix+'detected_union']}")
    tool_errors = [(label, fault, status) for label, row in report["tests"].items()
                   for fault, status in row["statuses"].items()
                   if status in {"invalid", "compile_error", "tool_error"}]
    print("Tool/compile errors:", tool_errors)
    if args.expected_aggregates:
        recorded = json.loads(args.expected_aggregates.read_text())["supplementary_stress"]
        matched = (
            report["baseline_valid_count"] == recorded["baseline_valid"]
            and report["agent_valid_count"] == recorded["agent_valid"]
            and report["baseline_detected_union"] == sorted(recorded["baseline_detected"])
            and report["agent_detected_union"] == sorted(recorded["agent_detected"])
            and not tool_errors and not recorded["tool_or_compile_errors"]
            and list(FAULTS) == recorded["mutants"]
        )
        report["published_aggregates_match"] = matched
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print("Published stress summary:", "MATCH" if matched else "DIFF")
        if not matched:
            raise SystemExit(1)
    print("Detailed summary:", out / "summary.json")


if __name__ == "__main__":
    main()
