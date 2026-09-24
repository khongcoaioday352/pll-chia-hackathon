"""Reproduce the public PLLGuard evidence from one command, without an LLM.

This deterministic demo replays SAVED agent programs; it does not generate new
agent proposals. Seven-fault stress and the human adequacy control are post hoc.
The optional time-matched baseline is a separate post hoc sensitivity check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = pathlib.Path("evidence")
SCRIPTS = pathlib.Path("scripts")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=pathlib.Path,
                        default=pathlib.Path("rtl_gf180_snapshot"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--include-time-matched", action="store_true",
                        help="Also run the post hoc matched-time baseline against 4+7 faults")
    args = parser.parse_args()
    rtl = args.rtl.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output must be a new or empty directory")
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        parser.error("Icarus Verilog (iverilog and vvp) must be on PATH")
    inputs = {str(path): ROOT / path for path in (
        EVIDENCE / "gemini_36_three_v2" / "summary.json",
        EVIDENCE / "stress_public_replay_matrix.json",
        EVIDENCE / "supplementary_console_summary.json")}
    inputs.update({"rtl/" + name: rtl / name for name in (
        "digital_pll.v", "digital_pll_controller.v", "ring_osc2x13.v")})
    if args.include_time_matched:
        for recorded in (EVIDENCE / "time_matched_console_summary.json",
                         EVIDENCE / "time_matched_public_replay_matrix.json"):
            inputs[str(recorded)] = ROOT / recorded
    missing = [name for name, path in inputs.items() if not path.is_file()]
    if missing:
        parser.error(f"missing public input files: {missing}")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"scope": "deterministic replay of public saved tests; NOT new LLM proposals",
                "python": sys.version.split()[0],
                "inputs_sha256": {name: digest(path) for name, path in inputs.items()},
                "steps": {}}
    commands = [
        ("source_check", [SCRIPTS / "check_source.py", "--rtl", rtl], None),
        ("budget", [SCRIPTS / "audit_test_budget.py", "--output",
                    output / "test_budget.json"], output / "test_budget.json"),
        ("primary", [SCRIPTS / "replay_summary.py", "--rtl", rtl, "--output",
                     output / "primary"], output / "primary" / "comparison.json"),
        ("stress", [SCRIPTS / "stress_suite.py", "--rtl", rtl, "--run",
                    EVIDENCE / "gemini_36_three_v2", "--expected-aggregates",
                    EVIDENCE / "supplementary_console_summary.json",
                    "--expected-matrix", EVIDENCE / "stress_public_replay_matrix.json",
                    "--output", output / "stress"], output / "stress" / "summary.json"),
        ("human_control", [SCRIPTS / "check_fault_adequacy.py", "--rtl", rtl,
                           "--output", output / "human_control"],
         output / "human_control" / "summary.json"),
    ]
    if args.include_time_matched:
        commands.append(("time_matched_post_hoc", [
            SCRIPTS / "time_matched_baseline.py", "--rtl", rtl,
            "--expected-aggregates", EVIDENCE / "time_matched_console_summary.json",
            "--expected-matrix", EVIDENCE / "time_matched_public_replay_matrix.json",
            "--output", output / "time_matched"],
            output / "time_matched" / "summary.json"))
    for label, command, result in commands:
        argv = [str(sys.executable), *map(str, command)]
        proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True,
                              check=False)
        (output / f"{label}.stdout.txt").write_text(proc.stdout)
        (output / f"{label}.stderr.txt").write_text(proc.stderr)
        passed = proc.returncode == 0 and (result is None or result.is_file())
        manifest["steps"][label] = {
            "status": "pass" if passed else "fail",
            "exit_code": proc.returncode,
            "result": str(result.relative_to(output)) if result else None,
            "result_sha256": digest(result) if result and result.is_file() else None,
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"{label}: {'PASS' if passed else 'FAIL'}", flush=True)
        if not passed:
            print("Details:", output / f"{label}.stderr.txt", "and",
                  output / f"{label}.stdout.txt", flush=True)
            raise SystemExit(1)
    replay = json.loads((output / "primary" / "comparison.json").read_text())
    stress = json.loads((output / "stress" / "summary.json").read_text())
    control = json.loads((output / "human_control" / "summary.json").read_text())
    budget = json.loads((output / "test_budget.json").read_text())
    verified = (replay["all_match"] and stress.get("published_aggregates_match")
                and stress.get("published_matrix_match")
                and control["both_missed_faults_detectable"]
                and budget["groups"]["agent"]["total_simulated_time_ns"] == 7260
                and budget["groups"]["baseline"]["total_simulated_time_ns"] == 5710)
    manifest["published_evidence_verified"] = bool(verified)
    if args.include_time_matched:
        matched = json.loads((output / "time_matched" / "summary.json").read_text())
        manifest["post_hoc_time_matched"] = {
            "classification": "new offline measurement; never silently folded into published claims",
            "published_matrix_match": matched.get("published_matrix_match"),
            "primary_agent_detected": matched["results"]["primary"]["agent_detected_union"],
            "primary_baseline_detected": matched["results"]["primary"]["baseline_detected_union"],
            "stress_agent_detected": matched["results"]["stress_post_hoc"]["agent_detected_union"],
            "stress_baseline_detected": matched["results"]["stress_post_hoc"]["baseline_detected_union"],
        }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Published evidence:", "VERIFIED" if verified else "DIFF",
          "| manifest:", output / "manifest.json", flush=True)
    if not verified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
