# Chapter 6: Laziness versus forgery

### Problem

We wanted a fast lane for a templated task: let a script check the facts and let that check stand in for a full independent review. The script's evidence (snapshot, manifest, results) lived in files the executing agent could write. Five rounds of adversarial review followed, each fixing the previous round's main defect and each finding a new way to forge a pass.

### What we built or changed

A sequence of local fact gates, ending in a gate with one registry as the only trust anchor, plus a stop-loss decision. Mechanism of the final gate (version 3), in enough detail to build a toy:

- **Registry** (JSON): per template name, the template version, SHA-256 of the template and of the gate, the root of the files under check, a required tag for ad-hoc notes, the allowed skill roots, the state directory, the verifier command, the declared route for each of four tasks, the approver, and the recorded disposition of the three planning lanes (evidence, skeptic, decision).
- **Snapshot**: before the work, the gate writes a state directory named by a snapshot id (an id format that rejects separators and `..`): a manifest (recursive list of files with hashes, copy of the raw input, hashes of the targets, top-level directory entries, the gate's and the template's hashes, and the placeholders computed inside the snapshot), plus a sidecar file with the manifest's own hash, both read-only.
- **Check**: takes only a snapshot id (no caller-supplied results, tags, receipts or skill directory) and runs 14 numbered checks (0 gate and template hashes; 1 targets exist and are non-empty; 2 summary starts with the version line; 3 each added item referenced once or covered by a valid receipt; 4 deleted items not referenced; 5 every reference exists; 6 changed groups indexed; 7 evidence unchanged since snapshot; 8 recursive inventory unchanged; 9 referenced skills exist and match snapshot hashes; 10 entry metadata matches headers; 11 added references unique; 12 ad-hoc notes carry the tag in both targets; 13 parameter-consistency result archived).
- **Closeout checker**: validates the volume's provenance against the registry (template name and version, lane dispositions equal to the registry, one route-outcome row per task with enumerated routes and `result=done`, no unauthorised new files, and the closeout page via the verifier).
- Declared threat model (in the file header): skipped or forged evidence, concurrent input drift, path traversal and caller-supplied anchors are in scope; an actor who can edit the gate or the registry is out of scope.

### Procedure as actually run

Each round was a fresh reviewer from another vendor with attacker posture, told to write a reproduction for every claim. Tests were added before each fix.

| Round | Target | Tests passing | Findings |
|---|---|---|---|
| 1 | Procedure text and first template | n/a | 18: 9 BLOCKER, 8 MAJOR, 1 MINOR (the fast lane bypasses the active-task check and the decision lane; the three lanes were "kept" in words but not executable; the template's side effects contradicted its allowed-write list) |
| 2 | A shell gate (two scripts) | n/a (static) | 12 new: 3 BLOCKER, 6 HIGH, 3 MEDIUM; plus 18 earlier items re-judged |
| 3 | Gate v1, a Python rewrite (541 lines) | 13 of 13 | 11: 1 BLOCKER, 7 HIGH, 3 MEDIUM; reproduced (for example `PASS` after a new input file added post-snapshot, forged working-directory fields, an empty tag that matches every line, a tampered copy of the previous snapshot) |
| 4 | Gate v2 plus a closeout checker | 30 of 30 | 4 new (2 BLOCKER, 2 HIGH) plus items carried over; the closeout checker accepted a caller-supplied results file and any verifier script that exits 0; the template's YAML block did not parse |
| 5 | Gate v3, registry as the only anchor | 43 of 43 | 11: 3 BLOCKER, 8 HIGH; 85 real subprocess commands, each recorded with argv, stdout, stderr and return code; verdict DO-NOT-MERGE |

Typical shell-gate defects in round 2 (for the toy): `check && exit 1 || true` swallows the earlier failure; a check function called before it is defined (the shell prints "command not found" and carries on); arguments accepted from the caller that decide what "added" and "deleted" mean; `grep -qF` substring counts.

**Round 5 findings, grouped by cause** (the attacker edits only task materials, the target, the manifest, check artifacts or other files; never the gate code or the registry):

| Cause | Findings | Reproduction |
|---|---|---|
| The actor can choose or rewrite the trust anchor | The registry path is a caller argument: a second registry with the attacker's tag, lane text and approver gave snapshot, check and closeout `rc=0`. A forged "pass" result file (fields copied from the public manifest) made closeout `rc=0` while the real gate returned `rc=1`; a stale pass survived drift; a failure that returns early left no artifact so closeout read the old pass. The manifest and its self-check sidecar can be rewritten together; a read-only file is the same actor's file | `rc=0` on all three |
| Evidence proves the past, not the present | A receipt covering a knowledge bullet stays valid after the covered text is deleted from the target; the out-of-scope-writes check took its cutoff from the volume file's mtime, so saving the volume erased the record of an unauthorised file | `rc=0` after the deletion; `rc=0` after one ordinary save |
| An unrecognised format is read as "nothing" | A heading style the parser did not know produced zero knowledge items, so an empty receipt list passed; deleting a whole group with no references passed because `set() <= anything` is true | `rc=0` |
| Self-attestation instead of verification | Replacing the fixed volume body by `done_criteria: []` still passed; a second lane record appended after the first correct one was ignored (only the first match was read); route fields were compared as id sets, not values | `rc=0` |
| Two entry points validate differently | The gate rejected a snapshot id with `..`; the closeout checker accepted it | `rc=2` vs `rc=0` |
| Exemptions by type | Two writable targets were exempt from the type check; replacing one with a symlink to a file outside the root passed | `rc=0` |

Also in the review: the 43 tests were all green because closeout tests wrote the manifest and the pass artifact by hand instead of running the real gate; "43 of 43 green" and "safe to merge" are different statements.

**Decision (stop-loss).** A stop-loss clause on the number of review rounds per target had been written into the plan before the rounds began. After the decision, the lesson was written back as a rule: when adversarial review of one target keeps returning blockers after more than three rounds, stop and ask whether the target is reachable under the stated threat model. Round 5 answered no for the three blockers in the first group. Outcome:

1. The full fast-lane procedure (which let a local gate pass replace the independent review) was not merged.
2. The gate stays as a mistake-catcher for laziness, skipped steps, drift and wrong paths.
3. A minimal increment was merged: one shadow record per newly created task volume from a local decision service (no routing change), and a registered template used as a draft only; every station of the normal procedure runs as before. That change went through three further review rounds that closed all findings; the last open item was a sentence claiming the shadow log stored only hashes, which was not true of the code, so the sentence was corrected and a task-text field removed from the code.
4. Rule written back: no future quick-sign-off design may treat a local gate's PASS as a reason to skip the independent acceptance. True forgery resistance would need the snapshot and result written somewhere the actor cannot write (a separate OS user, or a signature whose key the actor cannot read); that was not built.

### A second case: a review gate on a task board

The first acceptance completed with one run and zero review events because of the profile-reader bug; after that fix, adversarial review reported 12 findings with zero false positives, although the record itemises 11 (three bypass facts, five fixed, three declined), and the claim was narrowed to preventing common slips through the tool layer. Detection moved to a dispatcher scan the worker cannot call: first-day acceptance covered ten boards, 0 stored flags on the baseline run, 1 flag for a command-line bypass with card state unchanged, a legitimate child predating its parent's first run by 17 s, and a count that stayed 1 after rewinding the watermark, plus off/on behaviour. The implementer correctly challenged three specification conflicts, and the draft had five defects, including a baseline return after candidate scanning that would have flagged all history on a board with 20,145 events; the tool layer remains fail-open and the strict scan only flags, because a safe reopen contract was not established.

### Results

| Quantity | Value |
|---|---|
| Review rounds on the gate | 5 (a sixth to eighth on the minimal increment that was merged) |
| Findings per round | 18, 12, 11, 4 new, 11 (56 in total; BLOCKER 9, 3, 1, 2, 3 = 18) |
| Tests passing at the time of each review | n/a, n/a, 13, 30, 43: green in every round; each round still found at least 4 new issues |
| Round 5 evidence | 85 real subprocess commands with argv, stdout, stderr, return code; the 16 items left open or partial after round 4 re-judged with the original attacks: 5 closed, 8 partial, 3 still open |
| Root-cause groups in round 5 | 6 (anchor the actor can choose or rewrite; evidence about the past; unknown format read as nothing; self-attestation; two entry points; type exemptions) |
| Outcome | Do not merge the full fast lane; keep the gate as a mistake-catcher; merge a minimal shadow-and-draft increment |

### What did not work

- Adding more fields to a result JSON the actor can write.
- Marking a manifest read-only and keeping its hash in a neighbouring file.
- Using mtime as a baseline or as consumption evidence.
- Writing the lane records into the volume as free text and checking only the first match.
- More review rounds on the same target after round 3.

### Pitfalls (symptom -> root cause -> fix)

- A gate is green, a forged input is green too -> the verifier reads a file the actor wrote -> verify by re-running the check, not reading a result file.
- Two scripts disagree about what an id may contain -> two parsers -> one shared validator.
- Acceptance run shows everything passes -> the harness hits the gate's own exemption (Chapter 3).
- A claimed guarantee in the decision record -> never tested against a bypass -> add the bypass to the acceptance and write down the downgrade when it works.
- A "no-op" or "nothing to do" outcome accepted without evidence -> the check cannot tell "nothing found" from "could not parse" -> distinguish the two and fail closed on the second.

### The rule

If the actor can write the evidence, the gate catches mistakes, not forgery. For forgery you need a different identity that recomputes the fact from raw data, and anchors the actor cannot write. Decide the stop-loss before round one: past three rounds with blockers on the same target, ask whether the target is reachable at all.

## Public implementation boundary

The new toy implements recursive file snapshots, drift checks and closeout rather than the private domain-specific checks. The hardened variant fixes registry selection in code and recomputes the check during closeout. It still accepts a rewritten manifest/hash pair when both are owned by the actor; separate identities or signing keys are not implemented.
