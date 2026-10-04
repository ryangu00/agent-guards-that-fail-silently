# Implementation map

The public programs below implement the shipped-file plan with synthetic inputs. Paths and defaults from the original deployment are removed. No private source files, production state or actual detection criteria are included.

| Plan item | Public files | Adaptation and offline acceptance |
|---|---|---|
| Daily canary | `scripts/hook_canary.py`, `configs/canary.example.json`, `configs/settings.example.json`, `configs/gate_cases.json`, `examples/hooks/`, `examples/content_gate.py` | Required events and must-have tests come from JSON; generic commands replace private dependencies; exceptions are ledger alerts; exact fault injections run in `test_canary.py`. |
| Edit-time hook | `scripts/hook_selftest_on_edit.py` | Directory from argument or environment; English warnings; red, green, fake, bad syntax, plain and outside-directory fixtures. |
| Scheduler probe | `scripts/env_probe.sh` | Arbitrary argv, EXPECT/TIMEOUT/ADD_PATH; minimal subprocess environment; Python timeout avoids reliance on a missing external utility; PATH failure and recovery tested. |
| Index drift | `scripts/index_drift_check.py` | Parameterised flat directory, index names, claim expression and byte limits; number-only fix; orphan, mismatch, size and line failures tested. |
| Paused state | `scripts/is_paused.sh` | STATE or argument; fresh false gives rc 1; paused, missing, corrupt, stale or reader failure gives rc 0 with a reason where applicable. |
| Status line | `scripts/status_line.py` | New generic implementation; configured files only; healthy, red, stale, missing and unreadable fixtures. |
| Receipt gate | `scripts/receipt_gate/` | Reduced generic core and file-backed auditor, newly generated transcripts, toy writer and full forgery table; private database and second-agent parser removed. |
| Reference gate | `scripts/toy_gate/` | New generic snapshot/check/closeout toy, three forging scripts and a fixed-registry, recomputing variant; private reference implementation not shipped. |
| Path canary | `examples/path_canary.py` | New synthetic detector; runtime-built strings, boolean versus deciding-path assertions, boundary-fix failure and mixed-canary recovery. |
| Lying probes | `examples/lies/` | New comment-only self-test, echoed prompt, missing catalogue, pipeline status and engine-reporting regex demonstrations. |
| Reader check | `scripts/config_reader_check.py` | New JSON/literal-source heuristic; three-key project distinguishes a reader candidate, allowlisted mentions and no mentions. |
| Daily probes | `scripts/daily_probes.sh` | New restricted-PATH wrapper; pipefail, direct rc/output capture, stderr plus log failures, marker freshness and direct drift-check status. |

`tests/` uses the standard-library unittest runner and temporary synthetic files. The reproduction guide covers every plan item; it does not install hooks, a scheduler, a real gateway or an identity boundary.

The banner source retains the supplied template's drawing logic. Only the wordmark, tagline text and small diagram labels change. Rendering prerequisites beyond the template's Pillow import and platform font paths were not established by this task.

LICENSE and .gitignore are byte-for-byte copies of the requested templates. The legal copyright notice is retained as a public credit; there is no separate author line or tool attribution.
