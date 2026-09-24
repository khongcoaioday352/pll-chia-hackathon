# Competition experiment: agent-authored GF180 digital PLL tests

## Research question

Under the same simulator and agent-call budget, can a CHIA-orchestrated agent
create new black-box PLL tests that expose faults missed by an existing
testbench and a fixed test-selection strategy? For valid generated tests,
which behaviors can also be checked on an annotated post-layout GF180 netlist?

## Frozen evaluation protocol

1. Select a public, releasable version of the author's PLL RTL and its
   behavioral oscillator model. Record the commit and simulator version.
2. Define the externally observable contract for reset/enable, DCO trim,
   divider ratio, and (only if reliably measurable) acquisition or lock.
3. Freeze three independent baselines: the author's existing testbench, a
   fixed sweep with the same simulation budget, and the current starter's
   three predefined test families. Do not use a single disable test as the
   main baseline.
4. Freeze a fault suite with distinct behaviors and check that each fault
   compiles, the original meets the contract, and the fault changes an
   observable result. Reserve a subset for final evaluation; do not provide
   its source or labels to the agent.
5. Give the agent the contract, permitted interfaces and prior original-RTL
   measurements. Let it author new stimulus and assertions, not merely select
   `kind`, `div`, and `observe_ns`. Compile generated tests in isolation and
   reject tests that fail the original RTL.
6. Run the same fault suite and wall-time / simulator budgets for each
   approach. A fault is detected only when the test passes the original and
   fails the fault. Count invalid agent proposals and timeouts separately.
7. Preserve full prompts, proposals, generated test files, raw logs, source
   hashes, runtime and a machine-readable result table. Do not describe
   pre-seeded faults as discovered real bugs.
8. If gate-level netlist, SDF, and cell models are available, replay identical
   agent-generated stimuli through the existing Questa flow. Report the
   fraction that compile, produce observable clocks, and preserve valid
   functional properties, separated by corner. A post-layout result is not
   implied by a behavioral-model simulation.

## Outputs and claims

Primary measure: unique valid fault variants detected at a fixed simulation
budget. Secondary measures: original RTL pass rate, test validity, runtime,
AI model calls, and whether newly found failures are independently replayed.
Only make a coverage claim if an actual coverage tool supports it; fault
detection rate is not the same as line, toggle or functional coverage.

## Morning inputs needed

- RTL: controller, top module and oscillator behavioral model at a commit.
- Existing testbench, Makefile, any parameter overrides and compile defines.
- Permission to publish source and generated tests; do not include private PDK
  libraries, standard cells, SDF/SPEF, license files or secrets.
- Lab machine details: Python and package installer, Icarus/Verilator, Ray,
  OpenCode/model access, GitLab, EDA binaries, netlist, SDF, SPEF, cell models
  and simulator license. A single-host run is possible if these checks pass;
  otherwise run CHIA on another machine and keep EDA on the lab server.

## Go / no-go gates (Vietnam time, Sep 24–25)

- Sep 24, when lab power returns: clone GitLab, run the preflight and smoke test.
- Sep 24 16:00: one CHIA agent-authored program and simulator feedback completes.
- Sep 24 23:00: freeze the honest final result; stop feature expansion.
- Sep 25 12:00: four-page PDF and releasable repository are reviewable.
- Sep 25 16:30: submit via hackathon HotCRP; check uploaded PDF and URL.

The loop now compiles agent-authored step programs, but has **not** completed
an end-to-end agent run. Integrate the author's ZIP, validate the real result,
and establish a credible existing-testbench baseline before any improvement
claim in the paper.
