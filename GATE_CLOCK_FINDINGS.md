# GF180 routed-clock diagnostic (25 September 2026)

The following numbers were transcribed from private lab Questa runs. They are
digital gate-model observations, **not** a PLL-lock, silicon, SPICE, or PVT
signoff claim. Routed netlist, SDF, PDK files, and raw Questa logs remain private.

The TC SDF was regenerated with the current routed netlist, SPEF, SDC, and
liberty. The existing and regenerated SDF differed only in their `DATE` field;
both contained 878 `INTERCONNECT` entries. Questa reported successful SDF
backannotation and one `vsim-SDF-3438` warning. Annotation coverage has **not**
been independently certified. The private OpenROAD Makefile's SDF target was
updated to depend on the routed SPEF, routed SDC, and SDF generator as well as
the routed netlist; the original Makefile was backed up before this change.

In DCO mode, `clockp[0]` had repeated rising edges separated by approximately
611–612 ps with trim 0, compared with a 1212 ps `$period` requirement reported
on the controller flip-flops. TC logged 414 period violations over the first
200 ns. Holding DCO mode and changing trim to 1, then 65 and 1089, preserved
output activity, but those sequential measurements do not prove that the codes
are timing clean when independently restarted.

An independent reset before each trim code gave:

| External trim | Rising edges / 200 ns | `$period` violations |
| ---: | ---: | ---: |
| 0 | 36 | 414 |
| 1 | 17 | 23 |
| 2 | 32 | 368 |
| 4 | 32 | 368 |
| 65 | 16 | 23 |
| 1089 | 15 | 23 |

A second run with passive edge timestamps checked both top-level phases. Trim
4 produced 16 sub-1212 ps intervals per phase in its window. Trim 65 and 1089
each produced one per phase, near reset release. This matches 23 controller
flip-flop `$period` errors per short interval (368 = 16 × 23). One trial had
437 **total timing-check errors** but 414 **period errors**; these are different
counts, not evidence of simulator nondeterminism. The 23 other timing errors
still need classification in the private log.

The user's bounded closed-loop TC candidate (`ref_period_ns=40`, `div=8`) passed
the published behavioral RTL test with 202 and 200 output rising edges in two
1000 ns windows. The corresponding routed-netlist run measured zero in both
windows and failed its assertion, with 46 period violations. Turning DCO mode
back on did not restart the gate model; toggling the top-level reset restored
output activity while timing violations persisted. Gate-model output rate at
trim 1 was only about 80–85 MHz over the measured 200 ns windows; do not use
the doubled edges at trim 0 as a clean frequency measurement.

## Reproduce the aggregate privately

After placing `scripts/audit_gate_clock.py` in this repository on the lab host:

```bash
python3 scripts/audit_gate_clock.py --log results/gate_two_phase_trace_tc_v1/vsim.log --candidate results/gate_startup_code_sweep_v2b.json --output results/gate_two_phase_audit_v1.json
```

The audit reads measured edge intervals and `$period` records without removing
timing checks. It writes only aggregate counts, log hash, and explicit flags
that lock, physical ring behavior, and complete SDF annotation are unverified.

## Next hardware investigation

The narrow interval appears on **both** clock phases. In this gate model,
changing only the phase-0 output buffer or relaxing SDC would not remove the
observed waveform. Investigate the oscillator startup stage and delay-path
selection, check the GF180 digital cell-model assumptions against a circuit
transient simulation, then verify a separate RTL/physical-design variant after
fresh synthesis, routing, SPEF, and corner-specific SDF generation. Preserve
the published functional RTL snapshot and previous evidence for comparison.
