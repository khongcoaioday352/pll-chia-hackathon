# OpenCode gate diagnostic task (private, experimental)

Work only in this disposable git worktree. Diagnose existing PLLGuard gate probe
parsing or simulator setup. The launcher supplies only redacted measurements and
diagnostic booleans in your prompt. Its permission configuration blocks shell,
external directories and web access; independent checks run outside the model.
Do not request or transmit raw PDK, routed netlist, SDF, SPEF, full Questa logs,
secrets or model transcripts. Do not commit, push, publish or modify the lab.

Goal: make `scripts/audit_saved_gate.py` accurately parse **existing** TC log
measurements, with independent verification that every named measurement exists
once and the simulator reports no fatal SDF error. If the saved log truly lacks
measurements, report this honestly; do not synthesize values. When the audit
passes, BC/WC probes can be run separately by the launcher. Investigate errors
and edit only `scripts/audit_saved_gate.py`, `scripts/gate_output_probe.py`, and
`scripts/gate_batch.py`. Do not edit candidates, reference benchmarks, published
evidence, frozen RTL, fault definitions, hardware libraries or constraints.

The launcher will run Python syntax checks and output probes for you. Do not alter RTL,
force internal signals, insert artificial lock signals, change the reference
frequency, or adjust measurement windows solely to make a failing test pass.
An assertion pass means only its stated output behavior; it is not proof of
frequency/phase lock, complete SDF annotation, silicon PVT coverage or physical
signoff. Finish with a brief report of measured values, unresolved errors,
files changed and commands run. Stop if the provider rejects a request.
