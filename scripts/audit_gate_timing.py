"""Summarize private Questa timing violations without exporting cell or SDF text.

This audit does not waive timing checks or prove SDF annotation completeness.
Keep its output under the ignored results/ directory on the lab server.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from triage_gate_log import summarize_errors


CHECKS = ("setuphold", "setup", "hold", "width", "period", "recovery",
          "removal", "recrem", "skew", "nochange")


def timing_types(text: str) -> dict[str, int]:
    """Classify error blocks, including Questa's multiline timing messages."""
    lines = re.sub(r"(?m)^\s*#\s?", "", text).splitlines()
    counts: Counter[str] = Counter()
    for pos, line in enumerate(lines):
        if not re.search(r"(?i)^\s*(?:\*\*\s*(?:error|fatal)\b|error:)", line):
            continue
        block = " ".join(lines[pos:pos + 3]).lower()
        if "sdf" in block or "annotat" in block:
            continue
        matches = [kind for kind in CHECKS if re.search(r"\b(?:\$)?" + kind + r"\b", block)]
        if "setuphold" in matches:
            matches = [x for x in matches if x not in ("setup", "hold")]
        if "recrem" in matches:
            matches = [x for x in matches if x not in ("recovery", "removal")]
        counts[matches[0] if matches else "unknown"] += 1
    return dict(sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new; old evidence is immutable")
    report = {"classification": "private timing triage, not timing repair or lock proof",
              "timing_checks_suppressed": False, "sdf_annotation_verified": False,
              "lock_verified": False, "corners": {}}
    for corner in ("BC", "TC", "WC"):
        log = args.run / corner / "vsim.log"
        raw = log.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        summary = json.loads((args.run / corner / "summary.json").read_text())
        counts = summarize_errors(content)
        if counts["category_counts"].get("timing_check", 0) != summary["timing_check_error_count"]:
            parser.error(f"{corner}: timing counts differ from saved gate probe")
        row = {"log_sha256": hashlib.sha256(raw).hexdigest(),
               "timing_check_errors": summary["timing_check_error_count"],
               "timing_type_counts_heuristic": timing_types(content),
               "other_error_categories": {k: v for k, v in counts["category_counts"].items()
                                          if k != "timing_check"},
               "simulator_error_id_counts": counts["simulator_error_id_counts"],
               "output_assertions_observed": summary["observable_output_assertions_met"]}
        report["corners"][corner] = row
        print(f"{corner}: {row['timing_check_errors']} timing violations, "
              f"types={row['timing_type_counts_heuristic']}, "
              f"other={row['other_error_categories']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("Private aggregate:", args.output)


if __name__ == "__main__":
    main()
