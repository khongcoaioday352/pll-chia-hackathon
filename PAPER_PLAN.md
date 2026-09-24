# Four-page hackathon paper plan

Working title: **A CHIA Loop for Agent-Generated Verification of a GF180 Digital PLL**

For the stronger, post-layout-validated title and evidence gates, see
`TOP10_STRATEGY.md`. Do not place post-layout validation in the final title
until an agent-generated test is actually replayed with annotated SDF.

This is a writing plan, **not experimental results**.

1. **Problem and contribution (about 0.7 page):** Verification of the
   oscillator enable path, DCO trim response, and feedback divider of the
   GF180 `digital_pll` RTL. State the contribution as a reusable CHIA loop
   for agent-authored stimulus/assertions and mutation-based evaluation.
   The source describes its behavior as frequency locking; avoid claims
   about phase locking, phase noise or physical jitter.
2. **Method (about 1 page):** Diagram showing agent proposal, CHIA simulator
   node, objective original-RTL oracle, and held-out mutant evaluation. Specify
   model, token/call budget, simulation budget, selection history and filters.
3. **Experiment (about 0.8 page):** Identify exact source commit, functional
   simulation abstraction, testbench generation, frozen mutations, baseline,
   and machine/compiler versions. Validate each mutant and its observability.
4. **Results (about 1 page):** Table with baseline versus agent: original pass
   rate, mutants detected / valid mutants, calls, total time, and failure cases.
   If available, add a small functional RTL versus gate-level SDF replay table
   for identical generated stimuli. Include one concrete agent action and its
   simulator feedback. Do not fill in numbers until the final reproducible run.
5. **Limitations/conclusion/references (remaining space):** Functional model is
   not signoff timing or jitter characterization. State coverage limitations.
   Acknowledge AI assistance at the end if used.

Keep the entire PDF within four pages, including references, because the
hackathon instructions do not explicitly grant extra reference pages.
