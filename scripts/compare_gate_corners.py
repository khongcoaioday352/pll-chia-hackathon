"""Private, read-only comparison of gate corner diagnostics with frozen RTL.

Edge rates are finite-window observations. This script does not certify SDF
annotation, timing signoff, phase/frequency lock, or fabricated PVT coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.replay_summary import FROZEN_RTL_SHA256
from verify import RTL_FILES, run, validate


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=pathlib.Path, required=True)
    ap.add_argument("--candidate", type=pathlib.Path,
                    default=pathlib.Path("examples/agent_program.json"))
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must be new to preserve the original diagnostic")
    candidate = validate(json.loads(args.candidate.read_text()))
    if "steps" not in candidate:
        ap.error("requires a measured test program")
    measures = {step["name"]: step["ns"] for step in candidate["steps"]
                if step["op"] == "measure"}
    if not {"active", "stopped"} <= measures:
        ap.error("selected candidate needs active and stopped output measurements")
    rtl_hash = {name: sha256(args.rtl / name) for name in RTL_FILES}
    if rtl_hash != FROZEN_RTL_SHA256:
        ap.error("functional RTL differs from published snapshot")
    gate = json.loads((args.run / "summary.json").read_text())
    if set(gate.get("runs", {})) != {"BC", "TC", "WC"} or gate.get("status") not in (
            "collected_with_timing_violations", "completed_diagnostic"):
        ap.error("three complete BC/TC/WC diagnostics required")
    details = {corner: json.loads((args.run / corner / "summary.json").read_text())
               for corner in ("BC", "TC", "WC")}
    checks = {"same_gate_netlist": len({x["source_sha256"]["6_final.v"]
                                       for x in details.values()}) == 1,
              "same_gate_testbench": len({x["bench_sha256"] for x in details.values()}) == 1,
              "same_candidate": all(x["candidate_sha256"] == sha256(args.candidate)
                                    for x in details.values()),
              "corner_specific_sdf": len({x["source_sha256"]["digital_pll.sdf"]
                                          for x in details.values()}) == 3,
              "complete_output_measurements": all(x.get("measurements_complete") is True
                                                  for x in details.values()),
              "outputs_observed": all(x.get("observable_output_assertions_met") is True
                                      for x in details.values()),
              "no_other_simulator_errors": all(x.get("other_simulator_error_count") == 0
                                               for x in details.values())}
    if not all(checks.values()):
        ap.error(f"cross-corner consistency check failed: {checks}")
    args.output.mkdir(parents=True)
    functional = run(args.rtl.resolve(), candidate, args.output / "functional")
    if functional["status"] != "pass" or functional["rtl_sha256"] != rtl_hash:
        ap.error("frozen functional reference did not pass; cannot compare")
    functional_edges = {key: int(value) for key, value in re.findall(
        r"(?m)^MEASURE ([A-Za-z][A-Za-z0-9_]*)=(\d+)", functional["log"])}
    if set(functional_edges) != set(measures):
        ap.error("functional output measurements incomplete")
    rows = {}
    for corner in ("BC", "TC", "WC"):
        item = details[corner]
        edges = item["measurements"]
        rows[corner] = {"active_edges": edges["active"],
                        "stopped_edges": edges["stopped"],
                        "active_window_ns": measures["active"],
                        "observed_edge_rate_mhz": round(edges["active"] * 1000 / measures["active"], 3),
                        "one_edge_resolution_mhz": round(1000 / measures["active"], 3),
                        "difference_from_functional_edges": edges["active"] - functional_edges["active"],
                        "timing_check_error_count": item["timing_check_error_count"],
                        "other_simulator_error_count": item["other_simulator_error_count"],
                        "sdf_sha256": item["source_sha256"]["digital_pll.sdf"],
                        "annotation_completeness_verified": False,
                        "timing_clean": item["timing_check_error_count"] == 0}
    summary = {"classification": "private short-window behavioral versus gate output comparison",
               "checks": checks, "functional": {"active_edges": functional_edges["active"],
                                              "stopped_edges": functional_edges["stopped"],
                                              "active_window_ns": measures["active"],
                                              "observed_edge_rate_mhz": round(
                                                  functional_edges["active"] * 1000 / measures["active"], 3)},
               "corners": rows, "gate_summary_sha256": sha256(args.run / "summary.json"),
               "candidate_sha256": sha256(args.candidate),
               "netlist_identity_to_frozen_rtl_verified": False,
               "sdf_annotation_completeness_verified": False,
               "pll_lock_verified": False,
               "limitations": ["edge rate is a finite-window count; one-edge resolution is 1000/window_ns MHz",
                               "the initial active window can include startup transients and is not steady-state lock",
                               "timing-check errors prohibit a timing-clean post-route claim",
                               "same netlist hash across corners does not prove the netlist was built from pinned RTL",
                               "do not publish private lab assets or numeric diagnostics without authorization"]}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("Cross-corner inputs:", "CONSISTENT")
    print(f"Functional: {functional_edges['active']} edges / {measures['active']} ns")
    for corner, row in rows.items():
        print(f"{corner}: {row['active_edges']} edges / {measures['active']} ns, "
              f"stopped={row['stopped_edges']}, timing-check errors={row['timing_check_error_count']}")
    print("Private summary:", args.output / "summary.json")


if __name__ == "__main__":
    main()
