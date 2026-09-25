# Private gate diagnostics and hosted AI

The routed netlist, PDK cell models, SDF files, Questa logs and diagnostics
derived from them remain on the lab server. `scripts/agent_gate_cycle.py` is
disabled because an unattended hosted model would receive private lab
diagnostic information without explicit authorization.

`scripts/gate_batch.py` still runs TC, BC and WC sequentially on the lab server
without an AI backend. It keeps full output under ignored local `results/`
and stops when a diagnostic fails. AI repair can be resumed with a local model
that stays on the lab server or after a deliberate review of exactly what data
may leave the lab. Neither option changes the requirement to inspect SDF
annotation and observe the DUT output before any physical lock claim.
