# Lab handoff: one host, Python available

Run commands one at a time. Keep this project in `~/pll-chia-hackathon` and the
existing hardware repository in `~/stdcell-pll`. Never run `git add .` in the
hardware repository: it contains large generated outputs and an ORFS clone.

## Before going to the lab

1. Create an empty **private** GitLab project named `pll-chia-hackathon`.
   Upload the contents of this directory (not its parent ZIP) to its default
   branch. From a machine with Git access, in this directory, execute:

   ```sh
   git init
   git branch -M main
   git add .
   git commit -m 'Add CHIA GF180 PLL verification loop and lab runbook'
   git remote add origin <YOUR_GITLAB_REPO_URL>
   git push -u origin main
   ```

   Only paste your repository URL at the placeholder; do not publish a
   username/token in this file. If the GitLab project already exists, use its
   clone URL and check its branch before any push. `.gitignore` excludes
   results, virtualenv and vendor code. Do not switch the project to public
   before checking publication permissions and removing private material.

2. Keep a copy of this directory or the corresponding ZIP on your laptop as
   a transfer fallback. The bundled `rtl_gf180_snapshot` is historical and
   must be compared with the active server sources.
3. Prepare an OpenCode account/model option that is *actually callable* from
   the lab. `opencode/big-pickle` is only a previously tested suggestion and
   might be unavailable; no cloud credit is assumed. Do not commit credentials.
4. Open `paper/PAPER_DRAFT.md` and fill authors, method and sources now;
   leave all `[FILL]` results until the run is complete.

## On the lab server

Run these commands in the home directory, each on its own line:

```sh
cd ~
git clone <YOUR_GITLAB_REPO_URL> pll-chia-hackathon
cd ~/pll-chia-hackathon
bash scripts/lab_preflight.sh
```

If the project already exists on the lab server, use
`cd ~/pll-chia-hackathon` then `git status --short` and `git pull --ff-only`
only if there are no local source changes. Keep it separate from `stdcell-pll`.

For the Sep 24 `edu02` session, the following checks **have passed**: Python
3.12 in `osstools`, GitHub and PyPI access, Icarus and Verilator availability,
`~/pll-chia-venv` with CHIA/Ray installed, local Ray startup, and OpenCode
1.18.32 responding `READY` from `opencode/big-pickle`. The CHIA clone is
`~/chia-upstream` at commit `16c35e92aaaf9511c6453bf94cd5cf589698f4e3`;
the binary is under `~/.opencode/bin`. The project repo and full loop have not
yet been verified on the lab server. **Skip the install section below on this
server** and go directly to the lab RTL copy commands.

For any different server: read the preflight output. If Python/pip or the
model endpoint is unavailable, run CHIA from another computer and reserve
the lab server for EDA. Keep CHIA in a separate venv from `osstools`.

If GitHub and the Python package index are reachable from the lab server:

```sh
cd ~/pll-chia-hackathon
python3 -m venv .venv
git clone https://github.com/ucb-bar/chia.git vendor/chia
git -C vendor/chia checkout 16c35e92aaaf9511c6453bf94cd5cf589698f4e3
.venv/bin/python -m pip install -e vendor/chia
curl -fsSL https://opencode.ai/install -o "$HOME/opencode-install.sh"
bash "$HOME/opencode-install.sh"
```

If GitHub is blocked but GitLab and the Python package index work, replace the
`git clone` and `checkout` lines with these two lines before pip install:

```sh
mkdir -p vendor/chia
tar -xzf chia-source-16c35e9.tar.gz -C vendor/chia
```

The archive contains the official CHIA sources at the pinned commit and its
upstream license; it does not include Python dependencies. The standalone
OpenCode installer works without Node/npm. If `vendor/chia` already exists,
skip its clone.
CHIA's Python distribution
is `chialoops`, while its import name is `chia`. Do **not** install the unrelated
PyPI distribution named `chia`.

Confirm every dependency individually:

```sh
cd ~/pll-chia-hackathon
.venv/bin/python -c 'import chia, ray; print("CHIA/Ray import OK")'
timeout 45s .venv/bin/python -c 'import ray; ray.init(num_cpus=1, include_dashboard=False); print("RAY OK"); ray.shutdown()'
PATH="$HOME/.opencode/bin:$PATH" timeout 90s opencode run --model opencode/big-pickle 'Reply READY'
```

An API error is a model access problem, not a simulator result. Use a working
CHIA-compatible model if the example is no longer accessible. If all checks
pass, sync a *copy* of the current lab RTL into this repository:

```sh
cd ~/pll-chia-hackathon
bash scripts/sync_lab_rtl.sh "$HOME/stdcell-pll"
"$HOME/pll-chia-venv/bin/python" scripts/check_source.py --rtl rtl_gf180_snapshot
"$HOME/pll-chia-venv/bin/python" verify.py --rtl rtl_gf180_snapshot --candidate examples/agent_program.json --output results/smoke_lab
PATH="$HOME/.opencode/bin:$PATH" "$HOME/pll-chia-venv/bin/python" loop.py --rtl rtl_gf180_snapshot --rounds 1 --model opencode/big-pickle --output results/agent_lab_first
```

Check `results/smoke_lab/result.json` first: the original should pass. If the
one-round loop writes `results/agent_lab_first/summary.json`, inspect original
pass status, valid agent proposals, and logs. Then run the planned three rounds:

```sh
cd ~/pll-chia-hackathon
PATH="$HOME/.opencode/bin:$PATH" "$HOME/pll-chia-venv/bin/python" loop.py --rtl rtl_gf180_snapshot --rounds 3 --model opencode/big-pickle --output results/agent_lab_final
"$HOME/pll-chia-venv/bin/python" scripts/summarize.py results/agent_lab_final/summary.json
```

The CHIA OpenCode node is configured for text-only answers, with its file,
shell and network tools denied. The simulator, run as a separate CHIA node,
handles all test execution. If a model cannot answer without built-in tools,
record that result and use a compatible model; do not grant the LLM access to
private PDK files or lab data to make the run pass.

## Fast failure guide

| What you see | Immediate action |
| --- | --- |
| `python3` or pip missing | Activate the lab's existing conda environment; if it truly lacks Python, follow `SERVER_NO_PYTHON.md` on another host. |
| GitHub clone fails | Extract the bundled `chia-source-16c35e9.tar.gz` as shown above; Python package installation still needs a package index or cached wheels. |
| `opencode` missing | Run the standalone OpenCode installer from its official site; Node/npm are not required. |
| Model request fails | Check outbound connectivity and credentials, then try another accessible OpenCode model. Do not interpret the failure as a hardware result. |
| `RAY OK` does not appear within 45 s | Check the Ray stderr and worker process policy; switch CHIA execution to another host if local Ray cannot start. |
| `check_source.py` fails | Inspect changed RTL and review each intended mutation; do not patch blindly to force a detection claim. |
| Smoke result is not `pass` | Read `results/smoke_lab/compile.log` and `sim.log`; verify both simulator compile and run executables exist. |
| No valid agent proposal | Open `results/agent_lab_first/proposal_0.txt` and `agent_logs/`; adjust the prompt/model, then rerun into a **new** output directory. |

Keep a photo or copy of the first failed command and its output. Subsequent
commands depend on that result; skipping a failed step obscures the cause.

`results/` is intentionally ignored by Git. After inspecting validity and
before publishing, stage a compact evidence folder:

```sh
cd ~/pll-chia-hackathon
"$HOME/pll-chia-venv/bin/python" scripts/prepare_release.py results/agent_lab_final --out release_results/final
git status --short
```

Review `release_results/final/` for credentials, absolute user paths, and
publication permission before committing it. Keep the complete raw run,
including agent logs, privately for audit. Do not present the old
`GF180_SMOKE_RESULTS.json` as a fresh server run.

## Optional, existing BC/TC/WC evidence

```sh
cd ~/stdcell-pll
for c in BC TC WC; do test -s "openroad/results/gf180/pll/$c/digital_pll.sdf" && echo "$c SDF OK" || echo "$c SDF MISSING"; done
grep -nE 'read_spef|write_sdf' openroad/scripts/gen_sdf.tcl
cd ~/stdcell-pll/sim
make tb_digital_pll_gate_questa CORNER=TC SIM_TIME=25ns > postlayout_TC_25ns.log 2>&1
```

The known old `gen_sdf.tcl` lacked `read_spef`: check the **current** server
version before claiming interconnect delays. A short 25 ns gate simulation is
only a setup check, not evidence of lock or all-corner robustness. Do not
overwrite existing post-layout logs or rerun PNR casually. The present CHIA
loop evaluates functional RTL tests; there is no implemented automatic
BC/TC/WC optimization loop yet.

## Submission gate

- CHIA/Ray actually ran with a model and produced a trace plus summary.
- Baseline and agent were measured on the same frozen RTL/mutant set; report
  original-pass and mutant detection counts honestly.
- Open-source release URL contains the running loop, instructions and real
  results; confirm disclosure permission for all code and files first.
- Four-page, two-column ACM/IEEE-style PDF describes method and measured
  results, with AI writing assistance acknowledged. Start from
  `paper/PAPER_DRAFT.md`; replace every `[FILL]` and render to PDF.
- Submit the PDF and release URL through the hackathon HotCRP form before
  **Sep 24, 2026 AoE = Sep 25, 2026 18:59 Vietnam time**. Leave buffer for
  upload and form entry; do not use the clock edge as the working deadline.

Sources: https://agentic-arch.org/hackathon.html#submission and
https://docs.chialoops.ai/ .
