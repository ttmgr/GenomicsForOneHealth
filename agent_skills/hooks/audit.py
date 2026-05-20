"""Audit logging for proposed or executed workflows.

write_audit_log records, as JSON, exactly what a coding agent decided to run:
the selected skill, the inputs and parameters, the commands it built, any
results it parsed, the validation flags it raised, and the local source files
and external references the skill is traceable to.

The log is the durable, human-inspectable record that makes an agent-assisted
run reproducible and reviewable. It is plain JSON (standard library only).
"""

from __future__ import annotations

import json
import os
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
