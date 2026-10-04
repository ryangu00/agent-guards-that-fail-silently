#!/bin/sh
# Write an alternate caller-selected registry; snapshot/check can then bless it.
: "${1:?alternate registry path required}" "${2:?target required}" "${3:?state required}"
exec "${PYTHON:-python3}" - "$1" "$2" "$3" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"root": str(Path(sys.argv[2]).resolve()),
                                      "state": str(Path(sys.argv[3]).resolve())}))
PY
