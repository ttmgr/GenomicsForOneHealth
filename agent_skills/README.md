# agent_skills: a portable coding-agent harness (with a One Health skill layer)

This directory is a machine-readable, inspectable harness for driving documented
workflows with LLM-assisted coding agents (Codex, Claude Code, Cursor, Continue,
and similar tools). An agent uses it to route a project to the right documented
workflow, validate inputs, build commands only from declared templates, parse
outputs, run sanity checks, and write audit logs and memory, **without inventing
commands, parameters, tools, or databases**.

It is built as a portable **harness** with a thin project layer on top, so the
engine can be lifted into any repository:

- a project-agnostic **core** (the engine, instruction contract, schema, memory
  format, and offline checks);
- a **Claude Code adapter** (the only Claude-specific part);
- a **project layer** that supplies this repository's tool-specific hooks, routing
  prompt, and benchmark tasks;
- the **skills** — 13 GenomicsForOneHealth YAML workflow specs — as the *optional*
  project content the harness drives.

It is not a chatbot demo. It is a workflow-orchestration layer designed for
inspectability and reproducibility, and it is useful even with no LLM runtime: the
hooks and the eval runner are plain Python you can call directly. The local
repository is the source of truth; external references are used only for comparison
and never override the local workflows.

## Layout

```
agent_skills/
  README.md                  this file
  core/                      ── project-agnostic harness ──
    AGENTS.md                agent-agnostic operating contract
    schemas/skill.schema.json  JSON Schema for a skill
    hooks/                   preflight, command_builder, audit, generic parsers/validation
    prompts/                 extract_new_skill.md, validate_skill.md
    memory/README.md         the memory format spec
    eval/run_harness_checks.py  content-free offline runner
  adapters/claude_code/      ── Claude Code adapter ──
    CLAUDE.md                Claude Code operating rules
    README.md                how to install the harness in another repo
    settings.hooks.sample.json  sample .claude/settings.json wiring
  project/                   ── GenomicsForOneHealth layer ──
    hooks/                   parsers_genomics.py, validation_genomics.py
    prompts/use_skill_pack.md  project routing
    eval/                    benchmark_tasks.yaml, fixtures.py
  skills/*.yaml              13 skill specs (optional project content)
  references/                upstream Nanopore + EPI2ME comparison inventory
  examples/                  five worked examples
  memory/                    live memory store for this repo (MEMORY.md + facts)
  hooks/                     backward-compatible facade re-exporting core + project
  evals/run_benchmarks.py    project wiring for the offline runner
```

The `hooks/` facade and `evals/run_benchmarks.py` are kept so existing imports
(`from agent_skills.hooks import command_builder`) and the published docs links
keep working unchanged. New code should import from `agent_skills.core.hooks`
(portable) or `agent_skills.project.hooks` (project-specific).

## Skills

Each YAML in `skills/` describes one workflow: its domain, supported inputs, tools
(with version pins from the repository env files), required databases, declared
parameters, ordered `command_templates` extracted verbatim from the repository,
pre/post/validation hook references, outputs, caveats, failure modes, the
`source_files` it is derived from, any `external_references` used for comparison,
and `needs_review` notes for anything ambiguous.

The 13 skills: `air_metagenomics`, `wetland_dna_shotgun_metagenomics`,
`wetland_aiv_rna_consensus`, `wetland_viral_metagenomics`,
`wetland_12s_vertebrate_metabarcoding`, `zambia_edna_metabarcoding`,
`listeria_adaptive_sampling`, `amr_nanopore`, `cre_plasmid_clustering`,
`nanopore_amr_host_association`, `avian_influenza_profiling`, `from_feather_to_fur`,
`squiggle4viability`.

This pack is the agent-facing sibling of the repository's human-facing Pipeline
Advisor (`docs/`), which already enforces the same discipline: every curated
command must cite a source.

## Hooks

Standard library only, except `command_builder.load_skill_yaml`, which uses PyYAML
(already a project dependency; see the root `environment.yaml`).

Generic engine (`core/hooks/`, portable):

- `preflight.py`: input/file/dir/database/command existence checks.
- `command_builder.py`: load a skill, validate parameters, build (never execute)
  commands. It refuses undeclared parameters, reports missing required parameters,
  and shell-quotes values to prevent injection.
- `parsers.py`: VCF and generic TSV.
- `validation.py`: low classification rate (heuristic), empty output, missing
  database, missing command.
- `audit.py`: JSON audit log, plus `append_run_record` to distil a run into the
  memory store.

Project layer (`project/hooks/`, GenomicsForOneHealth-specific):

- `parsers_genomics.py`: NanoStat, Kraken2 report, AMRFinderPlus.
- `validation_genomics.py`: low yield, low N50, contamination, missing AMR hits.
  Default thresholds come from `Air_Metagenomics/config/config.yaml`.

## Memory

Durable memory persists what code and git history don't: architectural decisions,
distilled agent-run summaries, and operator preferences. The format is specified in
`core/memory/README.md` (one fact per file, frontmatter, a `MEMORY.md` index,
`[[wikilinks]]`), mirroring the Claude Code memory convention. The live store for
this repo is `agent_skills/memory/`; `audit.append_run_record` writes `type: run`
entries automatically.

## Quick start

```bash
# inspect a skill
python -c "from agent_skills.hooks import command_builder as cb; \
import json; print(json.dumps(cb.load_skill_yaml('agent_skills/skills/cre_plasmid_clustering.yaml')['skill']['display_name']))"

# run the offline benchmark suite (no LLM, no bioinformatics tools needed)
python agent_skills/evals/run_benchmarks.py
```

To drive a workflow with an agent, follow `project/prompts/use_skill_pack.md`. To
lift the harness into another repository, see `adapters/claude_code/README.md`.

## Caveats

All model outputs from this pack are suggestions, not biological, clinical,
regulatory, or diagnostic conclusions. Commands are built, not executed; the human
remains responsible for running them and interpreting results.
