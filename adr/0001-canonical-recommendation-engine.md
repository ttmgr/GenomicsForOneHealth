# Canonical Advisor engine: recommendation-engine.js (selector-engine.js parked)

The Advisor in `docs/` contains two complete recommenders. `recommendation-engine.js`
(score-based) is the live one — it is the only engine `index.html` loads and the only one
`app.js` calls. `selector-engine.js` (example-anchored, with its own `matchesWhen`,
page-navigation, and a richer data model spanning examples/playbooks/pipelines/expert_rules/
nanopore_profiles/external_workflows/matrix_profiles) is **parked**: nothing references it.

We chose to keep `recommendation-engine.js` canonical and leave `selector-engine.js` on disk
(not deleted) as a design alternative, rather than wiring it in or removing it.

## Considered options

- **Keep score-based engine, park the selector engine (chosen).** Lowest risk; preserves the
  shipped, working behavior and Tim's deliberate selector-engine work for possible future use.
- **Finish wiring the selector engine, retire the score-based one.** Higher quality target
  (the selector engine is pure and UMD-exported, hence testable) but a large, behavior-changing
  effort — out of scope for an architecture-cleanup pass.
- **Delete the selector engine and its data.** Removes ~684 lines of JS plus ~4,500 lines of
  curated JSON, but discards deliberate work; rejected as premature.

## Consequences

- `app.js` no longer fetches the seven JSON files that only the Selector engine consumed
  (`pipelines`, `playbooks`, `examples`, `expert_rules`, `nanopore_profiles`,
  `external_workflows`, `matrix_profiles`) — these were loaded on every visit but never read.
  `nanopore-guide.html` still fetches `matrix_profiles.json` itself; that is unaffected.
- The following files are now unreferenced by any page and safe to delete if the parked engine
  is abandoned: `docs/selector-engine.js`, `docs/data/questions.json` (superseded by
  `questions_v2.json`), and the seven JSON files above (except `matrix_profiles.json`, still
  used by the guide page). They are retained pending Tim's decision to delete or revive.
- A future review should not "fix" the missing wiring of `selector-engine.js` without first
  deciding to revive it — that is the deliberate state recorded here.

_Note: ADRs are kept at the repo-root `adr/` rather than `docs/adr/`, because `docs/` is the
published GitHub Pages site and Jekyll would render stray Markdown into public pages._
