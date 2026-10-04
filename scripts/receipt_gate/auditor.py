#!/usr/bin/env python3
"""Recompute synthetic transcript verdicts and check notes independently."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from core import parse_transcript_events, verdict


def note_exists(directory, slug):
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", slug):
        return False
    root = Path(directory).resolve()
    path = (root / (slug + ".md")).resolve()
    return root in path.parents and path.is_file() and bool(path.read_text().strip())


def audit(paths, exists):
    debts, skipped, scanned, last_error = [], 0, 0, ""
    for path in sorted(map(Path, paths)):
        if path.name.startswith("agent-"):
            skipped += 1
            continue
        scanned += 1
        try:
            result = verdict(parse_transcript_events(path))
            bad = []
            for receipt in result.receipts:
                try:
                    if not exists(receipt["slug"]):
                        bad.append(receipt["slug"])
                except Exception as exc:
                    last_error = f"existence check: {type(exc).__name__}"
                    bad.append(receipt["slug"])
            if result.state == "fire" or bad:
                debts.append({"file": path.name, **asdict(result), "invalid_notes": bad})
        except Exception as exc:
            last_error = f"transcript: {type(exc).__name__}"
            debts.append({"file": path.name, "error": last_error})
    return debts, {"ts": datetime.now(timezone.utc).isoformat(), "scanned": scanned,
                   "debts": len(debts), "excluded_agents": skipped, "last_error": last_error}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcripts", type=Path)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    debts, heartbeat = audit(args.transcripts.rglob("*.jsonl"), lambda slug: note_exists(args.notes, slug))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "debt.jsonl").write_text("".join(json.dumps(row) + "\n" for row in debts))
    (args.output / "debt.md").write_text("# Synthetic debt\n\n" + "\n".join(f"- {row['file']}: {row.get('missing', row.get('error'))}" for row in debts) + "\n")
    with (args.output / "heartbeat.jsonl").open("a") as stream:
        stream.write(json.dumps(heartbeat) + "\n")
    print(json.dumps(heartbeat, sort_keys=True))
