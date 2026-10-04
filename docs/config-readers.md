# Chapter 4: Config that exists but is not read

### Problem

A configuration key can be present, valid and documented, and have no effect, or an effect only in an environment other than the one you tested. A configuration cleanup is also a place where a "fix" can become the silent failure: you point a dead key at a live target and it still does nothing. The cases in this chapter are one cleanup (a key with no reader), one stale copy of a catalogue file, and four environment-visibility cases.

### What we built or changed

A procedure (the "reader check"), one rule for non-authoritative copies, and one acceptance rule for gates that read configuration. No tool existed for the reader check at the time; the shipped literal-search script is a new, limited implementation of that procedure.

**The reader check.** For each configuration key you want to trust:

1. Find its readers in the source tree of the version that is actually running (not the docs, not another version, not the installer). A key that appears only in a known-keys whitelist (so the validator does not complain) or in a setup wizard that writes a default does not count as having a reader.
2. If there is a reader, check where it reads from, in the environment it runs in: which file, which profile directory, which environment block. A reader that reads another file than the one you edited has no effect on your edit.
3. Compare the file with the effective runtime state where the platform exposes it (for a scheduler: ask for the job's resolved environment; for a process: its real environment; for a service: a config or status endpoint).
4. Make the check a test: run the consumer once in its real environment and assert the effect (a fallback counter stays 0; a request carries the credential; a gate triggers).

**Case A: a routing block with no reader.** An agent gateway's configuration contained a block that looked like model routing for multimodal requests, naming two fallbacks that pointed at inference hosts that no longer existed; several profiles also defined those two provider names, and one profile's `fallback_providers` listed only them (both hops dead, which is no fallback). Searching the running version's whole source tree found zero references to the two keys of the block. The block's name occurred in exactly two places: the known-root-keys whitelist of the config validator and the setup wizard, which writes `enabled=False`. The real vision path was a different key (`auxiliary.vision`) that already pointed at live backends. Decision: delete the whole block (three configs) and the two provider definitions (six configs); set the dead fallback list to empty so that the cloud fallback configured elsewhere carries the load; do not repoint the dead key, because repointing would keep a key that nothing reads. Verification: parse the old and new YAML and assert the difference equals exactly the expected deletions; run the gateway's own loader and structure validator on the five active configs (zero issues); no gateway restart because the deleted keys had no reader and the fallback list is re-read at run time.

**Case B: a stale copy of a catalogue file.** The infrastructure catalogue (one YAML file that agents are told is the source of truth at a fixed path) existed in a stale copy on a secondary machine: revision 2026-09-26.02 against the authoritative 2026-09-28.1. An agent on that machine following "the source of truth is that path" would read old data. Deleting the copy would send agents to the `.bak` files next to it, which are older still. Decision: replace the copy with a pointer stub that states where the authoritative file is and the exact command to read it remotely, and that deliberately contains no top-level `services` key, so a program that parses it as the catalogue raises an error instead of silently using stale data. The old file went into a dated `_stale-copy-<date>/` directory together with its `.bak` files and drift baseline.

**Case C: a policy table read in the wrong profile.** A missing default reviewer became an exemption: 1 of 1 tested worker profile returned `None`, while the default home returned the reviewer; discovery was about 2 days after landing (09-06 to 09-08). After resolving policy from the root independently of the profile, 4 profile environments were checked; the complete before/after table is in [results](results.md).

**Case D: our agent gateway.** For 4 days (09-02 to 09-06), consumers lacked the gateway credential, an optional-module error turned 401 into 500, and fallbacks hid the failure; with the correct key, 6 of 6 aliases returned 200. The variable was added to 3 profile environments with mode 600 retained, and the consumer regression produced zero fallback lines; 4 profiles also had empty title credentials, and a real title returned after a local keyless endpoint was configured.

**Case E: duplicate scheduler dictionaries.** Two `EnvironmentVariables` dictionaries left only the second effective, with 2 variables (escalation target and PATH). Removing the dead dictionary passed lint with zero behaviour change; the record was corrected to distinguish the intended setting from the effective environment.

### Procedure as actually run

1. Case D: found from a self-announcing log line in a worker ("Model fallback: ... via ... unavailable (provider failure)"); traced to the key; patched; verified with a regression card.
2. Case C: first acceptance failed; per-profile test; patch; later re-verified after moving the code.
3. Case E: surfaced by an adversarial review of a cleanup volume; verified with `grep -c EnvironmentVariables` (2) and the scheduler's resolved environment.
4. Cases A and B: during a clean-up on 2026-10-02, with the source search and the parse-diff test above.

### Results

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

### What did not work

- Pointing a dead key at a live target: still a dead key.
- Leaving the stale copy in place with a comment: agents read the file, not the comment.
- Deleting the stale copy: leads to `.bak` files.
- Testing a gate only in the default home (case C), and testing it with a card whose body already named the reviewer.
- Verifying a restart by looking at the health endpoint (see the orphan-process case in Chapter 3).

### Pitfalls (symptom -> root cause -> fix)

- A feature "configured" yet inert -> no reader, or a reader of another file -> run the reader check.
- A gate passes everything in workers but blocks in your shell -> profile-dependent config loading returned `None` -> resolve fleet-level keys from the root; test in a profile environment.
- Every call returns 500 "provider failure" and a fallback hides it -> missing credential, error handler raised a secondary error -> test with the consumer's own credential and assert the fallback counter is 0.
- Two documents claim to be the source of truth -> an old copy -> stub without the key structure.
- A scheduler job ignores an environment variable -> duplicate keys in the property list -> read the resolved environment, not the file.

### The rule

Before you trust a configuration key, find its reader in the code that runs, check that the reader looks where you wrote the key, from the environment it runs in, and test the effect once in that environment.

## Public implementation boundary

The JSON reader check reports string-literal candidates. A string in executable source can still be a writer, dead code or the wrong consumer; dynamic reads may be missed and repeated leaf names may be ambiguous. It cannot establish runtime use. The final acceptance step remains a run of the real consumer in its own environment, which is not part of this offline book.
