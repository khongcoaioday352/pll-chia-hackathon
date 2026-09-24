# Working manuscript — replace every [FILL] before submission

**Provisional title:** PLLGuard: A CHIA Loop for Agent-Generated Tests of a GF180 Digital PLL

**Authors:** [FILL names, affiliation, contacts]

> This file is an editable paper draft, not an experimental result or a PDF.
> The final PDF must fit four pages in a two-column ACM/IEEE style. Do not
> release or submit this text with unfilled evidence fields.

## Abstract

Verification of a tunable digital PLL poses a practical problem: a stimulus
that demonstrates oscillator activity may miss faults in enable control,
external trim selection, or feedback behavior. We present PLLGuard, a loop
implemented with CHIA that asks an AI model to generate bounded black-box
input sequences and output assertions, compiles the candidate into a Verilog
testbench, and scores it through an independent RTL simulator. The candidate
must pass the unmodified GF180 design; its fault-detection ability is then
evaluated against withheld RTL mutations. We compare [FILL: number of valid
agent tests and model calls] with [FILL: exact fixed baseline] under a matched
simulation budget. On [FILL: frozen RTL commit], the agent detected [FILL]
of [FILL: validated] fault variants, compared with [FILL] for the fixed
baseline. [FILL one concrete distinctive behavior if supported by run logs.]
The artifact releases the loop, test programs, generated benches, source
hashes, execution commands, and results. [FILL: If and only if demonstrated,
mention separately a post-layout replay with a named SDF corner.]

## 1. Problem and scope

The design under study is a GF180 standard-cell implementation of a digitally
controlled ring oscillator with a controller and divider. Inputs include
reset, enable, a reference clock, a DCO mode bit, a 26-bit external trim,
and a five-bit divider. The output is a two-bit clock port. The source calls
the block `digital_pll`; its feedback mechanism is more precisely described
as frequency locking in the source. We retain the published design name but
do not measure analog phase noise, physical jitter, or signoff timing in the
functional experiment.

Our question is whether an agent can write valid black-box tests that reveal
faults a fixed, equally budgeted test suite misses. A successful test has an
explicit pass/fail assertion, works on the unmodified design, and records a
simulation trace. This definition avoids counting model speculation as
verification evidence.

## 2. Loop and test language

The loop consists of a CHIA model call and a separate CHIA simulator function.
Each model turn receives an interface description and previous observations
from the original design. The model proposes one JSON program with ordered
`set`, `wait`, `measure`, and `assert` actions. `measure` counts output rising
edges in a bounded window; assertions compare counts or a fixed integer.
The program is checked against port ranges, action count, names, and total
duration before deterministic Verilog testbench generation. The testbench
drives only top-level inputs and observes only the top-level output. Icarus
Verilog or Verilator compiles and runs it. Compilation errors and timeouts
remain visible and are never scored as a valid detection.

The agent first sees feedback for tests on the original RTL. Mutated variants
are generated only after all proposals have been fixed and are not supplied
to the agent. A fault counts as detected when the test passes the original
and fails that variant. The loop saves proposed programs, generated benches,
compilation logs, simulation logs, hashes, and a machine-readable summary.

## 3. Experiment design

The source is [FILL: Git commit and SHA-256 for all three RTL files]. The
oscillator uses the `FUNCTIONAL` behavioral timing model; this is an RTL
abstraction, not a physical PVT model. We use [FILL: Icarus/Verilator and
version] on [FILL: machine and Python/CHIA/Ray versions] and [FILL: model
name and access mode]. The fixed baseline comprises the disable, DCO trim,
and divider test families already specified before the model run. It receives
the same number of test attempts as the agent's three proposals; test durations
and simulator time limits must be reported from the generated artifacts.

The fault suite includes bypassing enable reset, ignoring external DCO trim,
making ring trim inert, and fixing the controller comparison target. Each
mutation edits one RTL statement. Before reporting a detection rate, we
validate that all variants compile and have an observable relevant effect.
We label these faults *injected variants*, not discovered bugs in the design.
The same frozen variants are used for the fixed and agent-generated tests.

## 4. Results

Complete after executing `python scripts/summarize.py
results/agent_lab_final/summary.json` and inspecting the per-test logs.

| Measure | Fixed baseline | CHIA agent |
| --- | ---: | ---: |
| Attempted tests | [FILL] | [FILL] |
| Valid tests passing original | [FILL] | [FILL] |
| Unique validated variants detected | [FILL] | [FILL] |
| Compile / runtime errors | [FILL] | [FILL] |
| End-to-end elapsed time | [FILL] | [FILL] |

Report an actual example: the agent changed [FILL: ports and timing], asserted
[FILL: exact relation between observations], and the simulator returned
[FILL: relevant original and mutant log lines]. Discuss any missed mutation,
false assertion, invalid JSON proposal, or model access failure using the
corresponding original file in the release. If the existing author testbench
is run, describe its results separately; do not silently substitute it for
the equal-budget fixed baseline.

### Optional: post-layout replay

Only include this subsection after running the **same agent-generated test**
against the placed/routed netlist with a corner-specific, SPEF-aware SDF and
GF180 cell models. For BC, TC and WC give separate output observations and
annotated interconnect counts. If only the existing author testbench was run
with SDF, describe it as *separate validation*, not agent-test replay.

## 5. Limits and conclusion

The four mutation locations do not provide broad design coverage. Functional
oscillator simulation does not support claims about measured jitter or
robustness over all PVT conditions. Any corner-specific gate simulation is a
separate, slower experiment with different timing semantics. On the frozen
design and fault suite, our measured result is [FILL: modest, exact finding].
The contribution is a reproducible CHIA block that turns model-authored PLL
input programs into executable assertions and objective simulator feedback.

## Acknowledgment

AI assistance was used in preparing the prototype and drafting this paper.
The authors reviewed the implementation, experimental records, and all final
claims. [FILL: funding/access acknowledgement if applicable.]

## References

- CHIA official framework repository, commit 16c35e92aaaf9511c6453bf94cd5cf589698f4e3.
- Efabless/Caravel public PLL source and license; insert the exact source URL
  and snapshot commit that corresponds to the released artifact.
- A³ 2026 CHIA Hackathon rules, https://agentic-arch.org/hackathon.html.
- [FILL: GF180 library and simulator documentation actually used.]
