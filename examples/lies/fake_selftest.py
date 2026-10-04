#!/usr/bin/env python3
# A naive detector finds "--selftest" here; this branch never prints PASS.
import subprocess
import sys

if len(sys.argv) == 1:
    result = subprocess.run([sys.executable, __file__, "--selftest"], capture_output=True, text=True)
    print("naive: GREEN (flag in source and rc 0)")
    print("right: RED (no PASS)" if "PASS" not in result.stdout else "right: GREEN")
