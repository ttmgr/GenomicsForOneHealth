# agent_skills is a portable harness (agnostic core + Claude Code adapter) over a thin project layer

`agent_skills/` began as a project-specific skill pack: 13 GenomicsForOneHealth YAML
workflow specs plus Python hooks and instruction files written in service of those
YAMLs. The reusable value, though, is the *mechanism* — memory, hooks, and
instruction files that route a project to a documented workflow and build commands
without inventing them — not the genomics content. The engine and the genomics
content were interleaved in the same files, and there was no memory subsystem.

We restructured `agent_skills/` in place into three layers: a project-agnostic
**core** (`core/` — engine hooks, schema, agnostic `AGENTS.md`, the `extract`/
`validate` prompts, the memory-format spec, and a content-free offline runner), a
**Claude Code adapter** (`adapters/claude_code/`), and a thin **project layer**
(`project/` — the tool-specific parsers, threshold validators, routing prompt, and
benchmark tasks/fixtures). The 13 skill YAMLs remain as an optional project content
layer. A new memory subsystem (`core/memory/` spec + `agent_skills/memory/` store,
fed by `audit.append_run_record`) persists decisions, run summaries, and
preferences.

## Considered options

- **Layer in place with compatibility shims (chosen).** The hooks split by concern
  (100%-generic files move to `core/`; `parsers.py`/`validation.py` split into a
  generic core module and a `*_genomics` project module). `agent_skills/hooks/`
  becomes a facade re-exporting both, and `evals/run_benchmarks.py` becomes a thin
  wiring over the generic runner. Old import paths, the README quick-start, and the
  published `docs/agent-skills.html` links keep working. Moderate diff, no behavior
  change to any hook function.
- **Layer and rewrite every reference (no shims).** Cleaner end state but a larger,
  riskier diff that re-touches the docs page and every importer; rejected as not
  worth the churn now.
- **Leave it project-specific.** Rejected: it blocks the stated goal of lifting the
  harness into other repositories.

## Consequences

- `core/` must never import `project/`; the dependency runs core ← project ← facade.
  This keeps the core liftable into any repo with an empty or different project layer.
- The skill YAMLs stay at `agent_skills/skills/` and `evals/run_benchmarks.py` keeps
  its path precisely so the docs-page GitHub links and quick-start commands do not
  break; the facade is the seam that makes this possible.
- Run history is now part of durable memory (`agent_skills/memory/`) in addition to
  the JSON audit logs.
- A future reviewer should add new portable code under `core/` and new
  GenomicsForOneHealth specifics under `project/`, not back into the `hooks/` facade.

_Status: accepted._
