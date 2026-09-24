# Split execution: no Python on the lab server

## Roles

| Host | Runs | Inputs and outputs |
| --- | --- | --- |
| GitHub Codespaces or another Linux cloud VM | Python, CHIA, Ray, OpenCode, RTL simulator; saves agent proposals, testbenches, logs and JSON | Project source; public GF180 functional RTL |
| Lab EDA server | Existing `make` targets, Icarus/Questa/OpenROAD/OpenSTA, BC/TC/WC generation and post-layout replay | RTL/testbench via GitLab; annotated netlist, SDF and cell models; text logs back to the cloud |

The lab server needs **no Python, Ray, Node, or LLM client**. It does need
shell access and the existing EDA tools. If Codespaces cannot connect to the
lab server directly and no GitLab runner is installed there, human-assisted
GitLab transfer is the honest workflow. Run the CHIA agent/RTL loop fully on
Codespaces; report lab PVT experiments as separate validation, not an
automated CHIA worker.

## Read-only preflight on the lab server

Run each of these one-line commands from `~/stdcell-pll`. None requires Python:

```
pwd
command -v git
command -v iverilog
command -v vvp
command -v yosys
command -v openroad
command -v sta
test -x /home/tools/mentor/questasim/2024.2/questasim/bin/vsim && echo 'Questa executable OK'
ls -lh openroad/results/gf180/pll/base/6_final.v openroad/results/gf180/pll/base/6_final.spef
for c in BC TC WC; do test -s "openroad/results/gf180/pll/$c/digital_pll.sdf" && echo "$c SDF OK" || echo "$c SDF MISSING"; done
grep -nE 'read_spef|read_liberty|write_sdf' openroad/scripts/gen_sdf.tcl
```

The uploaded source ZIP contains an older `gen_sdf.tcl` with no `read_spef`;
inspect the current server file before trusting interconnect delay in SDF.

## Short gate-level check (after preflight)

If the netlist, one corner SDF, cell models and Questa all exist, the existing
`sim/Makefile` offers a short **existing-testbench** check. From
`~/stdcell-pll/sim`, run one line at a time:

```
make tb_digital_pll_gate_questa CORNER=TC SIM_TIME=25ns > postlayout_TC_25ns.log 2>&1
grep -nE 'Error|Warning|PASS|TIMEOUT|sdf|SDF' postlayout_TC_25ns.log | tail -n 40
```

This only checks a short time window; it does not prove lock, PVT robustness,
or that an agent-generated test can be replayed. Save the complete logs for
interpretation. Never start concurrent Questa runs from the same `sim/`
directory because the Makefile recreates its shared `work` directory.

## Next step for candidate design evaluation

Freeze the baseline source and logs first. A changed RTL needs a separate
PNR/netlist, corner SDF files and the *same* test stimuli. Do not overwrite
the baseline `results/` tree before extracting its metrics. Neither changing
the functional oscillator delay nor reusing the baseline SDF for changed RTL
is a physical PVT optimization result.
