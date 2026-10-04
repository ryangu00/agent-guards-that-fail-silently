#!/usr/bin/env python3
"""Fixed registry plus recomputed closeout; still a same-identity mistake-catcher."""
import argparse
from pathlib import Path
from toy_gate import check, load_registry, snapshot

REGISTRY = Path(__file__).resolve().with_name("registry.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "check", "closeout"))
    parser.add_argument("--snap")
    args = parser.parse_args()
    try:
        if args.action == "snapshot":
            print(snapshot(*load_registry(REGISTRY)))
            return 0
        if not args.snap:
            parser.error("--snap is required")
        ok = check(REGISTRY, args.snap)
        print("PASS" if ok else "FAIL")
        return int(not ok)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
