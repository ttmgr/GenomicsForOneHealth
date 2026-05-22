---
name: layered-harness-architecture
description: agent_skills is a portable harness (core + Claude Code adapter) over a thin project layer
metadata:
  type: decision
---

`agent_skills/` is structured as three layers so the engine is portable to any
repository: `core/` (project-agnostic hooks, schema, prompts, memory spec,
offline runner), `adapters/claude_code/` (Claude Code wiring), and `project/`
(GenomicsForOneHealth tool parsers, threshold validators, routing prompt,
benchmark tasks). The 13 skill YAMLs are an *optional* project content layer.
Old import paths (`agent_skills.hooks.*`), `evals/run_benchmarks.py`, and the
`skills/*.yaml` locations are preserved by compat shims.

**Why:** the reusable value is the mechanism (memory + hooks + instructions),
not the genomics content; separating them lets the harness be lifted into other
projects unchanged.

**How to apply:** put portable code in `core/`, never let `core/` import
`project/`; record structural decisions in `adr/`. Full rationale in ADR-0004.
See [[harness-operating-contract]], [[architecture-decisions-index]].
