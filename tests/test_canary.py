import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import hook_canary as canary


class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hooks = self.root / "hooks"
        self.hooks.mkdir()
        self.mirror = self.root / "mirror"
        self.mirror.mkdir()
        self.good = 'import sys\nif "--selftest" in sys.argv: print("selftest PASS")\n'
        (self.hooks / "good.py").write_text(self.good)
        (self.hooks / "plain.py").write_text("value = True\n")
        (self.mirror / "good.py").symlink_to(self.hooks / "good.py")
        self.config = {"settings": "settings.json", "hooks_dir": "hooks", "mirror_dir": "mirror",
                       "alerts": "alerts.jsonl", "required_events": {"good.py": ["PostToolUse", "PostToolUseFailure"], "plain.py": ["Stop"]},
                       "must_have_selftest": ["good.py"]}
        self.settings = {"hooks": {event: [{"hooks": [{"command": f"python3 {name}"}]}]
                                   for name, events in self.config["required_events"].items() for event in events}}
        self.save_settings()

    def save_settings(self):
        (self.root / "settings.json").write_text(json.dumps(self.settings))

    def run_probe(self):
        result = canary.run(self.config, self.root)
        saved = json.loads((self.root / "alerts.jsonl").read_text().splitlines()[-1])
        self.assertEqual(saved, result)
        return result

    def single(self, check, hook, error=None):
        result = self.run_probe()
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["alerts"]), 1, result)
        alert = result["alerts"][0]
        self.assertEqual((alert["check"], alert["hook"]), (check, hook))
        if error:
            self.assertIn(error, alert["error"])
        return alert

    def test_baseline(self):
        self.assertEqual(self.run_probe()["alerts"], [])

    def test_registration_fault(self):
        del self.settings["hooks"]["PostToolUseFailure"]
        self.save_settings()
        self.assertEqual(self.single("registration", "good.py")["missing_events"], ["PostToolUseFailure"])

    def test_syntax_fault_only(self):
        (self.hooks / "good.py").write_text('def broken(:\n# "--selftest"\n')
        self.single("compile", "good.py")

    def test_selftest_exit_failure(self):
        (self.hooks / "good.py").write_text('import sys\nif "--selftest" in sys.argv: sys.exit(1)\n')
        self.single("selftest", "good.py", "rc 1")

    def test_comment_only_flag(self):
        (self.hooks / "good.py").write_text('# "--selftest"\n')
        self.single("selftest", "good.py", "no PASS")

    def test_missing_required_flag(self):
        (self.hooks / "good.py").write_text('value = True\n')
        self.single("selftest", "good.py", "no self-test entry")

    def test_mirror_replaced(self):
        (self.mirror / "good.py").unlink()
        (self.mirror / "good.py").write_text("stale = True\n")
        self.single("mirror", "good.py")

    def test_missing_command_records_crash(self):
        self.config["commands"] = [{"name": "dependency", "argv": [str(self.root / "missing")], "expect_rc": 0, "expect_stdout": "PONG\n"}]
        self.single("dependency", "dependency", "FileNotFoundError")

    def test_lost_execute_permission_records_crash(self):
        tool = self.root / "tool"
        tool.write_text("#!/bin/sh\necho PONG\n")
        self.config["commands"] = [{"name": "dependency", "argv": [str(tool)], "expect_rc": 0, "expect_stdout": "PONG\n"}]
        self.single("dependency", "dependency", "PermissionError")

    def test_timeout(self):
        self.config["commands"] = [{"name": "dependency", "argv": [sys.executable, "-c", "import time; time.sleep(90)"], "timeout": 0.05, "expect_rc": 0, "expect_stdout": ""}]
        self.single("dependency", "dependency", "TimeoutExpired")

    def test_clean_environment(self):
        self.config["commands"] = [{"name": "dependency", "argv": ["{python}", "-c", "import os; print(os.environ['PATH'])"], "clean_env": True,
                                    "expect_rc": 0, "expect_stdout": canary.SYSTEM_PATH + "\n"}]
        self.assertTrue(self.run_probe()["ok"])

    def test_exact_output(self):
        self.config["commands"] = [{"name": "dependency", "argv": ["{python}", "-c", "print('Prompt: PONG')"], "expect_rc": 0, "expect_stdout": "PONG\n"}]
        self.single("dependency", "dependency")

    def test_content_cases_and_crash_are_distinct(self):
        self.config.update(gate_cases="cases.json", gate_argv=[sys.executable, str(ROOT / "examples/content_gate.py")])
        (self.root / "cases.json").write_text(json.dumps([{"label": "block", "body": "DEMO-BLOCK", "want_block": True},
                                                        {"label": "allow", "body": "plain", "want_block": False}]))
        self.assertTrue(self.run_probe()["ok"])
        self.config["gate_argv"] = [sys.executable, "-c", "raise RuntimeError('crash')"]
        self.assertEqual(len(self.run_probe()["alerts"]), 2)

    def test_required_hook_missing(self):
        (self.mirror / "good.py").unlink()
        (self.hooks / "good.py").unlink()
        self.single("compile", "good.py", "file missing")


if __name__ == "__main__":
    unittest.main()
