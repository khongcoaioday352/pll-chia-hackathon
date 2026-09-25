"""Read-only lab preflight for a credible future gate-level replay.

This never runs EDA tools, copies private PDK/netlist/SDF assets, or asserts
that any PLL has locked. Saved result contains only presence, size, hashes,
and an audit of the public historical testbench's lock oracle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil


def file_status(path: pathlib.Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        return {"present": False}
    return {"present": True, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lab", type=pathlib.Path,
                    default=pathlib.Path("~/stdcell-pll").expanduser())
    ap.add_argument("--reference-tb", type=pathlib.Path,
                    default=pathlib.Path("reference_tb/tb_digital_pll.v"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output already exists; keep audits immutable")
    lab = args.lab.expanduser()
    base = lab / "openroad" / "results" / "gf180" / "pll"
    paths = {"routed_netlist": base / "base" / "6_final.v",
             "routed_spef": base / "base" / "6_final.spef"}
    paths.update({f"{corner}_sdf": base / corner / "digital_pll.sdf"
                  for corner in ("BC", "TC", "WC")})
    files = {label: file_status(path) for label, path in paths.items()}
    tb_bytes = args.reference_tb.read_bytes()
    tb = tb_bytes.decode("utf-8")
    # The historical gate-level branch waits for input edges and sets locked
    # true without inspecting the output. It is deliberately not used to
    # certify lock, even if it prints "PASS" elsewhere in this testbench.
    gate_branch = re.search(r"`else\s+repeat\s*\(\s*50\s*\)\s*@\(posedge\s+osc\)\s*;\s*locked\s*=\s*1\s*;\s*`endif", tb)
    no_force = re.search(r"(?m)^\s*(?:force|release)\s+", tb) is None
    questa = shutil.which("vsim")
    fallback = pathlib.Path("/home/tools/mentor/questasim/2024.2/questasim/bin/vsim")
    binary_present = bool(questa or (fallback.is_file() and fallback.stat().st_mode & 0o111))
    result = {"classification": "read-only asset and oracle preflight; not a simulation result",
              "assets": files,
              "questa_binary_present": binary_present,
              "questa_license_tested": False,
              "reference_tb_sha256": hashlib.sha256(tb_bytes).hexdigest(),
              "historical_gate_lock_assumed_after_50_input_edges": bool(gate_branch),
              "reference_tb_has_procedural_force_or_release": not no_force,
              "physical_lock_verified": False,
              "gating_issue": ("reference gate branch assigns locked=1 without observing DUT output"
                               if gate_branch else "inspect full bench before claiming lock"),
              "limitations": ["presence and hash do not establish correct SDF annotation",
                              "license, cell model compatibility, and gate-level simulation not tested",
                              "do not upload PDK, routed netlist, SPEF or SDF to public GitHub"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for label, status in files.items():
        print(f"{label}: {'PRESENT' if status['present'] else 'MISSING'}")
    print("Questa binary:", "PRESENT" if binary_present else "MISSING")
    print("Historical gate-level lock oracle:", "ASSUMED, NOT MEASURED" if gate_branch else "REVIEW REQUIRED")
    print("Procedural force/release in reference TB:", "FOUND" if not no_force else "NONE")
    print("No gate-level lock result asserted | private audit:", args.output)


if __name__ == "__main__":
    main()
