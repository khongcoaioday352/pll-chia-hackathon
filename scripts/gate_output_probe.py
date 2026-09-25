"""Private Questa post-route probe using observable PLL outputs and corner SDF.

This is a diagnostic, not a claim of lock, PVT coverage or silicon behavior.
Never publish its simulator log, netlist, PDK files or SDF without permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from verify import make_tb, validate
from scripts.replay_summary import FROZEN_RTL_SHA256


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_tool(name: str, questa_home: pathlib.Path) -> pathlib.Path:
    path = questa_home / "bin" / name
    if path.is_file():
        return path
    located = shutil.which(name)
    if located:
        return pathlib.Path(located)
    raise ValueError(f"{name} unavailable; specify --questa-home")


def call(argv: list[str], cwd: pathlib.Path, log: pathlib.Path, seconds: int) -> tuple[int | None, bool]:
    try:
        done = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=seconds, check=False)
        output, rc, timed_out = done.stdout, done.returncode, False
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        rc, timed_out = None, True
    log.write_text(output, errors="replace")
    return rc, timed_out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lab", type=pathlib.Path,
                    default=pathlib.Path("~/stdcell-pll").expanduser())
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--candidate", type=pathlib.Path,
                    default=pathlib.Path("examples/agent_program.json"))
    ap.add_argument("--corner", choices=("BC", "TC", "WC"), default="TC")
    ap.add_argument("--questa-home", type=pathlib.Path,
                    default=pathlib.Path("/home/tools/mentor/questasim/2024.2/questasim"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--timeout-seconds", type=int, default=180)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output directory must be new; preserve previous evidence")
    if args.timeout_seconds < 1:
        ap.error("timeout-seconds must be positive; this is a process safety limit")
    rtl_hash = {name: digest(args.rtl / name) for name in FROZEN_RTL_SHA256}
    if rtl_hash != FROZEN_RTL_SHA256:
        ap.error("functional RTL differs from the frozen published snapshot")
    candidate = validate(json.loads(args.candidate.read_text()))
    bench = make_tb(candidate)
    if re.search(r"\b(?:force|release|deposit)\b|\bdut\s*\.", bench):
        ap.error("testbench contains a forbidden internal DUT operation/reference")
    lab = args.lab.expanduser().resolve()
    root = lab / "openroad" / "results" / "gf180" / "pll"
    sources = [lab / "src/rtl/gf180/mcu7t5v0/primitives.v",
               lab / "src/rtl/gf180/mcu7t5v0/gf180mcu_fd_sc_mcu7t5v0.v",
               root / "base/6_final.v"]
    sdf = root / args.corner / "digital_pll.sdf"
    for source in [*sources, sdf]:
        if not source.is_file() or not source.stat().st_size:
            ap.error(f"required private lab asset missing or empty: {source}")
    tools = {name: find_tool(name, args.questa_home.expanduser())
             for name in ("vlib", "vlog", "vsim")}
    args.output.mkdir(parents=True)
    tb = args.output / "tb.v"
    tb.write_text(bench)
    steps: list[dict] = []
    for name, command in [
        ("vlib", [str(tools["vlib"]), "work"]),
        *((f"vlog_{i}", [str(tools["vlog"]), "-work", "work", "-timescale=1ns/1ps",
                         str(source.resolve())]) for i, source in enumerate([*sources, tb])),
        ("vsim", [str(tools["vsim"]), "-c", "-t", "1ps", "-voptargs=+acc",
                  "-sdftyp", f"/tb/dut={sdf.resolve()}", "-do", "run -all; quit -f", "tb"]),
    ]:
        log = args.output / f"{name}.log"
        rc, timed_out = call(command, args.output, log, args.timeout_seconds)
        steps.append({"step": name, "returncode": rc, "timed_out": timed_out,
                      "log_file": log.name})
        print(f"{args.corner} {name}: {'TIMEOUT' if timed_out else 'exit ' + str(rc)}")
        if rc != 0 or timed_out:
            break
    simulated = steps[-1]["step"] == "vsim" and steps[-1]["returncode"] == 0
    log_text = (args.output / "vsim.log").read_text(errors="replace") if simulated else ""
    measurements = {k: int(v) for k, v in re.findall(r"(?m)^MEASURE (\w+)=(\d+)", log_text)}
    passed = "RESULT PASS PROGRAM" in log_text and "RESULT FAIL" not in log_text
    # SDF reports can contain benign lines such as "SDF errors: 0"; only
    # flag a concrete simulator error or a failed/missing annotation here.
    sdf_issue = bool(re.search(
        r"(?im)^\s*(?:\*\*\s*(?:error|fatal)\b|error:)|"
        r"(?i:sdf[^\n]*(?:failed to annotate|not found)|failed to annotate[^\n]*sdf)",
        log_text,
    ))
    result = {"classification": "private routed-netlist Questa output probe",
              "corner": args.corner, "sdf_selection": "-sdftyp with corner-specific SDF",
              "source_sha256": {p.name: digest(p) for p in [*sources, sdf]},
              "functional_rtl_sha256": rtl_hash, "candidate_sha256": digest(args.candidate),
              "bench_sha256": digest(tb), "steps": steps, "measurements": measurements,
              "functional_assertions_passed_in_gate_run": bool(simulated and passed and not sdf_issue),
              "sdf_error_pattern_found": sdf_issue,
              "lock_verified": False, "sdf_annotation_completeness_verified": False,
              "limitations": ["inspect local vsim.log for annotation coverage and timing warnings",
                              "functional assertion pass does not establish lock or PVT robustness",
                              "this check does not prove netlist provenance or match to pinned RTL"]}
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Output measurements:", measurements)
    print("Functional assertions:", "PASS" if result["functional_assertions_passed_in_gate_run"] else "NOT VERIFIED")
    print("Private logs and summary:", args.output)


if __name__ == "__main__":
    main()
