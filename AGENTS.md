# Agent instructions

This repository includes a machine-readable skill pack in `agent_skills/`.

Before editing workflows, commands, or pipeline documentation:

1. Read `agent_skills/README.md`.
2. Read the relevant skill YAML files in `agent_skills/skills/`.
3. Do not invent undocumented tools, parameters, commands, databases, or biological
   interpretations.
4. Preserve source traceability (`source_files`).
5. Preserve external reference traceability where used (`external_references`).
6. Mark ambiguous behavior as `needs_review`.
7. Keep changes small, explicit, and source-backed.

`agent_skills/` is a portable harness (agnostic `core/` + a Claude Code adapter)
over a thin project layer; the 13 skill YAMLs are optional project content (see
ADR-0004). Coding-agent operating rules are in `agent_skills/core/AGENTS.md`
(agent-agnostic) and `agent_skills/adapters/claude_code/CLAUDE.md` (Claude Code);
project routing is in `agent_skills/project/prompts/use_skill_pack.md`. Treat all
LLM outputs as suggestions, not biological, clinical, regulatory, or diagnostic
conclusions.
