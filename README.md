# PLLGuard: agent-generated functional verification of a GF180 digital PLL

**Hackathon artifact:** a CHIA/Gemini loop proposes bounded functional RTL tests; an Icarus Verilog simulator validates them against the unmodified source and injected fault variants. The publicly archived [primary summary](evidence/gemini_36_three_v2/summary.json), [supplementary results](evidence/supplementary_console_summary.json), [seven-fault per-test matrix](evidence/stress_public_replay_matrix.json), exact [GF180 RTL snapshot](rtl_gf180_snapshot/), and [API-free replay](scripts/replay_summary.py) permit inspection without additional model credits.

**Measured lab result:** three valid agent-generated tests detect 4/4 selected faults; three fixed tests detect 1/4. Replaying all six saved tests on the lab host produced six `MATCH` rows and `Replay: PASS`. A post hoc seven-fault stress suite gives 5/7 versus 2/7; the behavioral delay sweep gives 4/4 versus 3/4, 1/4, and 3/4 at 90%, 100%, and 110% delay multipliers. These are functional simulation results on one design, with model goals tuned during prior development on the initial four faults; they are not blind generalization, transistor PVT, or post-layout verification.

**Comparison budget audit:** three passing agent candidates generate 7,260 ns of nominal simulated stimulus on the unmodified RTL; three passing fixed-baseline candidates generate 5,710 ns (agent/baseline 1.2715). See [per-test budget evidence](evidence/test_budget_audit.json) and reproduce without Gemini or a simulator using `python3 scripts/audit_test_budget.py --output results/test_budget_audit.json`. The script regenerates each Verilog testbench from its frozen JSON and audits its delays. Equal candidate count is not equal simulated time, CPU time, or strength; the 4/4 versus 1/4 comparison is **not time-matched**.

**Matched-time follow-up:** after extending only the three fixed-baseline
observation windows, both groups have 7,260 ns of nominal simulated stimulus
on the passing original RTL. The lab run still reports 4/4 versus 1/4 on four
primary faults and 5/7 versus 2/7 on seven post hoc stress faults. Its full
[per-test matrix](evidence/time_matched_public_replay_matrix.json) was
compared against the author's saved lab result: `MATCH (78 status cells
checked)`. The [one-command offline demo](scripts/run_offline_demo.py) also
reported `Published evidence: VERIFIED` on the lab host. These are
reproductions and a post hoc sensitivity check, not independent new agent
proposals. The full raw simulator logs remain on the lab server.

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

## One-command offline demo

Reviewers can verify all public deterministic evidence from a clean checkout
with Python and Icarus Verilog, without a Gemini key, Ray, or a CHIA install:

```sh
python3 scripts/run_offline_demo.py --rtl rtl_gf180_snapshot --output results/offline_demo_v1
```

This checks the pinned source, audits the test budget, replays all six frozen
agent/baseline candidates on the four primary injected faults, matches the
published seven-fault aggregate and per-test status matrix, and runs the
**human-authored** adequacy control for the two missed faults. A successful
run prints `Published evidence: VERIFIED` and writes `manifest.json` with
input hashes, step status, and output hashes. It replays prior proposals;
it never creates fresh model output or reclassifies the human test as an agent
result. To additionally measure the post hoc time-matched baseline, pass
`--include-time-matched` and inspect its result separately.

## Independent clean-host replay on GitHub Actions

The [reproduction workflow](.github/workflows/reproduce.yml) installs Icarus
Verilog on Ubuntu and runs the offline demo with `--include-time-matched`.
It saves the manifest and simulator logs as a short-lived workflow artifact.
You can start it under **Actions → Reproduce PLLGuard evidence → Run workflow**
if the push that added it did not start a run automatically. A passing workflow
would verify portability on that GitHub runner; the author's lab results and
the already reported 78-cell saved-matrix audit are separate observations.
Do not describe this workflow as successful until its run is green.

## Post hoc time-matched baseline check (author-reported lab result)

The first comparison matches the number of candidates (3 versus 3) but the
agent's generated tests run for 7,260 simulated ns on the passing original RTL
versus 5,710 ns for the fixed baseline. To check this potential confound,
`scripts/time_matched_baseline.py` changes **only** the three baseline observe
windows to 595, 580 and 800 ns; each then matches a frozen agent test's nominal
simulated duration (1,220, 1,220 and 4,820 ns respectively). It reruns all six
candidates against the same four primary and seven post hoc source variants.
Run on a server with Icarus Verilog using an empty output directory:

```sh
python3 scripts/time_matched_baseline.py --rtl rtl_gf180_snapshot --summary evidence/gemini_36_three_v2/summary.json --expected-aggregates evidence/time_matched_console_summary.json --expected-matrix evidence/time_matched_public_replay_matrix.json --output results/time_matched_baseline_replay_v2
```

The author's lab run reported three valid tests in each group, with **4/4
versus 1/4** on the primary faults and **5/7 versus 2/7** on the post hoc
stress set; tool/compile errors: zero. The counts did not change after matching
nominal simulated time. See the [author-reported aggregate with provenance](evidence/time_matched_console_summary.json).
The author's [per-test status matrix](evidence/time_matched_public_replay_matrix.json)
is now archived alongside the aggregate. All six tests retained the same
original/fault pass/fail statuses as the previously published non-matched run
on both suites; this is a transcription from lab console output, not an
independent model run. Re-execute the command above and require both
`Author-reported aggregate replay: MATCH` and
`Published matched-time per-test matrix: MATCH`. Raw simulator logs remain on
the lab host pending review.

If you already ran `results/offline_demo_final_v1` before the public matched-time
matrix was added, compare its saved JSON without repeating any simulation:

```sh
python3 scripts/audit_saved_time_matched.py --run results/offline_demo_final_v1/time_matched/summary.json --expected evidence/time_matched_public_replay_matrix.json --output results/offline_demo_final_v1/saved_matrix_audit.json
```

The expected check is `Saved time-matched matrix: MATCH (78 status cells
checked)`. This verifies the stored result against the public transcription;
it does not constitute a second simulator run.

This is a **post hoc sensitivity check** planned after seeing the original
results. It matches simulated nanoseconds, not CPU cost, oracle strength, or
statistical independence. The headline primary and stress measurements above
continue to refer to the original fixed baseline.

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
per-candidate result matrix to `results/stress_matrix_audit_v1/summary.json`.
The September 24 lab run printed `Published stress summary: MATCH`, with three
valid tests in each group, 5/7 versus 2/7 detected and no compile/tool errors.
The subsequent lab replay also printed `Published per-test matrix: MATCH`,
validating each recorded original/fault status against the archived
[per-test matrix](evidence/stress_public_replay_matrix.json). Full raw simulation
logs remain on the lab server pending a privacy review. This is a deterministic replay of tests against a post hoc
fault suite, not an independent new agent-generation run.

### Check whether the missed faults are observable

The frozen agent suite missed reset and output phase 1. A **human-authored,
post hoc** candidate in `examples/phase1_reset_program.json` tests those two
properties. To check that the test language can detect both injected faults,
without model credits, run:

```sh
python3 scripts/check_fault_adequacy.py --rtl rtl_gf180_snapshot --output results/fault_adequacy_v1
```

The lab run reported `original: pass`, `resetb_bypassed: fail` and
`phase1_held_low: fail`: `Both missed faults detectable: PASS`. This human
control shows the language can expose both misses, **without increasing the
agent's 5/7**. The console-provenance record is in
[evidence/fault_adequacy_and_adaptive_replay.json](evidence/fault_adequacy_and_adaptive_replay.json).

## Experimental feedback-driven extension (not part of the measured result)

`scripts/adaptive_experiment.py` adds a separate CHIA experiment. It feeds
per-round results from the four original *development* fault variants back to
the model and scores the seven supplementary *evaluation* variants only after
all agent proposals are fixed. The evaluation source variants do not exist on
disk during proposal generation. Those seven definitions were created after
the earlier PLLGuard experiments and were already known to the developers;
this separation within a new run **does not make the evaluation historically
blind**. The third round is explicitly guided toward reset during operation
and clockp[1], based on the already observed misses; this is guided coverage
planning rather than autonomous discovery of those properties. Do not treat
this script as an improved measured result until a fresh model run and a
separate baseline have actually finished.

First audit the orchestration without an API call, using the publicly saved
three candidates. This is an infrastructure replay and must reproduce the
previous status vectors, rather than being described as a new agent result:

```sh
python3 scripts/adaptive_experiment.py --rtl rtl_gf180_snapshot --proposal-summary evidence/gemini_36_three_v2/summary.json --expected-evaluation evidence/stress_public_replay_matrix.json --rounds 3 --output results/adaptive_offline_audit_v1
```

The September 24 lab audit reported `Offline primary statuses: MATCH` and
`Evaluation status matrix: MATCH`, reproducing 5/7 versus 2/7 using the saved
candidates. This checks wiring and data separation; no model proposal was
created in that run. See [console-provenance record](evidence/fault_adequacy_and_adaptive_replay.json).

Only after the offline audit succeeds and model quota is available, a new
adaptive CHIA run can use `--backend gemini --model gemini-3.6-flash` with a
new output directory. A failed model request is not a successful trial. Keep
new outputs private until the agent proposals, raw logs, baseline and source
hashes have been reviewed.

The first live attempt in `results/adaptive_live_v1` produced **one of the three**
requested agent tests before a backend error. Its displayed 2/7 agent versus
2/7 baseline counts are **not a comparable result**: the baseline had three
tests while the agent had one. This attempt is excluded from competition scores.
The updated script records `complete_comparable_run` and prints `INCOMPLETE RUN`
for failures before all requested model proposals are available. Once backend
access is restored, continue from the original proposal without repeating the
first paid model call (the seed and output must be different directories):

```sh
python3 scripts/adaptive_experiment.py --rtl rtl_gf180_snapshot --backend gemini --model gemini-3.6-flash --rounds 3 --seed-run results/adaptive_live_v1 --output results/adaptive_live_resumed_v1
```

The new run copies the original prompt and model response as authorship
records and repeats deterministic development scoring before asking the model
for turns 2 and 3. It reports seed provenance and only compares against three
baseline tests when `complete_comparable_run` is true. If the model fails again,
retain the new partial output and use it as the next `--seed-run`; always pick a
fresh `--output`. The evaluation faults do not appear in prompts or feedback,
but prior fault outcomes informed human goals. A completed run is guided, not
historically blind.

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
