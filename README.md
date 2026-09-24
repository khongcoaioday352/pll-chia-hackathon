# PLLGuard: agent-generated functional verification of a GF180 digital PLL

**Hackathon artifact:** a CHIA/Gemini loop proposes bounded functional RTL tests; an Icarus Verilog simulator validates them against the unmodified source and injected fault variants. The publicly archived [primary summary](evidence/gemini_36_three_v2/summary.json), [supplementary results](evidence/supplementary_console_summary.json), [seven-fault per-test matrix](evidence/stress_public_replay_matrix.json), exact [GF180 RTL snapshot](rtl_gf180_snapshot/), and [API-free replay](scripts/replay_summary.py) permit inspection without additional model credits.

**Measured lab result:** three valid agent-generated tests detect 4/4 selected faults; three fixed tests detect 1/4. Replaying all six saved tests on the lab host produced six `MATCH` rows and `Replay: PASS`. A post hoc seven-fault stress suite gives 5/7 versus 2/7; the behavioral delay sweep gives 4/4 versus 3/4, 1/4, and 3/4 at 90%, 100%, and 110% delay multipliers. These are functional simulation results on one design, with model goals tuned during prior development on the initial four faults; they are not blind generalization, transistor PVT, or post-layout verification.

See `TOP10_STRATEGY.md` for the stronger post-layout validation target and
the evidence required before making that claim.
See `PVT_OPTION.md` for the more ambitious PVT design direction and the
multi-corner baseline/variant measurements required before using its title.
If the lab server has Python, follow `LAB_RUNBOOK.md` for a single-host run.
Otherwise see `SERVER_NO_PYTHON.md` for the Codespaces/EDA split.
`chia-source-16c35e9.tar.gz` is a pinned copy of the official CHIA source
(license included) for a lab host that can reach GitLab and Python packages
but cannot reach GitHub. It does not bundle pip dependencies.

This repository implements a CHIA loop that asks an AI agent to author new
black-box stimulus and assertions for a digital PLL. A simulator, not the
agent, scores each experiment. The mutation scores were hidden during the recorded three-turn model run,
although earlier development informed the prompt goals. The measured outcome is mutation detection relative to a fixed baseline.

## Status

The CHIA/Gemini loop has run end-to-end on the lab GF180 RTL. In a
three-round run on September 24, 2026, three agent-authored tests passed the
unmodified RTL and detected all four injected fault variants; a fixed,
three-test baseline detected one of four. Replaying these same frozen tests
with behavioral oscillator-delay parameters scaled to 90%, 100%, and 110%
yielded agent detection of 4/4 in each setting and baseline detection of
3/4, 1/4, and 3/4, respectively. These numbers come from the author's lab run. The exact tested RTL snapshot
and the machine-readable three-round summary are published under
`rtl_gf180_snapshot/` and `evidence/gemini_36_three_v2/`. Raw model transcripts
and full simulator logs remain on the lab host pending a privacy review.
The API-free replay below can check the deterministic simulator outcomes.

The four faults are deliberately injected variants, not bugs discovered in
the upstream design. The prompt goals were adjusted during development after
earlier trials on this suite, so these results do not measure generalization
to unseen faults. The delay sweep changes the FUNCTIONAL behavioral model,
not transistor PVT corners, gate-level timing, jitter, or post-layout lock.
The upstream design itself describes its control as frequency locking.

The earlier direct model and handwritten smoke tests are recorded separately
in `MODEL_SMOKE_RESULTS.json`, `SMOKE_RESULTS.json`, and
`GF180_SMOKE_RESULTS.json`; they are not the CHIA/Gemini result above.

## Inputs and constraints

`rtl/` contains a public Efabless Caravel PLL snapshot for local development
(Apache-2.0, commit `27cbe49c90ba5362ad52c9968dd98e035c30c74f`).
`rtl_gf180_snapshot/` contains the exact three GF180 RTL files used in the
September 24 lab run (source repository HEAD `7c54f7c`) plus a simulation-only
clock-buffer shim. Source SHA-256 is checked by `scripts/replay_summary.py`.
`reference_tb/tb_digital_pll.v` preserves the author's existing testbench as
a separate input; it is not the fixed three-test comparison baseline.
Never publish a private 65 nm PDK, proprietary cell models, or credentials.

The simulator adapter expects three modules: `digital_pll`,
`digital_pll_controller`, and `ring_osc2x13`. It uses the `FUNCTIONAL` ring
oscillator model and an identity clock-buffer shim. The sample tests are
functional checks, not physical jitter or post-layout timing claims.
The RTL header describes this design as technically a frequency-locked loop;
the project name follows its published `digital_pll` module name. The paper
should state this distinction explicitly.

## API-free replay of the measured result

From the repository root, with CHIA-independent Python and Icarus Verilog (or
Verilator) installed:

```sh
python3 scripts/replay_summary.py --rtl rtl_gf180_snapshot --output results/replay_v2
```

This executes all saved baseline and agent candidates against the unmodified
RTL and the original four fault variants. Six `MATCH` rows and `Replay: PASS`
are required before claiming an independent reproduction. No Gemini key is
used. `scripts/delay_sweep.py` and `scripts/stress_suite.py` evaluate the
supplementary experiments from a completed lab run and are documented as
behavioral sensitivity and post hoc stress tests. To reproduce the seven-fault
post hoc stress suite from the publicly archived candidate programs, without
Gemini credits or private run files, execute:

```sh
python3 scripts/stress_suite.py --rtl rtl_gf180_snapshot --run evidence/gemini_36_three_v2 --expected-aggregates evidence/supplementary_console_summary.json --expected-matrix evidence/stress_public_replay_matrix.json --output results/stress_matrix_audit_v1
```

A matching run prints `Published stress summary: MATCH` and writes a full
per-candidate result matrix to `results/stress_public_replay_v1/summary.json`.
The September 24 lab run printed `Published stress summary: MATCH`, with three
valid tests in each group, 5/7 versus 2/7 detected and no compile/tool errors.
Its per-test status matrix is archived publicly from the author's console output;
the added `--expected-matrix` check must still be run on the lab host to establish
a machine-checked match to the published matrix. Full raw simulation logs remain
on the lab server pending a privacy review. This is a deterministic replay of tests against a post hoc
fault suite, not an independent new agent-generation run.

## Run

Requires Python >=3.10, CHIA (`pip install -e /path/to/chia`), Icarus Verilog
or Verilator, and a CHIA-supported AI model backend. The default AI backend is
CHIA's OpenCode node; install its CLI (`npm install -g opencode-ai`) and test
the chosen model first. The public `opencode/big-pickle` model answered a
connectivity check during development; availability may change.

```
python3 verify.py --rtl rtl --candidate examples/disable.json --output results/disable
python3 verify.py --rtl rtl_gf180_snapshot --candidate examples/agent_program.json --output results/agent_program
python3 loop.py --rtl rtl_gf180_snapshot --rounds 3 --model opencode/big-pickle --output results/agent
```

### Gemini API Free tier on the lab server

If OpenCode Free rejects CHIA's custom agent, use Google's Gemini API through
CHIA's OpenAI-compatible backend. This does not use Google Cloud trial credits.
Confirm the key's project is Free tier in Google AI Studio. Never paste the key
into the repository, a command argument, screenshots, or issue logs.

```sh
cd ~/pll-chia-hackathon
"$HOME/pll-chia-venv/bin/python" -m pip install openai
read -rsp 'Gemini API key: ' GEMINI_API_KEY
echo
export GEMINI_API_KEY
"$HOME/pll-chia-venv/bin/python" loop.py --backend gemini --rtl rtl_gf180_snapshot --rounds 1 --output results/gemini_first
unset GEMINI_API_KEY
```

`read -rsp` hides the key while typing; export it in the same shell that
starts Ray. Results and agent logs belong under `results/` and are ignored by
Git until reviewed. This backend uses Google's official OpenAI-compatible
endpoint with `gemini-3.6-flash` by default; `--model` selects another available
Gemini model. Successful authentication and model availability must be checked
on the actual lab server.

The first two commands verify the simulator and the generated-test compiler
without AI. The last runs the CHIA agent loop. `--model` can name another
OpenCode model.
For Ray launched externally use `--ray-address auto`; local Ray is the default.
If your system only provides Verilator as a Python wheel, add its bundled
`verilator/bin` directory to `PATH` before executing these commands.

An agent test is JSON with `ref_period_ns` and up to 16 ordered `steps`:
`set` changes visible input ports; `wait` advances time; `measure` records
output rising edges in a bounded time window; `assert` compares measured
counts with another measurement or constant. `gt_by` / `lt_by` assertions
also accept a `margin` to demand a minimum difference in edge counts.
`verify.py` validates the JSON
and builds a standalone Verilog testbench; it never executes arbitrary text
as shell or Python code. `examples/agent_program.json` demonstrates this
format. The fixed baseline contains up to three predeclared tests, matching
the requested number of agent proposals.

The loop records prompts, agent proposals, baseline and mutant outcomes, hashes, logs,
and a summary JSON. A mutant counts as detected only when the same test passes
the original RTL and fails the mutant. Compile errors and timeouts are recorded
separately. For a genuinely independent future test, keep new fault identities and outcomes unseen during all prompt development.

## Evaluation protocol

1. Check that each mutation compiles and causes a relevant behavioral change.
2. Freeze the baseline test and mutant set before running the agent.
3. Give the agent only its original RTL observations and the interface spec.
4. Compare baseline and agent with identical mutant set and simulation budget.
5. Report detected/valid mutants, original RTL false positives, run time, and
   failed agent proposals; keep all unfiltered per-run logs.

## GitHub Codespaces quick start

Run everything in this section **in Codespaces**, never on the lab EDA server.

Create a **personal** GitHub repository, upload this project, open its
`Code` → `Codespaces` tab, and start a 2-core machine. In its terminal,
run these commands one line at a time (the second only if Verilator is
missing):

```
python3 --version
sudo apt-get update
sudo apt-get install -y verilator build-essential
python3 -m venv .venv
git clone https://github.com/ucb-bar/chia.git vendor/chia
.venv/bin/pip install -e vendor/chia
npm install --prefix "$HOME/.local" opencode-ai
PATH="$HOME/.local/node_modules/.bin:$PATH" opencode run --model opencode/big-pickle 'Reply READY'
.venv/bin/python verify.py --rtl rtl_gf180_snapshot --candidate examples/agent_program.json --output results/agent_program
timeout 45s .venv/bin/python -c 'import ray; ray.init(num_cpus=1, include_dashboard=False); print("RAY OK"); ray.shutdown()'
PATH="$HOME/.local/node_modules/.bin:$PATH" .venv/bin/python loop.py --rtl rtl_gf180_snapshot --rounds 3 --model opencode/big-pickle --output results/agent
```

If the Codespaces Python cannot install current CHIA, create an environment
with Python 3.10.19 and retry. Install errors, model access, Ray startup,
and results must all be checked in the actual Codespace; this environment
has not provided a successful end-to-end Ray run. Keep the final runnable
results in version control. Do not commit model secrets or private PDK files.

The published competition artifact should contain real results generated by
this flow and a four-page PDF. This README alone is not a submission.
