"""Recheck existing private Questa logs without rerunning physical simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.gate_output_probe import analyze_log
from verify import validate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="Existing gate_output_probe output directory")
    ap.add_argument("--candidate", type=pathlib.Path,
                    default=pathlib.Path("examples/agent_program.json"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("new audit output only; prior evidence stays unchanged")
    old = json.loads((args.run / "summary.json").read_text())
    candidate = validate(json.loads(args.candidate.read_text()))
    if "steps" not in candidate:
        ap.error("candidate must contain named output measurements")
    if hashlib.sha256(args.candidate.read_bytes()).hexdigest() != old["candidate_sha256"]:
        ap.error("saved run and candidate do not match")
    if hashlib.sha256((args.run / "tb.v").read_bytes()).hexdigest() != old["bench_sha256"]:
        ap.error("saved testbench hash mismatch")
    expected = [step["name"] for step in candidate["steps"] if step["op"] == "measure"]
    vsim_log = args.run / "vsim.log"
    if not vsim_log.is_file():
        ap.error("saved vsim.log not found")
    analysis = analyze_log(vsim_log.read_text(errors="replace"), expected)
    successful_vsim = any(row["step"] == "vsim" and row["returncode"] == 0
                          and not row["timed_out"] for row in old["steps"])
    observed = (successful_vsim and analysis["measurements_complete"] and
              analysis["program_pass_marker"] and not analysis["program_fail_marker"] and
              analysis["other_simulator_error_count"] == 0)
    passed = observed and analysis["timing_check_error_count"] == 0
    result = {"classification": "private retrospective log audit; no simulation rerun",
              "original_corner": old["corner"], "vsim_log_sha256": hashlib.sha256(vsim_log.read_bytes()).hexdigest(),
              "original_summary_sha256": hashlib.sha256((args.run / "summary.json").read_bytes()).hexdigest(),
              **analysis, "observable_output_assertions_met": bool(observed),
              "functional_assertions_passed_in_gate_run": bool(passed),
              "lock_verified": False, "sdf_annotation_completeness_verified": False,
              "limitations": ["log parsing cannot prove complete SDF annotation or frequency lock",
                              "this audit does not prove that the routed netlist matches pinned RTL"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Existing", old["corner"], "run:", "PASS" if passed else "REVIEW REQUIRED")
    print("Measured:", analysis["measurements"], "complete:", analysis["measurements_complete"])
    print("Output assertions observed:", bool(observed), "| timing check errors:",
          analysis["timing_check_error_count"], "| other simulator errors:",
          analysis["other_simulator_error_count"])
    print("Private audit:", args.output)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
