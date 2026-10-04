# Results and complete tables

Historical figures are transcribed from the supplied fact sheet. Synthetic acceptance tables are explicitly labelled; running this repository cannot recreate the historical counts. Markdown tables retain source quantities and qualifiers.

## Setting

Conditions: Recorded environment; these versions describe the historical setup, not prerequisites inferred from the style example.

| Item | Value |
|---|---|
| OS and scheduler | macOS with launchd (user agents). Scheduled jobs run with the scheduler's minimal environment (PATH of `/usr/bin:/bin:/usr/sbin:/sbin`); that fact causes several cases. |
| Language and shell | Python 3.14.6 (hooks and probes are standard library only), macOS system bash 3.2.57, BSD grep 2.6.0 (FreeBSD). Python `re` and `grep -E` disagree on three constructs used here (Chapter 3). |
| Host agent | A command-line coding agent with a hook system. Events used: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SessionStart`, `UserPromptSubmit`. A hook is a command that receives a JSON object on stdin (`hook_event_name`, `tool_name`, `tool_input`, `transcript_path`, and for stop events `stop_hook_active`) and may print JSON such as `{"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "..."}}`. Version at audit time: 2.1.158. |
| Second agent | A coding agent from another vendor (CLI 0.153.4 when its hook schema was read) used as cross-vendor reviewer and as a second host for the same hooks. |
| Scale | 14 wired hook entries across the event types, 12 of them in the canary's registration matrix at the time of the v2 canary; 118 session transcripts available for the 2026-09-21 audit; an append-only JSONL ledger with 1,878 lines at the 2026-10-03 snapshot. |
| Settings shape | `{"hooks": {"<Event>": [{"matcher": "Bash\|Edit\|Write", "hooks": [{"type": "command", "command": "python3 <hooks-dir>/guard.py", "timeout": 150}]}]}}`. The same hook may appear under several events with different matchers; that is exactly what the registration matrix checks. |

## Field cases: core cases

Conditions: Historical cases, dates in 2026; unknown and derived durations retain their original qualifiers; audit 2026-09-21.

| # | Guard | What the surface showed | What was true | Duration | How found | One-line assertion that would have caught it |
|---|---|---|---|---|---|---|
| 1 | A "same failure repeated, go search" hook | Hook registered; no complaints | The host emits tool failures as a different event (`PostToolUseFailure`) whose payload has an `error` field and no `tool_response`; the hook was registered only for `PostToolUse`, so it never saw a failure and its ledger stayed at zero trigger rows | Not recorded (found 07-10) | A spike while preparing the public plugin | Every guard's required events are listed in a matrix and compared with the settings file daily |
| 2 | Self-test canary of a secret-egress gate | Canary passed daily | It passed through a fallback path; the main path had been dead since the criteria gained a redaction-marker filter that filtered the canary itself. When a later, correct fix removed the fallback's match, the gate denied all egress | 47 days (07-07 to 08-23); degraded since the gate's first day (07-08) | A read-only probe was blocked; same evening | The canary asserts which path decided (`basis == expected`), not a boolean |
| 3 | A Stop hook that syncs notes to a knowledge base | Ran on every Stop, exit 0 | It matched a failure message by exact string; the message gained one word; 13 privacy-withheld files counted as hard failures; its progress marker froze at 07-08; every Stop replayed about 109 files in 86-91 s. 2,374 samples: mean 80.5 s, median 72 s, max 165 s. After the fix: 100-300 ms (latest sample 99 ms) | 68 days (07-08 to 09-14) | Diagnosing a different symptom (a cheap lane that "hung") | Marker freshness is checked daily (not advanced in 3 days = alarm) |
| 4 | A scheduled job's property list | The decision record said the job used a specific reviewer command | The file had two `EnvironmentVariables` dictionaries; the second silently replaced the first; the setting never took effect | 5 days (08-18 to 08-23) | A cross-vendor review of a cleanup | Ask the scheduler for the job's effective environment, not the file |
| 5 | Escalation tier of a closeout-reminder hook | Reminder fired often | `fire_count` was incremented only in the fire state and the ledger was written only on state transitions, so every logged count was 1 (141 of 141 at audit). The "urgent list for fire_count >= 2" branch could never run | 76 days (07-07 to 09-21) | Reading the code against the ledger | Each escalation branch has a fixture that reaches it |
| 6 | A "you did not record what you learned" reminder | Quiet | Two independent conditions made it unreachable (an early return after extracting a block; a precondition read ledger rows that were mostly never written, see case 5). All-history firings: 2, the last on 07-26 | About 8 weeks (07-26 to 09-21; the audit says 55 days, calendar arithmetic gives 57) | Audit | A fixture session that must trigger the reminder |
| 7 | A liveness probe of the cheap model lane in the daily job | FAIL lines in the daily log | Under the scheduler's PATH the probe exited 127 (`timeout` is not in the four system directories; the tool lived in a user directory). In an interactive shell everything worked, which is where the earlier fix had been verified | 6 consecutive days (log retained 7 FAIL lines) | Audit of the daily log | Run the probe under `env -i` with the scheduler's PATH; accept only after a real scheduler run (09-21 23:26: "probe ok") |
| 8 | A secret-label pattern shared by a write tool (`grep -E`) and an egress gate (Python `re`) | Both "loaded" the pattern | `[[:space:]]` is not a whitespace class in Python `re`; `^...$` needs `re.M`; `\[` inside brackets differs by engine. The gate-side label shapes never took effect | Not recorded | Cross-vendor review of the hardening bundle (09-21/22) | Run every shared pattern through both engines on shared positive and negative fixtures |
| 9 | Hook copies for a second agent | Hooks "wired" for both agents | 12 same-named hooks were hand-copied; 5 stayed at July versions, including the secret-egress gate whose copy made every cloud dispatch of that agent fail closed and lacked a later heading-label fix | 79 days (07-08 to 09-25) | Inventory | Make the copies symbolic links; compare bytes daily |
| 10 | The same hooks, now run by the second agent | "Clean" for every session | The hooks parsed only the first agent's transcript format; 237 session states had empty `shapes`. After adding a parser for the harness-written completion events: replay of the 237 gave fire 60, clean 177; for the last two days (30 sessions) clean 30 became fire 13, clean 17 | 2 days after the symlink fix (09-25 to 09-27) | Replay after a change | Feed each host's real sample session to every shared hook and assert a non-empty parse |

## Field cases: further cases

Conditions: Historical cases, dates in 2026; unknown and derived durations retain their original qualifiers; audit 2026-09-21.

| # | Guard or component | Surface | Truth | Duration | Found by |
|---|---|---|---|---|---|
| 11 | Gateway in front of several model backends | Port and process healthy | Consumers lacked the gateway key (the variable existed only in a shared secrets file, not in each profile's environment); the proxy's error handler hit a missing optional module and turned a 401 into a 500; consumers read 500 as "provider failure" and fell back silently. With the real key six aliases returned 200 | 4 days (09-02 to 09-06) | A worker log line that announced its own fallback |
| 12 | A review-queue poller | Process loaded | Log was 935 bytes, 13 lines, all "poller starting": it polled a board nobody used and pointed at an old install | 65 days (06-28 to 09-01; derived from the stated dates) | Reading the log during consolidation |
| 13 | A default-reviewer table for a task board | Review gate "on" | Config read in a profile environment returned `None` for a fleet-level table; the gate treated "no reviewer configured" as an exemption | About 2 days (09-06 to 09-08) | The acceptance run failed to trigger the gate |
| 14 | Off-host backup of a repository | Backup job "ran" | The newest bundle was 1,896 hours (79 days) old; the log held the same stale-backup alarm 2,016 times | 79 days | Reading logs during a host check |
| 15 | A serving container | Health monitor green | After a site power outage the container (restart policy `no`) stayed down; the monitor alerts once on a state change | About 3 days (09-29 to 10-02) | Found while doing something else |
| 16 | A semantic cache service | Service up | 0 keys, 3 commands in 6 days of uptime, 1,010 connections; the consumer's config pointed at an address where nothing listened | 6 days uptime | An operator's question |
| 17 | A routing configuration block | Looked like it controlled routing | Zero readers in the running source tree; it appeared only in a known-keys whitelist and an installer wizard that wrote `enabled=False` | Not recorded | Source search during cleanup (Chapter 4) |
| 18 | A nightly dedup job | "1 of 21 jobs failing" on a dashboard | Round 1: it treated exit 1 as failure although the tool printed valid JSON and exited 1; round 2 (next day): the scheduler's PATH had no `node` (rc 127) | 4 days, then 1 more day | A dashboard fixed first |
| 19 | A restarted service | Health 200, `launchctl list` shows a pid | An orphan process not owned by launchd held the port; the new instance crash-looped on "address in use"; a regression gate's numbers did not move | One rollout | An operator noticing unchanged numbers |
| 20 | An acceptance command | Exit 0 | `cmd \| tail; echo $?` reports `tail`'s status; third occurrence in six days | n/a | The operator |
| 21 | An acceptance harness for a new gate | "Nothing flagged" | The harness had not set the two environment variables that mark a call as a worker; the gate's own exemption swallowed every test. A second assertion ("card not flagged") was empty when the scan had not run or the card was older than the scan's watermark | n/a | Writing the checker |
| 22 | A closeout hook applied to unattended scheduled sessions | 287 fires in 30 days | 108 of them (37.6%) came from scheduled sessions that can never satisfy the rule; the pending-debt list at session start was not filtered by harness, so a human session was asked to clear a scheduler's debt | 30-day window | Audit |
| 23 | A memory index file ("N files are not in this index") | A number | The claim said 124; the actual count was 340 (2.7 times) for two months; 3 files were in no index at all | About 2 months | A question the agent could not answer |
| 24 | A compliance diagnostic for a reminder hook | "0 of 8 obeyed" | The script read only top-level session transcripts; 6 of 8 reminders landed inside sub-agent sessions it never opened. Recount by receiving agent: 1 of 8 within the window, not attributable to the advice (window: next 15 calls; unreminded siblings searched at the same moment); 2 were top-level and searched much later; 5 never did. The ledger's own "obeyed" tally (2 of 18) counted searches by sibling sub-agents | Frozen sample 07-27 to 09-21 | An independent verification of a draft public claim |
| 25 | State readers of four newly built "stop the line" scripts | Written as `if python3 -c ... 2>/dev/null; then` | A missing, corrupt or unreadable state file, or no `python3` on PATH, took the "proceed" branch | Pre-deploy | Two reviewers independently |

## Failure families

Conditions: Historical cases, dates in 2026; unknown and derived durations retain their original qualifiers; audit 2026-09-21.

| Family | What was judged | Cases |
|---|---|---|
| A. Exact string or code | A message, a pattern, a flag name or a status code matched literally | 3, 8, 11 (an error class decided by a status code) |
| B. Environment | The process had a different PATH, home, profile, environment block or uid than the checker | 4, 7, 11, 13, 18, 19 |
| C. Exit code or boolean | `0`, `true`, "no match" treated as health | 2, 18, 20, 21, 25 |
| D. Presence is not effect | The file, registration, copy, process or config key existed, or a branch was never reachable | 1, 5, 6, 9, 12, 14, 15, 16, 17 |
| E. Wrong scope of observation | The check looked at the wrong population, process, or transcript set | 10, 22, 23, 24 |

## Canary probe contracts

Conditions: Historical canary and hardening observations; ledger read 2026-10-03, hardening reviews 2026-09-21/22; protocol rows are specifications.

| Probe | What it does | Alert when |
|---|---|---|
| registration | Builds `{hook file: {events}}` from the settings file (substring match of the hook file name inside each command) and compares with a matrix of required events per hook | A required event is missing for a hook |
| compile | `py_compile` on every matrix hook that is a `.py`; existence check for shell wrappers | Syntax error or file missing |
| selftest | Runs every hook that offers `--selftest` or `--self-test` (decided by the literal flag in the source, then verified by running it) | return code is not 0, or stdout lacks the word `PASS`, or timeout (180 s), or a hook on the must-have-self-test list has no flag |
| content-gate | Calls a write gate in `--check-only` mode (never writes) on 7 bodies: 6 that must be blocked, 1 plain prose that must pass | Any answer differs from the expectation |
| lane | Runs the scheduler-environment probe for the cheap model lane; accepts only the exact output `PONG` and rc 0 | Anything else, including timeout (120 s) |
| review-lane | Calls the second agent's review wrapper in its own self-test mode: must produce a real model reply with zero "model metadata not found" warnings | Non-zero rc or timeout (180 s) |
| mirror | For each file in the second agent's hooks directory that has a same-named file in the first agent's, compares bytes (`filecmp.cmp(..., shallow=False)`); `.bak` files are ignored | Contents differ (the symlink was replaced by a regular file) |

## Canary history

Conditions: Historical canary and hardening observations; ledger read 2026-10-03, hardening reviews 2026-09-21/22; protocol rows are specifications.

| Quantity | Value |
|---|---|
| Records | 93, covering 85 consecutive days (2026-07-11 to 2026-10-03), at least one per day |
| Red records | 4 (3 on 08-19, 08-20, 08-21: review-lane transport failure, "no reply from the model"; 1 on 09-24: cheap-lane probe rc 124 timeout) |
| Back to green | 08-22 and 09-25, the following days |
| Clean in the last 5 records (09-29 to 10-03) | 5 of 5, all 7 probes |
| Records with a `checks` list | 17 (10 with 7 probes, 7 with 6); the first 76 predate the field |

## Hardening review findings

Conditions: Historical canary and hardening observations; ledger read 2026-10-03, hardening reviews 2026-09-21/22; protocol rows are specifications.

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

## Fifteen misleading checks

Conditions: Historical incidents; regex observations apply only to Python 3.14.6 and BSD grep 2.6.0; counter-assertions are procedures.

| # | The check | Why it was green | Counter-assertion |
|---|---|---|---|
| 1 | Canary asserts `hit == True` | A fallback path answered for a dead main path (above) | Assert `basis` |
| 2 | "Has a self-test" = flag string found in source | A comment mentions the flag, `main` ignores arguments, exits 0 | Run it; require rc 0 and `PASS`; keep a must-have list |
| 3 | Self-test case "simulates success" with prose | The user's sentence containing a command name counted as the command having run | Cases use real tool-call records with results |
| 4 | An assertion with `or True` | Always true | Grep the guard and its tests for always-true assertions (a pass over both found none left after the fix) |
| 5 | Grep a model's reply for `OK` | The prompt itself said "Reply with exactly: OK" and the output echoed it; "all four models OK" was false, only one model was usable | Match what only a real reply can contain; look at raw output |
| 6 | "Zero warnings after the fix" | The override `model_catalog_json=/dev/null` made the tool die at start: zero warnings because nothing ran (an empty string failed too: "Is a directory") | Assert positive evidence (a reply), never only absence |
| 7 | `cmd \| tail; echo $?` | Exit status of `tail` | `set -o pipefail`, or capture status before the pipe |
| 8 | A tool printing valid JSON and exiting 1 | A dedup script used the return code as the verdict and also parsed the output as JSON; the tool printed a warning, exited 1 and the script died on the warning line. The orchestrator's first fix added a stricter return-code check, which judged a working command dead; a real run exposed it | Extract the payload first; decide from the payload; run the fix once for real |
| 9 | Plugin list from a fresh CLI process says "loaded" | It listed what a new process would load, not what the running gateway had loaded; the ledger had zero events | Inspect the running process (its pid, its environment, its events), not a new one |
| 10 | Probe passes in an interactive shell | Different PATH and environment | `env -i` plus a scheduler-triggered run |
| 11 | Health 200 after restart | An orphan process held the port, the new instance crash-looped | Assert the pid the scheduler claims equals the pid listening on the port; read the process's real environment (`ps -E`) rather than the plist |
| 12 | "Card not flagged" assertion | Empty: the scan had not run, or the card was older than the scan's watermark | Assert the precondition of the check first (watermark above the card) and fail with "this assertion is empty" |
| 13 | Acceptance harness for a gate | The gate's own exemption (a worker marker in two environment variables) swallowed every test, so everything "passed" | Before testing a gate, prove the harness does not trigger the gate's exemption |
| 14 | A self-check table, all green | An outsourced draft's table was green and its case reasoning right, but it was a derivation of paths, not an execution: its "first run only builds the baseline" return sat after the candidate scan, so the first real run would have flagged all history (one board held 20,145 events) | Run the first run once, for real, on a copy |
| 15 | A compliance diagnostic reading transcripts | It opened only top-level files; 6 of 8 cases were inside sub-agent files (case 24 in Chapter 1) | State the diagnostic's input scope and test it against a case that is known to be outside the scope |

## Dual-engine regular expressions

Conditions: Historical incidents; regex observations apply only to Python 3.14.6 and BSD grep 2.6.0; counter-assertions are procedures.

| Pattern | Python `re` | `grep -E` (BSD) | Consequence |
|---|---|---|---|
| `[[:space:]]` against a space | no match (it parses as a set of the characters `[ : s p a c e` followed by `]`; Python warns "Possible nested set") | match | A whitespace-based label pattern is dead on the Python side |
| `[\[<]` against a backslash | no match (escaped bracket) | no match on this BSD grep; the POSIX reading (and GNU grep) treats the backslash as literal | Engines disagree; do not use backslash escapes inside brackets |
| `(\[\|<)` | same on both | same on both | Use alternation instead |
| `[ \t]` | same on both | same on both | Use this instead of `[[:space:]]` |
| `^...$` on multi-line text | line anchors only with `re.M` | always line anchors | Set `re.M` on the Python side |

## Misleading-check measurements

Conditions: Historical incidents; regex observations apply only to Python 3.14.6 and BSD grep 2.6.0; counter-assertions are procedures.

| Measurement | Value |
|---|---|
| Canary degradation | 47 days; 957 ledger lines, 0 canary rows; fixed and verified within one evening |
| Self-test flag detection | The local-model reviewer found the comment-only flag hole; the protocol change landed in the same night's session |
| Echoed-prompt grep | 4 of 4 models "OK" by grep; 1 of 4 usable in reality (the other three were rejected by the account type: "not supported when using the agent with a subscription account") |
| Missing-metadata warning | A tool printed the same "model metadata for X not found" warning every turn for 7 dispatches; it was read as noise 7 times and was the diagnosis |
| Compliance diagnostic (case 24) | "0 of 8" became "1 of 8 within the window, not attributable to the advice"; window: 15 calls; 5 never, 2 late |

## Reviewer configuration by profile

Conditions: Historical configuration measurements; A/B cleanup 2026-10-02, C discovery 09-06 to 09-08, D outage 09-02 to 09-06; unmeasured cells remain unmeasured.

| Environment (home set to) | Before (measured) | After (measured) |
|---|---|---|
| a worker profile A | `None` | reviewer from the root table |
| the default home | reviewer | reviewer |
| a worker profile B | not measured | reviewer from the root table |
| a third worker profile | not measured | reviewer from the root table |
| the reviewer's own profile | not measured | the default reviewer (so it does not review itself) |

## Configuration cleanup results

Conditions: Historical configuration measurements; A/B cleanup 2026-10-02, C discovery 09-06 to 09-08, D outage 09-02 to 09-06; unmeasured cells remain unmeasured.

| Case | Quantity | Value |
|---|---|---|
| A | Readers of the block's keys in the running version's tree | 0 (2 mentions: validator whitelist, setup wizard) |
| A | Deleted | 3 whole blocks; 2 provider definitions in 6 configs; 1 dead fallback list emptied |
| A | Post-change validation | structure validator: 0 issues on 5 configs; parse diff equals the expected deletions |
| B | Stale revision vs authoritative | 2026-09-26.02 vs 2026-09-28.1 |
| C | Before the fix | 1 of 1 tested worker profile returned `None`; the default home returned the reviewer; after the fix 4 profile environments were checked |
| C | Days between landing and discovery | about 2 (between 09-06 and 09-08) |
| D | Duration | 4 days; 6 of 6 aliases 200 with the correct key; 4 profile configs with an empty key for titles |
| E | Duplicate `EnvironmentVariables` dictionaries | 2; effective environment had 2 variables (escalation target, PATH) |

## Work-shape contracts

Conditions: Historical receipt-gate observations; snapshot 2026-10-03 19:32 local where stated; individual replay and scan conditions remain in each row.

| Shape | Fires when |
|---|---|
| infra | A write (edit/write tool, or a shell write form after stripping exempt paths) lands on a path matching the infrastructure path pattern (the agent's own hooks, settings, instruction files, the operator's tooling directory). |
| project | Any of: at least 3 distinct non-exempt absolute file paths written (temp directories, scratchpads, ledger files, worklog, decision records and task files are exempt); a publish command (`npm publish`, `gh release create`, `docker push`, `twine upload`, `cargo publish`); a task file flipped to `status: done` with no clean record for the same task file in the last 48 hours. |
| research | At least 8 retrieval events (web search or fetch, paper search; each distinct `.pdf` or `.docx` read counts 1; a sub-agent result of at least 3,000 characters counts 3), and no substantive write, and no receipt. |

## Receipt forgery review rounds

Conditions: Historical receipt-gate observations; snapshot 2026-10-03 19:32 local where stated; individual replay and scan conditions remain in each row.

| Step | Forgery | Defence added | What happened next |
|---|---|---|---|
| 1 | The orchestrator's own compound command: a real call that fails, then an `echo` that prints the OK line | Revision 1: reject a command containing a standalone `echo`, `printf`, `grep`, `rg`, `cat`, `tail` or `history` token; require no error status | The forgery was rejected, and so was a legitimate real write followed by an unrelated `echo` and a database query |
| 2 | (the false rejection above) | Revision 2: reject only when the command text itself contains the expected OK literal; keep command-position, direct-result, slug and error-status checks | The reviewer: escape split, `echo receipt-tool:\ OK slug=x` |
| 3 | Escape split | Revision 3: strip backslashes, quotes and backticks before the literal check | The reviewer: variable concatenation, a `printf` format string, a `printf` argument split |
| 4 | The forms above | No further text rule; adopt the structural rule (simple calls only) that the reviewer had proposed in its first round | No forgery by text found; residuals listed below |

## Receipt-gate measurements

Conditions: Historical receipt-gate observations; snapshot 2026-10-03 19:32 local where stated; individual replay and scan conditions remain in each row.

| Measurement | Value | Conditions |
|---|---|---|
| Plan review | 36 findings: 24 adopted, 8 partly, 4 rejected | Before implementation |
| Implementation review | 19 findings, all fixed | Fresh-context cross-vendor reviewers |
| Cross-vendor rounds | 4, ended with ship-OK | Reviewer constructions broke the orchestrator twice |
| Incident replay (a day of project work with no record) | fire: 39 project files, 6 done-flips, receipt missing | One private real session; public fixtures are synthetic |
| Clean session replay | clean (receipt in the direct result) | One real session |
| Scan performance | 82 MB of transcripts in 0.57 s | Single process |
| Auditor first run in a sandbox that could not reach the database | 1,021 scanned, 80 debts; heartbeat `last_error` carried the connection failure | The run did not claim a database check it could not do |
| Auditor rerun outside the sandbox | 1,023 scanned, 81 debts, `last_error` empty | |
| After skipping sub-agent transcripts | 785 scanned, 44 debts (38 of the 80 were sub-agent duplicates) | |
| First real scheduled run | 807 scanned, 44 debts | |
| Forged receipt, database check | `ok=False` for a nonexistent slug; `ok=True` for a real one | Direct test |
| Second agent replay (237 session states, all previously empty) | fire 60 (infra 56, research 3, infra+project 1), clean 177 | After the event-parser change |
| Second agent, last 2 days (30 rollouts) | clean 30 became fire 13, clean 17 | |

## Receipt ledger snapshot

Conditions: Historical receipt-gate observations; snapshot 2026-10-03 19:32 local where stated; individual replay and scan conditions remain in each row.

| Event | Count |
|---|---|
| closeout fire | 387 (first agent 186; scheduled-agent lane 148; second agent 53); 383 distinct sessions |
| closeout clean | 7 (4 of these sessions had fired earlier) |
| debt cleared by hand or auditor | 8 |
| auditor heartbeats | 94 (1 with a `last_error`) |
| fire rows with `fire_count` 2 (first agent) | 1 of 186 (first on 2026-09-25, after the fix of case 5) |

## Local fact-gate review rounds

Conditions: Historical adversarial rounds, not the shipped toy tests; exact dates not recorded in this table; findings and test counts are reported counts.

| Round | Target | Tests passing | Findings |
|---|---|---|---|
| 1 | Procedure text and first template | n/a | 18: 9 BLOCKER, 8 MAJOR, 1 MINOR (the fast lane bypasses the active-task check and the decision lane; the three lanes were "kept" in words but not executable; the template's side effects contradicted its allowed-write list) |
| 2 | A shell gate (two scripts) | n/a (static) | 12 new: 3 BLOCKER, 6 HIGH, 3 MEDIUM; plus 18 earlier items re-judged |
| 3 | Gate v1, a Python rewrite (541 lines) | 13 of 13 | 11: 1 BLOCKER, 7 HIGH, 3 MEDIUM; reproduced (for example `PASS` after a new input file added post-snapshot, forged working-directory fields, an empty tag that matches every line, a tampered copy of the previous snapshot) |
| 4 | Gate v2 plus a closeout checker | 30 of 30 | 4 new (2 BLOCKER, 2 HIGH) plus items carried over; the closeout checker accepted a caller-supplied results file and any verifier script that exits 0; the template's YAML block did not parse |
| 5 | Gate v3, registry as the only anchor | 43 of 43 | 11: 3 BLOCKER, 8 HIGH; 85 real subprocess commands, each recorded with argv, stdout, stderr and return code; verdict DO-NOT-MERGE |

## Round-five root causes

Conditions: Historical adversarial rounds, not the shipped toy tests; exact dates not recorded in this table; findings and test counts are reported counts.

| Cause | Findings | Reproduction |
|---|---|---|
| The actor can choose or rewrite the trust anchor | The registry path is a caller argument: a second registry with the attacker's tag, lane text and approver gave snapshot, check and closeout `rc=0`. A forged "pass" result file (fields copied from the public manifest) made closeout `rc=0` while the real gate returned `rc=1`; a stale pass survived drift; a failure that returns early left no artifact so closeout read the old pass. The manifest and its self-check sidecar can be rewritten together; a read-only file is the same actor's file | `rc=0` on all three |
| Evidence proves the past, not the present | A receipt covering a knowledge bullet stays valid after the covered text is deleted from the target; the out-of-scope-writes check took its cutoff from the volume file's mtime, so saving the volume erased the record of an unauthorised file | `rc=0` after the deletion; `rc=0` after one ordinary save |
| An unrecognised format is read as "nothing" | A heading style the parser did not know produced zero knowledge items, so an empty receipt list passed; deleting a whole group with no references passed because `set() <= anything` is true | `rc=0` |
| Self-attestation instead of verification | Replacing the fixed volume body by `done_criteria: []` still passed; a second lane record appended after the first correct one was ignored (only the first match was read); route fields were compared as id sets, not values | `rc=0` |
| Two entry points validate differently | The gate rejected a snapshot id with `..`; the closeout checker accepted it | `rc=2` vs `rc=0` |
| Exemptions by type | Two writable targets were exempt from the type check; replacing one with a symlink to a file outside the root passed | `rc=0` |

## Local fact-gate outcome

Conditions: Historical adversarial rounds, not the shipped toy tests; exact dates not recorded in this table; findings and test counts are reported counts.

| Quantity | Value |
|---|---|
| Review rounds on the gate | 5 (a sixth to eighth on the minimal increment that was merged) |
| Findings per round | 18, 12, 11, 4 new, 11 (56 in total; BLOCKER 9, 3, 1, 2, 3 = 18) |
| Tests passing at the time of each review | n/a, n/a, 13, 30, 43: green in every round; each round still found at least 4 new issues |
| Round 5 evidence | 85 real subprocess commands with argv, stdout, stderr, return code; the 16 items left open or partial after round 4 re-judged with the original attacks: 5 closed, 8 partial, 3 still open |
| Root-cause groups in round 5 | 6 (anchor the actor can choose or rewrite; evidence about the past; unknown format read as nothing; self-attestation; two entry points; type exemptions) |
| Outcome | Do not merge the full fast lane; keep the gate as a mistake-catcher; merge a minimal shadow-and-draft increment |

## Canary fault-injection specification

Conditions: Synthetic acceptance specification; expected outcomes, not historical measurements.

| Injection | Expected alert |
|---|---|
| Remove one hook's registration for one required event from `settings.json` | `registration`: that hook, that event |
| Introduce a syntax error in a required `.py` hook | `compile` for that hook |
| A hook whose self-test exits 1 | `selftest` rc 1 |
| A hook whose comment mentions the flag and which exits 0 without `PASS` | `selftest` no PASS |
| Delete the self-test flag from a hook on the must-have list | `selftest` "no self-test entry" |
| Replace one of the mirrored symlinks by a regular file with different bytes | `mirror` for that file |
| Make one probe command raise (a missing executable) | that probe crashes into an alert; the canary still writes its record |
| Leave everything alone | `ok: true`, `alerts: []` |

## Receipt forgery specification

Conditions: Synthetic acceptance specification; expected outcomes, not historical measurements.

| Command in the transcript | Direct result text | Valid receipt? |
|---|---|---|
| `receipt-tool --slug a` | `receipt-tool: OK slug=a` | yes |
| `receipt-tool --slug a && receipt-tool --slug b` | both OK lines | no (compound); the verify call alone is requested |
| `receipt-tool --slug a; echo "receipt-tool: OK slug=a"` where the tool failed | the echoed line | no (compound; error status) |
| `echo "receipt-tool: OK slug=a"` | the echoed line | no (command word is `echo`) |
| `echo receipt-tool:\ OK slug=a` | the echoed line | no |
| `p=receipt-tool; echo "$p: OK slug=a"` | the echoed line | no |
| `printf '%s: OK slug=%s' receipt-tool a` (the only command) | the printed line | no (command word is `printf`) |
| `receipt-tool --slug a` | `receipt-tool: OK slug=b` | no (slug mismatch) |
| `receipt-tool --slug a` with `is_error` true | the OK line | no |
| `receipt-tool --slug a` quoted inside prose in an assistant message (no tool call) | n/a | no (not a direct tool result) |
| Sub-agent returns a report containing the OK line | agent text | no |
| A script named `receipt-tool` placed earlier on PATH that prints the OK line | the OK line | yes (documented residual; the independent auditor's existence check is the second line of defence) |

## Qualifications that belong beside the tables

- Duration sample: 2, 2, 3, 4, 4, 5, 6, 6, 47, 57, 65, 68, 76, 79, 79 days; median 6, seven of fifteen at 47 days or more. The sheet calls these first-hand durations, while case 12 explicitly derives 65 days from dates and case 6 reconciles an audit's 55 with calendar arithmetic's 57. Keep that distinction; these are discovered failures, not a discovery-time population.
- The 2026-09-21 audit used a 30-day ledger window cut at 2026-08-22 and 118 transcripts. Two guards lacked ledgers; deny-text occurrence was a proxy: 3 of 118 and 9 of 118 sessions, not measured trigger counts.
- Canary history: 93 records across 85 consecutive days, 2026-07-11 to 2026-10-03. Fault start times were not recorded; time to detect was bounded by the daily schedule, not measured. Alert-to-green was 3 days and 1 day. No false-negative denominator exists.
- Edit-time catches: at least 3 in the first hour of the 2026-09-21/22 session; the notes record 4 for that session. These are different windows, not conflicting counts.
- Bundle review: local open-weight reasoning model, 756 s wall time, 14 findings / 12 adopted; second coding agent from another vendor, 12 / 10. Adoption counts were not independently audited.
- Index correction: `orphans=340 true_orphans=3 claim=124` FAIL became `true_orphans=0 claim=340` ok. On 2026-09-21, 48 long hooks moved verbatim, none deleted: 47,087 B to 21,723 B. Within two days the index reached 24,704 B. From 2026-09-16 to 2026-10-03, 9 recorded runs were ok and 10 failed; the last four failures were size only, 24,181 to 25,366 bytes against 24,000. All were real alarms without an owner.
- Canary incident: placeholder filter 2026-07-07; gate live 07-08; degraded from its first day. The 47-day sequence was resolved the same evening, between 20:33 and 22:19 on 2026-08-23; the decision record is dated 08-24 UTC. Five direct content cases and end-to-end block/allow checks were recorded. The 957-line ledger had no canary records.
- Compliance, frozen sample 07-27 to 09-21: **1 of 8 within the window, not attributable to the advice**. The window was the receiving agent's next 15 calls; 6 of 8 reminders were in sub-agent files; 5 never searched and 2 searched late. The ledger's 2 of 18 tally included siblings and is not a compliance estimate.
- Receipt snapshot: 1,878 ledger lines on 2026-10-03 19:32 local; fires exceed clears roughly 48 to 1. Seven clean records count transitions only. Scheduled unattended sessions are 148 of 387 (38%); this differs from the earlier 30-day audit's 108 of 287 (37.6%). No labelled false-positive rate or improvement in discipline is established.
- At one auditor run, 235 sub-agent transcripts were excluded and the skip count was reported. The real replay with 39 project files and 6 done-flips is not shipped.
- The review-gate table's 43 of 43 tests used hand-written manifest/pass artifacts in closeout tests; they did not establish that the real gate would pass. The round-five raw JSON is gone; the surviving report lists 85 subprocess commands. The toy recreates attack classes only.
