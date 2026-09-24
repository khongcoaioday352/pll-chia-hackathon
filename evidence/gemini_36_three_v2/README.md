# Three-round CHIA/Gemini measurement

`summary.json` was copied as structured JSON from the lab command output
shared by the author on September 24, 2026. It records six tests (three fixed
baseline, three agent proposals) and four injected fault variants. The
published GF180 snapshot has SHA-256 values recorded in
`scripts/replay_summary.py`; these equal the hashes printed by the lab run.

This summary is a measured result, but the raw lab logs and model transcripts
are not yet included in this directory. The author retains the full run at
`results/gemini_36_three_v2` on the lab server. Do not represent this summary
as a complete archival copy of that run.

Recompute the simulator portion without a model API key, from the repository
root:

```sh
python3 scripts/replay_summary.py --rtl rtl_gf180_snapshot --output results/replay_v2
```

The four mutations were selected by the authors. Prompt goals were revised
during development after earlier attempts on this same suite. These results
measure detection of injected functional RTL faults under a behavioral ring
oscillator. They do not measure transistor PVT, post-layout timing, phase
noise, or defect coverage across arbitrary designs.
