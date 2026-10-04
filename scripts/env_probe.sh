#!/bin/bash
# Resolve Python before cleaning PATH; no external timeout program is required.
probe_python="${PYTHON:-$(command -v python3)}"
exec "$probe_python" - "$@" <<'PY'
import os, subprocess, sys
expected = os.environ.get("EXPECT", "PONG")
path = "/usr/bin:/bin:/usr/sbin:/sbin"
if os.environ.get("ADD_PATH"):
    path = os.environ["ADD_PATH"] + ":" + path
try:
    result = subprocess.run(sys.argv[1:], env={"PATH": path}, stdin=subprocess.DEVNULL,
                            text=True, capture_output=True, timeout=float(os.environ.get("TIMEOUT", 90)))
    rc, out = result.returncode, result.stdout.rstrip("\n")
except FileNotFoundError:
    rc, out = 127, ""
except subprocess.TimeoutExpired:
    rc, out = 124, ""
except (OSError, ValueError) as exc:
    rc, out = 1, type(exc).__name__
if rc == 0 and out == expected:
    print("PASS")
    sys.exit(0)
print(f"FAIL rc={rc} out=[{out[:80]}]")
sys.exit(1)
PY
