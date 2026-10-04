#!/usr/bin/env python3
"""Synthetic detector: show why a boolean cannot identify the deciding path."""
from dataclasses import dataclass
import re


@dataclass
class Result:
    hit: bool
    basis: str


def prefix():
    return "toy" + "-" + "key" + "-"


def canary(mixed=False):
    tail = ("aB7cD9eF2g" * 4) if mixed else "x" * 40
    return "pad " + prefix() + tail


def detect(text, boundary=False):
    pattern = (r"\b" if boundary else "") + re.escape(prefix()) + r"[A-Za-z0-9]{40}"
    if any("xxxxx" not in match.group() for match in re.finditer(pattern, text)):
        return Result(True, "main")
    if re.search(pattern, "".join(text.split())):
        return Result(True, "fallback")
    return Result(False, "none")


def allows_egress(body, test_value, boundary=False):
    if not detect(test_value, boundary).hit:
        return False  # Fail closed when the self-test fails.
    return not detect(body, boundary).hit


if __name__ == "__main__":
    old = detect(canary())
    print(f"boolean canary: {'GREEN' if old.hit else 'RED'}; path={old.basis}")
    print(f"path canary: {'GREEN' if old.hit and old.basis == 'main' else 'RED'}")
    print(f"boundary fix with old canary: clean egress allowed={allows_egress('clean prose', canary(), True)}")
    new = detect(canary(True), True)
    print(f"mixed canary: path={new.basis}; clean egress allowed={allows_egress('clean prose', canary(True), True)}")
