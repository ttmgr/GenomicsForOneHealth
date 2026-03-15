# Advisor Data Guide

The advisor uses a rules-based recommendation engine with a 4-step question flow:

1. Molecule type (DNA / RNA)
2. Study type (isolate, metagenomic, transcriptome, targeted, virome)
3. Priorities (speed, accuracy, native modifications, yield, low input, multiplexing)
4. Optional constraints (input amount, quality, host background, barcoding, device, compute)

## New Files (Advisor)

- `questions_v2.json`
  Defines the 4-step question flow, question types (radio, multi_select), visibility rules, and constraint toggles.

- `recommendation_rules.json`
  Scoring rules for kit, basecalling, flowcell, and pipeline recommendations. Also contains constraint modifiers that block or prefer options, kit/basecalling/pipeline catalogs, wet-lab checklists, and Dorado model mappings.

- `route_mapping.json`
  Bridges the new molecule + study_type categories to existing pipelines, examples, playbooks, external workflows, and matrix profiles.

## Legacy Files (Still Referenced)

- `questions.json`
  Original wizard pages. Retained for validation scripts.

- `examples.json`
  Maps generalized routes to published repository backends. Referenced via route_mapping.json.

- `expert_rules.json`
  Post-route heuristic adjustments. Referenced for warnings and tool swaps.

- `nanopore_profiles.json`
  Kit, flow cell, and basecalling profile details and route defaults.

- `external_workflows.json`
  Fallback workflows (EPI2ME Labs, CZ ID) surfaced in the rationale pane.

- `matrix_profiles.json`
  Sample-specific guidance, literature links, and setup biases.

- `pipelines.json`
  Published workflow metadata: titles, docs, supported inputs, tracks.

- `playbooks.json`
  Action-sheet content: entry actions, curated commands, preprocessing defaults, tools, databases.

## Maintenance Rules

### Update a recommendation rule

1. Edit `recommendation_rules.json`.
2. Each rule needs: `id`, `when` (matching clause), `recommend` (target ID), `score_bonus`, `rationale`.
3. Constraint modifiers can `block` or `prefer` options based on user constraints.
4. The engine scores all eligible options (base score 50) and recommends the highest.

### Add a new kit or pipeline

1. Add the kit to `kit_catalog` in `recommendation_rules.json`.
2. Add scoring rules referencing the new kit ID.
3. Add a checklist entry in `checklists`.
4. Update `route_mapping.json` if it maps to new molecule + study_type combinations.

### Add a new study type

1. Add the option to `questions_v2.json` (study_type page) with appropriate `visible_when`.
2. Add scoring rules in `recommendation_rules.json`.
3. Add a mapping entry in `route_mapping.json`.

### Expert rule policy

- Expert rules refine the selected backend; they do not choose a different backend.
- Allowed effects: `tool_swap`, `step_insert`, `step_skip`, `warning_only`, `preprocessing_override`.

### Curated command policy

- Only include commands that are already documented in the repository.
- Every curated command must include a `source_url`.

## Review Expectations

- Run `node docs/scripts/validate_selector_data.mjs` after editing legacy data files.
- Run `node docs/scripts/check_selector_cases.mjs` after changing legacy routing or expert heuristics.
- Keep `last_reviewed` current in `pipelines.json` when a workflow entry is refreshed.
