"""Bounded OpenCode diagnostic cycle in an isolated, uncommitted git worktree.

The model can propose and edit code. Independent local scripts judge its edits.
No result is pushed or published; provider availability is not guaranteed.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time


ALLOWED_EDITS = {"scripts/audit_saved_gate.py", "scripts/gate_output_probe.py",
                 "scripts/gate_batch.py"}

# Inline OpenCode permissions keep the remote model on public project source.
# The launcher, rather than the model, reads private simulator logs and runs EDA.
PERMISSIONS = {"permission": {"*": "allow", "bash": "deny", "task": "deny",
                              "external_directory": "deny", "webfetch": "deny",
                              "websearch": "deny",
                              "edit": {"*": "deny", **{path: "allow" for path in ALLOWED_EDITS}}}}


def execute(args: list[str], cwd: pathlib.Path, log: pathlib.Path, *,
            env: dict[str, str] | None = None, limit: int = 900) -> int:
    with log.open("w") as stream:
        try:
            return subprocess.run(args, cwd=cwd, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=limit, check=False).returncode
        except subprocess.TimeoutExpired:
            stream.write("\nPROCESS WALL-TIME LIMIT REACHED\n")
            return 124


def changed_paths(worktree: pathlib.Path) -> set[str]:
    raw = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                                  cwd=worktree, text=True)
    return {line[3:] for line in raw.splitlines() if line}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--saved-tc", type=pathlib.Path,
                    default=pathlib.Path("results/gate_output_tc_v1"))
    ap.add_argument("--lab", type=pathlib.Path,
                    default=pathlib.Path("~/stdcell-pll").expanduser())
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--model", default="opencode/big-pickle")
    ap.add_argument("--attempts", type=int, default=2)
    args = ap.parse_args()
    if not 1 <= args.attempts <= 3:
        ap.error("attempts must be 1..3 to bound provider usage")
    source = args.saved_tc.resolve()
    if not all((source / name).is_file() for name in ("summary.json", "vsim.log", "tb.v")):
        ap.error("saved TC run must contain summary.json, vsim.log and tb.v")
    base = pathlib.Path(__file__).resolve().parents[1]
    top = pathlib.Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=base, text=True).strip())
    if top != base:
        ap.error("run the launcher from the checked-out PLLGuard repository")
    out = args.output.resolve()
    if out.exists():
        ap.error("choose a fresh --output path")
    out.mkdir(parents=True)
    workspace = pathlib.Path.home() / f"pllguard-ai-{int(time.time())}"
    if workspace.exists():
        ap.error("isolated worktree path already exists")
    setup = execute(["git", "worktree", "add", "--detach", str(workspace), "HEAD"],
                    base, out / "worktree_setup.log", limit=60)
    if setup:
        raise SystemExit(f"Could not create isolated worktree; see {out / 'worktree_setup.log'}")
    opencode = pathlib.Path.home() / ".opencode/bin/opencode"
    if not opencode.is_file():
        resolved = shutil.which("opencode")
        if not resolved:
            raise SystemExit("OpenCode binary missing; worktree preserved for review")
        opencode = pathlib.Path(resolved)
    env = os.environ.copy()
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(PERMISSIONS)
    original_audit = out / "initial_audit.json"
    execute([sys.executable, "scripts/audit_saved_gate.py", "--run", str(source),
             "--output", str(original_audit)], workspace,
            out / "initial_audit.log", limit=45)
    original_flags = json.loads(original_audit.read_text()) if original_audit.exists() else {}
    report: dict = {"worktree": str(workspace), "model": args.model,
                    "saved_tc": str(source), "attempts": [], "published": False,
                    "original_sdf_error_pattern_found": original_flags.get("sdf_error_pattern_found"),
                    "lock_verified": False, "status": "incomplete"}
    for index in range(args.attempts):
        # Provide only the small diagnostic booleans and output measurements;
        # OpenCode cannot read private lab logs or run arbitrary shell commands.
        prior = out / (f"audit_{index - 1}.json" if index else "initial_audit.json")
        if not prior.exists():
            execute([sys.executable, "scripts/audit_saved_gate.py", "--run", str(source),
                     "--output", str(prior)], workspace,
                    out / (f"audit_{index - 1}.log" if index else "initial_audit.log"), limit=45)
        feedback = json.loads(prior.read_text()) if prior.exists() else {}
        hints = {k: feedback.get(k) for k in ("measurements", "measurements_complete",
                                              "program_pass_marker", "program_fail_marker",
                                              "sdf_error_pattern_found")}
        previous_gate = out / f"BC_WC_{index - 1}" / "summary.json"
        if index and previous_gate.is_file():
            gate_feedback = json.loads(previous_gate.read_text())
            hints["corner_diagnostics"] = {corner: {key: row.get(key) for key in
                                            ("process_returncode", "functional_assertions_passed",
                                             "measurements", "sdf_error_pattern_found")}
                                           for corner, row in gate_feedback["runs"].items()}
        message = ("Follow AGENT_GATE_TASK.md. This is the independent, redacted "
                   f"TC audit (no raw logs): {json.dumps(hints, sort_keys=True)}. "
                   "Modify only allowed parser/runner scripts; return a short report. "
                   f"Iteration {index + 1} of {args.attempts}.")
        command = [str(opencode), "run", "--auto", "--model", args.model,
                   "--file", "AGENT_GATE_TASK.md"]
        if index:
            command.append("--continue")
        command.append(message)
        print(f"AI iteration {index + 1}/{args.attempts}", flush=True)
        model_rc = execute(command, workspace, out / f"model_{index}.log", env=env)
        altered = changed_paths(workspace)
        item: dict = {"iteration": index + 1, "provider_returncode": model_rc,
                      "modified_files": sorted(altered)}
        report["attempts"].append(item)
        if model_rc or not altered <= ALLOWED_EDITS:
            report["status"] = "provider_failed_or_out_of_scope_edits"
            print("STOP: provider failure or unauthorized file changes; review private model log", flush=True)
            break
        audit = out / f"audit_{index}.json"
        audit_rc = execute([sys.executable, "scripts/audit_saved_gate.py",
                            "--run", str(source), "--output", str(audit)],
                           workspace, out / f"audit_{index}.log", limit=45)
        item["saved_tc_audit_returncode"] = audit_rc
        if audit_rc == 0:
            gate_dir = out / f"BC_WC_{index}"
            gate_rc = execute([sys.executable, "scripts/gate_batch.py", "--lab",
                               str(args.lab.expanduser().resolve()), "--corners", "BC,WC",
                               "--output", str(gate_dir)], workspace,
                              out / f"gate_{index}.log", limit=900)
            item["bc_wc_diagnostic_returncode"] = gate_rc
            if gate_rc == 0:
                if original_flags.get("sdf_error_pattern_found"):
                    report["status"] = "requires_sdf_error_review"
                    print("TC and BC/WC output diagnostics collected; original SDF error marker still requires review", flush=True)
                else:
                    report["status"] = "functional_diagnostics_complete_review_sdf_logs"
                    print("TC audit and BC/WC functional diagnostics completed; review SDF logs", flush=True)
                break
        if not altered or index + 1 == args.attempts:
            report["status"] = "needs_manual_diagnosis"
            print("STOP: no validated repair within bounded attempts", flush=True)
            break
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Private summary:", out / "summary.json", flush=True)
    print("Review-only worktree:", workspace, flush=True)
    if report["status"] != "functional_diagnostics_complete_review_sdf_logs":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
