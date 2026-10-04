# Chapter 2: Negative probes that run where the guard runs

### Problem

A positive check ("the hook file exists, the job is loaded, the last run printed OK") cannot tell a guard that works from a guard that does nothing. A negative probe is an input for which the guard must act, plus an assertion that it did. It has to be run in the environment where the guard really runs, or it proves something about a different system.

### What we built or changed

Four pieces, all standard-library Python or POSIX shell:

1. **A daily canary** (`hook_canary`): reads the host's settings file and the hooks directory and runs seven kinds of probe. It appends one JSON line per run to an alerts ledger and exits non-zero on any alert. It has its own `--self-test` that injects faults and requires each to alert.
2. **An edit-time self-test hook** (`hook_selftest_on_edit`): a `PostToolUse` hook on `Write|Edit|MultiEdit` that, when a file inside the hooks directory was just written, compiles it and runs its self-test, and injects one warning line if either fails.
3. **A scheduler-environment probe** (`env_probe.sh`): runs a command under `env -i` with the scheduler's PATH and demands an exact expected output.
4. **A status line at session start** that reads the canary's last record and shows red, stale, missing and unreadable states.

**The seven probes in the canary** (names are ours):

| Probe | What it does | Alert when |
|---|---|---|
| registration | Builds `{hook file: {events}}` from the settings file (substring match of the hook file name inside each command) and compares with a matrix of required events per hook | A required event is missing for a hook |
| compile | `py_compile` on every matrix hook that is a `.py`; existence check for shell wrappers | Syntax error or file missing |
| selftest | Runs every hook that offers `--selftest` or `--self-test` (decided by the literal flag in the source, then verified by running it) | return code is not 0, or stdout lacks the word `PASS`, or timeout (180 s), or a hook on the must-have-self-test list has no flag |
| content-gate | Calls a write gate in `--check-only` mode (never writes) on 7 bodies: 6 that must be blocked, 1 plain prose that must pass | Any answer differs from the expectation |
| lane | Runs the scheduler-environment probe for the cheap model lane; accepts only the exact output `PONG` and rc 0 | Anything else, including timeout (120 s) |
| review-lane | Calls the second agent's review wrapper in its own self-test mode: must produce a real model reply with zero "model metadata not found" warnings | Non-zero rc or timeout (180 s) |
| mirror | For each file in the second agent's hooks directory that has a same-named file in the first agent's, compares bytes (`filecmp.cmp(..., shallow=False)`); `.bak` files are ignored | Contents differ (the symlink was replaced by a regular file) |

The lane and review-lane probes illustrate one probe per dependency. The public canary replaces the private probes with a configurable command/output list and a check-only gate with synthetic cases; none of the original labels or patterns is included.

**Case shapes for a content gate** (the seven bodies of the content-gate probe; historical shapes only; the public fixture uses an invented English-only label): (1) a key-shaped string, which must block; (2) a confidentiality label in full-width brackets; (3) a declarative sentence marking a document confidential, in the first of two languages; (4) the same declaration in the second language; (5) the label alone on a line as a heading, followed by body text; (6) a Markdown heading carrying the label; (7) the negative case: prose that merely mentions the word and the principle, which must pass. Cases 2 to 4 were added after the local-model reviewer showed inputs the gate missed, and case 5 (a reviewer's blocker) after the second vendor's reviewer did; the negative case came with the fix that removed generic words from the trigger list. The subprocess is run with the locale pinned to a UTF-8 locale; a reviewer worried that a restricted environment could default to bytes and break multibyte patterns (a concern, not a measured failure).

**The registration matrix** is per guard, not blanket. Example from our matrix: the failure-reminder hook requires `PostToolUse` and `PostToolUseFailure`; the write-verification hook requires `PostToolUse` and `Stop` (a failed write is not a false-success candidate, so it does not need the failure event); the closeout hook requires `Stop` and `SessionStart`; the edit-time self-test hook requires `PostToolUse`. The first run of the canary raised a false alarm because the matrix named a `.py` file for a hook that is a `.sh` wrapper,; the first run is the test of the matrix.

**The self-test protocol** is "return code 0 AND stdout contains PASS". Before that, the canary decided that a hook had a self-test by finding the string `"--selftest"` in its source. A reviewer pointed out the failure: a comment that mentions the flag, a `main` that ignores arguments and exits 0 would pass. The protocol plus a must-have list (deleting the flag from a required hook turns the canary red, instead of making it skip the hook) closed that.

**Edit-time self-test.** The host's hooks directory was not a git repository, so a pre-commit hook could not guard it. Instead, after every file write inside that directory the `PostToolUse` hook runs `py_compile`, then the file's own self-test, with the same protocol, and prints a `hookSpecificOutput.additionalContext` warning. It warns and does not block (fail open); a block was to be considered after a 14-day shadow period. Its own self-test uses five temporary files: red (exit 3), green (prints PASS), fake (mentions the flag only in a comment and exits 0), bad syntax, plain (no self-test), plus an outside-the-directory path that must be ignored.

**Scheduler-environment probe.** The original probe ran a dependency command under an empty environment, then compared its return code and exact output. The shipped [env_probe.sh](../scripts/env_probe.sh) takes an argv, `EXPECT`, `TIMEOUT`, and optional `ADD_PATH`; Python supplies the timeout so the demonstration does not depend on an unavailable timeout utility. This is a generic adaptation, not the original deployment command.

The point is that the probe is only green if the real job script exports the PATH it needs itself. The daily job script that failed with rc 127 (case 7) now begins with an explicit PATH export and a comment that says why; its probe block captures the return code, requires exact output, and writes the failure to both the log and stderr.

**Alerts and the status line.** One JSON line per run: `{"ts", "ok", "alerts": [{"check", "hook", "error" | "missing_events"}], "checks": [...]}`. A notification is raised on alert. Each probe is wrapped so that an exception inside a probe becomes an alert instead of killing the canary before it writes its record (a reviewer's finding: a lost execute bit on one tool raised `PermissionError` and the canary exited without writing). At session start the closeout hook prints one line per problem: red (last record not ok), stale (last record older than 72 hours), missing (no file), unreadable. The reason is a distinction the reviewers pushed for: "the guard is broken" and "nobody is looking at the guard" are two different failures and both must be visible.

**Canary self-test (`--self-test`).** It doctors a copy of the settings (removing the failure-event registration of one hook), writes a temp hooks directory with a syntactically broken file, a red self-test, a green one and a fake-green one, builds a second-agent directory with one symlink and one diverged file, and requires: registration alert for the removed event; compile alert for the broken file; selftest alerts for red and fake-green but none for green; mirror alert exactly for the diverged file; alerts for a missing probe script and a missing gate binary; and a clean result on the real system for registration, compile, content-gate and mirror. It prints a PASS line.

**Index-drift gate (case 23).** A second, smaller negative probe: invariants "every memory file is linked from the loaded index or one of two archive indexes" (true orphans = 0) and "the number the index claims for files not in it equals the real count". The script exits 1 on any violation; `--fix` may only change the number; dead links only warn. Added in the hardening pass: the file loaded at every session start is truncated beyond a size, so the gate also fails if the index exceeds 24,000 bytes or a line exceeds 600 bytes. Negative test recorded: add an unindexed file, expect "1 true orphan" and "340 != 341", delete it, expect ok.

### Procedure as actually run

- 2026-07-10: first canary (registration + compile only) after case 1.
- 2026-09-21: v2 after the audit: matrix extended from 6 to 12 hooks, self-test of every hook, lane probe under the scheduler's environment, content-gate positive and negative cases, then the edit-time hook.
- 2026-09-21/22: two review rounds on the whole bundle (below), fixes, a scheduler-triggered run of the canary and of the daily job.
- 2026-09-25: mirror probe added after case 9.
- Daily at 09:40 local time through a user launch agent. The historical manual command ran the canary directly; the public adaptation requires `--config` (exit 1 on alert) and supports `--self-test`.

Rules adopted with it (not all exercised yet):

1. Every wired guard has a negative probe in the canary.
2. A probe is accepted only after it has been run in the target environment (the scheduler or a fresh session), not in an interactive shell.
3. Changing a guard file runs its self-test immediately.
4. A new guard runs 14 days in warn-only (shadow) mode first.
5. A guard whose alerts take more than 3 days (median) to fix is retired instead of left as a noise source.
6. Every probe must be able to turn red under three injections: the guard broken, the wiring broken, the scheduling broken. (A reviewer's point: a "PONG" proves the call worked, not that the entry point cannot bypass the gate.) Partly implemented: the canary's self-test injects wiring faults and guard faults, and a scheduling fault (the job not running) shows up as a stale status line after 72 hours; it was not demonstrated guard by guard.

### Results

**Canary history** (alerts ledger, read 2026-10-03):

| Quantity | Value |
|---|---|
| Records | 93, covering 85 consecutive days (2026-07-11 to 2026-10-03), at least one per day |
| Red records | 4 (3 on 08-19, 08-20, 08-21: review-lane transport failure, "no reply from the model"; 1 on 09-24: cheap-lane probe rc 124 timeout) |
| Back to green | 08-22 and 09-25, the following days |
| Clean in the last 5 records (09-29 to 10-03) | 5 of 5, all 7 probes |
| Records with a `checks` list | 17 (10 with 7 probes, 7 with 6); the first 76 predate the field |

Reading: a fault shows up as red in the first daily record after it starts (fault start times were not recorded, so time-to-detect is bounded by the daily schedule, not measured); alert-to-green was 3 days for the review lane and 1 day for the cheap lane. There is no ground truth for how many silent failures the canary does not cover.

**What the probes caught in their first hours** (hardening session, 2026-09-21/22): the edit-time hook flagged the orchestrator's own broken test fixtures at least 3 times in the first hour (a missing-field case, a green stub that printed no PASS, an old case that simulated a call with prose); the memory notes record 4 catches for that session. Rule drawn: when a gate's protocol changes, change its cases in the same edit, or the new gate's first catch is its own tests.

**Cross-vendor review of the bundle** (2026-09-21/22): a local open-weight reasoning model (756 s wall time) returned 14 findings, 12 adopted; the second vendor's coding agent returned 12, 10 adopted. The findings were bugs in the new guards, not in old ones, which is the interesting part:

| Finding in the new guards | Fix |
|---|---|
| Four "stop the line" scripts read their state with `python3 -c ... 2>/dev/null`: missing, corrupt, unreadable state, or no `python3`, all meant "proceed" | One reader (`is_paused`) that fails closed: missing, corrupt or older than 3 days means "paused", with the reason on stderr |
| Consumption evidence was a file's mtime; a backup or an editor touching the file counted as "someone looked"; a future mtime kept the line alive | Evidence from timestamps inside the file or an explicit consume command; future times raise an alert |
| A probe caught only `TimeoutExpired`; `PermissionError` killed the canary before it wrote | Per-probe `try/except` that records the crash as an alert |
| Status line read with `except Exception: pass`: missing, stale and corrupt states showed nothing | Show each state explicitly (72 h staleness) |
| A health probe `grep -c Aborted \|\| true` wrote "healthy" when the program did not exist or timed out | Check rc and timeout; failure never writes healthy |
| A hook "consumed" a reminder because the user's message contained the command text | Count only real successful tool calls; empty blocks and failed calls do not clear the reminder |
| Two long index lines pointing to one target overwrote each other's text in the move to topic files | Accumulate per target file |
| A status field `done-but-blocked` matched `startswith("done")` and skipped the overdue check | Exact match against an enum; everything else is "unknown" |
| Date patterns hard-wired `2026-` | Generic year, per-record validation |
| A gate's standalone-heading case ("secret" on its own line) was not blocked | Positive case added to the canary and to the gate's own regression |

**Memory-index gate** (recorded outputs): before the fix `orphans=340 true_orphans=3 claim=124` FAIL; after `true_orphans=0 claim=340` ok; the index was cut from 47,087 B to 21,723 B on 2026-09-21 (48 long hooks moved verbatim to topic files, none deleted).

### What did not work

- **A gate that works and an alarm that is not consumed.** After the cleanup the index file reached 24,704 B within two days. In the daily log from 2026-09-16 to 2026-10-03 the drift check printed `ok` on 9 recorded runs and FAIL on 10; the last four FAIL lines are the size limit alone (24,181 to 25,366 bytes against 24,000), the claim number having been fixed. No false alarms among them, and no owner for them either. A probe cannot supply the owner.
- Source-grep detection of the self-test flag (see above).
- Relying on the interactive shell for acceptance of the scheduled probe (case 7).
- The "alert-to-fix median above 3 days means retire the gate" rule has no data yet beyond the two outages in the history table (3 days and 1 day).

### Pitfalls (symptom -> root cause -> fix)

- Canary red on its first run -> the matrix named the wrong file type for a hook -> keep the matrix next to the wiring and let the first run be the test of the matrix.
- Probe passes in a terminal, fails from the scheduler -> `timeout` and user-directory tools are not on the scheduler's PATH -> `env -i`, plus an explicit PATH export in the job script.
- Background run of the second agent's CLI hangs on "reading additional input from stdin" -> it waits on stdin -> run with `</dev/null`.
- A test that must start a fresh agent session silently resumed an old one -> a shell function wrapped the agent CLI and added a resume flag -> call the real binary path in probes and tests.
- A probe wrapper `2>/dev/null` hides why a lane died -> keep stderr in a log file (the worker's stderr is now appended to a log instead of discarded).
- Two copies of a hook drift -> symlinks make drift structurally impossible; the daily byte comparison catches the symlink being replaced by an editor's atomic write.

### The rule

Give every guard a probe that goes red when the guard does nothing, run it where the guard runs, make it assert the path that should have answered, and put its result on a line that a human sees at the start of work, including "stale" and "missing".

## Public implementation boundary

The public canary retains registration, compilation, executed self-tests, byte comparison and per-probe exception records. Commands are argv arrays; `{python}` resolves to the current interpreter; relative paths resolve from the config directory. An intentionally broken required hook yields a compile alert only, suppressing a duplicate self-test error. Config-load or ledger-write failures exit nonzero on stderr. The content adapter accepts only the explicit BLOCK/ALLOW protocol; a crash is not a successful denial. Real scheduler acceptance is still required for a deployment.
