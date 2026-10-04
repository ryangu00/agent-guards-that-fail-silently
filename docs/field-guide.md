# Chapter 1: A field guide to silent guard failures

### Problem

When a guard stops working, the symptom is absence: no block, no warning, no ledger row. Absence is also what a healthy guard produces on a quiet day. The cases below were collected so the reader can recognise the shapes, and so each chapter can say which case it addresses.

### What we built or changed

A case file, not a tool. Each case has: what the surface showed, what was true, how long, how it was found, and the one-line assertion that would have caught it. The case file came from three sources: a read-only audit on 2026-09-21 of the 14 wired hooks and the scheduled guard jobs (ledger counts in a 30-day window cut at 2026-08-22; for hooks without a ledger, a grep of their trigger text in all 118 session transcripts; Stop-chain latency taken from the `durationMs` field that the host records for each hook in the transcripts); incident records from the preceding months; and a cleanup and verification pass in late September.

### Procedure as actually run

1. List every wired guard and every scheduled guard job.
2. For each, answer from primary data only: how many times did it fire in 30 days, when did it last fire, what does its log or ledger contain? Where no ledger exists, use a proxy and say so (a grep of the guard's deny text in transcripts: 3 of 118 sessions for one guard, 9 of 118 for another).
3. Read the code of each guard that fires suspiciously often or never.
4. Re-run the failing path in the environment where the guard really runs.

### Results

**Table 1.1: the ten core cases.** Dates are 2026; durations are first-hand unless marked.

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

**Table 1.2: fifteen further field cases.**

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
| 24 | A compliance diagnostic for a reminder hook | "0 of 8 obeyed" | The script read only top-level session transcripts; 6 of 8 reminders landed inside sub-agent sessions it never opened. Recount by receiving agent: 1 of 8 within the window, not attributable to the advice (the window was its next 15 calls; sibling sub-agents that had not been reminded searched at the same moment); 2 were top-level and searched much later; 5 never did. The ledger's own "obeyed" tally (2 of 18) counted searches by sibling sub-agents | Frozen sample 07-27 to 09-21 | An independent verification of a draft public claim |
| 25 | State readers of four newly built "stop the line" scripts | Written as `if python3 -c ... 2>/dev/null; then` | A missing, corrupt or unreadable state file, or no `python3` on PATH, took the "proceed" branch | Pre-deploy | Two reviewers independently |

**Table 1.3: five ways a liveness check was fooled** (primary family per case; several cases belong to two).

| Family | What was judged | Cases |
|---|---|---|
| A. Exact string or code | A message, a pattern, a flag name or a status code matched literally | 3, 8, 11 (an error class decided by a status code) |
| B. Environment | The process had a different PATH, home, profile, environment block or uid than the checker | 4, 7, 11, 13, 18, 19 |
| C. Exit code or boolean | `0`, `true`, "no match" treated as health | 2, 18, 20, 21, 25 |
| D. Presence is not effect | The file, registration, copy, process or config key existed, or a branch was never reachable | 1, 5, 6, 9, 12, 14, 15, 16, 17 |
| E. Wrong scope of observation | The check looked at the wrong population, process, or transcript set | 10, 22, 23, 24 |

**Durations.** Fifteen cases have a first-hand duration: 2, 2, 3, 4, 4, 5, 6, 6, 47, 57, 65, 68, 76, 79, 79 days (median 6, seven of the fifteen at 47 days or more). This is a sample of failures that were found, so it overstates how fast failures are found and says nothing about how many are still silent.

**Detection.** In the records, no case among the first ten was reported by an alarm belonging to the failing guard; they were found by an audit (5, 6, 7, 9), a cross-vendor review (4, 8), a downstream symptom (2, 3), a spike (1) and a replay after a change (10).

### What did not work

- Watching the process and the port. Case 11 had a green port, a live process and four all-green launch probes; none exercised the consumer's own credential.
- Alarms nobody consumed. Case 14 had the alarm 2,016 times; case 12's log was the alarm. A later gate in this book (Chapter 2) works, and has fired on most days since 09-23 because nobody owns its message.
- Fixing the instance without fixing the class. Case 3 was fixed on 09-14 and its sibling case 7 was found a week later (the earlier fix had been verified only interactively); cases 8, 9 and 10 were found in the following two weeks. The class was addressed only on 09-21 with the probe rules of Chapter 2.

### Pitfalls (symptom -> root cause -> fix)

- Dashboard green, work not done -> the check measured presence (registered, loaded, listening) -> add a probe that needs the guard to act.
- "Works in my shell", dead under the scheduler -> interactive PATH and environment differ -> probe under `env -i` with the scheduler's PATH, accept only after a scheduler-triggered run.
- A bare `except: pass` on the main path -> every request passes through untouched (also published in the thinking-tier-proxy book) -> log and re-raise, or fail closed on the decision path.
- A counter that is always 1 -> written only on transitions -> make the ledger write the quantity you later read, and test the branch that reads it.

### The rule

For every guard, write down the sentence "this guard is alive if and only if X happens", and make X something the guard has to do, observed from outside the guard, in the environment where it runs.

The public [axiom plugin](https://github.com/ryangu00/axiom) had a separate silent-ledger failure: its stuck-search hook did not write a ledger event in enforce mode until the 2026-10 update. This was fixed in the plugin's 2026-10 release; no version number is asserted here.

## Public implementation boundary

This is a selected case collection, not a fleet-wide failure-rate estimate. No real logs, transcripts or private guard configurations are shipped. The dead config-reader case remains case 17 in the numbered collection; no host identity is attached.
