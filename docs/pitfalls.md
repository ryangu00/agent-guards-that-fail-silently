# Pitfalls

Symptoms are not verdicts. Each entry pairs the symptom with the recorded cause, repair, and the remaining acceptance boundary.

## Chapter 1

- Dashboard green, work not done -> the check measured presence (registered, loaded, listening) -> add a probe that needs the guard to act.
- "Works in my shell", dead under the scheduler -> interactive PATH and environment differ -> probe under `env -i` with the scheduler's PATH, accept only after a scheduler-triggered run.
- A bare `except: pass` on the main path -> every request passes through untouched (also published in the thinking-tier-proxy book) -> log and re-raise, or fail closed on the decision path.
- A counter that is always 1 -> written only on transitions -> make the ledger write the quantity you later read, and test the branch that reads it.

Acceptance boundary: This is a selected case collection, not a fleet-wide failure-rate estimate. No real logs, transcripts or private guard configurations are shipped. The dead config-reader case remains case 17 in the numbered collection; no host identity is attached.

## Chapter 2

- Canary red on its first run -> the matrix named the wrong file type for a hook -> keep the matrix next to the wiring and let the first run be the test of the matrix.
- Probe passes in a terminal, fails from the scheduler -> `timeout` and user-directory tools are not on the scheduler's PATH -> `env -i`, plus an explicit PATH export in the job script.
- Background run of the second agent's CLI hangs on "reading additional input from stdin" -> it waits on stdin -> run with `</dev/null`.
- A test that must start a fresh agent session silently resumed an old one -> a shell function wrapped the agent CLI and added a resume flag -> call the real binary path in probes and tests.
- A probe wrapper `2>/dev/null` hides why a lane died -> keep stderr in a log file (the worker's stderr is now appended to a log instead of discarded).
- Two copies of a hook drift -> symlinks make drift structurally impossible; the daily byte comparison catches the symlink being replaced by an editor's atomic write.

Acceptance boundary: The public canary retains registration, compilation, executed self-tests, byte comparison and per-probe exception records. Commands are argv arrays; `{python}` resolves to the current interpreter; relative paths resolve from the config directory. An intentionally broken required hook yields a compile alert only, suppressing a duplicate self-test error. Config-load or ledger-write failures exit nonzero on stderr. The content adapter accepts only the explicit BLOCK/ALLOW protocol; a crash is not a successful denial. Real scheduler acceptance is still required for a deployment.

## Chapter 3

- Canary passes, gate denies everything -> canary and criteria disagree about what a fake secret looks like -> build the canary like a real secret and assert the path.
- Self-test "passes" after the flag was deleted -> flag detection by source text -> run it, check `PASS`.
- A shared pattern works in one tool and never in the other -> engine syntax differences -> common subset, both engines in the test.
- An acceptance script exits 0 with an empty result -> the thing it asserts about never ran -> assert preconditions first.

Acceptance boundary: These are selected executable examples, not reproductions of all fifteen historical failures. The toy prefix is invented; it is not a production secret detector. Regex output names the engines actually run and reports bracket-escape disagreement only when that engine exhibits it.

## Chapter 4

- A feature "configured" yet inert -> no reader, or a reader of another file -> run the reader check.
- A gate passes everything in workers but blocks in your shell -> profile-dependent config loading returned `None` -> resolve fleet-level keys from the root; test in a profile environment.
- Every call returns 500 "provider failure" and a fallback hides it -> missing credential, error handler raised a secondary error -> test with the consumer's own credential and assert the fallback counter is 0.
- Two documents claim to be the source of truth -> an old copy -> stub without the key structure.
- A scheduler job ignores an environment variable -> duplicate keys in the property list -> read the resolved environment, not the file.

Acceptance boundary: The JSON reader check reports string-literal candidates. A string in executable source can still be a writer, dead code or the wrong consumer; dynamic reads may be missed and repeated leaf names may be ambiguous. It cannot establish runtime use. The final acceptance step remains a run of the real consumer in its own environment, which is not part of this offline book.

## Chapter 5

- Escalation tier never appears -> the counter was written only on transitions (case 5) -> write the counter you later read, test the branch.
- Every scheduled session produces a fire -> the same criteria were applied to unattended sessions -> tag the harness on every ledger row and filter by it when showing debt to a human.
- Audit shows twice the debt -> sub-agent transcripts counted as sessions -> skip them and show the count skipped.
- A gate's fixtures are real sessions -> private content -> build synthetic transcripts with the same event shape.
- The second agent's sessions always "clean" -> parser did not recognise its format (case 10) -> replay one real sample of every host's format through every shared hook.
- Receipts in a compound workflow ignored -> by design -> run the verify call alone.

Acceptance boundary: The public core uses generic hooks/tooling/settings paths and synthetic host-format messages. It does not include the second-agent parser or a live hook installer. Only harness-written calls and paired direct results can count. The public auditor substitutes a caller-supplied nonempty-file existence check for the private database query; it does not authenticate transcript authorship, prove content quality or provide a separate security identity.

## Chapter 6

- A gate is green, a forged input is green too -> the verifier reads a file the actor wrote -> verify by re-running the check, not reading a result file.
- Two scripts disagree about what an id may contain -> two parsers -> one shared validator.
- Acceptance run shows everything passes -> the harness hits the gate's own exemption (Chapter 3).
- A claimed guarantee in the decision record -> never tested against a bypass -> add the bypass to the acceptance and write down the downgrade when it works.
- A "no-op" or "nothing to do" outcome accepted without evidence -> the check cannot tell "nothing found" from "could not parse" -> distinguish the two and fail closed on the second.

Acceptance boundary: The new toy implements recursive file snapshots, drift checks and closeout rather than the private domain-specific checks. The hardened variant fixes registry selection in code and recomputes the check during closeout. It still accepts a rewritten manifest/hash pair when both are owned by the actor; separate identities or signing keys are not implemented.
