#!/usr/bin/env python3
"""Generic, warn-only receipt verdicts adapted from the supplied core."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shlex

PROJECT_FILES = 3
RETRIEVALS = 8
LARGE_RESULT = 3000
LARGE_WEIGHT = 3
COMPOUND = (";", "|", "&", "`", "$(", "<(", "\n")
RECEIPT_TOOLS = {"receipt-tool", "receipt-verify"}
RETRIEVAL_TOOLS = {"WebSearch", "WebFetch", "PaperSearch"}
PUBLISH = re.compile(r"\b(?:npm\s+publish|gh\s+release\s+create|docker\s+push|twine\s+upload|cargo\s+publish)\b")
SHELL_WRITE = re.compile(r">>|(?<![<>&])>(?![>=])|\b(?:tee|cp|mv|rm|mkdir|touch|chmod)\b|\bsed\s+-i\b")


@dataclass
class Event:
    tool_name: str
    command: str = ""
    file_path: str = ""
    detail: str = ""
    tool_use_id: str = ""
    result_source: str = "none"
    result_text: str = ""
    exit_ok: bool | None = None


@dataclass
class Verdict:
    state: str
    shapes: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    receipts: list = field(default_factory=list)
    hits: dict = field(default_factory=dict)


def arguments(event):
    try:
        return shlex.split(event.command)
    except ValueError:
        return []


def slug_of(event):
    args = arguments(event)[1:]
    for index, arg in enumerate(args):
        if arg == "--slug":
            return args[index + 1] if index + 1 < len(args) else ""
        if arg.startswith("--slug="):
            return arg.split("=", 1)[1]
    return next((arg for arg in args if not arg.startswith("-")), "")


def valid_receipt(event):
    args = arguments(event)
    head = Path(args[0]).name if args else ""
    if event.tool_name != "Bash" or event.exit_ok is False or head not in RECEIPT_TOOLS:
        return False
    if any(token in event.command for token in COMPOUND):
        return False
    if not event.tool_use_id or event.result_source != "direct_tool_result":
        return False
    slug = slug_of(event)
    return bool(slug) and f"{head}: OK" in event.result_text and slug in re.findall(r"\bslug=(\S+)", event.result_text)


def parse_transcript_events(path):
    events, pending = [], {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        message = record.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        role = message.get("role", record.get("type"))
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and role == "assistant":
                identifier = block.get("id", "")
                if not identifier or identifier in pending:
                    raise ValueError("missing or duplicate tool-use id")
                inp = block.get("input", {})
                event = Event(block["name"], inp.get("command", ""), inp.get("file_path", ""),
                              inp.get("new_string", inp.get("content", "")), identifier)
                events.append(event)
                pending[identifier] = event
            elif block.get("type") == "tool_result" and role == "user":
                event = pending.get(block.get("tool_use_id"))
                if event:
                    if event.result_source != "none":
                        raise ValueError("duplicate tool result")
                    text = block.get("content", "")
                    if isinstance(text, list):
                        text = "\n".join(item.get("text", "") for item in text if item.get("type") == "text")
                    event.result_source, event.result_text = "direct_tool_result", str(text)
                    event.exit_ok = not block["is_error"] if "is_error" in block else None
    return events


def verdict(events, recent_clean=(), now=None):
    now = now or datetime.now(timezone.utc)
    receipts = [{"slug": slug_of(event)} for event in events if valid_receipt(event)]
    writes = [event for event in events if event.tool_name in {"Write", "Edit", "MultiEdit"} and event.exit_ok is not False]
    worklog = any(Path(event.file_path).name == "WORKLOG.md" and event.detail.strip() for event in writes)
    changelog = any("tasks" in Path(event.file_path).parts and re.search(r"(?m)^\s*-\s*\{ts:", event.detail) for event in writes)
    memory = any("memory" in Path(event.file_path).parts and event.detail.strip() for event in writes)

    def exempt(path):
        return Path(path).name == "WORKLOG.md" or Path(path).name.endswith("-ledger.jsonl") or bool(
            set(Path(path).parts) & {"tmp", "scratchpad", "memory", "tasks", "decisions"})

    def infra(path):
        return bool(set(Path(path).parts) & {"hooks", "tooling"}) or Path(path).name in {"settings.json", "INSTRUCTIONS.md"}

    files = {event.file_path for event in writes if Path(event.file_path).is_absolute() and not exempt(event.file_path)}
    infra_hits = {path for path in files if infra(path)}
    project_files = files - infra_hits
    shell_writes, publish = False, False
    for event in events:
        if event.tool_name != "Bash" or event.exit_ok is False:
            continue
        publish = publish or bool(PUBLISH.search(event.command))
        args = arguments(event)
        paths = [arg for arg in args if arg.startswith("/") and not exempt(arg)]
        if SHELL_WRITE.search(event.command) and paths:
            shell_writes = True
            infra_hits.update(path for path in paths if infra(path))
        if SHELL_WRITE.search(event.command) and any(Path(arg).name == "WORKLOG.md" for arg in args):
            worklog = True

    done = [event for event in writes if "tasks" in Path(event.file_path).parts
            and re.search(r"(?m)^\s*status:\s*done\s*$", event.detail)]

    def recent(path):
        for record in recent_clean:
            try:
                age = now - datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
                if record["task_file"] == path and timedelta() <= age <= timedelta(hours=48):
                    return True
            except (KeyError, ValueError, TypeError):
                continue
        return False
    documents = {event.file_path for event in events if event.tool_name == "Read" and Path(event.file_path).suffix.lower() in {".pdf", ".docx"}}
    retrievals = sum(event.tool_name in RETRIEVAL_TOOLS for event in events) + len(documents)
    retrievals += sum(LARGE_WEIGHT for event in events if event.tool_name == "Agent" and
                      event.result_source == "direct_tool_result" and len(event.result_text) >= LARGE_RESULT)
    shapes = []
    if infra_hits:
        shapes.append("infra")
    if len(project_files) >= PROJECT_FILES or publish or any(not recent(event.file_path) for event in done):
        shapes.append("project")
    if retrievals >= RETRIEVALS and not (files or shell_writes or publish or done or receipts):
        shapes.append("research")
    missing = set()
    if "infra" in shapes:
        if not worklog:
            missing.add("worklog")
        if not receipts:
            missing.add("receipt")
    if "project" in shapes:
        if not (worklog or changelog):
            missing.add("changelog or worklog")
        if not receipts:
            missing.add("receipt")
    if "research" in shapes and not (receipts or memory):
        missing.add("receipt or memory")
    return Verdict("fire" if missing else "clean", shapes, sorted(missing), receipts,
                   {"project_files": len(project_files), "retrievals": retrievals})
