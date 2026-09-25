# Controller response: lab-reported edge counts (2026-09-25)

The author explicitly authorized publication of these lab-reported measurements
on 2026-09-25. This is a **post hoc behavioral diagnostic**, transcribed from
the author's lab console. It is not an agent-authored test, a scored mutation
experiment, a PVT measurement, or a PLL lock test. The raw `result.json` logs
and `summary.json` remain in `results/controller_operating_map_v1/` on the lab
server. The diagnostic script used for this one run exists in historical
commit [63bfdc3](https://github.com/khongcoaioday352/pll-chia-hackathon/commit/63bfdc37f1a451bac0f84c6e357fff94827979d6).
It was removed from current CI and the default branch because its preset
wait times did not fit the author's requested workflow.

For each table entry the testbench used a fresh reset, set `dco=0`, selected
the indicated input reference period and divider, waited the indicated time,
then counted `clockp[0]` rising edges in 400 ns. Values are the observed
edge count after 2000 ns / 4000 ns respectively.

| Reference period | div=6 | div=8 | div=12 | div=16 |
| --- | ---: | ---: | ---: | ---: |
| 30 ns | 81 / 80 | 86 / 86 | 86 / 86 | 86 / 86 |
| 40 ns | 68 / 68 | 81 / 79 | 86 / 86 | 86 / 86 |
| 50 ns | 70 / 68 | 70 / 68 | 86 / 86 | 86 / 86 |

In a separate sequential divider change after 2000 ns of waiting at each
setting, the measured `div=6 → div=16` counts in two 400 ns windows were
81 → 85 (30 ns), 68 → 85 (40 ns), and 70 → 85 (50 ns). The 30 ns pair
reproduces the frozen `agent_1` count, whose original assertion requires an
increase **greater than 10**, while the observed increase is 4. The 30 ns
steady `div=8` count of 86 edges/400 ns is consistent with the frozen
baseline's 172 edges/800 ns on the unmodified RTL.

The [source-derived functional envelope](behavioral_frequency_envelope.json)
explains the edge-count plateaus without inferring lock. In the pinned Verilog,
`hiclock` toggles every `delay = 1.168 + 0.012 × popcount(trim[25:0])` ns,
and `clockp[0]` completes one cycle in four such delays. The resulting
modeled range is **168.919–214.041 MHz**. It predicts approximately
67.57–85.62 edges per 400 ns window at the two bounds; integer counts near
68 and 86 in the lab are consistent with this behavior. Among the 12
(reference period, divider) targets in the table, only 30 ns/div=6 and
40 ns/div=8 have targets inside this modeled range. A target inside the
range may still fail to lock or converge. The source comment about SPICE
reaching 90 MHz concerns a different physical model; it does not change this
functional simulation parameter range.

Several independent tests measured ~86 edges in 400 ns, equivalent to about
215 MHz **as a measured output edge rate in this functional model**. This
pattern warrants examining the model and controller operating region; counts
alone do not prove an oscillator frequency ceiling, PLL lock, or a physical
chip limitation. Longer waits up to 4000 ns did not materially change these
specific edge counts; this does not establish convergence for other settings.
The script's printed `pass` only checked that the recorded count was at least
zero. It is not evidence that a target divider or lock condition was met.

No Verilog `force` was applied to PLL internal signals or outputs by this
script; it **did** set external input stimuli and prescribe clock period,
wait times, and observation windows. The 27 reported measurements therefore
cannot be described as free from prescribed times or inputs. Future passive
analysis may read the saved result files without rerunning simulations.
