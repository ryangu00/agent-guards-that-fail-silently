#!/bin/bash
# Scheduled jobs must declare their own PATH; an interactive PATH is not evidence.
export PATH="${ADD_PATH:+$ADD_PATH:}/usr/bin:/bin:/usr/sbin:/sbin"
set -o pipefail
probe_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
: "${LOG:?Set LOG to a disposable log file}"
: "${MARKER:?Set MARKER to the progress marker}"
: "${DRIFT_CONFIG:?Set DRIFT_CONFIG to a JSON argv array}"
daily_failed=0
report_failure() { printf '%s\n' "$1" >> "$LOG"; printf '%s\n' "$1" >&2; daily_failed=1; }
daily_out=$("$probe_dir/env_probe.sh" "$@" 2>&1)
daily_rc=$?
if [ "$daily_rc" -eq 0 ] && [ "$daily_out" = PASS ]; then
    printf '%s\n' 'probe ok' >> "$LOG"
else
    report_failure "PROBE FAIL rc=$daily_rc out=[$daily_out]"
fi
if ! "${PYTHON:-python3}" - "$MARKER" "${MAX_DAYS:-3}" <<'PY'
import os, sys, time
try:
    age = time.time() - os.stat(sys.argv[1]).st_mtime
    sys.exit(0 if 0 <= age <= float(sys.argv[2]) * 86400 else 1)
except (OSError, ValueError):
    sys.exit(1)
PY
then
    report_failure 'MARKER FAIL: missing, stale or future marker'
fi
# Test the check's status directly; never the status of tail on its output.
if ! "${PYTHON:-python3}" - "$DRIFT_CONFIG" >> "$LOG" 2>&1 <<'PY'
import json, subprocess, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    argv = json.load(stream)
sys.exit(subprocess.run(argv, check=False).returncode)
PY
then
    report_failure 'DRIFT FAIL'
fi
exit "$daily_failed"
