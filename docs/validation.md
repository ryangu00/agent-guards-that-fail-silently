# Offline validation of the public examples

These are execution results for this checkout's synthetic tests. They are separate from the historical measurements in `results.md`; they do not reproduce the original deployment, review rounds or scheduler acceptance.

The test environment used Python 3.14.6. All dependencies used by the test suite were local.

```bash
mkdir -p .work
TMPDIR="$PWD/.work" PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Exact result lines from the repository-local temporary-directory run:

```text
Ran 35 tests in 2.691s

OK
hook-selftest-on-edit selftest PASS
```

The standalone entry points were also run:

```text
hook-canary self-test PASS
hook-selftest-on-edit selftest PASS
receipt forgery tests PASS
hook-canary: clean
```

Every Bash command block in `reproduce.md` was executed in order in a disposable copy, retaining shell variables between blocks. Expected failure statuses were checked as well as successful statuses:

```text
Reproduction guide: PASS (all documented command blocks executed)
Publication checks: PASS (text restrictions; table inventory; links; syntax; template-only banner edits)
Template copies: PASS (LICENSE and .gitignore byte-for-byte)
Banner execution: rendered with the supplied script
```

Publication checks covered CJK characters, private path/name patterns, non-loopback address-shaped values, Markdown table widths, local links, Python compilation, shell syntax, the case/table inventory and the exact permitted banner-template substitutions. The required LICENSE copyright notice is retained as a public credit. These checks are not a general secret-scanner guarantee.

The tables were directly transcribed during input reading and retain historical qualifications. The raw input directory resolved to the cookbook staging directory; raw staging files were removed from the public deliverable after adaptation. A fresh byte-for-byte comparison of tables against those removed raw inputs was therefore not performed at closeout.
