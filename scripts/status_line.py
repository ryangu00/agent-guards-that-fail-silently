#!/usr/bin/env python3
"""Display red, stale, missing and unreadable status; keep healthy status quiet."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def status_lines(files, hours=72, now=None):
    now = now or datetime.now(timezone.utc)
    lines = []
    for name, path in files.items():
        try:
            record = json.loads(Path(path).read_text().strip().splitlines()[-1])
            if type(record["ok"]) is not bool:
                raise ValueError("ok must be boolean")
            ts = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
            if ts > now:
                raise ValueError("future timestamp")
            if not record["ok"]:
                lines.append(f"[RED] {name}")
            elif now - ts > timedelta(hours=hours):
                lines.append(f"[STALE] {name}")
        except FileNotFoundError:
            lines.append(f"[MISSING] {name}")
        except Exception:
            lines.append(f"[UNREADABLE] {name}")
    return lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--hours", type=float, default=72)
    args = parser.parse_args()
    for line in status_lines({Path(p).name: p for p in args.files}, args.hours):
        print(line)
