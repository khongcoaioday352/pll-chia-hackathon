# Reference-period sensitivity of combined PLL tests (lab console, 2026-09-25)

The author ran `scripts/combined_period_sweep.py` against
`results/combined_public_replay_v1/summary.json` on the pinned GF180
behavioral RTL. The raw 30/40/50 ns summary and simulator results remain
at `results/combined_period_sweep_v1/` on the lab server. This table is
an author-reported console transcript until the full per-test matrices are
published or replayed in public CI.

| Input reference period | Four frozen agent tests, original-valid | Agent faults detected | Four time-matched controls, original-valid | Control faults detected |
| --- | ---: | ---: | ---: | ---: |
| 30 ns | 3/4 | 4/7 | 3/4 | 4/7 |
| 40 ns | 4/4 | 7/7 | 4/4 | 4/7 |
| 50 ns | 4/4 | 7/7 | 4/4 | 6/7 |

At 30 ns, `agent_1` and `baseline_matched_2` failed on the
unmodified RTL. Both four-test groups missed exactly the same three
controller faults: `controller_decrease_disabled`,
`controller_increase_disabled`, and `controller_updates_early`.
At 50 ns all eight tests passed the unmodified RTL; the time-matched
control missed `controller_decrease_disabled`, while the agent suite
missed none. These identities were transcribed from the lab summary.

No simulator, compilation, or test-format errors were reported. The
40 ns re-evaluation exactly matched the previously published nominal
per-test matrix. Tests that failed on the unmodified RTL contributed
**zero** detected faults in that period.

**Interpretation:** The agent suite does not outperform the matched
control at 30 ns. Its nominal advantage is strongest at 40 ns and
smaller at 50 ns. This is a post hoc input reference-clock period
sensitivity check on behavioral RTL; it is **not** a transistor-level
PVT measurement, not a guarantee of PLL lock, and not a blind or
statistically representative generalization experiment. The seven
mutations and control policies were developed with knowledge of
earlier outcomes. Candidate and control sets were frozen *before*
this reference-period replay but not before the prior PLL project work.

Public reproduction from a clean checkout:

```bash
python3 scripts/combined_coverage.py --rtl rtl_gf180_snapshot \
  --live evidence/adaptive_reference_live_v3_public.json \
  --output results/combined_public
python3 scripts/combined_period_sweep.py --rtl rtl_gf180_snapshot \
  --combined results/combined_public \
  --output results/combined_period
```
