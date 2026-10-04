#!/usr/bin/env python3
"""Rewrite both actor-owned hashes after target drift, in a disposable toy."""
import argparse
import json
from pathlib import Path
from toy_gate import digest, inventory

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("snapshot", type=Path)
args = parser.parse_args()
manifest = args.snapshot / "manifest.json"
data = json.loads(manifest.read_text())
data["files"] = inventory(Path(data["root"]))
raw = json.dumps(data, sort_keys=True).encode()
for name, body in (("manifest.json", raw), ("manifest.sha256", digest(raw).encode())):
    path = args.snapshot / name
    path.chmod(0o644)
    path.write_bytes(body)
    path.chmod(0o444)
