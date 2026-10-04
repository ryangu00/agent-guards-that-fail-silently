#!/usr/bin/env python3
"""Configurable offline guard probes, adapted from the supplied daily canary."""
import argparse
import filecmp
import json
import os
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def selftest_flag(path):
    source = Path(path).read_text(encoding="utf-8")
    return next((flag for flag in ("--selftest", "--self-test") if flag in source), None)


def compile_error(path):
    try:
        # Bytecode stays in a temporary directory, never beside a checked hook.
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(path), cfile=str(Path(tmp) / "hook.pyc"), doraise=True)
    except Exception as exc:
        return str(exc)
    return None


def selftest_error(path, required=False, timeout=180):
    flag = selftest_flag(path)
    if not flag:
        return "no self-test entry" if required else None
    result = subprocess.run([sys.executable, str(path), flag], input="", text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        return f"rc {result.returncode}"
    if not re.search(r"\bPASS\b", result.stdout):
        return "no PASS"
    return None


def registration(settings, required):
    seen = {}
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                for name in required:
                    if name in hook.get("command", ""):
                        seen.setdefault(name, set()).add(event)
    return [{"check": "registration", "hook": name,
             "missing_events": sorted(set(events) - seen.get(name, set()))}
            for name, events in required.items() if set(events) - seen.get(name, set())]


def run_command(spec, base):
    argv = [sys.executable if arg == "{python}" else arg for arg in spec["argv"]]
    env = {"PATH": SYSTEM_PATH, "LC_ALL": "C", "PYTHONUTF8": "1"} if spec.get("clean_env") else None
    result = subprocess.run(argv, cwd=base, env=env, input="", text=True,
                            capture_output=True, timeout=spec.get("timeout", 180))
    if result.returncode != spec["expect_rc"] or result.stdout != spec["expect_stdout"]:
        return [{"check": spec["name"], "hook": spec["name"],
                 "error": f"rc={result.returncode}; unexpected status or stdout"}]
    return []


def run(config, base):
    base = Path(base).resolve()
    resolve = lambda value: base / value
    alerts, checks = [], []

    def guarded(name, fn, hook=None):
        checks.append(name)
        try:
            alerts.extend(fn())
        except Exception as exc:
            alerts.append({"check": name, "hook": hook or name,
                           "error": f"probe crashed: {type(exc).__name__}: {exc}"})

    required = config["required_events"]
    directory = resolve(config["hooks_dir"])
    guarded("registration", lambda: registration(json.loads(resolve(config["settings"]).read_text()), required))
    broken = set()
    for name in required:
        path = directory / name

        def compile_one(path=path, name=name):
            error = "file missing" if not path.is_file() else compile_error(path) if path.suffix == ".py" else None
            if error:
                broken.add(name)
                return [{"check": "compile", "hook": name, "error": error}]
            return []
        guarded("compile", compile_one, name)
    must = set(config.get("must_have_selftest", []))

    def selftests():
        result = []
        for name in sorted({p.name for p in directory.glob("*.py")} | must):
            if name in broken:
                continue  # A syntax fault has one causal alert, not a duplicate run failure.
            try:
                error = selftest_error(directory / name, name in must, config.get("selftest_timeout", 180))
            except Exception as exc:
                error = f"probe crashed: {type(exc).__name__}: {exc}"
            if error:
                result.append({"check": "selftest", "hook": name, "error": error})
        return result
    guarded("selftest", selftests)
    if config.get("mirror_dir"):
        def mirror():
            return [{"check": "mirror", "hook": p.name, "error": "contents differ"}
                    for p in sorted(resolve(config["mirror_dir"]).iterdir())
                    if ".bak" not in p.name and (directory / p.name).is_file()
                    and not filecmp.cmp(p, directory / p.name, shallow=False)]
        guarded("mirror", mirror)
    for spec in config.get("commands", []):
        guarded(spec["name"], lambda spec=spec: run_command(spec, base))
    if config.get("gate_cases"):
        def content_gate():
            output = []
            cases = json.loads(resolve(config["gate_cases"]).read_text())
            argv = [sys.executable if a == "{python}" else a for a in config["gate_argv"]]
            for case in cases:
                result = subprocess.run(argv + ["--check-only"], input=case["body"], cwd=base,
                                        text=True, capture_output=True, timeout=180,
                                        env={"PATH": SYSTEM_PATH, "PYTHONUTF8": "1"})
                # A crash must not be mistaken for an intentional denial.
                expected = 1 if case["want_block"] else 0
                if result.returncode != expected or result.stdout.strip() != ("BLOCK" if expected else "ALLOW"):
                    output.append({"check": "content-gate", "hook": case["label"], "error": "unexpected decision"})
            return output
        guarded("content-gate", content_gate)
    record = {"ts": datetime.now(timezone.utc).isoformat(), "ok": not alerts,
              "alerts": alerts, "checks": sorted(set(checks))}
    ledger = resolve(config["alerts"])
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        import unittest
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[1] / "tests"), pattern="test_canary.py")
        result = unittest.TextTestRunner().run(suite)
        if result.wasSuccessful():
            print("hook-canary self-test PASS")
        return int(not result.wasSuccessful())
    if not args.config:
        parser.error("--config is required")
    try:
        record = run(json.loads(args.config.read_text()), args.config.resolve().parent)
    except Exception as exc:
        print(f"ALERT: canary could not run or persist its record: {exc}", file=sys.stderr)
        return 1
    print("hook-canary: clean" if record["ok"] else "hook-canary: ALERT")
    if record["alerts"]:
        print(json.dumps(record["alerts"]), file=sys.stderr)
    return int(not record["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
