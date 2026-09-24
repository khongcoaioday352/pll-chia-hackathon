"""Print a compact audit of a real CHIA summary, without claiming coverage."""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/summarize.py results/.../summary.json")
    data = json.loads(pathlib.Path(sys.argv[1]).read_text())
    rows = data.get("tests", {})
    baseline = [(name, row) for name, row in rows.items() if name.startswith("baseline_")]
    agent = [(name, row) for name, row in rows.items() if name.startswith("agent_")]
    print(f"Model: {data.get('model')} | mutants: {len(data.get('mutants', []))} | requested rounds: {data.get('rounds')}")
    print(f"Baseline tests: {len(baseline)}; valid on original: {sum(r.get('original_pass', False) for _, r in baseline)}; unique mutants detected: {len(data.get('baseline_detected', []))}")
    print(f"Agent tests: {len(agent)}; valid on original: {sum(r.get('original_pass', False) for _, r in agent)}; unique mutants detected: {len(data.get('agent_detected_union', []))}")
    print(f"Invalid agent proposals: {len(data.get('invalid_agent_proposals', []))}")
    for name, row in rows.items():
        print(f"{name}: original_pass={row.get('original_pass')} detected={row.get('detected')} statuses={row.get('statuses')}")
    if not agent or not any(r.get("original_pass") for _, r in agent):
        raise SystemExit("NOT READY: no valid agent-authored test; inspect agent_logs and proposal files")
    if not baseline:
        raise SystemExit("NOT READY: no fixed baseline tests")
    print("Audit OK: the run contains valid agent-authored and baseline tests; interpret effectiveness from the rows above.")


if __name__ == "__main__":
    main()
