# Chapter 3: Probes that lie

### Problem

Probes are guards, and they fail silently in the same ways. This chapter collects the cases where a check reported green without checking, with the test that shows each.

### What we built or changed

A list of fifteen lies and the counter-assertion for each; one worked example (the 47-day canary) reproduced here by a synthetic toy detector.

### The worked example: a canary that asserted a boolean

An egress gate decides whether outbound content contains a secret. It has two paths: the main criteria, and a fallback that removes all whitespace and re-matches (to catch secrets split across lines). Its canary was built as a key prefix plus 40 identical letters `x`. The criteria also contained a placeholder filter that treats a run of `xxxxx` as a redaction marker (so a documentation example such as `<prefix>-xxxxxxxx` is not blocked). From the day the filter shipped (2026-07-07) the canary was filtered out on the main path, and the fallback path, which had no placeholder filter, matched it. The canary asserted only `hit == True`, so it passed every day, for 47 days, through the wrong path. The gate itself went live on 07-08, so the canary was degraded from the gate's first day. A different, correct fix (a left word-boundary on prefix-type key patterns, to stop false hits on English words ending in `sk` followed by a hyphen) made the fallback stop matching the canary too, because the whitespace removal glued a pad character to the prefix. The canary then failed and the gate, failing closed as designed, denied all egress. That is how it was found: a read-only probe was blocked, the same evening (backups and the decision record put the whole sequence between 20:33 and 22:19 on 2026-08-23; the record is dated 08-24 in UTC). The ledger held 957 lines and none was a canary record, because the two deny branches for canary failure and for criteria-extraction failure blocked without writing to the ledger.

Fixes, in order of importance:

1. The canary is built to look like a real key (a prefix plus 40 random-looking characters), not like a redaction marker. A self-test must use the shape of the thing it claims the gate can catch. The public toy constructs a synthetic prefix and payload at run time; no historical canary string is included.
2. Assert the path: `result.hit is True and result.basis == "main"`. Asserting only the boolean allows any path to answer for a dead one.
3. Both deny branches now write a ledger row. A failing guard must leave a trace.

Rejected on purpose: reverting the boundary fix (it was right); adding the placeholder filter to the fallback path too (it would weaken the fallback for split secrets, to make the self-test convenient); downgrading a canary failure to a warning that allows egress (a security control's self-test failure must fail closed; the problem was never that it failed closed, but that it was invisible).

Verification recorded: five cases through the content function directly (canary now decides on the main path; a real-shape key blocks; a placeholder passes; the false-positive sample from the boundary fix passes; clean prose passes) and end to end (the previously blocked read-only probe passes; a command containing a real-shape key plus a cloud endpoint is blocked on the spot).

### The fifteen lies

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

**Dual-engine regular expressions (case 8 in Chapter 1), reproducible in a minute.** The same pattern text, evaluated by two engines on this machine (Python 3.14.6, BSD grep 2.6.0):

| Pattern | Python `re` | `grep -E` (BSD) | Consequence |
|---|---|---|---|
| `[[:space:]]` against a space | no match (it parses as a set of the characters `[ : s p a c e` followed by `]`; Python warns "Possible nested set") | match | A whitespace-based label pattern is dead on the Python side |
| `[\[<]` against a backslash | no match (escaped bracket) | no match on this BSD grep; the POSIX reading (and GNU grep) treats the backslash as literal | Engines disagree; do not use backslash escapes inside brackets |
| `(\[\|<)` | same on both | same on both | Use alternation instead |
| `[ \t]` | same on both | same on both | Use this instead of `[[:space:]]` |
| `^...$` on multi-line text | line anchors only with `re.M` | always line anchors | Set `re.M` on the Python side |

The fix was to write every shared pattern in the intersection of the two syntaxes and to run each shared pattern on both engines against shared fixtures, in the canary's content-gate probe.

**An erratum that is itself an example.** A decision record stated that a closeout plugin was "loaded in all four gateways". The check had been a plugin listing from a freshly started command-line process. The ledger had zero events from that lane. The record was corrected the same morning; the running-process behaviour evidence was still missing when the volume closed. Lesson as case 9 above.

### Procedure as actually run

The incident records supplied the historical failing inputs. The public examples recreate selected failure shapes using synthetic data: the canary, self-test flag, echoed prompt, missing catalogue, pipeline status, regex parity and scheduler environment. They do not replay private inputs.

### Results

| Measurement | Value |
|---|---|
| Canary degradation | 47 days; 957 ledger lines, 0 canary rows; fixed and verified within one evening |
| Self-test flag detection | The local-model reviewer found the comment-only flag hole; the protocol change landed in the same night's session |
| Echoed-prompt grep | 4 of 4 models "OK" by grep; 1 of 4 usable in reality (the other three were rejected by the account type: "not supported when using the agent with a subscription account") |
| Missing-metadata warning | A tool printed the same "model metadata for X not found" warning every turn for 7 dispatches; it was read as noise 7 times and was the diagnosis |
| Compliance diagnostic (case 24) | "0 of 8" became "1 of 8 within the window, not attributable to the advice"; window: 15 calls; 5 never, 2 late |

### What did not work

- Treating the 7 repeated warnings as noise. A warning that appears every run is either noise or the symptom; decide by reading it once.
- Using a low-level absence ("no warnings") as acceptance.
- Pure-function self-tests: one passed while the call site was broken (a local variable shadowed a function, a bare `except` swallowed the error: published in the proxy books).

### Pitfalls (symptom -> root cause -> fix)

- Canary passes, gate denies everything -> canary and criteria disagree about what a fake secret looks like -> build the canary like a real secret and assert the path.
- Self-test "passes" after the flag was deleted -> flag detection by source text -> run it, check `PASS`.
- A shared pattern works in one tool and never in the other -> engine syntax differences -> common subset, both engines in the test.
- An acceptance script exits 0 with an empty result -> the thing it asserts about never ran -> assert preconditions first.

### The rule

A check is not evidence until you have seen it fail for the right reason: for every probe, break the guard on purpose once and watch the probe go red, and make the probe name the path it expects.

## Public implementation boundary

These are selected executable examples, not reproductions of all fifteen historical failures. The toy prefix is invented; it is not a production secret detector. Regex output names the engines actually run and reports bracket-escape disagreement only when that engine exhibits it.

The synthetic runner prints the installed engines' actual bracket/backslash result even if it differs from the historical table. The source does not establish the full build and invocation details needed to reconcile such a difference; the historical table is not rewritten as a new measurement.
