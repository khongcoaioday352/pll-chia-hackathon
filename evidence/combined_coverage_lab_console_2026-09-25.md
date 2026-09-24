# Combined PLL behavioral fault coverage (lab console, 2026-09-25)

This record transcribes the author's lab output from
`results/combined_coverage_matched_v2/summary.json`. The raw simulator
result JSON files and the complete live Gemini run remain on the lab host.
The reproduction script is `scripts/combined_coverage.py`, and the
additional model-authored proposal is frozen in
`examples/live_reset_phase_agent2.json`.

| Suite | Original-valid tests | Injected faults detected | Nominal simulated time |
| --- | ---: | ---: | ---: |
| Original three agent tests | 3/3 | 5/7 | 7,260 ns |
| Combined four agent tests | 4/4 | 7/7 | 8,280 ns |
| Original three fixed baselines | 3/3 | 2/7 | 5,710 ns |
| Baselines plus human-written phase/reset test | 4/4 | 4/7 | 6,510 ns |
| Time-matched baselines plus extended human-written phase/reset test | 4/4 | 4/7 | 8,280 ns |

Lab console checks: published prior stress matrix **MATCH**; published
time-matched matrix **MATCH**; live agent reset matrix **MATCH**; new
agent test passes the original RTL with 30 ns and 50 ns reference periods;
no tool or compilation errors.

The original three-test agent suite detected five faults, and the later
agent-authored phase/reset test detected the two previously missed faults:
`resetb_bypassed` and `phase1_held_low`. The adaptive live run that
generated the later test made three proposals: proposal 0 (reused from an
earlier run) passed the original RTL, proposal 1 failed the original RTL
at the nominal 40 ns period, and proposal 2 passed. The combined
four-test suite consists of the **three original passing tests** plus
**proposal 2**. Do not present the adaptive live run itself as 3/3 valid.

**Interpretation:** The seven injected faults and the human-guided reset
goal were chosen after observing earlier outcomes. The four-test controls
were also adjusted after seeing the results. This is a post hoc,
behavioral-RTL fault coverage comparison, not a blind benchmark, a
statistical claim about unseen faults, a measurement of transistor-level
PVT, or evidence of physical PLL lock across BC/TC/WC. The matched
control equalizes nominal simulation nanoseconds and number of tests;
it does not equalize assertion strength, CPU time, or development effort.

Re-run on the exact pinned GF180 RTL with the author's complete live
summary present:

```bash
python scripts/combined_coverage.py --rtl rtl_gf180_snapshot \
  --live results/adaptive_reference_resumed_v3 \
  --output results/combined_coverage_replay
```

A curated, explicitly labeled console transcript containing the new
candidate, source raw-summary SHA-256, exact evaluation status matrix, and
matched human-control status matrix is published as
`evidence/adaptive_reference_live_v3_public.json`. Re-run from a clean
checkout by using that JSON as the `--live` argument. The GitHub Actions
workflow `reproduce.yml` performs this run and retains simulation logs.
The complete raw model conversation and simulator files remain on the lab
host; this public transcript cannot independently prove model authorship.
