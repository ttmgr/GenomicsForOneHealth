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

Coding-agent operating rules are in `agent_skills/AGENTS.md` (agent-agnostic) and
`agent_skills/CLAUDE.md` (Claude Code). Treat all LLM outputs as suggestions, not
biological, clinical, regulatory, or diagnostic conclusions.
