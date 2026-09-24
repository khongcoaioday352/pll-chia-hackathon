"""Frozen, inspectable fault injection for the public PLL snapshot."""
from __future__ import annotations

import pathlib
import shutil

from verify import RTL_FILES

# Exact substitutions intentionally fail closed when the source changes.
# Review each mutant for semantic validity before citing a detection rate.
MUTATIONS = {
    "ignore_enable": ("digital_pll.v",
        "assign ireset = ~resetb | ~enable;", "assign ireset = ~resetb;"),
    "ignore_dco_trim": ("digital_pll.v",
        "assign itrim = (dco == 1'b0) ? otrim : ext_trim;",
        "assign itrim = otrim;"),
    "ring_trim_inert": ("ring_osc2x13.v",
        "delay = delay_base + delay_per_bit * $itor(bcount);",
        "delay = delay_base;"),
    "controller_target_fixed": ("digital_pll_controller.v",
        "if (sum > div) begin", "if (sum > 5'd8) begin"),
}


def prepare(original: pathlib.Path, target: pathlib.Path) -> dict[str, pathlib.Path]:
    paths = {"original": target / "original"}
    for name in ("original", *MUTATIONS):
        dst = target / name
        dst.mkdir(parents=True, exist_ok=True)
        for source in (*RTL_FILES, "clockbuf_shim.v"):
            shutil.copy2(original / source, dst / source)
        paths[name] = dst
        if name == "original":
            continue
        filename, before, after = MUTATIONS[name]
        path = dst / filename
        data = path.read_text()
        if name == "ring_trim_inert" and data.count(before) != 1:
            before = "delay = 1.168 + 0.012 * $itor(bcount);"
            after = "delay = 1.168;"
        if data.count(before) != 1:
            raise ValueError(f"mutant {name}: expected exactly one match in {filename}")
        path.write_text(data.replace(before, after, 1))
    return paths
