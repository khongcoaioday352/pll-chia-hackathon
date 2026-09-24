"""Check whether the two faults missed by the frozen agent suite are observable.

The reset/phase candidate is human authored AFTER inspecting the stress results.
It is a mutation-adequacy control, never part of the agent's reported 5/7.
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
from scripts.stress_suite import FAULTS


TARGETS = ("resetb_bypassed", "phase1_held_low")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--candidate", type=pathlib.Path,
                    default=pathlib.Path("examples/phase1_reset_program.json"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    rtl, out = args.rtl.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("output must be a new or empty directory")
    actual = {name: hashlib.sha256((rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if actual != FROZEN_RTL_SHA256:
        ap.error("RTL SHA-256 mismatch: use the exact published lab snapshot")
    candidate = validate(json.loads(args.candidate.read_text()))
    for fault in TARGETS:
        filename, before, _after = FAULTS[fault]
        if (rtl / filename).read_text().count(before) != 1:
            ap.error(f"fault {fault}: source anchor absent or ambiguous")
    sources = {}
    for label in ("original", *TARGETS):
        dst = out / "sources" / label
        dst.mkdir(parents=True)
        for filename in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(rtl / filename, dst / filename)
        if label in TARGETS:
            filename, before, after = FAULTS[label]
            source = dst / filename
            source.write_text(source.read_text().replace(before, after, 1))
        sources[label] = dst
    statuses = {label: run(path, candidate, out / "runs" / label)["status"]
                for label, path in sources.items()}
    adequate = (statuses["original"] == "pass" and
                all(statuses[fault] == "fail" for fault in TARGETS))
    report = {
        "classification": "Post hoc HUMAN-authored oracle; not an agent proposal",
        "candidate": candidate, "rtl_sha256": actual,
        "statuses": statuses, "both_missed_faults_detectable": adequate,
        "interpretation": "Shows these two faults are detectable by the current top-level test language; does not change the agent result of 5/7.",
    }
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Human oracle status:", statuses, flush=True)
    print("Both missed faults detectable:", "PASS" if adequate else "FAIL",
          "Detailed results:", out / "summary.json")
    if not adequate:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
