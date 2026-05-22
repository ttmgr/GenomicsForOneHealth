---
name: architecture-decisions-index
description: Pointer to the repository's architectural decision records
metadata:
  type: reference
---

Architectural decisions are recorded as ADRs under `adr/` (repo root, not
`docs/adr/`, because `docs/` is the published Pages site):

- `adr/0001-canonical-recommendation-engine.md` — Advisor uses the score-based engine; selector engine parked.
- `adr/0002-defer-analysis-script-consolidation.md` — cross-pipeline parsing/figure consolidation deferred.
- `adr/0003-publication-scripts-frozen-forks.md` — publication-tied script variants kept as frozen snapshots.
- `adr/0004-layered-agnostic-harness.md` — agent_skills split into agnostic core + Claude Code adapter + project layer.

See [[layered-harness-architecture]].
