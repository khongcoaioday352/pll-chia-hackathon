"""Stage a reviewable, compact copy of measured outputs for a public release."""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()
    run, out = args.run.resolve(), args.out.resolve()
    summary_file = run / "summary.json"
    if not summary_file.is_file():
        ap.error(f"missing real-run summary: {summary_file}")
    data = json.loads(summary_file.read_text())
    valid = [r for n, r in data.get("tests", {}).items()
             if n.startswith("agent_") and r.get("original_pass")]
    if not valid:
        ap.error("no valid agent-authored test in this run")
    if out.exists() and any(out.iterdir()):
        ap.error("output directory must be empty; do not overwrite previous release evidence")
    out.mkdir(parents=True, exist_ok=True)
    top = ["summary.json", "history.json"]
    top.extend(p.name for p in run.glob("prompt_*.txt"))
    top.extend(p.name for p in run.glob("proposal_*.txt"))
    included = []
    for name in sorted(set(top)):
        src = run / name
        if src.is_file():
            shutil.copy2(src, out / name)
            included.append(src.relative_to(run).as_posix())
    for src in sorted((run / "runs").rglob("*")):
        if src.is_file() and src.name in {
            "candidate.json", "tb.v", "result.json", "compile.log", "sim.log"
        }:
            dst = out / src.relative_to(run)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            included.append(src.relative_to(run).as_posix())
    (out / "EVIDENCE_NOTE.txt").write_text(
        "Measured CHIA run staged from " + str(run) + "\n"
        "Review every file for correctness, source authorization, user paths, "
        "and credentials before publishing.\n"
        "CHIA/OpenCode environment and raw agent logs are not included here; "
        "keep them privately for audit.\n"
        "Files:\n" + "\n".join(included) + "\n"
    )
    print(f"Staged {len(included)} measured files at {out}")
    print("Inspect the stage before git add / making the repo public.")


if __name__ == "__main__":
    main()
