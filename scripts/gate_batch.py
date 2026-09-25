"""Run private post-route output probes sequentially, without an AI backend.

Stop at the first failed corner. Keep EDA logs and lab artifacts on the server;
the aggregate report contains only measurements and diagnostic status.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lab", type=pathlib.Path,
                    default=pathlib.Path("~/stdcell-pll").expanduser())
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--candidate", type=pathlib.Path,
                    default=pathlib.Path("examples/agent_program.json"))
    ap.add_argument("--corners", default="TC,BC,WC")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    corners = args.corners.split(",")
    if not corners or len(set(corners)) != len(corners) or any(c not in ("BC", "TC", "WC") for c in corners):
        ap.error("--corners must be distinct BC,TC,WC values separated by commas")
    if args.output.exists():
        ap.error("output directory must be new; prior lab results remain immutable")
    args.output.mkdir(parents=True)
    report: dict = {"classification": "private post-route diagnostic; no lock/PVT claim",
                    "corners_requested": corners, "corners_completed": [], "runs": {},
                    "all_functional_assertions_passed": False,
                    "lock_verified": False, "sdf_annotation_completeness_verified": False}
    failed = False
    for corner in corners:
        dest = args.output / corner
        cmd = [sys.executable, str(pathlib.Path(__file__).with_name("gate_output_probe.py").resolve()),
               "--lab", str(args.lab), "--rtl", str(args.rtl),
               "--candidate", str(args.candidate), "--corner", corner,
               "--output", str(dest)]
        print(f"START {corner}", flush=True)
        with (args.output / f"driver_{corner}.log").open("w") as log:
            process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)
        summary_path = dest / "summary.json"
        if summary_path.exists():
            data = json.loads(summary_path.read_text())
            row = {"process_returncode": process.returncode,
                   "functional_assertions_passed": data["functional_assertions_passed_in_gate_run"],
                   "measurements": data["measurements"], "sdf_error_pattern_found": data["sdf_error_pattern_found"],
                   "source_sha256": data["source_sha256"],
                   "sdf_annotation_completeness_verified": False}
            report["corners_completed"].append(corner)
        else:
            row = {"process_returncode": process.returncode,
                   "error": "probe produced no summary; review private driver log"}
        report["runs"][corner] = row
        if process.returncode or not row.get("functional_assertions_passed", False):
            failed = True
            print(f"STOP {corner}: probe did not establish functional assertion pass; review {args.output}/driver_{corner}.log", flush=True)
            break
        print(f"PASS {corner}: measurements={row['measurements']} (lock/SDF completeness unverified)", flush=True)
    report["all_functional_assertions_passed"] = not failed and len(report["corners_completed"]) == len(corners)
    report["status"] = "completed_diagnostic" if report["all_functional_assertions_passed"] else "stopped_for_review"
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Summary:", args.output / "summary.json", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
