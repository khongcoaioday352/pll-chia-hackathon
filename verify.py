"""Deterministic PLL test compiler and black-box simulator adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import time
from typing import Any

RTL_FILES = ("digital_pll.v", "digital_pll_controller.v", "ring_osc2x13.v")
VALID_KINDS = ("disable", "dco_trim", "divider")
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,23}\Z")


def validate(candidate: dict[str, Any]) -> dict[str, Any]:
    if "steps" in candidate:
        return validate_program(candidate)
    kind = candidate.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}")
    ref = int(candidate.get("ref_period_ns", 40))
    div = int(candidate.get("div", 8))
    trim = int(candidate.get("trim", 0))
    observe = int(candidate.get("observe_ns", 100))
    if not 20 <= ref <= 100 or not 2 <= div <= 30:
        raise ValueError("ref_period_ns 20..100; div 2..30")
    if not 0 <= trim < (1 << 26) or not 50 <= observe <= 1000:
        raise ValueError("trim 0..2^26-1; observe_ns 50..1000")
    if kind == "divider" and observe < 500:
        raise ValueError("divider requires observe_ns >=500 for edge-count precision")
    return {"kind": kind, "ref_period_ns": ref, "div": div,
            "trim": trim, "observe_ns": observe}


def bounded_int(value: Any, lo: int, hi: int, label: str) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{label} must be an integer in {lo}..{hi}")
    return value


def validate_program(candidate: dict[str, Any]) -> dict[str, Any]:
    if set(candidate) != {"ref_period_ns", "steps"}:
        raise ValueError("program needs exactly ref_period_ns and steps")
    ref = bounded_int(candidate["ref_period_ns"], 20, 100, "ref_period_ns")
    steps = candidate["steps"]
    if not isinstance(steps, list) or not 3 <= len(steps) <= 16:
        raise ValueError("steps must contain 3..16 actions")
    names: set[str] = set()
    has_set = has_assert = False
    total_ns = 20
    validated = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("every step must be an object")
        op = step.get("op")
        if op == "set":
            if not set(step) <= {"op", "resetb", "enable", "dco", "div", "trim"} or len(step) < 2:
                raise ValueError("invalid set fields")
            clean = {"op": op}
            for key, value in step.items():
                if key == "op":
                    continue
                lo, hi = (2, 30) if key == "div" else (0, (1 << 26)-1) if key == "trim" else (0, 1)
                clean[key] = bounded_int(value, lo, hi, key)
            has_set = True
        elif op in ("wait", "measure"):
            required = {"op", "ns"} if op == "wait" else {"op", "ns", "name"}
            if set(step) != required:
                raise ValueError(f"{op} fields must be {sorted(required)}")
            ns = bounded_int(step["ns"], 2, 2000, "ns")
            total_ns += ns
            clean = {"op": op, "ns": ns}
            if op == "measure":
                name = step["name"]
                if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
                    raise ValueError("measure name must be unique and alphanumeric")
                names.add(name)
                clean["name"] = name
        elif op == "assert":
            delta = step.get("operator") in ("gt_by", "lt_by")
            expected = {"op", "left", "operator", "right", "margin"} if delta else {"op", "left", "operator", "right"}
            if set(step) != expected:
                raise ValueError(f"assert needs exactly {sorted(expected)}")
            if step["operator"] not in ("eq", "gt", "lt", "ge", "le", "ne", "gt_by", "lt_by"):
                raise ValueError("unsupported assertion operator")
            if delta:
                bounded_int(step["margin"], 1, 100, "margin")
            left, right = step["left"], step["right"]
            if not isinstance(left, str) or left not in names:
                raise ValueError("left must name a previous measurement")
            if isinstance(right, str):
                if right not in names:
                    raise ValueError("right must name a previous measurement")
            else:
                bounded_int(right, 0, 2000, "right")
            clean = dict(step)
            has_assert = True
        else:
            raise ValueError(f"unsupported action: {op}")
        validated.append(clean)
    if not (has_set and names and has_assert) or total_ns > 6000:
        raise ValueError("need set, measure and assert; total run <=6000 ns")
    return {"ref_period_ns": ref, "steps": validated}


def make_program_tb(p: dict[str, Any]) -> str:
    names = [s["name"] for s in p["steps"] if s["op"] == "measure"]
    decl = "\n".join(f"  integer m_{name}=0;" for name in names)
    lines = []
    operators = {"eq": "==", "gt": ">", "lt": "<", "ge": ">=", "le": "<=", "ne": "!=", "gt_by": ">", "lt_by": "<"}
    for index, step in enumerate(p["steps"]):
        op = step["op"]
        if op == "set":
            for key, value in step.items():
                if key != "op":
                    target = "ext_trim" if key == "trim" else key
                    lines.append(f"    {target} = {value};")
        elif op == "wait":
            lines.append(f"    #{step['ns']};")
        elif op == "measure":
            lines += ["    edges = 0;", f"    #{step['ns']};",
                      f"    m_{step['name']} = edges;",
                      f"    $display(\"MEASURE {step['name']}=%0d\",m_{step['name']});"]
        else:
            right = f"m_{step['right']}" if isinstance(step["right"], str) else str(step["right"])
            if step["operator"] == "gt_by":
                right = f"({right} + {step['margin']})"
            elif step["operator"] == "lt_by":
                right = f"({right} - {step['margin']})"
            lines.append(f"    if (!(m_{step['left']} {operators[step['operator']]} {right}))")
            lines.append(f"      $fatal(1, \"RESULT FAIL ASSERT_{index}\");")
    body = "\n".join(lines)
    return f"""`timescale 1ns/1ps
module tb;
  reg resetb=0, enable=0, osc=0, dco=0;
  reg [4:0] div=5'd8;
  reg [25:0] ext_trim=0;
  wire [1:0] clockp;
  integer edges=0;
{decl}
  digital_pll dut(.resetb(resetb),.enable(enable),.osc(osc),
    .clockp(clockp),.div(div),.dco(dco),.ext_trim(ext_trim));
  always #{p['ref_period_ns']/2:g} osc = ~osc;
  always @(posedge clockp[0]) edges = edges + 1;
  initial begin
    #20;
{body}
    $display("RESULT PASS PROGRAM"); $finish;
  end
  initial begin #10000; $display("RESULT FAIL WATCHDOG"); $finish; end
endmodule
"""


def make_tb(p: dict[str, Any]) -> str:
    if "steps" in p:
        return make_program_tb(p)
    # Measure edge counts in bounded windows. Disable and DCO checks are
    # invariant to exact analog oscillator delay; divider check is approximate.
    common = f"""`timescale 1ns/1ps
module tb;
  reg resetb=0, enable=0, osc=0, dco=0;
  reg [4:0] div=5'd{p['div']};
  reg [25:0] ext_trim=26'd{p['trim']};
  wire [1:0] clockp;
  integer edges=0, base_edges=0, slow_edges=0;
  digital_pll dut(.resetb(resetb),.enable(enable),.osc(osc),
    .clockp(clockp),.div(div),.dco(dco),.ext_trim(ext_trim));
  always #{p['ref_period_ns']/2:g} osc = ~osc;
  always @(posedge clockp[0]) edges = edges + 1;
  initial begin
    #20; resetb=1; enable=1;
"""
    if p["kind"] == "disable":
        body = f"""    dco=1; #{p['observe_ns']};
    if (edges < 2) $display("RESULT FAIL NO_START edges=%0d",edges);
    else begin
      enable=0; edges=0; #10; edges=0;
      #{p['observe_ns']};
      if (edges == 0) $display("RESULT PASS DISABLE");
      else $display("RESULT FAIL DISABLE edges=%0d",edges);
    end
"""
    elif p["kind"] == "dco_trim":
        body = f"""    dco=1; ext_trim=0; #20; edges=0;
    #{p['observe_ns']}; base_edges=edges;
    ext_trim=26'h3ffffff; #20; edges=0;
    #{p['observe_ns']}; slow_edges=edges;
    if (base_edges > slow_edges && slow_edges > 0)
      $display("RESULT PASS DCO_TRIM fast=%0d slow=%0d",base_edges,slow_edges);
    else $display("RESULT FAIL DCO_TRIM fast=%0d slow=%0d",base_edges,slow_edges);
"""
    else:
        body = f"""    dco=0; #{max(p['observe_ns']*5, 1000)}; edges=0;
    #{p['observe_ns']}; base_edges=edges;
    // The target is div / ref_period_ns; allow 8 percent tolerance.
    if (base_edges*{p['ref_period_ns']} >= {p['div']}*{p['observe_ns']*0.92:g}
        && base_edges*{p['ref_period_ns']} <= {p['div']}*{p['observe_ns']*1.08:g})
      $display("RESULT PASS DIVIDER edges=%0d",base_edges);
    else $display("RESULT FAIL DIVIDER edges=%0d",base_edges);
"""
    return common + body + "    $finish;\n  end\n  initial begin #200000; $display(\"RESULT FAIL WATCHDOG\"); $finish; end\nendmodule\n"


def run(rtl: pathlib.Path, candidate: dict[str, Any], output: pathlib.Path) -> dict[str, Any]:
    p = validate(candidate)
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidate.json").write_text(json.dumps(p, indent=2) + "\n")
    (output / "tb.v").write_text(make_tb(p))
    sources = [str(output / "tb.v"), str(rtl / "clockbuf_shim.v")]
    sources += [str(rtl / name) for name in RTL_FILES]
    if shutil.which("iverilog") and shutil.which("vvp"):
        cmd = ["iverilog", "-g2012", "-DSIM", "-DFUNCTIONAL", "-s", "tb",
               "-o", str(output / "sim.vvp"), "-I", str(rtl), *sources]
        sim_cmd = ["vvp", str(output / "sim.vvp")]
    elif shutil.which("verilator"):
        cmd = ["verilator", "--binary", "--timing", "-Wno-fatal",
               "-CFLAGS", "-std=c++20",
               "-j", "2", "--top-module", "tb", "-DSIM", "-DFUNCTIONAL",
               "--Mdir", str(output / "obj_dir"), "-o", "sim", *sources]
        sim_cmd = [str(output / "obj_dir" / "sim")]
    else:
        raise RuntimeError("Install Icarus Verilog or Verilator before evaluation")
    started = time.monotonic()
    try:
        build = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output / "compile.log").write_text(build.stdout + build.stderr)
        if build.returncode:
            status, log = "compile_error", build.stderr
        else:
            sim = subprocess.run(sim_cmd,
                                 capture_output=True, text=True, timeout=30)
            log = sim.stdout + sim.stderr
            status = ("pass" if "RESULT PASS " in log and sim.returncode == 0
                      else "fail" if "RESULT FAIL " in log else "invalid")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        status, log = "tool_error", str(exc)
    (output / "sim.log").write_text(log)
    result = {"status": status, "seconds": round(time.monotonic()-started, 3),
              "candidate": p, "log": log[-2000:],
              "rtl_sha256": {n: hashlib.sha256((rtl/n).read_bytes()).hexdigest()
                             for n in RTL_FILES}}
    (output / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", type=pathlib.Path, required=True)
    ap.add_argument("--candidate", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    print(json.dumps(run(args.rtl, json.loads(args.candidate.read_text()), args.output), indent=2))
