# Selector Data Guide

The selector now uses a wizard model with three layers:

1. generic routing pages
2. published example mapping
3. post-route expert heuristics

## Files

- `questions.json`
  Defines the wizard pages and answer schema. This is the main UI contract for the selector. Each page entry describes the page id, title, summary, page type, and the questions rendered on that page.

- `examples.json`
  Maps generalized routes to published repository backends. Exact example entries resolve directly to a pipeline and optional track. Unsupported example entries resolve to the nearest published backend while preserving an explicit unsupported label.

- `expert_rules.json`
  Stores post-route heuristic adjustments. These rules may insert or skip steps, add warnings, or swap preferred tools inside the selected backend. They must never reroute to another backend.

- `pipelines.json`
  Keeps the published workflow metadata: titles, docs, supported inputs, tracks, and routing-related fields that are still useful outside the wizard.

- `playbooks.json`
  Provides the operator-facing action-sheet content for each backend or track: entry actions, curated commands, preprocessing defaults, prerequisites, outputs, and evidence links.

## Maintenance Rules

### Add a new published backend

1. Add or update the workflow entry in `pipelines.json`.
2. Add a matching action sheet in `playbooks.json`.
3. Add one or more example routes in `examples.json`.
4. Add expert rules only if the new backend needs route-specific heuristic tuning that does not change backend selection.

### Add a new wizard question

1. Add it to the correct page in `questions.json`.
2. If it is used by expert rules, update `expert_rules.json`.
3. If it is referenced by conditional visibility, ensure the dependency points to an earlier question.

### Add a new example

Every example must include:

- `id`
- `label`
- `sample_contexts`
- `material_classes`
- `target_goals`
- `status_class`
- `route_summary`
- `selection_help`

Exact examples must include:

- `pipeline_id`
- optional `track_id`

Unsupported examples must include:

- `nearest_pipeline_id`
- optional `nearest_track_id`
- `unsupported_reason`

### Curated command policy

- Only include commands that are already documented in the repository.
- Every curated command must include a `source_url`.
- If the repo does not document a reliable copy-ready command, leave `curated_commands` empty and point the user to the correct wrapper or README entry instead.

### Expert rule policy

- Expert rules refine the selected backend; they do not choose a different backend.
- Allowed effects are `tool_swap`, `step_insert`, `step_skip`, `warning_only`, and `preprocessing_override`.
- Do not add any field that reroutes to a different `pipeline_id` or `track_id`.

## Review Expectations

- Run `node docs/scripts/validate_selector_data.mjs` after editing selector data.
- Run `node docs/scripts/check_selector_cases.mjs` after changing routing or expert heuristics.
- Keep `last_reviewed` current in `pipelines.json` when a workflow entry is refreshed.
