"""CHIA-orchestrated agent-authored PLL stimulus and assertion programs."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
from typing import Any

import ray
from chia.base.ChiaFunction import ChiaFunction, get
from chia.models.opencode import OpenCodeLLM
from chia.models.openai_compat import OpenAICompatLLM

from mutants import prepare
from verify import RTL_FILES, run, validate


@ChiaFunction()
def simulate(rtl: str, candidate: dict[str, Any], output: str) -> dict[str, Any]:
    """Run the deterministic external simulator and save its complete log."""
    return run(pathlib.Path(rtl), candidate, pathlib.Path(output))


SPEC = """You design black-box verification tests for a digital PLL.
Ports: resetb (active-low reset), enable, osc (reference clock), div[4:0],
dco (DCO mode), ext_trim[25:0], clockp[1:0]. In DCO mode ext_trim selects
ring oscillator delay; in feedback mode the controller adjusts trim to aim
for div output cycles per reference cycle. Author one NEW test as JSON with
exactly {"ref_period_ns":40,"steps":[...]} and ref_period_ns 20..100.
Actions, in order: {"op":"set","resetb":1,"enable":1,"dco":1,
"div":8,"trim":0} may set any subset of those ports; resetb/enable/dco
0..1, div 2..30, trim 0..67108863. {"op":"wait","ns":20} waits.
{"op":"measure","name":"fast","ns":200} counts rising output edges
in a fresh window and records the count. {"op":"assert","left":"fast",
"operator":"gt","right":0} checks a previous measurement against another
previous measurement name or a nonnegative integer. Operators: eq, ne, gt,
ge, lt, le.
To reject edge-window noise, use operator gt_by with margin 5 to mean
left > right + 5; lt_by means left < right - margin. For these two, the
assert object must also have integer "margin" in 1..100.
At least one set, measure, and assert; 3..16 actions; each
duration 2..2000 ns and total duration <=6000 ns. Simulation starts with
resetb=enable=dco=0, div=8, trim=0 and waits 20 ns before your first action.
You must deassert resetb and enable before testing output edges. Example:
{"ref_period_ns":40,"steps":[{"op":"set","resetb":1,"enable":1,
"dco":1},{"op":"measure","name":"active","ns":200},
{"op":"assert","left":"active","operator":"gt","right":0}]}
Use a distinct behavior from earlier original-design observations. The
assertions must be sound on the original RTL. Reply with ONE JSON object only.
"""


def extract_json(message: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", message):
        try:
            value, _ = decoder.raw_decode(message[match.start():])
            if isinstance(value, dict):
                return validate(value)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    raise ValueError("agent response did not contain a valid test program")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--backend", choices=("opencode", "gemini"), default="opencode")
    ap.add_argument("--model", default=None)
    ap.add_argument("--ray-address", default=None)
    args = ap.parse_args()
    if not 1 <= args.rounds <= 12:
        ap.error("rounds must be 1..12")
    if args.backend == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        ap.error("export GEMINI_API_KEY in this shell before running Gemini")
    model = args.model or ("gemini-2.5-flash" if args.backend == "gemini"
                           else "opencode/big-pickle")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Keep the hidden mutations absent from disk until all agent proposals
    # are finalized. This prevents accidental or deliberate benchmark leakage.
    original_dir = root / "sources" / "original"
    original_dir.mkdir(parents=True, exist_ok=True)
    for name in (*RTL_FILES, "clockbuf_shim.v"):
        shutil.copy2(args.rtl.resolve() / name, original_dir / name)
    # Same-host local Ray is enough for this small design; CHIA functions
    # schedule onto the Ray runtime and preserve profiling instrumentation.
    ray.init(address=args.ray_address, ignore_reinit_error=True,
             **({"resources": {"openai_creds" if args.backend == "gemini"
                               else "opencode_creds": 1}}
                if args.ray_address is None else {}))
    agent_dir = root / "agent_workspace"
    agent_dir.mkdir(exist_ok=True)
    if args.backend == "gemini":
        agent = OpenAICompatLLM(
            model=model, timeout_seconds=180, retries=1,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.environ["GEMINI_API_KEY"], max_tokens=2048,
            log_dir=str(root / "agent_logs"),
        )
    else:
        agent = OpenCodeLLM(model=model, timeout_seconds=180,
                            retries=1, log_dir=str(root / "agent_logs"),
                            work_dir=str(agent_dir),
                            dangerously_skip_permissions=False,
                            config={"*": "deny"})
    # Fixed, predeclared baseline uses the same number of simulator tests
    # as the agent's proposal budget (up to three).
    baseline = [
        {"kind": "disable", "ref_period_ns": 40, "div": 8,
         "trim": 0, "observe_ns": 200},
        {"kind": "dco_trim", "ref_period_ns": 40, "div": 8,
         "trim": 0, "observe_ns": 200},
        {"kind": "divider", "ref_period_ns": 40, "div": 8,
         "trim": 0, "observe_ns": 800},
    ][:args.rounds]
    history: list[dict[str, Any]] = []
    candidates = [(f"baseline_{i}", item) for i, item in enumerate(baseline)]
    for turn in range(args.rounds):
        prompt = SPEC + "\nPrevious original-design observations:\n" + json.dumps(history)
        (root / f"prompt_{turn}.txt").write_text(prompt)
        response = get(agent.prompt.chia_remote(agent, prompt))
        raw = str(response.result)
        (root / f"proposal_{turn}.txt").write_text(raw)
        if not response.success:
            history.append({"turn": turn, "error": "AI backend failed", "raw": raw})
            continue
        try:
            candidate = extract_json(raw)
        except (ValueError, TypeError) as exc:
            history.append({"turn": turn, "error": str(exc), "raw": raw})
            continue
        label = f"agent_{turn}"
        original = get(simulate.chia_remote(str(original_dir), candidate,
                                            str(root / "runs" / label / "original")))
        history.append({"turn": turn, "candidate": candidate,
                        "original_status": original["status"],
                        "original_log": original["log"][-500:]})
        candidates.append((label, candidate))
        (root / "history.json").write_text(json.dumps(history, indent=2) + "\n")

    # Evaluation is held out until proposals have been fixed. Both baseline
    # and agent tests get the same mutants and individual run budgets.
    sources = prepare(args.rtl.resolve(), root / "sources")
    summary: dict[str, Any] = {"model": model, "backend": args.backend,
                               "rounds": args.rounds,
                               "mutants": list(sources)[1:], "tests": {}}
    for label, candidate in candidates:
        refs = {name: simulate.chia_remote(str(path), candidate,
                str(root / "runs" / label / name)) for name, path in sources.items()}
        results = {name: get(ref) for name, ref in refs.items()}
        valid = results["original"]["status"] == "pass"
        detected = [name for name in list(sources)[1:] if valid and
                    results[name]["status"] == "fail"]
        summary["tests"][label] = {"candidate": candidate,
            "original_pass": valid, "detected": detected,
            "statuses": {n: r["status"] for n, r in results.items()}}
        (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    summary["baseline_detected"] = sorted({name
        for label, result in summary["tests"].items() if label.startswith("baseline_")
        for name in result["detected"]})
    summary["agent_detected_union"] = sorted({name
        for label, result in summary["tests"].items() if label.startswith("agent_")
        for name in result["detected"]})
    summary["invalid_agent_proposals"] = [row for row in history if "error" in row]
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
