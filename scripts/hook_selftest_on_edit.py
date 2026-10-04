#!/usr/bin/env python3
"""Warn after editing a hook; compilation and executed self-tests are required."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from hook_canary import compile_error, selftest_error


def check(path, hooks_dir):
    if not path or Path(path).suffix != ".py":
        return None
    path, directory = Path(path).resolve(), Path(hooks_dir).resolve()
    if directory not in path.parents:
        return None
    try:
        error = compile_error(path) or selftest_error(path, timeout=120)
        return f"[RED] {path.name}: {error}" if error else None
    except Exception as exc:
        return f"[RED] {path.name}: {type(exc).__name__}: {exc}"


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cases = {"red.py": 'import sys\nif "--selftest" in sys.argv: sys.exit(3)\n',
                 "green.py": 'import sys\nif "--selftest" in sys.argv: print("PASS")\n',
                 "fake.py": '# "--selftest" is mentioned only\n',
                 "bad.py": "def broken(:\n", "plain.py": "value = True\n"}
        for name, body in cases.items():
            (root / name).write_text(body)
            assert bool(check(root / name, root)) == (name in {"red.py", "fake.py", "bad.py"})
        assert check(root.parent / "outside.py", root) is None
    print("hook-selftest-on-edit selftest PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hooks-dir", default=os.environ.get("HOOKS_DIR"))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.hooks_dir:
        parser.error("--hooks-dir or HOOKS_DIR is required")
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
            return
        message = check(data.get("tool_input", {}).get("file_path"), args.hooks_dir)
    except Exception as exc:
        message = f"[RED] edit-time probe unreadable: {type(exc).__name__}"
    if message:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}))


if __name__ == "__main__":
    main()
