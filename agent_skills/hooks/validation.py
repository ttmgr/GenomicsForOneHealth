"""Sanity checks that turn parsed outputs into caveated flags.

Every function returns:
    {"flag": True/False, "severity": "info"|"warning", "message": "..."}

A flag is advisory only. These checks help a coding agent produce a caveated
report; they are not biological, clinical, or diagnostic judgments.

Default thresholds for yield, read length, and N50 are taken from the
repository's own quality_thresholds block in
Environmental_Metagenomics/Air_Metagenomics/config/config.yaml
(min_reads_per_sample: 1000, min_bases_per_sample: 500000,
min_mean_read_length: 200, min_n50: 1000). Thresholds without a repository
source are marked in their docstring as heuristics and are caller-overridable.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# Sourced from Air_Metagenomics/config/config.yaml -> quality_thresholds
MIN_READS_PER_SAMPLE = 1000
MIN_BASES_PER_SAMPLE = 500000
MIN_MEAN_READ_LENGTH = 200
MIN_N50 = 1000


def _flag(flag: bool, severity: str, message: str) -> dict:
    return {"flag": flag, "severity": severity, "message": message}


def low_read_yield(
    n_reads: Optional[float] = None,
    total_bases: Optional[float] = None,
    min_reads: int = MIN_READS_PER_SAMPLE,
    min_bases: int = MIN_BASES_PER_SAMPLE,
) -> dict:
    """Flag a sample whose read count or base yield is below threshold.

    Thresholds default to the repository's air-metagenomics quality settings.
    """
    if n_reads is None and total_bases is None:
        return _flag(False, "info", "No yield metrics provided; cannot assess read yield.")
    problems = []
    if n_reads is not None and n_reads < min_reads:
        problems.append(f"reads={n_reads:g} < {min_reads}")
    if total_bases is not None and total_bases < min_bases:
        problems.append(f"bases={total_bases:g} < {min_bases}")
    if problems:
        return _flag(True, "warning", "Low read yield: " + "; ".join(problems))
    return _flag(False, "info", "Read yield within configured thresholds.")


def low_n50(n50: Optional[float] = None, min_n50: int = MIN_N50) -> dict:
    """Flag an assembly/read N50 below threshold (repo default 1000)."""
    if n50 is None:
        return _flag(False, "info", "No N50 provided; cannot assess.")
    if n50 < min_n50:
        return _flag(True, "warning", f"Low N50: {n50:g} < {min_n50}.")
    return _flag(False, "info", f"N50 {n50:g} within configured threshold.")


def low_classification_rate(classified_percent: Optional[float], min_percent: float = 50.0) -> dict:
    """Flag a low taxonomic classification rate.

    The default of 50% is a heuristic, not a repository-sourced threshold; set
    min_percent to a study-appropriate value. Useful with parsers.parse_kraken2_report
    (summary.classified_percent).
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


def contamination_signal(
    flagged_contigs: Optional[Iterable[Any]] = None,
    n_flagged: Optional[int] = None,
) -> dict:
    """Flag a possible contamination signal.

    Accepts either an iterable of contamination-flagged contigs (e.g. from a
    Nanomotif detect_contamination output) or a precomputed count. Any
    positive count raises a warning to review manually.
    """
    count = n_flagged
    if count is None and flagged_contigs is not None:
        count = sum(1 for _ in flagged_contigs)
    if count is None:
        return _flag(False, "info", "No contamination input provided; cannot assess.")
    if count > 0:
        return _flag(True, "warning", f"Possible contamination signal: {count} flagged contig(s) to review.")
    return _flag(False, "info", "No contamination signal detected in provided input.")


def missing_amr_hits(n_hits: Optional[int]) -> dict:
    """Flag (info) when an AMR screen returned zero hits.

    Absence of hits is informational, not an error: it may be a true negative.
    """
    if n_hits is None:
        return _flag(False, "info", "No AMR hit count provided; cannot assess.")
    if n_hits == 0:
        return _flag(True, "info", "No AMR/virulence hits detected (may be a true negative; review coverage).")
    return _flag(False, "info", f"{n_hits} AMR/virulence hit(s) detected.")


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
