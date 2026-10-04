#!/usr/bin/env python3
"""Deliberately forgeable teaching gate: local hashes are not trusted anchors."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink refused")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def load_registry(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text())
    return (path.parent / config["root"]).resolve(), (path.parent / config["state"]).resolve()


def snapshot(root, state):
    root, state = Path(root).resolve(), Path(state).resolve()
    if not root.is_dir() or state == root or root in state.parents:
        raise ValueError("state must be outside an existing target directory")
    identifier = uuid.uuid4().hex
    folder = state / identifier
    folder.mkdir(parents=True)
    data = json.dumps({"root": str(root), "files": inventory(root)}, sort_keys=True).encode()
    for name, body in (("manifest.json", data), ("manifest.sha256", digest(data).encode())):
        path = folder / name
        path.write_bytes(body)
        path.chmod(0o444)
    return identifier


def folder_for(state, identifier):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError("invalid snapshot id")
    folder = Path(state) / identifier
    if folder.is_symlink():
        raise ValueError("snapshot symlink refused")
    return folder


def check(registry, identifier):
    root, state = load_registry(registry)
    folder = folder_for(state, identifier)
    try:
        raw = (folder / "manifest.json").read_bytes()
        manifest = json.loads(raw)
        ok = ((folder / "manifest.sha256").read_text().strip() == digest(raw)
              and manifest["root"] == str(root) and manifest["files"] == inventory(root))
    except (OSError, ValueError, KeyError):
        ok = False
    # This artifact is writable by the actor: intentionally not authentication.
    (folder / f"check-{time.time_ns()}.json").write_text(json.dumps({"all_pass": ok}))
    return ok


def closeout(registry, identifier):
    _, state = load_registry(registry)
    results = sorted(folder_for(state, identifier).glob("check-*.json"))
    return bool(results) and json.loads(results[-1].read_text()).get("all_pass") is True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path(__file__).with_name("registry.json"))
    sub = parser.add_subparsers(dest="action", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("root", type=Path)
    snap.add_argument("state", type=Path)
    for name in ("check", "closeout"):
        sub.add_parser(name).add_argument("--snap", required=True)
    args = parser.parse_args()
    try:
        if args.action == "snapshot":
            print(snapshot(args.root, args.state))
            return 0
        ok = (check if args.action == "check" else closeout)(args.registry, args.snap)
        print("PASS" if ok else "FAIL")
        return int(not ok)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
