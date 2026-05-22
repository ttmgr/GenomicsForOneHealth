"""Backward-compatible facade for the harness hooks.

The hooks were split into a portable, project-agnostic engine and a
GenomicsForOneHealth project layer:
  - agent_skills/core/hooks/     project-agnostic engine
  - agent_skills/project/hooks/  tool-specific parsers and threshold validators

This package re-exports both so existing imports keep working unchanged:
    from agent_skills.hooks import preflight, command_builder, parsers, validation, audit

New code should import from agent_skills.core.hooks (portable) or
agent_skills.project.hooks (project-specific) directly.
"""

from agent_skills.core.hooks import preflight, command_builder, audit
from . import parsers, validation

__all__ = ["preflight", "command_builder", "parsers", "validation", "audit"]
__version__ = "0.2.0"
