"""Audit clock glitches in a private Questa gate-level run.

Use with the candidate JSON that produced the run.  Only aggregate values are
written; never publish the private Questa log, SDF, library, or routed netlist.
This is a digital-model diagnosis, not an analog PVT or PLL-lock certificate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


PERIOD = re.compile(r"\$period\(.*?:\s*\d+\s+ps,\s*:\s*(\d+)\s+ps,\s*(\d+)\s+ps")
EDGE = re.compile(r"EDGE_NS phase=(\d+) trim=(\d+) delta=([0-9.]+) at=([0-9.]+)")
MEASURE = re.compile(r"(?m)^\s*#?\s*MEASURE ([A-Za-z][A-Za-z0-9_]*)=(\d+)\s*$")
ERROR = re.compile(r"\*\* (?:Error|Fatal):\s*\$(\w+)\(")


def intervals(candidate: dict) -> list[dict]:
    """Recover bench stimulus intervals from verify.make_program_tb's clock."""
    if "steps" not in candidate:
        raise ValueError("expected a program candidate with timed steps")
    t_ns = 20  # verify.make_program_tb starts the program after #20.
    trim = 0
    resetb = 0
    spans = []
    for step in candidate["steps"]:
        if step["op"] == "set":
            resetb = step.get("resetb", resetb)
            trim = step.get("trim", trim)
        elif step["op"] in ("wait", "measure"):
            start = t_ns
            t_ns += step["ns"]
            if step["op"] == "measure":
                spans.append({"name": step["name"], "trim": trim,
                              "resetb": resetb, "start_ps": start * 1000,
                              "end_ps": t_ns * 1000})
    return spans


def audit(log: bytes, candidate: dict) -> dict:
    text = log.decode("utf-8", errors="replace")
    spans = intervals(candidate)
    measured = {name: int(n) for name, n in MEASURE.findall(text)}
    if set(measured) != {s["name"] for s in spans}:
        raise ValueError("missing or duplicate measurement in simulator log")
    events = []
    for line in text.splitlines():
        match = PERIOD.search(line)
        if match:
            events.append((int(match[1]), int(match[2])))
    observed_edges = [tuple((int(p), int(c), float(d), float(t)))
                      for p, c, d, t in EDGE.findall(text)]
    required = sorted({minimum for _, minimum in events})
    rows = []
    matched_events = 0
    for span in spans:
        start, end = span["start_ps"], span["end_ps"]
        in_window = [(t, minimum) for t, minimum in events if start <= t < end]
        matched_events += len(in_window)
        phase = {}
        for p in (0, 1):
            deltas = [round(delta * 1000) for pp, code, delta, at in observed_edges
                      if pp == p and code == span["trim"] and
                      start <= round(at * 1000) < end]
            phase[str(p)] = {
                "traced_intervals": len(deltas),
                "minimum_delta_ps": min(deltas) if deltas else None,
                # A period requirement from a violated check is a diagnostic
                # threshold only, not a complete STA or SDF coverage proof.
                "below_observed_period_requirement":
                    sum(delta < min(required) for delta in deltas) if required else None,
            }
        rows.append({"name": span["name"], "trim": span["trim"],
                     "start_ps": start, "end_ps": end,
                     "output_rising_edges": measured[span["name"]],
                     "period_violations": len(in_window), "phase": phase})
    return {
        "classification": "private routed-gate clock diagnostic",
        "log_sha256": hashlib.sha256(log).hexdigest(),
        "total_period_violations": len(events),
        "period_violations_outside_measured_windows": len(events) - matched_events,
        "observed_period_requirements_ps": required,
        "timing_error_types": dict(sorted(Counter(ERROR.findall(text)).items())),
        "sdf_backannotation_completed_marker":
            "SDF Backannotation Successfully Completed" in text,
        "sdf_warnings": len(re.findall(r"\*\* Warning: \(vsim-SDF-", text)),
        "program_pass_marker": "RESULT PASS PROGRAM" in text,
        "measured_windows": rows,
        "lock_verified": False,
        "sdf_annotation_completeness_verified": False,
        "physical_ring_behavior_verified": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must be new to preserve earlier evidence")
    result = audit(args.log.read_bytes(), json.loads(args.candidate.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Period violations:", result["total_period_violations"],
          "| timing error types:", result["timing_error_types"])
    for row in result["measured_windows"]:
        print(f"{row['name']} trim={row['trim']}: edges={row['output_rising_edges']} "
              f"period_errors={row['period_violations']} "
              f"phase0={row['phase']['0']} phase1={row['phase']['1']}")
    print("Private aggregate:", args.output)


if __name__ == "__main__":
    main()
