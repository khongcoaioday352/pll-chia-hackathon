"""Audit published generated testbenches for internal DUT forcing.

This static check does not execute a simulator or establish lock. The published
test programs prescribe input clock periods and measurement times; those are
reported explicitly and must not be confused with a force-free-time claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.audit_test_budget import budget
from scripts.replay_summary import FROZEN_RTL_SHA256
from verify import RTL_FILES, make_tb, validate

FORBIDDEN = (
    re.compile(r"\b(?:force|release|deposit|uvm_hdl_force|vpi_put_value)\b", re.I),
    re.compile(r"\bdut\s*\.\s*[A-Za-z_][\w.\[\]]*\s*(?:<=|=|\+\+|--)", re.I),
    re.compile(r"\b(?:assign|defparam)\s+dut\s*\.", re.I),
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--primary", type=pathlib.Path,
                    default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    ap.add_argument("--later", type=pathlib.Path,
                    default=pathlib.Path("evidence/adaptive_reference_live_v3_public.json"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must not already exist")
    rtl_sha256 = {name: hashlib.sha256((args.rtl / name).read_bytes()).hexdigest()
                  for name in RTL_FILES}
    if rtl_sha256 != FROZEN_RTL_SHA256:
        ap.error("RTL differs from pinned published source")
    primary_bytes, later_bytes = args.primary.read_bytes(), args.later.read_bytes()
    primary, later = json.loads(primary_bytes), json.loads(later_bytes)
    if later["rtl_sha256"] != rtl_sha256:
        ap.error("later candidate belongs to different RTL")
    candidates = {name: row["candidate"] for name, row in primary["tests"].items()
                  if name.startswith(("agent_", "baseline_"))}
    if (set(candidates) != {*(f"agent_{i}" for i in range(3)),
                           *(f"baseline_{i}" for i in range(3))}
            or not all(primary["tests"][name]["original_pass"] for name in candidates)
            or later["tests"]["agent_2"]["development"]["original_pass"] is not True):
        ap.error("expected three passing original agent and baseline tests plus later agent_2")
    candidates["later_agent_2"] = later["tests"]["agent_2"]["candidate"]
    rows = {}
    for name, item in sorted(candidates.items()):
        candidate = validate(item)
        tb = make_tb(candidate)
        # Strip comments before scanning; measure instructions remain in code.
        scanned = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", tb)
        violations = [pattern.pattern for pattern in FORBIDDEN if pattern.search(scanned)]
        if violations:
            ap.error(f"{name} contains forcing or an internal DUT write: {violations}")
        rows[name] = {"generated_testbench_sha256": hashlib.sha256(tb.encode()).hexdigest(),
                      "source": "later live proposal" if name == "later_agent_2" else "original published run",
                      "reference_period_ns": candidate["ref_period_ns"],
                      "nominal_simulated_time_ns": budget(candidate)["simulated_time_ns"],
                      "prescribed_wait_and_measure_ns": [step["ns"] for step in candidate.get("steps", [])
                                                        if step["op"] in ("wait", "measure")],
                      "sets_external_inputs": True,
                      "internal_dut_force_or_assignment": False}
    output = {"scope": "static scan of seven generated candidate testbenches only",
              "claim": "no procedural force/release/deposit or hierarchical DUT write in generated benches",
              "limitation": "reference clock, input stimuli, and observation time are prescribed; no PLL lock or physical PVT conclusion",
              "rtl_sha256": rtl_sha256,
              "input_sha256": {"primary": hashlib.sha256(primary_bytes).hexdigest(),
                               "later": hashlib.sha256(later_bytes).hexdigest()},
              "tests": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Stimulus integrity: PASS ({len(rows)} generated benches, no internal DUT forcing)")
    print("Timed inputs: explicitly prescribed; no lock/PVT claim |", args.output)


if __name__ == "__main__":
    main()
