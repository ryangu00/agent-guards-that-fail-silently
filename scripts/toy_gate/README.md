# Actor-owned evidence

This new generic reference implementation illustrates the fact sheet's trust-anchor failures; none of the private reference-gate source or domain fixtures is shipped.

Copy this directory into a disposable directory, create `target/`, and keep `state/` outside it. The local `registry.json` names those relative paths. `toy_gate.py snapshot DIR STATE` writes a recursive file-hash manifest and read-only hash sidecar. `check --snap ID` compares the current target and writes a result artifact. Deliberately weak `closeout --snap ID` trusts the newest lexically named `check-*.json` artifact. The optional caller-selected `--registry` is deliberately unsafe.

The demonstrations target only that disposable state:

- `forge_pass_artifact.sh SNAPSHOT_DIRECTORY` writes a newest passing artifact after a real failed check.
- `forge_manifest_pair.py SNAPSHOT_DIRECTORY` changes both actor-owned hashes to bless drift.
- `forge_registry.sh REGISTRY TARGET STATE` supplies another registry and a new snapshot location.

`hardened_gate.py` reads only the registry next to its own code and reruns `check` during closeout. This rejects a forged artifact and a caller-selected registry. It does not reject the rewritten manifest/hash pair, nor can it protect code or registry files owned by the actor. Both entry points share the snapshot-id validator.

These tests call real subprocess entry points before attacks. They do not manufacture green setup artifacts as a substitute for executing the gate. See [the full reproduction](../../docs/reproduce.md) and `tests/test_toy_gate.py`. The toy checks file content/inventory, not the private gate's 14 domain checks; it does not implement protected identities or signatures.
