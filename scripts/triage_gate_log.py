"""Classify private Questa errors locally without printing simulator log lines.

Only aggregate categories and simulator message IDs are emitted. No PDK,
netlist, SDF, raw Questa text, lab path, or cell instance is copied to GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import pathlib
import re


def classify(line: str) -> str:
    lower = line.lower()
    if re.search(r"sdf|annotat|iopath|interconnect|celltype|instance not found", lower):
        return "annotation_or_sdf"
    if re.search(r"setup|hold|pulse|width|period|recovery|removal|timing.?check|timing violation", lower):
        return "timing_check"
    if re.search(r"license|licence", lower):
        return "license"
    return "other_needs_private_review"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="Private gate_output_probe output directory")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must be new to retain previous audits")
    log = args.run / "vsim.log"
    raw = log.read_bytes()
    clean = re.sub(r"(?m)^\s*#\s?", "", raw.decode("utf-8", errors="replace"))
    lines = clean.splitlines()
    found = []
    for i, line in enumerate(lines):
        if re.search(r"(?i)^\s*(?:\*\*\s*(?:error|fatal)\b|error:)|"
                     r"(?i:sdf[^\n]*(?:failed to annotate|not found)|failed to annotate[^\n]*sdf)", line):
            # Questa often emits the error code on one line and the descriptive
            # timing check or annotation detail on the following line.
            kind = classify(line)
            if kind == "other_needs_private_review" and i + 1 < len(lines):
                kind = classify(lines[i + 1])
            found.append((kind, re.findall(r"(?i)\bvsim-(\d{2,6})\b", line)))
    categories = Counter(kind for kind, _ in found)
    codes = Counter(code for _, group in found for code in group)
    result = {"classification": "private local error triage; not SDF verification",
              "vsim_log_sha256": hashlib.sha256(raw).hexdigest(),
              "error_count": len(found), "category_counts": dict(sorted(categories.items())),
              "simulator_error_id_counts": dict(sorted(codes.items())),
              "raw_error_text_saved": False, "annotation_completeness_verified": False,
              "lock_verified": False,
              "note": "Categories are keyword heuristics; inspect private vsim.log for root cause."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Error count:", len(found), "| categories:", dict(categories),
          "| Questa IDs:", dict(codes))
    print("Classification only; inspect private log before making a PVT claim.")


if __name__ == "__main__":
    main()
