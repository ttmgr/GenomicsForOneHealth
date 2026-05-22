"""Backward-compatible parsers facade.

Generic, tool-independent parsers come from the agnostic core; tool-specific
parsers from the GenomicsForOneHealth project layer. Import sites that used
``agent_skills.hooks.parsers.<fn>`` keep working unchanged.
"""

from agent_skills.core.hooks.parsers import (  # noqa: F401
    _missing,
    _to_number,
    parse_generic_tsv,
    parse_vcf,
)
from agent_skills.project.hooks.parsers_genomics import (  # noqa: F401
    parse_amrfinder_table,
    parse_kraken2_report,
    parse_nanostat,
)

__all__ = [
    "parse_vcf",
    "parse_generic_tsv",
    "parse_nanostat",
    "parse_kraken2_report",
    "parse_amrfinder_table",
]
