#!/bin/sh
exec "${PYTHON:-python3}" - <<'PY'
import subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    missing = Path(tmp) / "missing.json"
    result = subprocess.run([sys.executable, "-c", 'import json,sys; json.load(open(sys.argv[1])); print("REPLY")', str(missing)], capture_output=True, text=True)
    print("naive: GREEN (no metadata warning)" if "metadata warning" not in result.stderr else "naive: RED")
    print("right: RED (startup failed; no reply)" if result.returncode or result.stdout != "REPLY\n" else "right: GREEN")
PY
