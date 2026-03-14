# Selector Data Guide

The selector data model is split so routing logic, operator guidance, and unsupported-case handling can evolve independently.

## Files

- `pipelines.json`
  Routing metadata for each published workflow in the collection. This file should stay concise and should not become the main operator manual.

- `questions.json`
  Ordered question flow and allowed option values. Treat this as the schema for user answers.

- `playbooks.json`
  Action-sheet content for each supported workflow or track. This is where entry actions, curated commands, prerequisites, outputs, and workflow-specific notes belong.

- `presets.json`
  Common starting scenarios that prefill the selector for researchers who already know their broad use case.

- `out_of_scope.json`
  Explicit unsupported or partial-fit rules. Use this file when a workflow is biologically adjacent to the collection but still not truly covered by the published repository.

## Maintenance Rules

### Add a new pipeline

1. Add the routing entry to `pipelines.json`.
2. Add at least one matching playbook to `playbooks.json`.
3. Add or update presets if the new workflow is a common starting scenario.
4. Add an out-of-scope rule only if the new workflow changes an existing unsupported boundary.

### Add a playbook

Every playbook must include:

- `pipeline_id`
- `track_id` (`null` for pipeline-level playbooks)
- `recommended_when`
- `avoid_when`
- `required_inputs`
- `entry_actions`
- `preprocessing_defaults`
- `required_tools`
- `required_databases`
- `expected_outputs`
- `runtime_notes`
- `evidence_links`

### Curated command policy

- Only include commands that are already documented in the repository.
- Every curated command must include a `source_url`.
- If the repo does not document a reliable copy-ready command, leave `curated_commands` empty and point users to the correct wrapper script or README entry instead.
- Do not invent local paths, unpublished flags, or machine-specific database locations.

### Unsupported-case policy

Use `out_of_scope.json` when:

- the user intent is scientifically adjacent to the collection,
- the repo does not contain a validated exact workflow,
- and forcing a normal recommendation would overstate support.

Do not use unsupported rules to hide uncertainty that should instead be represented as a low-confidence nearest fit.

## Review Expectations

- Run `node docs/scripts/validate_selector_data.mjs` after data edits.
- Run `node docs/scripts/check_selector_cases.mjs` after changing routing or playbooks.
- Keep `last_reviewed` current in `pipelines.json` when a workflow entry is refreshed.
