"""Lightweight, inspectable hooks for the GenomicsForOneHealth agent skill pack.

These modules let a coding agent validate inputs, build (never execute) commands,
parse documented tool outputs, run sanity checks, and write audit logs for the
One Health Nanopore workflows described in agent_skills/skills/*.yaml.

Design rules:
  - Standard library only, except command_builder.load_skill_yaml which uses
    PyYAML (already a project dependency; see environment.yaml).
  - Functions return plain dictionaries with explicit, documented keys.
  - Nothing here executes a workflow command or mutates input data.

The local repository is the source of truth. These hooks never invent commands,
parameters, tools, or databases; they only operate on what a skill declares.
"""

from . import preflight, command_builder, parsers, validation, audit

__all__ = ["preflight", "command_builder", "parsers", "validation", "audit"]
__version__ = "0.1.0"
