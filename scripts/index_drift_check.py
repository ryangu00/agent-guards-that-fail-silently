#!/usr/bin/env python3
"""Check index coverage, the uncovered-count claim, and loaded-index byte caps."""
import argparse
from pathlib import Path
import re


def check(directory, indexes, claim_regex, max_bytes=24000, max_line_bytes=600, fix=False):
    root = Path(directory)
    files = {p.name for p in root.glob("*.md")} - set(indexes)
    texts = {name: (root / name).read_text(encoding="utf-8") for name in indexes}
    links = {name: {p for p in re.findall(r"\]\(([^)]+\.md)\)", text)
                    if "/" not in p} - set(indexes) for name, text in texts.items()}
    main = indexes[0]
    orphans = files - links[main]
    true_orphans = files - set().union(*links.values())
    text = texts[main]
    match = re.search(claim_regex, text)
    claim = int(match.group(1)) if match else None
    if fix and match and claim != len(orphans):
        text = text[:match.start(1)] + str(len(orphans)) + text[match.end(1):]
        (root / main).write_text(text, encoding="utf-8")
        claim = len(orphans)
    errors = []
    if true_orphans:
        errors.append(f"true_orphans={len(true_orphans)}")
    if claim != len(orphans):
        errors.append(f"claim {claim} != {len(orphans)}")
    if len(text.encode()) > max_bytes:
        errors.append(f"size exceeds {max_bytes} bytes")
    if any(len(line.encode()) > max_line_bytes for line in text.splitlines()):
        errors.append(f"line exceeds {max_line_bytes} bytes")
    warnings = [f"dead links in {name}: {', '.join(sorted(targets - files))}"
                for name, targets in links.items() if targets - files]
    return {"orphans": len(orphans), "true_orphans": len(true_orphans), "claim": claim,
            "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--indexes", nargs="+", required=True)
    parser.add_argument("--claim-regex", default=r"(\d+) files are not in this index")
    parser.add_argument("--max-bytes", type=int, default=24000)
    parser.add_argument("--max-line-bytes", type=int, default=600)
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    try:
        result = check(args.directory, args.indexes, args.claim_regex, args.max_bytes, args.max_line_bytes, args.fix)
    except Exception as exc:
        print(f"FAIL: index unreadable: {type(exc).__name__}")
        return 1
    print(" ".join(f"{key}={result[key]}" for key in ("orphans", "true_orphans", "claim")))
    for warning in result["warnings"]:
        print(f"warn: {warning}")
    for error in result["errors"]:
        print(f"FAIL: {error}")
    if not result["errors"]:
        print("ok")
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
