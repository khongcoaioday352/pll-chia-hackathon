"""Stage reviewable CHIA/Gemini proposal provenance from a saved lab run.

This reads saved text; it never calls a model or simulator. The output is a
PRIVATE staging directory: review every file before voluntarily publishing it.
Hash matches establish consistency with the saved run, not provider attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.replay_summary import FROZEN_RTL_SHA256
from verify import RTL_FILES, validate

HIGH_RISK = re.compile(
    r"AIza[0-9A-Za-z_-]{20,}|github_pat_[0-9A-Za-z_]{20,}|"
    r"(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{20,}|"
    r"sk-[0-9A-Za-z_-]{20,}|"
    r"(?i:authorization|api[_-]?key|password|secret|bearer|access[_-]?token)"
    r"\s*(?:=|:)\s*[^\s]{8,}"
)
LAB_PATH = re.compile(r"/(?:home|workspace|mnt)/[^\s\"']+")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def extract_candidate(reply: str) -> dict:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", reply):
        try:
            value, _ = decoder.raw_decode(reply[match.start():])
            if isinstance(value, dict):
                return validate(value)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    raise ValueError("saved model reply has no valid test candidate")


def sanitize(text: str) -> tuple[str, dict]:
    if HIGH_RISK.search(text):
        raise ValueError("possible credential in transcript; no transcript was staged")
    cleaned, paths = LAB_PATH.subn("<REDACTED_LAB_PATH>", text)
    cleaned, emails = EMAIL.subn("<REDACTED_EMAIL>", cleaned)
    if HIGH_RISK.search(cleaned):
        raise ValueError("possible credential after redaction")
    return cleaned, {"lab_paths": paths, "emails": emails}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=pathlib.Path, required=True,
                    help="Original completed loop.py output, including prompt_*.txt/proposal_*.txt")
    ap.add_argument("--published", type=pathlib.Path,
                    default=pathlib.Path("evidence/gemini_36_three_v2/summary.json"))
    ap.add_argument("--rtl", type=pathlib.Path,
                    default=pathlib.Path("rtl_gf180_snapshot"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("output must be new or empty")
    public_bytes = args.published.read_bytes()
    private_bytes = (args.run / "summary.json").read_bytes()
    public, private = json.loads(public_bytes), json.loads(private_bytes)
    pinned = {name: hashlib.sha256((args.rtl / name).read_bytes()).hexdigest()
              for name in RTL_FILES}
    if pinned != FROZEN_RTL_SHA256:
        ap.error("published RTL differs from pinned source")
    saved_original = args.run / "sources" / "original"
    if any(hashlib.sha256((saved_original / name).read_bytes()).hexdigest() != pinned[name]
           for name in RTL_FILES):
        ap.error("saved original-run RTL differs from published source")
    for key in ("model", "backend", "goal_profile", "rounds", "mutants",
                "baseline_detected", "agent_detected_union", "invalid_agent_proposals"):
        if public.get(key) != private.get(key):
            ap.error(f"published and saved summaries differ at {key}")
    names = {f"agent_{i}" for i in range(3)} | {f"baseline_{i}" for i in range(3)}
    if public.get("rounds") != 3 or set(public["tests"]) != names or set(private["tests"]) != names:
        ap.error("expected exactly three completed original agent and baseline rounds")
    for name in names:
        if public["tests"][name] != private["tests"][name]:
            ap.error(f"saved and published test results differ at {name}")

    # Complete privacy and provenance checks before writing any transcript.
    prepared = []
    for index in range(3):
        pair = []
        for kind in ("prompt", "proposal"):
            path = args.run / f"{kind}_{index}.txt"
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            if kind == "proposal" and extract_candidate(text) != public["tests"][f"agent_{index}"]["candidate"]:
                ap.error(f"raw agent proposal {index} differs from published candidate")
            safe, counts = sanitize(text)
            pair.append({"name": f"{kind}_{index}.txt", "safe": safe,
                         "raw_sha256": digest(raw), "safe_sha256": digest(safe.encode()),
                         "redactions": counts})
        prepared.extend(pair)
    out.mkdir(parents=True, exist_ok=True)
    for row in prepared:
        (out / row["name"]).write_text(row["safe"])
    manifest = {"classification": "local private stage for manual publication review",
                "limitations": ["saved file hashes do not independently attest a model provider",
                                "automatic redaction is incomplete; manually inspect before publishing"],
                "published_summary_sha256": digest(public_bytes),
                "saved_summary_sha256": digest(private_bytes),
                "rtl_sha256": pinned,
                "checked_agents": 3,
                "files": [{key: row[key] for key in ("name", "raw_sha256", "safe_sha256", "redactions")}
                          for row in prepared]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Provenance: 3/3 proposals match the published candidate JSON and saved scoring matrix")
    print("PRIVATE STAGE: manually inspect all six text files before any public upload |", out)


if __name__ == "__main__":
    main()
