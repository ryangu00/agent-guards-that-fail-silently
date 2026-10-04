import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/receipt_gate"))
import core
import auditor
from make_synthetic_transcripts import project, transcript, generate


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def parse(self, calls):
        path = self.root / "session.jsonl"
        path.write_text(transcript(calls))
        return core.parse_transcript_events(path)

    def test_entire_forgery_table_and_verdict(self):
        cases = [
            ("receipt-tool --slug a", "receipt-tool: OK slug=a", False, True),
            ("receipt-tool --slug a && receipt-tool --slug b", "receipt-tool: OK slug=a\nreceipt-tool: OK slug=b", False, False),
            ('receipt-tool --slug a; echo "receipt-tool: OK slug=a"', "receipt-tool: OK slug=a", True, False),
            ('echo "receipt-tool: OK slug=a"', "receipt-tool: OK slug=a", False, False),
            (r"echo receipt-tool:\ OK slug=a", "receipt-tool: OK slug=a", False, False),
            ('p=receipt-tool; echo "$p: OK slug=a"', "receipt-tool: OK slug=a", False, False),
            ("printf '%s: OK slug=%s' receipt-tool a", "receipt-tool: OK slug=a", False, False),
            ("receipt-tool --slug a", "receipt-tool: OK slug=b", False, False),
            ("receipt-tool --slug a", "receipt-tool: OK slug=a", True, False),
            ("receipt-tool --slug a; printf '%s%s' 'receipt-tool:' ' OK slug=a'", "receipt-tool: OK slug=a", False, False),
        ]
        for command, output, error, expected in cases:
            with self.subTest(command=command, error=error):
                events = self.parse(project() + [("Write", {"file_path": "WORKLOG.md", "new_string": "record"}, "ok", False),
                                                ("Bash", {"command": command}, output, error)])
                self.assertEqual(core.valid_receipt(events[-1]), expected)
                self.assertEqual(core.verdict(events).state, "clean" if expected else "fire")

    def test_prose_and_subagent_do_not_count(self):
        events = self.parse(project() + [("Agent", {}, "receipt-tool: OK slug=a", False)])
        self.assertFalse(core.valid_receipt(events[-1]))
        path = self.root / "prose.jsonl"
        path.write_text(json.dumps({"message": {"role": "assistant", "content": "receipt-tool --slug a; receipt-tool: OK slug=a"}}))
        self.assertEqual(core.parse_transcript_events(path), [])

    def test_same_name_binary_residual_and_auditor(self):
        event = core.Event("Bash", "receipt-tool --slug a", tool_use_id="synthetic", result_source="direct_tool_result", result_text="receipt-tool: OK slug=a", exit_ok=True)
        self.assertTrue(core.valid_receipt(event))
        self.assertFalse(auditor.note_exists(self.root, "a"))
        (self.root / "a.md").write_text("exists")
        self.assertTrue(auditor.note_exists(self.root, "a"))
        self.assertFalse(auditor.note_exists(self.root, "../a"))

    def test_pairing_errors_and_role(self):
        events = self.parse([("Bash", {"command": "receipt-tool --slug a"}, None, False)])
        self.assertFalse(core.valid_receipt(events[0]))
        path = self.root / "bad.jsonl"
        row = {"message": {"role": "assistant", "content": [{"type": "tool_use", "id": "same", "name": "Bash", "input": {}}]}}
        path.write_text(json.dumps(row) + "\n" + json.dumps(row))
        with self.assertRaises(ValueError):
            core.parse_transcript_events(path)

    def test_three_sessions_and_audit(self):
        generate(self.root)
        expected = {"project-fire": "fire", "project-clean": "clean", "research-fire": "fire"}
        for stem, state in expected.items():
            self.assertEqual(core.verdict(core.parse_transcript_events(self.root / (stem + ".jsonl"))).state, state)
        (self.root / "agent-child.jsonl").write_text("{}\n")
        debts, heartbeat = auditor.audit(self.root.glob("*.jsonl"), lambda slug: auditor.note_exists(self.root / "notes", slug))
        self.assertEqual((heartbeat["scanned"], heartbeat["debts"], heartbeat["excluded_agents"]), (3, 2, 1))
        def broken(slug):
            raise OSError("synthetic")
        debts, heartbeat = auditor.audit([self.root / "project-clean.jsonl"], broken)
        self.assertEqual(heartbeat["debts"], 1)
        self.assertTrue(heartbeat["last_error"])

    def test_shapes_exemptions_and_recent_clean(self):
        now = datetime.now(timezone.utc)
        task = str(Path("tasks/demo.md").absolute())
        event = core.Event("Edit", file_path=task, detail="status: done")
        self.assertEqual(core.verdict([event]).state, "fire")
        self.assertEqual(core.verdict([event], [{"task_file": task, "ts": now.isoformat()}], now).state, "clean")
        self.assertEqual(core.verdict([event], [{"task_file": task, "ts": (now-timedelta(hours=72)).isoformat()}], now).state, "fire")
        search = [core.Event("WebSearch") for _ in range(8)]
        self.assertIn("research", core.verdict(search).shapes)
        self.assertEqual(core.verdict(search + [core.Event("Write", file_path="memory/topic.md", detail="saved")]).state, "clean")
        self.assertIn("infra", core.verdict([core.Event("Write", file_path=str(Path("hooks/guard.py").absolute()))]).shapes)
        self.assertIn("project", core.verdict([core.Event("Bash", command="npm publish")]).shapes)

    def test_retrieval_weights_and_distinct_documents(self):
        events = [core.Event("Agent", result_source="direct_tool_result", result_text="x" * 3000)] * 2
        events += [core.Event("Read", file_path="paper.pdf"), core.Event("Read", file_path="paper.pdf"), core.Event("Read", file_path="paper.docx")]
        self.assertEqual(core.verdict(events).hits["retrievals"], 8)
        self.assertIn("research", core.verdict(events).shapes)


if __name__ == "__main__":
    unittest.main()
