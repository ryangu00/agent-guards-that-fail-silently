#!/usr/bin/env python3
"""Find literal-key mentions outside an explicit non-reader file allowlist.

This is a source-search heuristic, not proof that a consumer executes a read.
"""
import argparse
import ast
import json
from pathlib import Path
import re


def keys(value, prefix=""):
    for key, item in value.items():
        dotted = f"{prefix}.{key}" if prefix else key
        yield dotted
        if isinstance(item, dict):
            yield from keys(item, dotted)


def check(config, source, ignored):
    mentions = {}
    root = Path(source)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if path.suffix == ".py":
            tree = ast.parse(text)
            literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        else:
            literals = {match[1] for match in re.findall(r"(['\"])(.*?)\1", text)}
        mentions[path.relative_to(root).as_posix()] = literals
    result = []
    for dotted in keys(config):
        found = [name for name, literals in mentions.items()
                 if dotted in literals or dotted.rsplit(".", 1)[-1] in literals]
        readers = [name for name in found if name not in ignored]
        result.append({"key": dotted, "status": "has reader" if readers else "no reader",
                       "readers": readers, "allowlisted_only": bool(found) and not readers})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--ignore", nargs="*", default=[])
    args = parser.parse_args()
    result = check(json.loads(args.config.read_text()), args.source, set(args.ignore))
    for row in result:
        print(f"{row['key']}: {row['status']}" + (" (allowlisted mentions only)" if row["allowlisted_only"] else ""))
    raise SystemExit(int(any(row["status"] == "no reader" for row in result)))
