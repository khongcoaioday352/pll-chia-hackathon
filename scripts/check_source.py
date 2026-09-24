"""Fail fast if the live lab RTL cannot support the frozen mutation suite."""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mutants import MUTATIONS, prepare
from verify import RTL_FILES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", type=pathlib.Path, required=True)
    args = ap.parse_args()
    root = args.rtl.resolve()
    for name in (*RTL_FILES, "clockbuf_shim.v"):
        p = root / name
        if not p.is_file():
            ap.error(f"missing source: {p}")
        print(f"{name}: {hashlib.sha256(p.read_bytes()).hexdigest()}")
    with tempfile.TemporaryDirectory(prefix="pll_mutation_check_") as tmp:
        sources = prepare(root, pathlib.Path(tmp))
        assert set(sources) == {"original", *MUTATIONS}
    print(f"Mutation source check OK: {len(MUTATIONS)} variants can be prepared")


if __name__ == "__main__":
    main()
