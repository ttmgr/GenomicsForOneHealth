"""Load skills and build commands from declared templates. Never executes.

Guarantees:
  - Only parameters declared by a skill may be used. Unknown parameters are
    refused, never silently accepted.
  - Missing required parameters produce a structured error, never a guess.
  - Placeholder names are validated and values are shell-quoted, so a value
    cannot inject extra shell tokens into a built command string.
  - Commands are returned as strings only. Nothing here runs a command.

load_skill_yaml uses PyYAML (a project dependency; see environment.yaml). The
rest of this module is standard library only.
"""

from __future__ import annotations

import os
import re
import shlex
import string
from typing import Any

_VALID_FIELD = re.compile(r"^[A-Za-z0-9_]+$")
_FORMATTER = string.Formatter()


def load_skill_yaml(path: str) -> dict:
    """Load a skill YAML file into a dict.

    Returns {"ok": True, "skill": <dict>} or {"ok": False, "error": <msg>}.
    """
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": f"Skill file not found: {path}"}
    try:
        import yaml  # PyYAML; declared in environment.yaml
    except ImportError:
        return {
            "ok": False,
            "error": "PyYAML is required to load skills. Install with: pip install pyyaml",
        }
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        return {"ok": False, "error": f"Failed to parse skill YAML: {exc}"}
    if not isinstance(data, dict):
        return {"ok": False, "error": f"Skill YAML did not parse to a mapping: {path}"}
    return {"ok": True, "skill": data}


def _declared_parameters(skill: dict) -> dict:
    """Return {name: {required, default, ...}} from a skill's parameters list.

    Accepts the canonical list-of-dicts form. Tolerates a simple
    mapping {name: spec} too.
    """
    declared: dict[str, dict] = {}
    params = skill.get("parameters") or []
    if isinstance(params, dict):
        for name, spec in params.items():
            spec = spec if isinstance(spec, dict) else {}
            declared[str(name)] = spec
    else:
        for spec in params:
            if isinstance(spec, dict) and spec.get("name"):
                declared[str(spec["name"])] = spec
    return declared


def validate_required_parameters(skill: dict, parameters: dict) -> dict:
    """Check supplied parameters against a skill's declared parameters.

    Fails if any required parameter (without a default) is missing, or if a
    supplied parameter is not declared by the skill.
    """
    parameters = parameters or {}
    declared = _declared_parameters(skill)
    declared_names = set(declared)

    missing = []
    for name, spec in declared.items():
        is_required = bool(spec.get("required", False))
        has_default = "default" in spec and spec["default"] is not None
        if is_required and not has_default and name not in parameters:
            missing.append(name)

    unknown = sorted(set(parameters) - declared_names)

    ok = not missing and not unknown
    parts = []
    if missing:
        parts.append(f"missing required: {', '.join(sorted(missing))}")
    if unknown:
        parts.append(f"undeclared (refused): {', '.join(unknown)}")
    message = "All parameters valid." if ok else "; ".join(parts)
    return {"ok": ok, "missing": sorted(missing), "unknown": unknown, "message": message}


def build_command(command_template: str, parameters: dict) -> dict:
    """Build one command string from a template and parameters.

    The template uses ``{name}`` placeholders. Every placeholder must have a
    matching key in ``parameters``; values are shell-quoted. Placeholder names
    must match ``[A-Za-z0-9_]+``. Returns the built command or a structured
    error listing missing/invalid placeholders.
    """
    parameters = parameters or {}
    if not isinstance(command_template, str):
        return {"ok": False, "command": None, "message": "Command template is not a string."}

    fields: list[str] = []
    try:
        for _literal, field_name, _spec, _conv in _FORMATTER.parse(command_template):
            if field_name:
                fields.append(field_name)
    except ValueError as exc:
        return {"ok": False, "command": None, "message": f"Malformed template: {exc}"}

    invalid_fields = sorted({f for f in fields if not _VALID_FIELD.match(f)})
    missing = sorted({f for f in fields if _VALID_FIELD.match(f) and f not in parameters})
    if invalid_fields or missing:
        parts = []
        if invalid_fields:
            parts.append(f"invalid placeholder names: {', '.join(invalid_fields)}")
        if missing:
            parts.append(f"missing values: {', '.join(missing)}")
        return {
            "ok": False,
            "command": None,
            "missing": missing,
            "invalid_fields": invalid_fields,
            "message": "; ".join(parts),
        }

    # Substitute manually so each value is shell-quoted (prevents injection).
    out_parts: list[str] = []
    for literal, field_name, _spec, _conv in _FORMATTER.parse(command_template):
        out_parts.append(literal)
        if field_name:
            out_parts.append(shlex.quote(str(parameters[field_name])))
    return {"ok": True, "command": "".join(out_parts), "missing": [], "invalid_fields": [], "message": "ok"}


def build_commands_for_skill(skill: dict, parameters: dict) -> dict:
    """Validate parameters, then build every declared command template.

    Defaults declared on parameters are applied before building. Returns the
    list of per-template results and an overall ok flag. Refuses to build if
    parameter validation fails.
    """
    parameters = parameters or {}
    validation = validate_required_parameters(skill, parameters)
    if not validation["ok"]:
        return {"ok": False, "commands": [], "validation": validation, "message": validation["message"]}

    # Apply declared defaults, then user-supplied values take precedence.
    effective = {}
    for name, spec in _declared_parameters(skill).items():
        if isinstance(spec, dict) and spec.get("default") is not None:
            effective[name] = spec["default"]
    effective.update(parameters)

    templates = skill.get("command_templates") or []
    built = []
    all_ok = True
    for entry in templates:
        if isinstance(entry, dict):
            template = entry.get("template") or entry.get("command") or ""
            label = entry.get("id") or entry.get("label") or entry.get("step") or ""
        else:
            template = str(entry)
            label = ""
        result = build_command(template, effective)
        result["label"] = label
        built.append(result)
        all_ok = all_ok and result["ok"]

    return {
        "ok": all_ok,
        "commands": built,
        "validation": validation,
        "message": "All commands built." if all_ok else "Some commands could not be built.",
    }
