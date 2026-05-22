"""Project-agnostic harness hooks — the portable engine.

These modules let any coding agent validate inputs, build (never execute)
commands from declared templates, parse standard outputs, run sanity checks,
and write audit logs. Nothing here is tied to a particular project: drop this
package into any repository, pair it with that repo's skill YAMLs and an
(optional) project hook layer, and it works unchanged.

Design rules:
  - Standard library only, except command_builder.load_skill_yaml which uses
    PyYAML.
  - Functions return plain dictionaries with explicit, documented keys.
  - Nothing here executes a workflow command or mutates input data.

The local repository is the source of truth. These hooks never invent commands,
parameters, tools, or databases; they only operate on what a skill declares.
"""

from . import preflight, command_builder, parsers, validation, audit

__all__ = ["preflight", "command_builder", "parsers", "validation", "audit"]
__version__ = "0.2.0"
