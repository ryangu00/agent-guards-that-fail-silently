# Reproduce the failure shapes offline

These are synthetic demonstrations specified by the fact sheet. They exercise the public implementations, not historical sessions, the original database or a real scheduler. Run from the repository root. Python 3.10 or newer, Bash and grep must already be installed; no installer or network command is needed. A deployment's agent CLI, effective environment, credentials, protected identity and scheduler registration remain unknown until that deployment supplies them.

## Keep generated data disposable

```bash
mkdir -p .work
export TMPDIR="$PWD/.work"
export PYTHONDONTWRITEBYTECODE=1
probe_python="$(command -v python3)"
export PYTHON="$probe_python"
python3 -m unittest discover -s tests -v
```

The tests create temporary fixture directories beneath `TMPDIR`. They exercise failure and recovery; a deliberately rejected fixture is a passing assertion. Test counts and timing in terminal output describe this suite only, never the historical review rounds.

## Registration, self-tests and the check-only gate

```bash
python3 scripts/hook_canary.py --config configs/canary.example.json
python3 scripts/status_line.py .work/canary-alerts.jsonl
python3 scripts/hook_canary.py --self-test
python3 scripts/hook_selftest_on_edit.py --selftest
```

The configured example should print `hook-canary: clean`; healthy status prints nothing. Each canary run appends a JSON line. Its self-test prints `hook-canary self-test PASS` after running the fault-injection tests. Edit-time self-test prints `hook-selftest-on-edit selftest PASS`.

The config resolves paths relative to its own directory. `required_events` maps hook filenames to event lists; registration follows the original substring-match mechanism. `must_have_selftest` prevents removal of the test entry from becoming a skip. `commands` uses argv arrays, exact stdout, expected return code, timeout and optional clean environment; `{python}` selects the interpreter running the canary. With `clean_env`, the subprocess receives only the system PATH and encoding settings. `mirror_dir`, when configured, compares same-named files with the hook directory and ignores `.bak` names.

`gate_cases` supplies `label`, `body` and `want_block`. The adapter invokes `gate_argv` plus `--check-only`, passes a body on stdin and requires `BLOCK` with rc 1 or `ALLOW` with rc 0. The invented English label is not a real privacy rule. Exceptions and unexpected gate return codes are failures, not proof of intentional blocking.

`tests/test_canary.py` builds a temporary settings file and hooks directory. It independently removes registration, breaks syntax, makes a self-test exit 1, supplies a comment-only flag, deletes a required flag, replaces a symlink, and invokes a missing executable. Each specified injection must yield exactly its causal alert. Extra tests cover command timeout, lost execute permission, exact output, clean environment and a gate crash. Compilation failure suppresses the derivative self-test alert for that same required file.

To see the edit hook's host output:

```bash
mkdir -p .work/hooks
printf '%s\n' 'import sys' 'if "--selftest" in sys.argv: sys.exit(3)' > .work/hooks/red.py
python3 -c 'import json,pathlib; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":str(pathlib.Path(".work/hooks/red.py").resolve())}}))' \
  | python3 scripts/hook_selftest_on_edit.py --hooks-dir .work/hooks
```

The JSON contains `hookSpecificOutput.additionalContext` starting with `[RED]`. A file outside the configured hooks directory is ignored. This hook warns without blocking; it is not an installed host integration.

## Scheduler PATH: fail, then recover

```bash
mkdir -p .work/bin
printf '%s\n' '#!/bin/sh' 'echo PONG' > .work/bin/mytool
chmod +x .work/bin/mytool
PATH="$PWD/.work/bin:$PATH" mytool
EXPECT=PONG PYTHON="$probe_python" scripts/env_probe.sh mytool
ADD_PATH="$PWD/.work/bin" EXPECT=PONG PYTHON="$probe_python" scripts/env_probe.sh mytool
```

The interactive command prints `PONG`. The restricted probe exits 1 and prints `FAIL rc=127 out=[]`. The `ADD_PATH` run prints `PASS`. `TIMEOUT` controls the subprocess timeout; the default 90 seconds follows the original example. Timeout reports rc 124. Python supplies this timeout because a separate timeout executable may itself be absent. The command receives an empty environment plus its declared PATH and closed stdin; output comparison strips trailing newlines like shell command substitution.

Exercise the daily wrapper with a real check rather than a pipeline tail:

```bash
touch .work/marker
python3 - <<'PY'
import json, pathlib, sys
root = pathlib.Path('.work/index')
root.mkdir(exist_ok=True)
(root / 'INDEX.md').write_text('0 files are not in this index\n')
(root / 'ARCHIVE.md').write_text('')
pathlib.Path('.work/drift-command.json').write_text(json.dumps([
    sys.executable, 'scripts/index_drift_check.py', str(root),
    '--indexes', 'INDEX.md', 'ARCHIVE.md']))
PY
env -i PYTHON="$probe_python" LOG="$PWD/.work/daily.log" \
  MARKER="$PWD/.work/marker" DRIFT_CONFIG="$PWD/.work/drift-command.json" \
  /bin/bash scripts/daily_probes.sh mytool
env -i PYTHON="$probe_python" ADD_PATH="$PWD/.work/bin" LOG="$PWD/.work/daily.log" \
  MARKER="$PWD/.work/marker" DRIFT_CONFIG="$PWD/.work/drift-command.json" \
  /bin/bash scripts/daily_probes.sh mytool
```

The first daily run fails and records the probe failure both in the log and on stderr. The second exits successfully and logs `probe ok` plus the index check's output. Deleting the marker gives `MARKER FAIL`; a failing drift subprocess gives `DRIFT FAIL`. The marker default is 3 days; `MAX_DAYS` changes that demonstration threshold. This checks a progress marker, not human consumption evidence: file mtime is not evidence that someone acted on an alarm.

These commands simulate the scheduler environment. They do not meet the historical rule that deployment acceptance must include a real scheduler-triggered run.

## Index coverage, claim repair and byte limits

```bash
python3 - <<'PY'
from pathlib import Path
root = Path('.work/index')
root.mkdir(exist_ok=True)
for index in range(10):
    (root / f'topic{index}.md').write_text('Synthetic topic.\n')
(root / 'INDEX.md').write_text('2 files are not in this index\n' +
    '\n'.join(f'[topic](topic{i}.md)' for i in range(7)) + '\n')
(root / 'ARCHIVE.md').write_text('[topic](topic7.md)\n[topic](topic8.md)\n')
PY
python3 scripts/index_drift_check.py .work/index --indexes INDEX.md ARCHIVE.md
python3 scripts/index_drift_check.py .work/index --indexes INDEX.md ARCHIVE.md --fix
printf '%s\n' '[topic](topic9.md)' >> .work/index/ARCHIVE.md
python3 scripts/index_drift_check.py .work/index --indexes INDEX.md ARCHIVE.md
```

The first run reports `true_orphans=1` and `claim 2 != 3`. `--fix` repairs the number only; it still fails on the orphan. Adding the missing archive link permits `ok`. The synthetic counts are fixture sizes, not the historical 340-file inventory. Appending 30,000 bytes to the loaded index produces the 24,000-byte size failure and the 600-byte line failure; neither is repaired by `--fix`. Dead links warn but do not independently fail. Links to subdirectories are outside this flat-index example.

## State reader and status line

```bash
python3 - <<'PY'
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
root = Path('.work/status')
root.mkdir(exist_ok=True)
now = datetime.now(timezone.utc)
for name in ('healthy', 'red', 'stale'):
    ts = now - timedelta(hours=80) if name == 'stale' else now
    (root / (name + '.jsonl')).write_text(json.dumps({'ts':ts.isoformat(),'ok':name != 'red'})+'\n')
(root / 'unreadable.jsonl').write_text('garbage\n')
(root / 'state.json').write_text(json.dumps({'_ts':now.isoformat(),'paused':False}))
PY
python3 scripts/status_line.py .work/status/healthy.jsonl .work/status/red.jsonl \
  .work/status/stale.jsonl .work/status/missing.jsonl .work/status/unreadable.jsonl
STATE=.work/status/state.json scripts/is_paused.sh
```

Status prints exactly the red, stale, missing and unreadable lines; healthy is silent. For `is_paused.sh`, rc 1 means healthy and not paused; rc 0 means paused. Missing, corrupt, future or older-than-3-days state produces a reason on stderr and pauses. A missing Python interpreter also pauses. This inverted status is deliberate; do not wrap it as a conventional success-is-healthy check.

## Configuration reader search

```bash
mkdir -p .work/reader/source
printf '%s\n' '{"active":true,"inert":false,"absent":true}' > .work/reader/config.json
printf '%s\n' 'value = config["active"]' > .work/reader/source/app.py
printf '%s\n' 'known = {"inert"}' > .work/reader/source/validator.py
printf '%s\n' 'config["inert"] = False' > .work/reader/source/wizard.py
python3 scripts/config_reader_check.py .work/reader/config.json .work/reader/source \
  --ignore validator.py wizard.py
```

Expect one `has reader`, two `no reader`, and a nonzero result. The inert key is labelled `allowlisted mentions only`; the absent key has no mentions. The script emits dotted paths for nested keys and searches the dotted or leaf literal. Dynamic key construction, duplicated leaf names, writes and dead source branches limit the inference: follow the candidate reader and test the actual consumer to establish effect.

## The lying probes

```bash
python3 examples/path_canary.py
python3 examples/lies/fake_selftest.py
/bin/sh examples/lies/echoed_prompt.sh
PYTHON="$probe_python" /bin/sh examples/lies/empty_catalog.sh
/bin/bash examples/lies/pipe_status.sh
python3 examples/lies/regex_parity.py
```

The path toy first reports boolean GREEN with `path=fallback`, then path RED. Adding the boundary fix makes clean egress fail closed with the old canary; the mixed canary restores the main path and permits clean prose. These are detector-shape examples, not real secret detection.

The comment-only self-test, echoed prompt and empty catalogue show naive GREEN versus right RED. Pipeline status prints `naive: rc=0` and `right: rc=1`. Regex output includes Python and grep engine versions plus each positive/negative comparison. `[[:space:]]` differs; bracket/backslash behaviour depends on the installed grep, and should not be forced to disagree where the engines agree. The historical table was measured on Python 3.14.6 and BSD grep 2.6.0 only.

## Structural receipts and independent recomputation

```bash
python3 scripts/receipt_gate/make_synthetic_transcripts.py .work/transcripts
python3 scripts/receipt_gate/test_forgery.py
python3 scripts/receipt_gate/auditor.py .work/transcripts \
  --notes .work/transcripts/notes --output .work/audit
python3 scripts/receipt_gate/receipt-tool --notes .work/notes --slug a --body 'Synthetic note.'
```

The generator creates a project fire, a clean project, a research fire and a nonempty note for the clean receipt. The auditor records debts for the two fires and a heartbeat for the scan. Its existence predicate can be replaced by a caller-supplied function. Missing or failed existence checks create debt; the auditor does not silently call them verified.

The forgery suite tests every specified form against both the receipt predicate and a complete verdict. Real compound receipts are rejected intentionally. Agent prose and sub-agent reports do not count. A same-named executable earlier on PATH remains a positive receipt at the structural layer; a missing note fails the independent check. Reusing an existing slug still passes existence, and the file mock is not a protected verifier identity.

## The local gate: run real checks before forging

Copy the generic toy so every attack operates on disposable material:

```bash
cp -R scripts/toy_gate .work/toy
mkdir -p .work/toy/target
printf '%s\n' before > .work/toy/target/note.md
snap=$(python3 .work/toy/toy_gate.py snapshot .work/toy/target .work/toy/state)
python3 .work/toy/toy_gate.py check --snap "$snap"
printf '%s\n' after > .work/toy/target/note.md
python3 .work/toy/toy_gate.py check --snap "$snap"
```

The first check passes and the drifted check fails. The registry paths are relative to the registry file, not to the caller's working directory. State must be outside the target to avoid hashing the snapshot into itself.

Forge a result artifact:

```bash
/bin/sh .work/toy/forge_pass_artifact.sh ".work/toy/state/$snap"
python3 .work/toy/toy_gate.py closeout --snap "$snap"
python3 .work/toy/hardened_gate.py closeout --snap "$snap"
```

Weak closeout passes on the forged newest artifact. Hardened closeout recomputes and fails.

Rewrite the actor-owned manifest and its sidecar:

```bash
python3 .work/toy/forge_manifest_pair.py ".work/toy/state/$snap"
python3 .work/toy/toy_gate.py check --snap "$snap"
python3 .work/toy/hardened_gate.py closeout --snap "$snap"
```

Both now pass: changing mode bits back to writable and rehashing the changed target defeats this local anchor. This is a demonstrated residual, not an omitted assertion.

Select another registry:

```bash
PYTHON="$probe_python" /bin/sh .work/toy/forge_registry.sh \
  .work/toy/alternate.json .work/toy/target .work/toy/alternate-state
alternate_snap=$(python3 .work/toy/toy_gate.py --registry .work/toy/alternate.json \
  snapshot .work/toy/target .work/toy/alternate-state)
python3 .work/toy/toy_gate.py --registry .work/toy/alternate.json check --snap "$alternate_snap"
python3 .work/toy/toy_gate.py --registry .work/toy/alternate.json closeout --snap "$alternate_snap"
python3 .work/toy/hardened_gate.py closeout --snap "$alternate_snap" --registry .work/toy/alternate.json
```

The weak entry points accept the caller's registry and the newly blessed target. The hardened entry point rejects `--registry` because its path is fixed in code. Fixing the path does not stop an actor who can edit that registry, the gate or both snapshot files. Real forgery resistance needs an independently controlled anchor; no separate-user or signing setup is included.

The historical reference gate's full private domain checks, original raw attack output, live scheduler acceptance and running-process plugin state are not reproduced here. The public plugin's latest compliance documentation also remains unverified without a network check.
