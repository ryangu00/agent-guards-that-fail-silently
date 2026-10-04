from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))
import config_reader_check
import index_drift_check
import hook_selftest_on_edit
import status_line
import path_canary


class UtilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def shell(self, script, *args, env=None, input=None):
        return subprocess.run(["/bin/bash", str(ROOT / script), *map(str, args)], capture_output=True,
                              text=True, input=input, env=env or dict(os.environ, PYTHON=sys.executable))

    def test_edit_hook_selftest_and_stdin(self):
        hook_selftest_on_edit.selftest()
        hook = self.root / "red.py"
        hook.write_text('import sys\nif "--selftest" in sys.argv: sys.exit(3)\n')
        command = [sys.executable, str(ROOT / "scripts/hook_selftest_on_edit.py"), "--hooks-dir", str(self.root)]
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(hook)}}
        result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"].startswith("[RED]"))
        payload["tool_input"]["file_path"] = str(self.root.parent / "outside.py")
        self.assertEqual(subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True).stdout, "")

    def test_scheduler_path_output_and_timeout(self):
        binary = self.root / "mytool"
        binary.write_text("#!/bin/sh\necho PONG\n")
        binary.chmod(0o755)
        env = dict(os.environ, PYTHON=sys.executable, PATH=str(self.root) + ":/usr/bin:/bin")
        self.assertEqual(subprocess.run(["mytool"], env=env, capture_output=True, text=True).stdout, "PONG\n")
        result = self.shell("scripts/env_probe.sh", "mytool", env=env)
        self.assertEqual((result.returncode, result.stdout), (1, "FAIL rc=127 out=[]\n"))
        env["ADD_PATH"] = str(self.root)
        self.assertEqual(self.shell("scripts/env_probe.sh", "mytool", env=env).stdout, "PASS\n")
        binary.write_text("#!/bin/sh\necho 'prompt PONG'\n")
        self.assertEqual(self.shell("scripts/env_probe.sh", "mytool", env=env).returncode, 1)
        env["TIMEOUT"] = "0.05"
        result = self.shell("scripts/env_probe.sh", sys.executable, "-c", "import time; time.sleep(90)", env=env)
        self.assertIn("rc=124", result.stdout)

    def test_pause_states_and_missing_python(self):
        now = datetime.now(timezone.utc)
        for name, body, rc, reason in [
            ("fresh", {"_ts": now.isoformat(), "paused": False}, 1, ""),
            ("paused", {"_ts": now.isoformat(), "paused": True}, 0, "requested"),
            ("old", {"_ts": (now-timedelta(days=4)).isoformat(), "paused": False}, 0, "stale"),
            ("bad", "garbage", 0, "unreadable"),
            ("missing", None, 0, "missing"),
            ("future", {"_ts": (now+timedelta(days=1)).isoformat(), "paused": False}, 0, "unreadable")]:
            with self.subTest(name=name):
                path = self.root / name
                if body is not None:
                    path.write_text(json.dumps(body) if isinstance(body, dict) else body)
                result = self.shell("scripts/is_paused.sh", path)
                self.assertEqual(result.returncode, rc)
                self.assertIn(reason, result.stderr)
        result = self.shell("scripts/is_paused.sh", self.root / "fresh", env={"PATH": "/usr/bin:/bin", "PYTHON": str(self.root / "missing-python")})
        self.assertEqual(result.returncode, 0)
        self.assertIn("Python missing", result.stderr)

    def test_status_states(self):
        now = datetime.now(timezone.utc)
        files = {name: self.root / name for name in ("healthy", "red", "stale", "missing", "unreadable")}
        for name in ("healthy", "red", "stale"):
            files[name].write_text(json.dumps({"ts": (now-timedelta(hours=80) if name == "stale" else now).isoformat(), "ok": name != "red"}) + "\n")
        files["unreadable"].write_text("bad")
        self.assertEqual(status_line.status_lines(files, now=now), ["[RED] red", "[STALE] stale", "[MISSING] missing", "[UNREADABLE] unreadable"])

    def test_index_orphan_claim_size_and_fix_scope(self):
        for index in range(10):
            (self.root / f"topic{index}.md").write_text("topic\n")
        index = self.root / "INDEX.md"
        index.write_text("2 files are not in this index\n" + "\n".join(f"[topic](topic{n}.md)" for n in range(7)))
        archive = self.root / "ARCHIVE.md"
        archive.write_text("[topic](topic7.md)\n[topic](topic8.md)\n")
        run = lambda **kw: index_drift_check.check(self.root, ["INDEX.md", "ARCHIVE.md"], r"(\d+) files are not in this index", **kw)
        result = run()
        self.assertEqual((result["true_orphans"], result["claim"], result["orphans"]), (1, 2, 3))
        self.assertIn("claim 2 != 3", result["errors"])
        before = index.read_text()
        result = run(fix=True)
        self.assertEqual(index.read_text(), before.replace("2 files", "3 files"))
        self.assertEqual(result["true_orphans"], 1)
        archive.write_text(archive.read_text() + "[topic](topic9.md)\n")
        self.assertEqual(run()["errors"], [])
        index.write_text(index.read_text() + "\n" + "x" * 30000)
        self.assertIn("size exceeds 24000 bytes", run()["errors"])
        self.assertIn("line exceeds 600 bytes", run()["errors"])

    def test_config_readers(self):
        (self.root / "app.py").write_text('value = config["active"]\n')
        (self.root / "validator.py").write_text('known = {"inert"}\n')
        (self.root / "wizard.py").write_text('config["inert"] = False\n')
        rows = config_reader_check.check({"active": True, "inert": False, "absent": True}, self.root, {"validator.py", "wizard.py"})
        self.assertEqual([r["status"] for r in rows], ["has reader", "no reader", "no reader"])
        self.assertTrue(rows[1]["allowlisted_only"])
        self.assertFalse(rows[2]["allowlisted_only"])

    def test_path_canary(self):
        old = path_canary.detect(path_canary.canary())
        self.assertTrue(old.hit)
        self.assertEqual(old.basis, "fallback")
        self.assertFalse(path_canary.detect(path_canary.canary(), True).hit)
        self.assertFalse(path_canary.allows_egress("clean", path_canary.canary(), True))
        self.assertEqual(path_canary.detect(path_canary.canary(True), True).basis, "main")
        self.assertTrue(path_canary.allows_egress("clean", path_canary.canary(True), True))

    def test_lying_probes(self):
        result = subprocess.run([sys.executable, str(ROOT / "examples/lies/fake_selftest.py")], text=True, capture_output=True)
        self.assertIn("naive: GREEN", result.stdout)
        self.assertIn("right: RED", result.stdout)
        for script in ("echoed_prompt.sh", "empty_catalog.sh"):
            result = self.shell("examples/lies/" + script)
            self.assertEqual(result.returncode, 0)
            self.assertIn("naive: GREEN", result.stdout)
            self.assertIn("right: RED", result.stdout)
        result = self.shell("examples/lies/pipe_status.sh")
        self.assertEqual(result.stdout, "naive: rc=0\nright: rc=1\n")
        result = subprocess.run([sys.executable, str(ROOT / "examples/lies/regex_parity.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DISAGREE '[[:space:]]'", result.stdout)
        self.assertIn("Python ", result.stdout)

    def test_daily_run_drift_failure_and_stale_marker(self):
        tool = self.root / "mytool"
        tool.write_text("#!/bin/sh\necho PONG\n")
        tool.chmod(0o755)
        marker = self.root / "marker"
        marker.touch()
        drift = self.root / "drift.json"
        drift.write_text(json.dumps([sys.executable, "-c", "print('ok')"]))
        env = {"PATH": "/usr/bin:/bin", "PYTHON": sys.executable, "LOG": str(self.root / "daily.log"), "MARKER": str(marker), "DRIFT_CONFIG": str(drift)}
        result = self.shell("scripts/daily_probes.sh", "mytool", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("PROBE FAIL", result.stderr)
        env["ADD_PATH"] = str(self.root)
        self.assertEqual(self.shell("scripts/daily_probes.sh", "mytool", env=env).returncode, 0)
        drift.write_text(json.dumps([sys.executable, "-c", "print('FAIL'); raise SystemExit(1)"]))
        result = self.shell("scripts/daily_probes.sh", "mytool", env=env)
        self.assertIn("DRIFT FAIL", result.stderr)
        marker.unlink()
        self.assertIn("MARKER FAIL", self.shell("scripts/daily_probes.sh", "mytool", env=env).stderr)


if __name__ == "__main__":
    unittest.main()
