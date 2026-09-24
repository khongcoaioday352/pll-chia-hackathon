# Competitive direction: PLLGuard

## Candidate title

**PLLGuard: A CHIA Loop for Agent-Generated and Post-Layout-Validated Tests of a GF180 Digital PLL**

Use this title only after at least one agent-generated test has actually been
replayed on a gate-level GF180 netlist with an annotated SDF. Until then use:
**PLLGuard: A CHIA Loop for Agent-Generated Verification of a GF180 Digital PLL**.
The design's own RTL calls its behavior frequency locking; describe it as a
digital PLL/FLL and make no claim of physical phase-noise measurement.

## Research question

Can a feedback-driven CHIA agent produce valid input sequences and oracles for
the PLL's enable/reset, DCO trim, and divider behavior, then prioritize tests
which remain useful across functional RTL and post-layout simulation, at a
limited simulator budget?

## The loop to demonstrate

1. Agent writes a bounded stimulus and assertion program for PLL pins.
2. A CHIA simulator node compiles a testbench and runs it on original GF180 RTL.
3. A deterministic oracle validates original behavior; invalid tests and
   their diagnostics go back to the agent for revision.
4. A frozen, withheld fault suite scores valid tests with the same budget as
   a fixed sweep and the author's original testbench. No fault source or
   identity is shown to the agent.
5. Replay one or more high-value tests on the routed netlist with BC/TC/WC
   SDF when these files, cell models, and Questa are available. Measure only
   observable clock behavior, timing-sensitive failures, and simulation cost.
   Do not score a functional assertion as a physical jitter metric.

Steps 1–4 are needed for a credible hackathon submission. Step 5 is the
distinguishing demonstration for the stronger title. The current repository
implements the bounded test language, functional simulator, and fault scoring;
CHIA end-to-end execution and gate-level replay have not been demonstrated.

## Experimental evidence required

| Evidence | Minimum proof | Current state |
| --- | --- | --- |
| Real agent loop | CHIA/Ray run with saved prompts, agent proposals, Verilog and logs | Pending a host where Ray starts |
| Fair comparison | Same number of proposed tests and simulator budget; original testbench and fixed tests reported | Fixed tests pass; existing testbench not yet scored |
| Discriminating benchmark | More than the four trivial seeded faults; valid and replayable faults frozen before evaluation | Pending design and validation |
| Post-layout relevance | At least one identical stimulus replayed with netlist and annotated SDF | Requires lab outputs and Questa |
| Scientific honesty | Original-pass/false-positive rate, failure cases, runtime, environment, source hashes | Adapter records most fields; no final run |

## Go/no-go for the stronger claim

If the gate-level netlist/SDF is unavailable, fails to elaborate, or produces
no interpretable clock trace before the writing cutoff, do not mention
post-layout *results* in the title or abstract. Submit the functional CHIA
loop with its real limitations if it runs. If the agent never completes a
CHIA-managed test/simulator cycle, the artifact is not ready for submission
as a completed CHIA hackathon loop.

The organizers request a 4-page PDF and an open-source CHIA loop with its
results; they list autonomous verification collateral and RTL-to-GDS as
example tracks and also accept original ideas. Ranking is a committee
judgment; satisfying the checklist does not guarantee top 10.
