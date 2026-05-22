---
name: harness-operating-contract
description: The non-negotiable operating rules every agent using this pack must follow
metadata:
  type: preference
---

The local repository is the source of truth. The harness never invents commands,
parameters, tools, or databases — it builds commands only from a skill's declared
`command_templates`, and it builds them, it does not execute them. Destructive
commands require explicit human confirmation. All outputs are suggestions, not
biological, clinical, regulatory, or diagnostic conclusions.

**Why:** the pack's whole value is inspectability and reproducibility; a single
invented command breaks the traceability guarantee.

**How to apply:** follow `core/AGENTS.md` (agnostic) or
`adapters/claude_code/CLAUDE.md` (Claude Code); route with
`project/prompts/use_skill_pack.md`. See [[layered-harness-architecture]].
