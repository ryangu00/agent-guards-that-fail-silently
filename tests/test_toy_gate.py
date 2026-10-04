import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ToyGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "scripts/toy_gate", self.root / "toy", ignore=shutil.ignore_patterns("__pycache__"))
        self.toy = self.root / "toy"
        (self.toy / "target").mkdir()
        self.target = self.toy / "target/note.md"
        self.target.write_text("before\n")
        result = self.command("toy_gate.py", "snapshot", "target", "state")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.snap = result.stdout.strip()

    def command(self, script, *args):
        executable = "/bin/sh" if script.endswith(".sh") else sys.executable
        return subprocess.run([executable, str(self.toy / script), *map(str, args)], cwd=self.toy,
                              capture_output=True, text=True)

    def test_real_check_drift_and_forged_artifact(self):
        self.assertEqual(self.command("toy_gate.py", "check", "--snap", self.snap).returncode, 0)
        self.target.write_text("after\n")
        self.assertEqual(self.command("toy_gate.py", "check", "--snap", self.snap).returncode, 1)
        result = self.command("forge_pass_artifact.sh", self.toy / "state" / self.snap)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.command("toy_gate.py", "closeout", "--snap", self.snap).returncode, 0)
        self.assertEqual(self.command("hardened_gate.py", "closeout", "--snap", self.snap).returncode, 1)

    def test_rewritten_manifest_pair_remains_a_residual(self):
        self.target.write_text("after\n")
        self.assertEqual(self.command("toy_gate.py", "check", "--snap", self.snap).returncode, 1)
        self.assertEqual(self.command("forge_manifest_pair.py", self.toy / "state" / self.snap).returncode, 0)
        self.assertEqual(self.command("toy_gate.py", "check", "--snap", self.snap).returncode, 0)
        self.assertEqual(self.command("hardened_gate.py", "closeout", "--snap", self.snap).returncode, 0)

    def test_forged_registry_and_fixed_registry(self):
        self.target.write_text("after\n")
        forged = self.toy / "forged.json"
        alternate = self.toy / "alternate-state"
        self.assertEqual(self.command("forge_registry.sh", forged, self.target.parent, alternate).returncode, 0)
        result = self.command("toy_gate.py", "--registry", forged, "snapshot", self.target.parent, alternate)
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = result.stdout.strip()
        self.assertEqual(self.command("toy_gate.py", "--registry", forged, "check", "--snap", snapshot).returncode, 0)
        self.assertEqual(self.command("toy_gate.py", "--registry", forged, "closeout", "--snap", snapshot).returncode, 0)
        self.assertEqual(self.command("hardened_gate.py", "closeout", "--snap", self.snap, "--registry", forged).returncode, 2)
        self.assertEqual(self.command("hardened_gate.py", "closeout", "--snap", self.snap).returncode, 1)

    def test_shared_identifier_validation_and_recursive_drift(self):
        for script in ("toy_gate.py", "hardened_gate.py"):
            for action in ("check", "closeout"):
                self.assertEqual(self.command(script, action, "--snap", "../escape").returncode, 2)
        (self.target.parent / "nested").mkdir()
        (self.target.parent / "nested/new.md").write_text("new")
        self.assertEqual(self.command("toy_gate.py", "check", "--snap", self.snap).returncode, 1)

    def test_hardened_snapshot_and_closeout_use_real_check(self):
        result = self.command("hardened_gate.py", "snapshot")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.command("hardened_gate.py", "closeout", "--snap", result.stdout.strip()).returncode, 0)


if __name__ == "__main__":
    unittest.main()
