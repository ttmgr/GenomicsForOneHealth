---
name: run-history
description: Where agent-run summaries are written and how they are indexed
metadata:
  type: reference
---

Agent-assisted workflow runs are distilled into `type: run` memory files in this
directory (`agent_skills/memory/run-<timestamp>-<skill>.md`), written by
`core/hooks/audit.append_run_record(memory_dir, skill_name, summary, ...)`, which
also appends the pointer line to `MEMORY.md`. The full machine-readable record
(inputs, parameters, commands, parsed results, flags) stays in the JSON audit log
from `audit.write_audit_log`. See [[harness-operating-contract]].
