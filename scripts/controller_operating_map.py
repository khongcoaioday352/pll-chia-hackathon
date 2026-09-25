"""Post hoc behavioral PLL edge-count characterization on pinned GF180 RTL.

These human-designed diagnostics are not agent-authored tests, mutation scores,
physical PVT measurements, or evidence of PLL lock. Each steady-state row uses
a fresh simulator reset. A separate transition row reproduces the div=6 to
div=16 sequence used by the frozen agent test without enforcing its assertion.
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

MEASUREMENT = re.compile(r"^MEASURE ([A-Za-z][A-Za-z0-9_]*)=(\d+)$", re.M)


def steady_candidate(period: int, divider: int, dwell: int) -> dict:
    waits = [{"op": "wait", "ns": min(2000, dwell - n)}
             for n in range(0, dwell, 2000)]
    return validate({"ref_period_ns": period, "steps": [
        {"op": "set", "resetb": 1, "enable": 1, "dco": 0, "div": divider},
        *waits,
        {"op": "measure", "ns": 400, "name": "edges"},
        {"op": "assert", "left": "edges", "operator": "ge", "right": 0},
    ]})


def transition_candidate(period: int) -> dict:
    return validate({"ref_period_ns": period, "steps": [
        {"op": "set", "resetb": 1, "enable": 1, "dco": 0, "div": 6},
        {"op": "wait", "ns": 2000},
        {"op": "measure", "ns": 400, "name": "div6"},
        {"op": "set", "div": 16},
        {"op": "wait", "ns": 2000},
        {"op": "measure", "ns": 400, "name": "div16"},
        {"op": "assert", "left": "div6", "operator": "ge", "right": 0},
    ]})


def measure(rtl: pathlib.Path, candidate: dict, path: pathlib.Path) -> dict:
    result = run(rtl, candidate, path)
    counts = {name: int(value) for name, value in MEASUREMENT.findall(result["log"])}
    return {"status": result["status"], "counts": counts,
            "result_path": str(path / "result.json")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    rtl, out = args.rtl.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("output must be new or empty")
    actual = {name: hashlib.sha256((rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if actual != FROZEN_RTL_SHA256:
        ap.error("RTL hash differs from pinned GF180 source")
    report = {"classification": "human-designed post hoc behavioral diagnostics; not PVT, PLL lock, or agent score",
              "rtl_sha256": actual, "window_ns": 400, "steady": [], "transitions": []}
    failures = []
    for period in (30, 40, 50):
        for divider in (6, 8, 12, 16):
            for dwell in (2000, 4000):
                row = {"ref_period_ns": period, "div": divider,
                       "dwell_ns": dwell, "ideal_divided_edge_count": 400 * divider / period}
                row.update(measure(rtl, steady_candidate(period, divider, dwell),
                                   out / "runs" / f"ref{period}_div{divider}_wait{dwell}"))
                report["steady"].append(row)
                if row["status"] != "pass" or "edges" not in row["counts"]:
                    failures.append(row["result_path"])
                print(f"{period} ns div={divider:2d} wait={dwell:4d}: "
                      f"{row['counts'].get('edges', '?')} edges | {row['status']}", flush=True)
        transition = {"ref_period_ns": period}
        transition.update(measure(rtl, transition_candidate(period),
                                  out / "runs" / f"ref{period}_div6_to16"))
        report["transitions"].append(transition)
        if transition["status"] != "pass" or set(transition["counts"]) != {"div6", "div16"}:
            failures.append(transition["result_path"])
        print(f"{period} ns div 6→16: {transition['counts']} | {transition['status']}", flush=True)
    report["measurement_errors"] = failures
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Detailed summary:", out / "summary.json")
    if failures:
        raise SystemExit("Some measurements failed; inspect measurement_errors")


if __name__ == "__main__":
    main()
