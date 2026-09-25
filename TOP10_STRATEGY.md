# PLLGuard: evidence-based Top 10 assessment

## Accurate project title

**PLLGuard: A CHIA Loop for Agent-Generated Functional Verification of a GF180 Digital PLL/FLL**

The source describes frequency locking. The current artifact measures functional
RTL test generation and injected-fault detection, not post-layout PLL lock,
physical PVT robustness, jitter, or an analog PLL design. Use a title claiming
post-layout validation only if an agent-authored candidate has actually been
replayed against a gate-level netlist and annotated SDF with archived results.

## Research question and agentic loop

Can a CHIA/Gemini agent author bounded, original-valid black-box PLL pin tests
that detect more injected functional faults than fixed tests under the same
number of proposals and a matched nominal simulator-time budget?

1. The agent writes a JSON program of pin inputs, timed observations, and assertions.
2. A CHIA/Ray simulator function compiles and executes it against pinned GF180 functional RTL.
3. Original-RTL results enter the agent's next-turn feedback; invalid original tests do not earn mutation detections.
4. After proposing tests, deterministic replay scores frozen candidates against fault variants; baseline candidates use the same evaluator.
5. The public artifact pins RTL hashes, candidate JSON, fault definitions, exact per-test statuses, and no-key replay commands.

The recorded initial four-fault comparison was influenced by earlier prompt
development. The seven-fault stress suite, reset follow-up, and control
matching were post hoc. Do not describe any of these as historically blind.

## Demonstrated results and limitations

| Evidence | What is supported now |
| --- | --- |
| Live CHIA/Gemini run | Three agent-authored initial candidates all passed original RTL and detected 4/4 selected faults; three fixed candidates detected 1/4. The later adaptive run generated three proposals, **two** original-valid, including the reset/phase candidate. |
| Post hoc seven-fault evaluation | Initial three agent candidates detected 5/7 versus 2/7 fixed tests. Adding the later valid agent reset test gives four original-valid candidates detecting 7/7 at 40 ns; four human/fixed time-matched controls detect 4/7. Both groups use 8,280 ns nominal total simulated time. This does not match CPU effort or assertion strength. |
| Period sensitivity | At 30 ns: both groups 3/4 valid and 4/7 detected. At 40 ns: 4/4 valid, agent 7/7 versus control 4/7. At 50 ns: 4/4 valid, agent 7/7 versus control 6/7. |
| Functional frequency feasibility | Static pinned-RTL derivation gives 168.919–214.041 MHz. Only 2/12 target divider/reference combinations in the author-authorized diagnostic fall inside the modeled range. A passing assertion is not proof of PLL lock. |
| Reproducibility and integrity | Earlier clean-host [GitHub Actions replay](https://github.com/khongcoaioday352/pll-chia-hackathon/actions/runs/36084650810) succeeded; public candidate and fault matrices can be replayed without an LLM key. The no-internal-DUT-force audit passed locally and on the author's lab host for seven published generated benches. The latest CI changes still need a confirmed successful run. |
| Physical validation | No published replay of an agent-authored program with routed netlist and annotated BC/TC/WC SDF. No measured jitter, PVT yield, or post-layout lock claim. |

Important source files: [live summary](evidence/gemini_36_three_v2/summary.json),
[combined four-test replay](scripts/combined_coverage.py),
[period matrix](evidence/combined_period_ci_matrix.json),
[oscillator envelope](evidence/behavioral_frequency_envelope.json),
[authorized lab diagnostic](evidence/controller_response_lab_console_2026-09-25.md),
[stimulus integrity audit](scripts/audit_stimulus_contract.py), and
[reproduction workflow](.github/workflows/reproduce.yml).
Raw model transcripts and full original simulator logs still live on the lab
server; curated candidate and per-test status evidence is public.

## Submission priorities

1. Confirm the latest GitHub Actions run and the two new static audits; resolve any real CI failure before release.
2. Preserve the scope above in the 4-page paper and provide the public repository/release URL. Mark AI writing assistance as required by the organizers.
3. If time and available lab inputs allow, obtain a genuine gate-level replay and archive setup, netlist/SDF provenance, observable result and failure cases. Otherwise omit post-layout claims.
4. Keep original prompts and agent provenance reviewable when safe to disclose; do not substitute curated status rows for full raw transcripts.

The official [hackathon rules](https://agentic-arch.org/hackathon.html)
request a four-page PDF and an open-sourced CHIA loop with results by Sep 24
AoE. Top 10 is a human ranking, not an automatic threshold from mutation score.
