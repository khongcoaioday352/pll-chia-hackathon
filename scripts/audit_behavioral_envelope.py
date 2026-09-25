"""Derive the functional oscillator frequency envelope without simulation.

This checks the exact pinned RTL implementation and reports whether a target
divider/reference rate lies inside the modeled ring oscillator range. Being
inside is necessary, not sufficient, for frequency lock. This does not model
SPICE, PVT corners, jitter, settling, or controller convergence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.replay_summary import FROZEN_RTL_SHA256
from verify import RTL_FILES


def extract_parameter(source: str, name: str) -> float:
    found = re.findall(r"\bparameter\s+real\s+" + re.escape(name) +
                       r"\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;", source)
    if len(found) != 1:
        raise ValueError(f"cannot uniquely derive {name} from pinned RTL")
    return float(found[0])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rtl", type=pathlib.Path, default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("output must not already exist")
    rtl = args.rtl
    hashes = {name: hashlib.sha256((rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if hashes != FROZEN_RTL_SHA256:
        ap.error("RTL differs from pinned source; inspect model before applying derivation")
    top = (rtl / "digital_pll.v").read_text()
    ring = (rtl / "ring_osc2x13.v").read_text()
    if not all(fragment in ring for fragment in (
            "always #delay", "delay = delay_base + delay_per_bit * $itor(bcount)",
            "for (i = 0; i < 26; i = i + 1)",
            "clockp[0] <= (clockp[0] === 1'b0)")):
        ap.error("functional oscillator structure changed; rederive frequency formula")
    if not all(fragment in top for fragment in (
            ".delay_base(osc_delay_base)", ".delay_per_bit(osc_delay_per_bit)")):
        ap.error("top-level delay parameter wiring changed")
    base = extract_parameter(top, "osc_delay_base")
    per_bit = extract_parameter(top, "osc_delay_per_bit")
    if base <= 0 or per_bit < 0:
        ap.error("nonpositive or negative delay parameter")
    trim_bits = 26
    # hiclock toggles every delay, posedges every 2*delay; clockp[0]
    # toggles on those posedges, so its full period is 4*delay.
    min_mhz = 1000 / (4 * (base + per_bit * trim_bits))
    max_mhz = 1000 / (4 * base)
    cases = []
    for period in (30, 40, 50):
        for div in (6, 8, 12, 16):
            target = 1000 * div / period
            classification = ("below modeled minimum" if target < min_mhz
                              else "above modeled maximum" if target > max_mhz
                              else "within modeled range")
            cases.append({"reference_period_ns": period, "div": div,
                          "target_mhz": round(target, 6),
                          "classification": classification})
    result = {
        "claim_scope": "static functional-model frequency feasibility only; not proof of PLL lock",
        "rtl_sha256": hashes,
        "derivation": "f_clockp0_MHz = 1000 / (4 * (osc_delay_base_ns + popcount(trim[25:0]) * osc_delay_per_bit_ns))",
        "base_delay_ns": base, "delay_per_trim_bit_ns": per_bit,
        "trim_bit_count": trim_bits,
        "modeled_min_mhz": round(min_mhz, 6),
        "modeled_max_mhz": round(max_mhz, 6),
        "predicted_edges_per_400ns_at_min": round(0.4 * min_mhz, 6),
        "predicted_edges_per_400ns_at_max": round(0.4 * max_mhz, 6),
        "cases": cases,
        "limitation": "inside range is necessary, not sufficient; startup, quantization, control loop behavior and physical effects are excluded",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Functional envelope: {min_mhz:.3f}–{max_mhz:.3f} MHz; "
          f"{sum(x['classification'] == 'within modeled range' for x in cases)}/"
          f"{len(cases)} nominal targets inside modeled range")
    for period in (30, 40, 50):
        print(f"{period} ns:", ", ".join(
            f"div={row['div']} {row['classification']}" for row in cases
            if row["reference_period_ns"] == period))
    print("Static audit:", args.output)


if __name__ == "__main__":
    main()
