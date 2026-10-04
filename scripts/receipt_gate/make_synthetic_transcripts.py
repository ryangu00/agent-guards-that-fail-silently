#!/usr/bin/env python3
"""Generate independent synthetic events, never copied from real sessions."""
import argparse
import json
from pathlib import Path


def transcript(calls):
    rows = []
    for index, (name, inp, output, error) in enumerate(calls):
        identifier = f"synthetic-{index}"
        rows.append({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": identifier, "name": name, "input": inp}]}})
        if output is not None:
            rows.append({"message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": identifier, "is_error": error, "content": output}]}})
    return "\n".join(json.dumps(row) for row in rows) + "\n"


def project():
    # Invented logical paths in transcript data; these files are never accessed.
    anchor = Path("/synthetic-project")  # fixed fake root, never accessed
    return [("Write", {"file_path": str(anchor / name), "new_string": "synthetic"}, "written", False)
            for name in ("a.py", "b.py", "c.py")]


def generate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    clean = project() + [("Write", {"file_path": "WORKLOG.md", "new_string": "Synthetic record."}, "written", False),
                         ("Bash", {"command": "receipt-tool --slug a"}, "receipt-tool: OK slug=a", False)]
    for name, calls in (("project-fire", project()), ("project-clean", clean),
                        ("research-fire", [("WebSearch", {"query": "synthetic"}, "result", False)] * 8)):
        (directory / (name + ".jsonl")).write_text(transcript(calls))
    notes = directory / "notes"
    notes.mkdir(exist_ok=True)
    (notes / "a.md").write_text("Synthetic note.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    generate(parser.parse_args().directory)
