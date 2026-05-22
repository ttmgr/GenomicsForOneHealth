"""Backward-compatible validation facade.

Generic, threshold-free checks come from the agnostic core; threshold-bearing,
domain-specific checks from the GenomicsForOneHealth project layer. Import sites
that used ``agent_skills.hooks.validation.<fn>`` keep working unchanged.
"""

from agent_skills.core.hooks.validation import (  # noqa: F401
    _flag,
    command_not_available,
    database_not_detected,
    low_classification_rate,
    unexpected_empty_output,
)
from agent_skills.project.hooks.validation_genomics import (  # noqa: F401
    MIN_BASES_PER_SAMPLE,
    MIN_MEAN_READ_LENGTH,
    MIN_N50,
    MIN_READS_PER_SAMPLE,
    contamination_signal,
    low_n50,
    low_read_yield,
    missing_amr_hits,
)

__all__ = [
    "low_classification_rate",
    "unexpected_empty_output",
    "database_not_detected",
    "command_not_available",
    "low_read_yield",
    "low_n50",
    "contamination_signal",
    "missing_amr_hits",
    "MIN_READS_PER_SAMPLE",
    "MIN_BASES_PER_SAMPLE",
    "MIN_MEAN_READ_LENGTH",
    "MIN_N50",
]
