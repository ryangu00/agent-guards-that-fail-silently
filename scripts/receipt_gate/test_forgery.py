#!/usr/bin/env python3
"""Run the synthetic forgery table and complete receipt verdict checks."""
from pathlib import Path
import unittest

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[2] / "tests"), pattern="test_receipts.py")
    result = unittest.TextTestRunner().run(suite)
    if result.wasSuccessful():
        print("receipt forgery tests PASS")
    raise SystemExit(int(not result.wasSuccessful()))
