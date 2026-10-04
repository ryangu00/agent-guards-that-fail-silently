#!/usr/bin/env python3
"""Invented English-only label; this is not a privacy detector."""
import argparse
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check-only", action="store_true", required=True)
parser.parse_args()
blocked = "DEMO-BLOCK" in sys.stdin.read()
print("BLOCK" if blocked else "ALLOW")
raise SystemExit(int(blocked))
