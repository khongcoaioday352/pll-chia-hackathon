"""Reproduce a saved mutation summary without an LLM or API credits."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mutants import prepare
from verify import RTL_FILES, run, validate


FROZEN_RTL_SHA256 = {
    "digital_pll.v": "a248e88bf36741ba3c2ce417d287e919bf18ae4ccf64e6fe2fc4ddcdc56d49be",
    "digital_pll_controller.v": "8eccb472147bcaa7832e9d4dcda3fa7c873accdd2a8dcdfbae95fb9281973480",
    "ring_osc2x13.v": "986596591514a2176613dca298b12437641c24268e14824a33777d62b101b74c",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--summary", type=pathlib.Path,
                    default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    rtl, summary_path, out = args.rtl.resolve(), args.summary.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("output directory must be new or empty")
    actual = {name: hashlib.sha256((rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if actual != FROZEN_RTL_SHA256:
        ap.error("RTL SHA-256 mismatch; replay requires the exact published lab snapshot")
    expected = json.loads(summary_path.read_text())
    sources = prepare(rtl, out / "sources")
    if list(sources)[1:] != expected["mutants"]:
        ap.error("fault suite differs from the published experiment")
    comparisons = {}
    for label, previous in expected["tests"].items():
        candidate = validate(previous["candidate"])
        results = {fault: run(path, candidate, out / "runs" / label / fault)
                   for fault, path in sources.items()}
        statuses = {fault: result["status"] for fault, result in results.items()}
        valid = statuses["original"] == "pass"
        detected = [fault for fault in expected["mutants"]
                    if valid and statuses[fault] == "fail"]
        matched = (statuses == previous["statuses"]
                   and valid == previous["original_pass"]
                   and sorted(detected) == sorted(previous["detected"]))
        comparisons[label] = {"matched": matched, "statuses": statuses,
                              "detected": detected, "original_pass": valid}
        print(f"{label}: {'MATCH' if matched else 'DIFF'} detected={detected}", flush=True)
    audit = {"all_match": all(row["matched"] for row in comparisons.values()),
             "rtl_sha256": actual, "expected_summary": str(args.summary),
             "tests": comparisons}
    (out / "comparison.json").write_text(json.dumps(audit, indent=2) + "\n")
    print("Replay:", "PASS" if audit["all_match"] else "FAIL",
          "Detailed results:", out / "comparison.json")
    if not audit["all_match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
