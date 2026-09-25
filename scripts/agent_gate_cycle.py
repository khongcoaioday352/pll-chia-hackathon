"""Fail-closed placeholder for hosted AI gate diagnostics.

The lab's Questa/SDF diagnostics are private. This entry point intentionally
does not contact a hosted model or read those logs. Use gate_batch.py to run
the measured experiments locally without API credits.
"""
from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "Hosted AI gate repair is disabled: it would share information derived "
        "from private lab diagnostics. Run scripts/gate_batch.py locally, "
        "and keep full Questa/SDF logs on the lab server."
    )


if __name__ == "__main__":
    main()
