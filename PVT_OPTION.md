# PVT-aware digital PLL direction: decision gate

## Comparison with current verification project

| Direction | Potential contribution | Evidence needed | 36-hour feasibility |
| --- | --- | --- | --- |
| Agent-generated PLL tests | Reusable CHIA verification loop | End-to-end CHIA run, fair baseline and faults | Better: functional simulator already works |
| Agent-driven PVT-robust PLL design | An improved design, optimized for worst-corner behavior | Before/after frequency and lock, routed netlist and SDF for several corners | Risky: each RTL change may require synthesis/PNR and working gate-level simulation |
| PVT-aware verification plus one targeted improvement | Agent locates fragile behavior and proposes a bounded design change; validate across measured corners | CHIA loop and one verified design comparison across available corners | Best compromise *only if* lab multi-corner flow works promptly |

## Honest research question

Can a CHIA agent find a bounded RTL/controller change that improves the
GF180 digital PLL/FLL's **worst measured PVT corner** while preserving output
frequency, startup and area constraints at every tested corner?

Do not claim suitability for *every* PVT point: the existing script uses only
BC = FF/-40C/5.5V, TC = TT/25C/5.0V and WC = SS/125C/4.5V. The GF180 5V
standard-cell documentation also characterizes SS/-40C/4.5V and
FF/125C/5.5V, which could be added if the files and time permit. A sparse
corner set does not prove behavior over continuous process/voltage/temperature
variation.

## Minimal loop that would justify a PVT design title

If the lab server provides Python, Ray, the model endpoint and EDA, CHIA and
simulators can run on one host (see `LAB_RUNBOOK.md`). Otherwise run CHIA on a
separate host (see `SERVER_NO_PYTHON.md`). Until the agent-generated test is
actually replayed through the PVT EDA flow inside the CHIA loop, report PVT
data as separate validation rather than an automated CHIA node.

1. Freeze the present GF180 PLL as a baseline and save its source hash.
2. Run its existing RTL, netlist and annotated SDF across the available
   corners; record whether clock output starts, measured frequency error,
   time to a stated frequency tolerance, and simulation failures. Check
   timing constraints and area separately.
3. Give the agent failures and bounded edit permission for the controller
   and synthesizable trim/control logic. Keep the ring oscillator topology and
   public interface fixed for the first experiment.
4. Synthesize, route and regenerate corner-specific SDF for any changed RTL;
   a functional-model parameter edit alone is not a physical PVT improvement.
5. Compare baseline and revised implementation with identical stimulus,
   constraints and corner files; score worst-corner frequency/settling and
   count any new failures. Preserve rejected attempts, commands and logs.

## Decision gate

Do not retitle the project as PVT optimization until *both* baseline and a
changed implementation complete the same multi-corner physical flow. If gate
simulation remains blocked, continue the functional CHIA verification loop,
and state PVT-aware design as future work. A TC-only run or a changed
behavioral delay constant cannot substantiate a robust-PVT design claim.
