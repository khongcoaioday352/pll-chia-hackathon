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
Check annotation coverage in the simulator log before claiming SDF behavior:
the script cannot automatically certify complete annotation. A passing probe
demonstrates only the stated output behavior for this candidate, this netlist,
and this corner. It does not establish lock, jitter, full PVT coverage, or
identity between the routed netlist and published functional RTL.

If TC compiles, run BC and WC with **new output directories** by changing
`--corner` and `--output`. Do not copy the private netlist, cell models, SDF,
full Questa log, or lab paths into the public repository. Publish numerical
results only after reviewing them and obtaining authorization.
