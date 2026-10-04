# Chapter 5: Structural rules beat blacklists

### Problem

We wanted a mechanical check that an agent had really left a record (a note in a knowledge base, a worklog line) when it finished substantial work, instead of relying on a reminder in an instruction file. The natural design: look in the session transcript for a line of the receipt tool's output, such as `receipt-tool: OK slug=<slug>`. The agent can print that line itself. Every text pattern we added to refuse a forged line was beaten by a different way of composing a shell command.

### What we built or changed

A closeout gate with three parts: shape detection (what kind of work was done), receipt validation (a structural rule), and an independent daily auditor. It is warn-only: it never blocks.

**Shapes of work** (a pure function from a list of normalised events to a verdict; one implementation shared by the hook for the first agent, the plugin for a scheduled-agent lane, and the auditor):

| Shape | Fires when |
|---|---|
| infra | A write (edit/write tool, or a shell write form after stripping exempt paths) lands on a path matching the infrastructure path pattern (the agent's own hooks, settings, instruction files, the operator's tooling directory). |
| project | Any of: at least 3 distinct non-exempt absolute file paths written (temp directories, scratchpads, ledger files, worklog, decision records and task files are exempt); a publish command (`npm publish`, `gh release create`, `docker push`, `twine upload`, `cargo publish`); a task file flipped to `status: done` with no clean record for the same task file in the last 48 hours. |
| research | At least 8 retrieval events (web search or fetch, paper search; each distinct `.pdf` or `.docx` read counts 1; a sub-agent result of at least 3,000 characters counts 3), and no substantive write, and no receipt. |

"Fulfilled" means: infra needs a worklog entry and a receipt; project needs (a task-file changelog entry or a worklog entry) and a receipt; research needs a receipt or a write into the memory directory. A sub-agent invocation does not count as a receipt (the sub-agent's report is self-report); the main session must run the verify command afterwards.

**The receipt rule (final form).** A receipt counts only when all five hold, bound to the same `tool_use_id`:

1. The tool call is a shell call whose command position (first word, basename) is the receipt tool or its verifier.
2. **The command is a simple call: it contains none of `;`, `|`, `&`, a backtick, `$(`, `<(`, or a newline.** Anything else is a compound command and the receipt is not counted.
3. The paired direct tool result (not agent prose, not a quoted log) contains the tool's expected OK literal.
4. The slug in the result equals the slug argument of the command.
5. The call did not report an error (exit status not failed).

Why rule 2 is structural: in a compound command any later program can print text into the same tool result, and the combination space of ways to print "receipt-tool: OK slug=x" (echo literal, escaped split, variable concatenation, `printf` format string, `printf` argument splitting) cannot be enumerated. In a simple call the only program that prints is the receipt tool, so there is nothing left to forge by text. A reference implementation of the check is 15 lines:

```python
COMPOUND = (";", "|", "&", "`", "$(", "<(", "\n")

def valid_receipt(ev, tool="receipt-tool"):
    if ev.tool_name != "Bash" or ev.exit_ok is False:
        return False
    if ev.argv_head != tool:                      # command position, by basename
        return False
    if any(tok in ev.command for tok in COMPOUND):  # the structural rule
        return False
    if ev.result_source != "direct_tool_result":    # not prose, not a sub-agent report
        return False
    slug = slug_of(ev.command)                      # --slug value or first positional
    return bool(slug) and f"{tool}: OK" in ev.result_text \
        and slug in re.findall(r"\bslug=(\S+)", ev.result_text)
```

The cost, by design: a real receipt inside a compound workflow (`receipt-tool A && receipt-tool B`) is not counted; the reminder then asks for one simple `verify <slug>` call, once.

**The auditor.** A daily scheduled job re-reads the raw transcripts of the last N days (both agents), recomputes the verdict with the same core (it does not trust the hook's ledger conclusions, to avoid a shared contamination), and checks every receipt against ground truth with a read-only database query: the record exists, is not deleted, its body is non-empty, and it is not split across sources. It never uses the knowledge base's own tool interface for this check, because that interface is bound to a different source scope per client and answers differently (the only trustworthy channel is the direct query). It writes a debt list (a JSON-lines file and a markdown file) and a heartbeat row to the ledger with the count scanned, count of debts and the last error. Sub-agent transcripts are skipped (the orchestrator is responsible for their closeout) but their count is reported, so the skip is visible (235 excluded at one run).

**Warn-only escalation.** One warning per session at Stop, listing exactly what is missing and a command template with a suggested slug. A session that fires twice becomes a "must-do list" at the next session start until the session shows a clean record or the auditor clears the debt. The ledger is written on state transitions only. The gate never blocks; an earlier blocking write-verification gate had produced four false positives, and a closeout guard that blocks would block legitimate work in the many sessions where the criteria are wrong.

**Second agent's transcripts.** The same core parses the second agent's session files, but only the events the harness itself writes (command executed with argv, aggregated output and exit code; file changes with a diff; tool calls to external servers; web searches). It does not parse the JavaScript the model writes to call its own tools, because the model controls that text and can make it print a receipt-shaped line. This is rule 3 again: trust only what the harness wrote.

### Procedure as actually run

1. Specification (2026-07-07): three shapes, receipt levels L1 (command mentions it, abolished), L2 (structural receipt), L3 (independent database check).
2. Implementation by a second vendor's coding agent in three revisions; the orchestrator wrote the acceptance.
3. Forgery rounds (below), with the orchestrator building a forged compound `echo` that broke the implementer's first PASS, and the reviewer building escape, variable and `printf` forms that broke the orchestrator's two fixes.
4. Acceptance: replay of two real sessions (one known incident, one clean), a real scheduled run of the auditor, rollback drill both ways, and a trigger test in the second agent.

**The forgery rounds:**

| Step | Forgery | Defence added | What happened next |
|---|---|---|---|
| 1 | The orchestrator's own compound command: a real call that fails, then an `echo` that prints the OK line | Revision 1: reject a command containing a standalone `echo`, `printf`, `grep`, `rg`, `cat`, `tail` or `history` token; require no error status | The forgery was rejected, and so was a legitimate real write followed by an unrelated `echo` and a database query |
| 2 | (the false rejection above) | Revision 2: reject only when the command text itself contains the expected OK literal; keep command-position, direct-result, slug and error-status checks | The reviewer: escape split, `echo receipt-tool:\ OK slug=x` |
| 3 | Escape split | Revision 3: strip backslashes, quotes and backticks before the literal check | The reviewer: variable concatenation, a `printf` format string, a `printf` argument split |
| 4 | The forms above | No further text rule; adopt the structural rule (simple calls only) that the reviewer had proposed in its first round | No forgery by text found; residuals listed below |

The specification says the reviewer's four rounds demonstrated four forms but lists five (echo literal, escape split, variable concatenation, `printf` format string, `printf` argument split); the count used here is "five forms over four review rounds".

The orchestrator had rejected the structural proposal in round one because of "false rejections of compound workflows". The decision record calls that the wrong trade-off: the cost of a false rejection is one reminder and one extra call; the cost of the blacklist was an open-ended arms race.

### Results

| Measurement | Value | Conditions |
|---|---|---|
| Plan review | 36 findings: 24 adopted, 8 partly, 4 rejected | Before implementation |
| Implementation review | 19 findings, all fixed | Fresh-context cross-vendor reviewers |
| Cross-vendor rounds | 4, ended with ship-OK | Reviewer constructions broke the orchestrator twice |
| Incident replay (a day of project work with no record) | fire: 39 project files, 6 done-flips, receipt missing | One private real session; the public fixture is synthetic, not that session |
| Clean session replay | clean (receipt in the direct result) | One real session |
| Scan performance | 82 MB of transcripts in 0.57 s | Single process |
| Auditor first run in a sandbox that could not reach the database | 1,021 scanned, 80 debts; heartbeat `last_error` carried the connection failure | The run did not claim a database check it could not do |
| Auditor rerun outside the sandbox | 1,023 scanned, 81 debts, `last_error` empty | |
| After skipping sub-agent transcripts | 785 scanned, 44 debts (38 of the 80 were sub-agent duplicates) | |
| First real scheduled run | 807 scanned, 44 debts | |
| Forged receipt, database check | `ok=False` for a nonexistent slug; `ok=True` for a real one | Direct test |
| Second agent replay (237 session states, all previously empty) | fire 60 (infra 56, research 3, infra+project 1), clean 177 | After the event-parser change |
| Second agent, last 2 days (30 rollouts) | clean 30 became fire 13, clean 17 | |

**Ledger snapshot, read 2026-10-03 19:32 local (1,878 lines):**

| Event | Count |
|---|---|
| closeout fire | 387 (first agent 186; scheduled-agent lane 148; second agent 53); 383 distinct sessions |
| closeout clean | 7 (4 of these sessions had fired earlier) |
| debt cleared by hand or auditor | 8 |
| auditor heartbeats | 94 (1 with a `last_error`) |
| fire rows with `fire_count` 2 (first agent) | 1 of 186 (first on 2026-09-25, after the fix of case 5) |

How to read this honestly: fires outnumber clears roughly 48 to 1. Clean is written on state transitions only, so 7 undercounts sessions that finished with receipts; there is no labelled false-positive rate; 148 of 387 fires (38%) are scheduled unattended sessions, and many second-agent fires are deliverable files written by dispatched workers, which is a criteria question. What the numbers do support: the gate detects, the auditor independently confirms, and the discipline it asks for is rarely completed after the fact.

### What did not work

- Four rounds of text patterns (above).
- Counting a sub-agent's own statement or a quoted earlier receipt as a receipt.
- Trusting the hook's own ledger as the verdict: a hook cannot check itself, which is why the auditor recomputes from raw transcripts.
- Believing the gate effective on the scheduled-agent lane: the plugin-list check was run in a new process, the ledger had zero events from that lane, and the record was corrected (Chapter 3).

### Residual risks accepted (the specification's list, plus one hole the inventory's verifier noted)

- Noted by the inventory's verifier, not by the specification: a script named like the receipt tool, placed earlier on PATH, defeats a rule that checks the command word and not the binary. The specification's own threat model is lazy or accidental false completion, not a hostile agent.
- Reusing an already existing real slug passes the existence check; a hash comparison of the written content against the stored record is not implemented.
- Shell write detection is word-list based and can miss writes hidden inside scripts.
- The check measures behaviour volume, not whether the record is any good.

### Pitfalls (symptom -> root cause -> fix)

- Escalation tier never appears -> the counter was written only on transitions (case 5) -> write the counter you later read, test the branch.
- Every scheduled session produces a fire -> the same criteria were applied to unattended sessions -> tag the harness on every ledger row and filter by it when showing debt to a human.
- Audit shows twice the debt -> sub-agent transcripts counted as sessions -> skip them and show the count skipped.
- A gate's fixtures are real sessions -> private content -> build synthetic transcripts with the same event shape.
- The second agent's sessions always "clean" -> parser did not recognise its format (case 10) -> replay one real sample of every host's format through every shared hook.
- Receipts in a compound workflow ignored -> by design -> run the verify call alone.

### The rule

Do not defend text with more text. Decide what a trustworthy call looks like structurally, accept only that, and let an independent auditor recompute the verdict from raw data.

## Public implementation boundary

The public core uses generic hooks/tooling/settings paths and synthetic host-format messages. It does not include the second-agent parser or a live hook installer. Only harness-written calls and paired direct results can count. The public auditor substitutes a caller-supplied nonempty-file existence check for the private database query; it does not authenticate transcript authorship, prove content quality or provide a separate security identity.
