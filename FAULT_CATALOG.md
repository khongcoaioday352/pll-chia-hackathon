# Fault catalog and observable claims

Each entry is an **injected RTL variant** created by one exact textual substitution
in the pinned GF180 functional model. These are controlled test targets, not
discovered defects in the original PLL. The frozen agent programs were generated
during the recorded three-turn CHIA/Gemini run; earlier prompt development used
the primary suite. The additional seven variants were assembled after that run,
so this is **post hoc stress**, not a historically blind test set.

The table summarizes the union across three original-passing agent programs
and the union across three original-passing fixed baseline programs. A detected
fault means a candidate passed the unmodified RTL and failed that variant.
Full per-candidate results are in [primary JSON](evidence/gemini_36_three_v2/summary.json)
and [stress matrix](evidence/stress_public_replay_matrix.json).

| Suite | Variant | Exact behavioral change | Agent | Fixed baseline |
| --- | --- | --- | --- | --- |
| Primary | `ignore_enable` | Remove `enable` from internal reset gating | Yes | Yes |
| Primary | `ignore_dco_trim` | Ignore externally selected DCO trim | Yes | No |
| Primary | `ring_trim_inert` | Remove trim contribution from functional ring delay | Yes | No |
| Primary | `controller_target_fixed` | Replace programmable `div` threshold with 8 | Yes | No |
| Post hoc | `resetb_bypassed` | Remove `resetb` from internal reset gating | No | No |
| Post hoc | `dco_mode_stuck_external` | Force the external trim path | Yes | Yes |
| Post hoc | `controller_increase_disabled` | Hold trim instead of incrementing it | Yes | No |
| Post hoc | `controller_decrease_disabled` | Hold trim instead of decrementing it | Yes | No |
| Post hoc | `controller_updates_early` | Apply controller update earlier in its `prep` sequence | Yes | No |
| Post hoc | `ring_trim_reversed` | Reverse trim's contribution to functional ring delay | Yes | Yes |
| Post hoc | `phase1_held_low` | Hold oscillator output phase 1 low | No | No |

The source substitutions live in [`mutants.py`](mutants.py) and
[`scripts/stress_suite.py`](scripts/stress_suite.py). The two misses are
testable by a **human-authored** post hoc program
[`examples/phase1_reset_program.json`](examples/phase1_reset_program.json):
it passes the original and fails `resetb_bypassed` and `phase1_held_low`.
That check demonstrates observability in this bounded test language; it does
not change the 5/7 agent result or establish exhaustive verification.

All delay-sweep results change parameters of the FUNCTIONAL ring-delay model.
They do not establish transistor PVT coverage, physical jitter, lock time,
or post-layout timing.
