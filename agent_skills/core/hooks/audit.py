"""Audit logging for proposed or executed workflows.

write_audit_log records, as JSON, exactly what a coding agent decided to run:
the selected skill, the inputs and parameters, the commands it built, any
results it parsed, the validation flags it raised, and the local source files
and external references the skill is traceable to.

The log is the durable, human-inspectable record that makes an agent-assisted
run reproducible and reviewable. It is plain JSON (standard library only).

append_run_record additionally distils a run into a single Markdown memory file
under a memory store (see core/memory/README.md) and registers it in that
store's MEMORY.md index, so run history becomes part of the harness's durable
memory rather than only a one-off JSON log. It is project-agnostic: the caller
supplies the memory directory.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional, Sequence


def write_audit_log(
    output_path: str,
    skill_name: str,
    inputs: Any,
    parameters: Any,
    commands: Any,
    results: Any,
    flags: Any,
    source_files: Optional[Sequence[str]] = None,
    external_references: Optional[Sequence[str]] = None,
) -> dict:
    """Write a JSON audit log and return a status dict.

    Args:
        output_path: Destination .json file. Parent directories are created.
        skill_name: The ``name`` field of the skill that was used.
        inputs: Mapping or list describing the input files/directories.
        parameters: The parameter values supplied to the skill.
        commands: The command strings that were built (and possibly run).
        results: Parsed outputs or a summary of them.
        flags: Validation flags raised (list of dicts from validation.py).
        source_files: Local repository files the skill is derived from.
        external_references: Upstream URLs used only for comparison.

    Returns:
        {"ok": True, "path": <path>} on success, otherwise
        {"ok": False, "message": <error>}.
    """
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "skill_name": skill_name,
        "inputs": inputs,
        "parameters": parameters,
        "commands": commands,
        "results": results,
        "flags": flags,
        "source_files": list(source_files) if source_files else [],
        "external_references": list(external_references) if external_references else [],
    }

    try:
        parent = os.path.dirname(os.path.abspath(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, default=str)
            handle.write("\n")
    except OSError as exc:
        return {"ok": False, "message": f"Failed to write audit log: {exc}"}

    return {"ok": True, "path": output_path}


def _slugify(text: str) -> str:
    """Lowercase, hyphenated, filesystem-safe slug fragment."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "run"


def append_run_record(
    memory_dir: str,
    skill_name: str,
    summary: str,
    flags: Optional[Sequence[dict]] = None,
    source_files: Optional[Sequence[str]] = None,
    status: str = "completed",
    index_file: str = "MEMORY.md",
) -> dict:
    """Distil one run into a ``type: run`` memory file and index it.

    Writes a Markdown memory file under ``memory_dir`` (frontmatter + body, per
    core/memory/README.md) and appends a one-line pointer to ``memory_dir``'s
    index (``MEMORY.md`` by default). Project-agnostic: pass the memory store of
    whatever repository the harness is running in.

    Args:
        memory_dir: Directory of the memory store (created if absent).
        skill_name: The ``name`` of the skill the run used.
        summary: One- or two-sentence human summary of what the run did/found.
        flags: Validation flags raised during the run (list of dicts).
        source_files: Repo-relative files the skill is traceable to.
        status: Run outcome, e.g. "completed", "failed", "proposed".
        index_file: Index filename within ``memory_dir``.

    Returns:
        {"ok": True, "path": <memory file>, "index": <index path>} or
        {"ok": False, "message": <error>}.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    stamp = re.sub(r"[^0-9]", "", timestamp)[:14]  # YYYYMMDDHHMMSS
    name = f"run-{stamp}-{_slugify(skill_name)}"
    filename = f"{name}.md"
    headline = " ".join((summary or "").split())
    short = headline if len(headline) <= 100 else headline[:97] + "..."

    flag_lines = ""
    raised = [f for f in (flags or []) if isinstance(f, dict) and f.get("flag")]
    if raised:
        flag_lines = "\n".join(
            f"- [{f.get('severity', 'info')}] {f.get('message', '')}" for f in raised
        )
        flag_lines = f"\n\n**Flags raised:**\n{flag_lines}"
    source_lines = ""
    if source_files:
        source_lines = "\n\n**Source files:** " + ", ".join(f"`{s}`" for s in source_files)

    body = (
        f"---\n"
        f"name: {name}\n"
        f"description: {short or 'agent run'}\n"
        f"metadata:\n"
        f"  type: run\n"
        f"  skill: {skill_name}\n"
        f"  status: {status}\n"
        f"  timestamp_utc: {timestamp}\n"
        f"---\n\n"
        f"{headline or 'Run recorded.'}"
        f"{flag_lines}"
        f"{source_lines}\n"
    )

    try:
        os.makedirs(memory_dir, exist_ok=True)
        record_path = os.path.join(memory_dir, filename)
        with open(record_path, "w", encoding="utf-8") as handle:
            handle.write(body)

        index_path = os.path.join(memory_dir, index_file)
        index_line = f"- [run {stamp} — {skill_name}]({filename}) — {short or 'agent run'}\n"
        with open(index_path, "a", encoding="utf-8") as handle:
            handle.write(index_line)
    except OSError as exc:
        return {"ok": False, "message": f"Failed to append run record: {exc}"}

    return {"ok": True, "path": record_path, "index": index_path}
