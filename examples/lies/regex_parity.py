#!/usr/bin/env python3
"""Report observed engine parity; bracket escaping depends on the grep build."""
import platform
import re
import subprocess
import warnings

CASES = [(r"[[:space:]]", " ", 0), (r"[[:space:]]", "Z", 0),
         (r"[\[<]", "\\", 0), (r"[\[<]", "<", 0), (r"[\[<]", "Z", 0),
         (r"(\[|<)", "[", 0), (r"(\[|<)", "Z", 0),
         (r"[ \t]", " ", 0), (r"[ \t]", "Z", 0),
         (r"^label$", "body\nlabel\nend", 0),
         (r"^label$", "body\nlabel\nend", re.M), (r"^label$", "body", re.M)]


def compare():
    results = []
    for pattern, body, flags in CASES:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            py = bool(re.search(pattern, body, flags))
        grep = subprocess.run(["grep", "-E", pattern], input=body + "\n", text=True, capture_output=True)
        if grep.returncode not in (0, 1):
            raise RuntimeError(grep.stderr)
        results.append((pattern, body, flags, py, grep.returncode == 0))
    return results


if __name__ == "__main__":
    version = subprocess.run(["grep", "--version"], capture_output=True, text=True)
    print("Python " + platform.python_version())
    print((version.stdout or version.stderr).splitlines()[0])
    for pattern, body, flags, py, grep in compare():
        print(f"{'AGREE' if py == grep else 'DISAGREE'} {pattern!r} input={body!r} flags={flags}: Python={py} grep={grep}")
