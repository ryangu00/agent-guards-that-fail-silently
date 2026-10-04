#!/bin/bash
# rc 0 means paused (including failure); rc 1 means healthy and not paused.
state_path="${1:-${STATE:-}}"
pause_python="${PYTHON:-python3}"
if ! command -v "$pause_python" >/dev/null 2>&1; then
    echo 'paused: Python missing' >&2
    exit 0
fi
"$pause_python" - "$state_path" <<'PY'
import datetime, json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        data = json.load(stream)
    ts = datetime.datetime.fromisoformat(data["_ts"].replace("Z", "+00:00"))
    age = datetime.datetime.now(datetime.timezone.utc) - ts
    if age.total_seconds() < 0:
        raise ValueError("future timestamp")
    if age > datetime.timedelta(days=3):
        print("paused: stale state", file=sys.stderr)
        sys.exit(0)
    if type(data["paused"]) is not bool:
        raise ValueError("paused must be boolean")
    if data["paused"]:
        print("paused: requested", file=sys.stderr)
    sys.exit(0 if data["paused"] else 1)
except FileNotFoundError:
    print("paused: missing state", file=sys.stderr)
except Exception as exc:
    print(f"paused: unreadable state ({type(exc).__name__})", file=sys.stderr)
PY
pause_rc=$?
if [ "$pause_rc" -ne 0 ] && [ "$pause_rc" -ne 1 ]; then
    echo 'paused: state reader failed' >&2
    exit 0
fi
exit "$pause_rc"
