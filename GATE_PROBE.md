# Routed-netlist output probe (private lab run)

The lab preflight confirms that the routed GF180 netlist, BC/TC/WC SDF files and
Questa executable exist. It does **not** establish that the gate model oscillates,
that SDF was successfully applied, or that the PLL locks. The historical
`tb_digital_pll.v` gate branch unconditionally assigns `locked = 1` after 50
reference edges and cannot serve as a lock oracle.

From the PLLGuard repository on the lab server, run a first, short **TC** probe:

```bash
"$HOME/pll-chia-venv/bin/python" scripts/gate_output_probe.py --lab "$HOME/stdcell-pll" --corner TC --candidate examples/agent_program.json --output results/gate_output_tc_v1
```

The script compiles the lab standard-cell models, routed `6_final.v`, and a
generated black-box testbench with Questa; it passes the **TC-specific** SDF to
`vsim -sdftyp /tb/dut=...`. The testbench only drives top-level inputs and
counts transitions of `clockp[0]` and `clockp[1]`. It contains no internal
signal forcing, direct writes into the DUT or synthetic lock indicator. The
selected candidate checks whether the output oscillates when enabled and
stops after disable. Reference clock, stimulus times, and observation windows
are prescribed by the candidate and are part of the experiment.

Examine `results/gate_output_tc_v1/summary.json` plus **private** `vsim.log`.
Any compilation failure, simulator error, timeout, SDF annotation warning,
unknown output, or failing assertion must be reported as a diagnostic result.
Timing-check violations remain visible alongside observed edge counts and
prevent a timing-clean PASS.
Check annotation coverage in the simulator log before claiming SDF behavior:
the script cannot automatically certify complete annotation. A passing probe
demonstrates only the stated output behavior for this candidate, this netlist,
and this corner. It does not establish lock, jitter, full PVT coverage, or
identity between the routed netlist and published functional RTL.

If TC compiles, run BC and WC with **new output directories** by changing
`--corner` and `--output`. Do not copy the private netlist, cell models, SDF,
full Questa log, or lab paths into the public repository. Publish numerical
results only after reviewing them and obtaining authorization.

## Unattended sequential run

`scripts/gate_batch.py` runs TC, BC, WC in that order without any model API or
interactive prompt. It stops on a failed compilation, simulator error, missing
result, or failed functional assertion. Each corner uses a separate private
output directory; `summary.json` is a small local aggregate, not a proof of
lock or complete SDF annotation. Run it in the background from the repository:

```bash
nohup "$HOME/pll-chia-venv/bin/python" scripts/gate_batch.py --lab "$HOME/stdcell-pll" --output results/gate_batch_v1 > results/gate_batch_v1.console.log 2>&1 < /dev/null &
```

Inspect `results/gate_batch_v1.console.log` and
`results/gate_batch_v1/summary.json` later. Keep the private per-corner
`driver_*.log`, `vlog_*.log` and `vsim.log` on the lab server. To repeat a run,
choose a fresh `--output` directory.

If TC produces only timing-check errors while output assertions are observed,
add `--collect-timing-diagnostics` to gather BC and WC. This option does not
waive timing violations or declare any corner passing. It stops on compile
failures, missing measurements, assertion failures, SDF annotation errors or
other simulator errors. The aggregate status becomes
`collected_with_timing_violations` if any corner reports timing-check errors.
