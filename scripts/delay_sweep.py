"""Replay frozen CHIA proposals under behavioral oscillator-delay perturbations.

These are sensitivity tests of the FUNCTIONAL RTL model, NOT silicon PVT
corners, gate-level simulation, or claims about physical jitter/lock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mutants import prepare
from verify import RTL_FILES, run, validate


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, required=True)
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="Completed CHIA run directory containing summary.json and runs/")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    rtl, prior, output = args.rtl.resolve(), args.run.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        ap.error("output must be a new or empty directory; never overwrite evidence")
    summary_path = prior / "summary.json"
    if not summary_path.is_file():
        ap.error(f"missing completed run: {summary_path}")
    summary = json.loads(summary_path.read_text())
    rows = summary.get("tests", {})
    candidates = {name: validate(row["candidate"]) for name, row in rows.items()
                  if name.startswith(("baseline_", "agent_"))}
    if not any(n.startswith("baseline_") for n in candidates) or not any(
            n.startswith("agent_") for n in candidates):
        ap.error("completed run must contain baseline and agent candidates")
    expected_hashes = json.loads((prior / "runs" / "agent_0" / "original" /
                                  "result.json").read_text())["rtl_sha256"]
    hashes = {name: sha256(rtl / name) for name in RTL_FILES}
    if hashes != expected_hashes:
        ap.error("RTL does not match the frozen CHIA run; check sync_lab_rtl.sh")
    source = (rtl / "digital_pll.v").read_text()
    # Change only the two parameters used in FUNCTIONAL oscillator mode.
    params = {"osc_delay_base": 1.168, "osc_delay_per_bit": 0.012}
    for key, val in params.items():
        pattern = rf"(parameter real {key}\s*=\s*){val}(\s*;)"
        if len(list(re.finditer(pattern, source))) != 1:
            ap.error(f"could not locate unique original {key}={val} in RTL")
    output.mkdir(parents=True, exist_ok=True)
    report = {"scope": "behavioral delay sensitivity only; NOT physical PVT",
              "source_run": str(args.run), "rtl_sha256": hashes,
              "candidates_sha256": sha256(summary_path), "cases": {}}
    for label, multiplier in (("fast_90pct", .90), ("nominal_100pct", 1.0),
                              ("slow_110pct", 1.10)):
        case_root = output / label
        # prepare() creates sources/original itself; seed it from a separate
        # directory to avoid copying each file onto itself.
        clean = case_root / "seed"
        clean.mkdir(parents=True)
        for filename in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(rtl / filename, clean / filename)
        revised = source
        for key, val in params.items():
            pattern = rf"(parameter real {key}\s*=\s*){val}(\s*;)"
            revised = re.sub(pattern, lambda m: f"{m[1]}{val * multiplier:.6f}{m[2]}",
                             revised, count=1)
        (clean / "digital_pll.v").write_text(revised)
        sources = prepare(clean, case_root / "sources")
        case = {"delay_multiplier": multiplier, "parameters_ns": {
            key: val * multiplier for key, val in params.items()}, "tests": {}}
        for name, candidate in candidates.items():
            statuses = {variant: run(path, candidate,
                       case_root / "runs" / name / variant)["status"]
                        for variant, path in sources.items()}
            valid = statuses["original"] == "pass"
            detected = [m for m in sources if m != "original" and valid
                        and statuses[m] == "fail"]
            case["tests"][name] = {"original_pass": valid, "detected": detected,
                                   "statuses": statuses}
        for prefix in ("baseline_", "agent_"):
            selected = {name: row for name, row in case["tests"].items()
                        if name.startswith(prefix)}
            case[prefix + "valid_count"] = sum(row["original_pass"]
                                                for row in selected.values())
            case[prefix + "detected_union"] = sorted({fault for row in selected.values()
                                                      for fault in row["detected"]})
        report["cases"][label] = case
        (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{label}: agent {case['agent_valid_count']}/{sum(n.startswith('agent_') for n in candidates)} valid, "
              f"detected {len(case['agent_detected_union'])}/{len(sources)-1}; "
              f"baseline {case['baseline_valid_count']}/{sum(n.startswith('baseline_') for n in candidates)} valid, "
              f"detected {len(case['baseline_detected_union'])}/{len(sources)-1}", flush=True)
    print("Detailed summary:", output / "summary.json")


if __name__ == "__main__":
    main()
