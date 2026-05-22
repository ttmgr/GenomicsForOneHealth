"""Project-agnostic sanity checks that turn parsed outputs into caveated flags.

Every function returns:
    {"flag": True/False, "severity": "info"|"warning", "message": "..."}

A flag is advisory only. These checks help a coding agent produce a caveated
report; they are not domain, biological, clinical, or diagnostic judgments.

This module holds only checks that need no project-specific threshold: presence
of an expected output, a missing database, an unavailable command, and a
caller-overridable classification-rate heuristic. Threshold-bearing,
domain-specific validators (read yield, N50, contamination, AMR hits) live in
the project layer, e.g. agent_skills/project/hooks/validation_genomics.py.
"""

from __future__ import annotations

from typing import Optional


def _flag(flag: bool, severity: str, message: str) -> dict:
    return {"flag": flag, "severity": severity, "message": message}


def low_classification_rate(classified_percent: Optional[float], min_percent: float = 50.0) -> dict:
    """Flag a low taxonomic classification rate.

    The default of 50% is a heuristic, not a repository-sourced threshold; set
    min_percent to a study-appropriate value. Useful with a Kraken2-report
    parser's summary.classified_percent.
    """
    if classified_percent is None:
        return _flag(False, "info", "No classification rate provided; cannot assess.")
    if classified_percent < min_percent:
        return _flag(
            True,
            "warning",
            f"Low classification rate: {classified_percent:g}% < {min_percent:g}% (heuristic threshold).",
        )
    return _flag(False, "info", f"Classification rate {classified_percent:g}% above heuristic threshold.")


def unexpected_empty_output(path: Optional[str] = None, count: Optional[int] = None) -> dict:
    """Flag a missing/empty expected output file, or a zero record count."""
    import os

    if path is not None:
        if not os.path.exists(path):
            return _flag(True, "warning", f"Expected output missing: {path}")
        if os.path.isfile(path) and os.path.getsize(path) == 0:
            return _flag(True, "warning", f"Expected output is empty: {path}")
        return _flag(False, "info", f"Output present: {path}")
    if count is not None:
        if count == 0:
            return _flag(True, "warning", "Expected output contained zero records.")
        return _flag(False, "info", f"Output contains {count} record(s).")
    return _flag(False, "info", "No output path or count provided; cannot assess.")


def database_not_detected(preflight_result: Optional[dict] = None, path: Optional[str] = None) -> dict:
    """Flag a missing database.

    Pass either a result dict from preflight.check_database_exists or a path to
    check directly here.
    """
    if preflight_result is not None:
        if not preflight_result.get("ok", False):
            return _flag(True, "warning", f"Database not detected: {preflight_result.get('message', 'unknown')}")
        return _flag(False, "info", "Database detected.")
    if path is not None:
        from . import preflight

        result = preflight.check_database_exists(path)
        if not result["ok"]:
            return _flag(True, "warning", f"Database not detected: {result['message']}")
        return _flag(False, "info", "Database detected.")
    return _flag(False, "info", "No database input provided; cannot assess.")


def command_not_available(command: Optional[str] = None, preflight_result: Optional[dict] = None) -> dict:
    """Flag an unavailable command.

    Pass either a result dict from preflight.check_command_available or a
    command name to check directly here.
    """
    if preflight_result is not None:
        if not preflight_result.get("ok", False):
            return _flag(True, "warning", f"Command unavailable: {preflight_result.get('message', 'unknown')}")
        return _flag(False, "info", "Command available.")
    if command is not None:
        from . import preflight

        result = preflight.check_command_available(command)
        if not result["ok"]:
            return _flag(True, "warning", f"Command unavailable: {result['message']}")
        return _flag(False, "info", f"Command available: {command}")
    return _flag(False, "info", "No command provided; cannot assess.")
