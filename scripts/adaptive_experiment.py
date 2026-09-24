"""Experimental CHIA loop with training feedback and a no-feedback evaluation set.

The seven evaluation faults were designed after prior PLLGuard development and
are therefore NOT a historically blind or statistically independent benchmark.
Never mix this experiment's results with the published original three-round run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ray
from chia.base.ChiaFunction import get
from chia.models.opencode import OpenCodeLLM
from chia.models.openai_compat import OpenAICompatLLM
from loop import SPEC, extract_json, simulate
from mutants import prepare
from scripts.replay_summary import FROZEN_RTL_SHA256
from scripts.stress_suite import FAULTS
from verify import RTL_FILES, validate


BASELINE = [
    {"kind": "disable", "ref_period_ns": 40, "div": 8, "trim": 0, "observe_ns": 200},
    {"kind": "dco_trim", "ref_period_ns": 40, "div": 8, "trim": 0, "observe_ns": 200},
    {"kind": "divider", "ref_period_ns": 40, "div": 8, "trim": 0, "observe_ns": 800},
]

# Human-guided interface coverage goals. The final goal was added after the
# earlier stress result exposed reset/phase blind spots; do not call new runs
# on those same seven faults historically blind or automatically discovered.
GOALS = (
    "Compare DCO-mode output edge counts for low versus high external trim.",
    "In feedback mode compare output after two distinct divider settings, with settling time.",
    "Exercise clockp[1] with measure phase=1, resetb asserted while enabled, "
    "and recovery when resetb returns to 1; include enable=0 if the action budget allows.",
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluation_sources(rtl: pathlib.Path, target: pathlib.Path) -> dict[str, pathlib.Path]:
    """Create the evaluation variants only AFTER the final proposal is fixed."""
    paths = {}
    for label in ("original", *FAULTS):
        dst = target / label
        dst.mkdir(parents=True)
        for filename in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(rtl / filename, dst / filename)
        if label != "original":
            filename, before, after = FAULTS[label]
            source = dst / filename
            data = source.read_text()
            if data.count(before) != 1:
                raise ValueError(f"ambiguous fault anchor: {label}")
            source.write_text(data.replace(before, after, 1))
        paths[label] = dst
    return paths


def score(candidate: dict[str, Any], sources: dict[str, pathlib.Path],
          target: pathlib.Path) -> dict[str, Any]:
    refs = {name: simulate.chia_remote(str(source), candidate, str(target / name))
            for name, source in sources.items()}
    results = {name: get(ref) for name, ref in refs.items()}
    statuses = {name: row["status"] for name, row in results.items()}
    valid = statuses["original"] == "pass"
    return {"original_pass": valid, "statuses": statuses,
            "detected": [name for name in sources if name != "original" and
                         valid and statuses[name] == "fail"],
            "tool_errors": [name for name, status in statuses.items()
                            if status in ("invalid", "compile_error", "tool_error")]}


def model_agent(args: argparse.Namespace, root: pathlib.Path):
    if args.backend == "gemini":
        from os import environ
        return OpenAICompatLLM(
            model=args.model, timeout_seconds=180, retries=1,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=environ["GEMINI_API_KEY"], max_tokens=8192,
            log_dir=str(root / "agent_logs"))
    work = root / "agent_workspace"
    work.mkdir(exist_ok=True)
    return OpenCodeLLM(model=args.model, timeout_seconds=180, retries=1,
                       log_dir=str(root / "agent_logs"), work_dir=str(work),
                       dangerously_skip_permissions=False, config={"*": "deny"})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--backend", choices=("gemini", "opencode"), default="gemini")
    ap.add_argument("--model", default=None)
    ap.add_argument("--ray-address", default=None)
    ap.add_argument("--proposal-summary", type=pathlib.Path,
                    help="Offline infrastructure check using frozen proposals; NOT a new agent run")
    ap.add_argument("--seed-run", type=pathlib.Path,
                    help="Resume a partial live run in a NEW directory, preserving prior model-authored candidates")
    ap.add_argument("--expected-evaluation", type=pathlib.Path,
                    help="Optional exact status matrix for an offline replay audit")
    args = ap.parse_args()
    if not 1 <= args.rounds <= 3:
        ap.error("rounds must be 1..3 to keep the fixed baseline equal in size")
    if args.expected_evaluation and not args.proposal_summary:
        ap.error("--expected-evaluation applies only to the offline frozen-proposal replay")
    if args.proposal_summary and args.seed_run:
        ap.error("choose either --proposal-summary or --seed-run")
    if not args.proposal_summary and args.backend == "gemini" and not os.getenv("GEMINI_API_KEY"):
        ap.error("GEMINI_API_KEY missing; offline --proposal-summary needs no key")
    rtl, root = args.rtl.resolve(), args.output.resolve()
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty")
    actual = {name: digest(rtl / name) for name in RTL_FILES}
    if actual != FROZEN_RTL_SHA256:
        ap.error("RTL differs from exact pinned GF180 lab source")
    model = args.model or ("gemini-3.6-flash" if args.backend == "gemini"
                           else "opencode/big-pickle")
    offline = args.proposal_summary is not None
    replay = json.loads(args.proposal_summary.read_text()) if offline else None
    if replay is not None:
        missing = [f"agent_{i}" for i in range(args.rounds)
                   if f"agent_{i}" not in replay["tests"]]
        if missing:
            ap.error(f"frozen summary lacks proposals: {missing}")
    seed = args.seed_run.resolve() if args.seed_run else None
    seed_rows: list[dict[str, Any]] = []
    if seed:
        if seed == root:
            ap.error("seed run and output must be different directories")
        seed_summary = json.loads((seed / "summary.json").read_text())
        if (seed_summary.get("rtl_sha256") != actual or
                seed_summary.get("model") != model or
                not seed_summary.get("classification", "").startswith("New CHIA model run")):
            ap.error("seed is not a compatible live model run on this exact RTL")
        rows = seed_summary["tests"]
        seed_rows = [rows[f"agent_{i}"] for i in range(args.rounds)
                     if f"agent_{i}" in rows]
        if (len(seed_rows) != seed_summary["completed_agent_rounds"] or
                any(f"agent_{i}" not in rows for i in range(len(seed_rows))) or
                len(seed_rows) == args.rounds):
            ap.error("seed must contain a contiguous, incomplete agent prefix")
    root.mkdir(parents=True, exist_ok=True)
    dev = prepare(rtl, root / "development_sources")
    ray.init(address=args.ray_address, ignore_reinit_error=True,
             **({"resources": {"openai_creds" if args.backend == "gemini"
                               else "opencode_creds": 1}}
                if args.ray_address is None and not offline else {}))
    agent = None if offline else model_agent(args, root)
    history: list[dict[str, Any]] = []
    tests: dict[str, dict[str, Any]] = {}
    backend_error = None
    for turn in range(args.rounds):
        label = f"agent_{turn}"
        already = sorted({fault for row in history for fault in row.get("detected", [])})
        prompt = (SPEC + "\nDevelopment fault names: " + ", ".join(list(dev)[1:])
                  + "\nHuman-guided coverage goal this round: " + GOALS[turn]
                  + "\nDetected so far: " + json.dumps(already)
                  + "\nCreate a valid test for a property not yet covered if possible."
                  + "\nPrevious development feedback:\n" + json.dumps(history))
        if turn < len(seed_rows):
            # Retain the original prompt and model response as authorship
            # evidence; the new prompt applies only to NEW model calls.
            for name in (f"prompt_{turn}.txt", f"proposal_{turn}.txt"):
                source = seed / name
                if source.is_file():
                    shutil.copy2(source, root / name)
            candidate = validate(seed_rows[turn]["candidate"])
        elif offline:
            (root / f"prompt_{turn}.txt").write_text(prompt)
            candidate = validate(replay["tests"][label]["candidate"])
            (root / f"proposal_{turn}.txt").write_text(json.dumps(candidate) + "\n")
        else:
            (root / f"prompt_{turn}.txt").write_text(prompt)
            try:
                response = get(agent.prompt.chia_remote(agent, prompt))
                raw = str(response.result)
                (root / f"proposal_{turn}.txt").write_text(raw)
                if not response.success:
                    raise ValueError("model returned unsuccessful response")
                candidate = extract_json(raw)
            except Exception as exc:
                backend_error = type(exc).__name__
                history.append({"turn": turn, "error_type": backend_error})
                (root / "history.json").write_text(json.dumps(history, indent=2) + "\n")
                break
        row = score(candidate, dev, root / "development_runs" / label)
        tests[label] = {"candidate": candidate, "development": row}
        history.append({"turn": turn, "candidate": candidate,
                        "original_pass": row["original_pass"],
                        "detected": row["detected"], "statuses": row["statuses"]})
        (root / "history.json").write_text(json.dumps(history, indent=2) + "\n")
        print(f"{label}: valid={row['original_pass']} development={row['detected']}", flush=True)
    # Evaluation faults are absent from prompts and per-round feedback. In a
    # resumed experiment the earlier run's evaluated files can exist elsewhere
    # on disk, but the model has no filesystem tools; record this limitation.
    # Baselines are fixed before this experiment and use the same simulator.
    if backend_error and not any(name.startswith("agent_") for name in tests):
        partial = {"classification": "Backend failed before any agent proposal",
                   "backend_error_type": backend_error, "model": model,
                   "development_history": history,
                   "note": "No new agent result or evaluation score was produced."}
        (root / "summary.json").write_text(json.dumps(partial, indent=2) + "\n")
        print("Backend failed before agent proposal:", backend_error, flush=True)
        raise SystemExit(2)
    for i, baseline in enumerate(BASELINE[:args.rounds]):
        tests[f"baseline_{i}"] = {"candidate": baseline,
            "development": score(baseline, dev, root / "development_runs" / f"baseline_{i}")}
    ev = evaluation_sources(rtl, root / "evaluation_sources")
    for label, row in tests.items():
        row["evaluation"] = score(row["candidate"], ev, root / "evaluation_runs" / label)
    report = {"classification": (
        "Offline replay of frozen published proposals; NOT a new model run" if offline
        else "New CHIA model run with per-round development feedback"),
        "evaluation_caveat": "Seven fault definitions are excluded from prompts in this run, but developers knew their prior outcomes; NOT historically blind.",
        "model": "none (frozen proposals)" if offline else model,
        "backend_error_type": backend_error,
        "requested_rounds": args.rounds, "completed_agent_rounds": sum(
            name.startswith("agent_") for name in tests),
        "seed": ({"source_run": str(seed),
                  "source_summary_sha256": digest(seed / "summary.json"),
                  "model_authored_proposals_reused": len(seed_rows)} if seed else None),
        "rtl_sha256": actual, "development_faults": list(dev)[1:],
        "evaluation_faults": list(ev)[1:], "tests": tests,
        "development_history": history}
    for group in ("baseline_", "agent_"):
        report[group + "evaluation_detected"] = sorted({fault
            for label, row in tests.items() if label.startswith(group)
            for fault in row["evaluation"]["detected"]})
    report["complete_comparable_run"] = (backend_error is None and
        report["completed_agent_rounds"] == args.rounds)
    if offline:
        primary_match = all(row["development"]["statuses"] ==
                            replay["tests"][label]["statuses"]
                            for label, row in tests.items())
        report["offline_primary_status_match"] = primary_match
        print("Offline primary statuses:", "MATCH" if primary_match else "DIFF")
    if args.expected_evaluation:
        expected = json.loads(args.expected_evaluation.read_text())
        eval_match = (expected["rtl_sha256"] == actual and
                      set(expected["tests"]) == set(tests) and
                      all(row["evaluation"]["statuses"] ==
                          expected["tests"][label]["statuses"]
                          for label, row in tests.items()))
        report["evaluation_status_match"] = eval_match
        print("Evaluation status matrix:", "MATCH" if eval_match else "DIFF")
    (root / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["complete_comparable_run"]:
        print("COMPLETE evaluation agent/baseline:", len(report["agent_evaluation_detected"]),
              len(report["baseline_evaluation_detected"]), "out of", len(ev)-1)
    else:
        print("INCOMPLETE RUN:", report["completed_agent_rounds"], "of",
              args.rounds, "agent proposals; backend error:", backend_error,
              "-- evaluation counts are exploratory, not a fair comparison")
    print("Detailed summary:", root / "summary.json")
    if backend_error:
        raise SystemExit(2)
    if offline and not report["offline_primary_status_match"]:
        raise SystemExit(1)
    if args.expected_evaluation and not report["evaluation_status_match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
