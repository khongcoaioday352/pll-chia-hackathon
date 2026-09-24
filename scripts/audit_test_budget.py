"""Audit simulated-time budgets of the frozen published test candidates.

The times are obtained from the generated testbenches on the passing original
RTL. They are simulated nanoseconds, NOT CPU seconds, model tokens, or PVT.
The baseline disable test follows its original-pass branch; on a failing
mutant that branch may execute differently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from verify import make_tb, validate


def budget(candidate: dict) -> dict:
    valid = validate(candidate)
    bench = make_tb(valid)
    # The reference oscillator and watchdog have their own always/initial
    # blocks. Inspect only the main stimulus block before its normal finish.
    stimulus = bench.split("  initial begin\n", 1)[1]
    normal_finish = ('$display("RESULT PASS PROGRAM"); $finish;'
                     if "steps" in valid else '    $finish;')
    stimulus = stimulus.split(normal_finish, 1)[0]
    waits = [float(v) for v in re.findall(r"#(\d+(?:\.\d+)?)\s*;", stimulus)]
    if not waits or waits[0] != 20:
        raise ValueError("testbench timing template changed; review the audit")
    if "steps" in valid:
        expected = 20 + sum(step["ns"] for step in valid["steps"]
                            if step["op"] in ("wait", "measure"))
        assertions = sum(step["op"] == "assert" for step in valid["steps"])
        phases = sorted({step.get("phase", 0) for step in valid["steps"]
                         if step["op"] == "measure"})
    else:
        n = valid["observe_ns"]
        expected = {"disable": 20 + n + 10 + n,
                    "dco_trim": 20 + 20 + n + 20 + n,
                    "divider": 20 + max(5*n, 1000) + n}[valid["kind"]]
        assertions = 2 if valid["kind"] == "disable" else 1
        phases = [0]
    elapsed = sum(waits)
    if elapsed != expected:
        raise ValueError(f"expected {expected} ns, got {elapsed} ns from generated bench")
    return {"simulated_time_ns": int(elapsed), "assertions": assertions,
            "observed_phases": phases,
            "generated_tb_sha256": hashlib.sha256(bench.encode()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=pathlib.Path,
                        default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.summary.read_bytes()
    report = json.loads(source)
    rows = {}
    for name, row in report["tests"].items():
        if name.startswith(("agent_", "baseline_")):
            if not row.get("original_pass"):
                parser.error(f"{name} fails original; nominal timing path not assured")
            rows[name] = budget(row["candidate"])
    groups = {}
    for prefix in ("agent_", "baseline_"):
        selected = [row for name, row in rows.items() if name.startswith(prefix)]
        groups[prefix[:-1]] = {
            "tests": len(selected),
            "total_simulated_time_ns": sum(row["simulated_time_ns"] for row in selected),
            "total_assertions": sum(row["assertions"] for row in selected),
        }
    if groups["agent"]["tests"] != groups["baseline"]["tests"] or not groups["agent"]["tests"]:
        parser.error("baseline and agent test counts differ")
    output = {"scope": "passing original RTL, generated testbench nominal time; not CPU cost",
              "source_summary_sha256": hashlib.sha256(source).hexdigest(),
              "tests": rows, "groups": groups,
              "agent_to_baseline_time_ratio": round(
                  groups["agent"]["total_simulated_time_ns"] /
                  groups["baseline"]["total_simulated_time_ns"], 4)}
    if args.output.exists():
        parser.error("output exists; keep each audit result immutable")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("Agent/baseline simulated time (ns):",
          groups["agent"]["total_simulated_time_ns"],
          groups["baseline"]["total_simulated_time_ns"])
    print("Ratio:", output["agent_to_baseline_time_ratio"],
          "| original-pass tests:", groups["agent"]["tests"],
          "each group | output:", args.output)


if __name__ == "__main__":
    main()
