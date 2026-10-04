# Structural receipts

This standard-library adaptation keeps the supplied core's receipt predicate and work-shape thresholds. It replaces private paths with generic `hooks`, `tooling`, `settings.json`, `INSTRUCTIONS.md`, `tasks`, `memory`, `WORKLOG.md` and exempt scratch/decision/ledger paths.

`make_synthetic_transcripts.py DIRECTORY` generates host-format JSONL. Assistant `tool_use` and user `tool_result` records pair by id. The parser rejects duplicate ids/results, and only direct tool results supply receipts. It does not parse another host's model-authored wrapper code. A real integration must use harness-written execution events and test each independent consumer of that format.

`core.py` is a pure verdict layer after transcript reading. It detects infrastructure, project and research work and reports missing records. The constants are the historical rule's 3 files, 8 retrievals, 3,000-character sub-agent result weighted as 3 retrievals, and 48-hour task-clean window. It warns conceptually; it is not an installed blocking hook. Shell write detection remains a word-list heuristic and cannot see writes hidden inside programs.

`auditor.py TRANSCRIPTS --notes NOTES --output OUTPUT` recomputes verdicts and checks each accepted slug through a nonempty-file predicate. Sub-agent files are skipped visibly. Missing notes, predicate exceptions and malformed transcripts remain debt. Output is a debt JSONL, Markdown list and append-only heartbeat; it is synthetic demonstration state, not a production ledger.

`receipt-tool --notes NOTES --slug SLUG --body TEXT` writes a toy note and prints the receipt. Command basename is not executable authentication. Existing slug reuse, actor-edited transcripts, low-quality records and actor-owned note storage remain outside this local assurance.

Run `python3 scripts/receipt_gate/test_forgery.py` from the repository root. [The reproduction guide](../../docs/reproduce.md) gives the full command sequence. A successful forgery-table test means the specified negative inputs were rejected and documented residuals still reproduce; it is not a security certification.
