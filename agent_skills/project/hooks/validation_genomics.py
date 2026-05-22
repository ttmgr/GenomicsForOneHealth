"""GenomicsForOneHealth threshold-bearing, domain-specific sanity checks.

Every function returns:
    {"flag": True/False, "severity": "info"|"warning", "message": "..."}

A flag is advisory only; it is not a biological, clinical, or diagnostic
judgment. Generic, threshold-free checks (classification rate, empty output,
missing database/command) live in the agnostic core
(agent_skills/core/hooks/validation.py).

Default thresholds for yield, read length, and N50 are taken from the
repository's own quality_thresholds block in
Environmental_Metagenomics/Air_Metagenomics/config/config.yaml
(min_reads_per_sample: 1000, min_bases_per_sample: 500000,
min_mean_read_length: 200, min_n50: 1000).
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from agent_skills.core.hooks.validation import _flag

# Sourced from Air_Metagenomics/config/config.yaml -> quality_thresholds
MIN_READS_PER_SAMPLE = 1000
MIN_BASES_PER_SAMPLE = 500000
MIN_MEAN_READ_LENGTH = 200
MIN_N50 = 1000


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
