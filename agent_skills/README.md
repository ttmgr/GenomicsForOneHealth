# agent_skills: a coding-agent skill pack for One Health genomics

This directory is a machine-readable, inspectable layer over the
GenomicsForOneHealth pipeline collection. It lets LLM-assisted coding agents
(Codex, Claude Code, Cursor, Continue, and similar tools) route a sequencing
project to the right documented workflow, validate inputs, build commands only
from declared templates, parse outputs, run sanity checks, and write audit logs,
without inventing commands, parameters, tools, or databases.

It is not a chatbot demo. It is a workflow-orchestration layer designed for
inspectability and reproducibility, and it is useful even with no LLM runtime: the
hooks and the eval runner are plain Python you can call directly.

The local repository is the source of truth. Current public Oxford Nanopore and
EPI2ME references are used only for comparison and completeness (see
`references/external_nanopore_epi2me_inventory.md`); they never override the local
workflows.

## Layout

```
agent_skills/
  README.md                  this file
  AGENTS.md                  agent-agnostic operating rules
  CLAUDE.md                  Claude Code operating rules
  schemas/skill.schema.json  JSON Schema for a skill
  skills/*.yaml              one skill per documented workflow (13)
  hooks/                     preflight, command_builder, parsers, validation, audit
  prompts/                   reusable prompts (use / extract / validate)
  references/                upstream Nanopore + EPI2ME comparison inventory
  examples/                  five worked examples
  evals/                     benchmark_tasks.yaml + run_benchmarks.py
```

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

- `preflight.py`: input/file/dir/database/command existence checks.
- `command_builder.py`: load a skill, validate parameters, build (never execute)
  commands. It refuses undeclared parameters, reports missing required parameters,
  and shell-quotes values to prevent injection.
- `parsers.py`: NanoStat, Kraken2 report, AMRFinderPlus, VCF, and generic TSV.
- `validation.py`: low yield, low N50, low classification rate, contamination,
  missing AMR hits, empty output, missing database, missing command. Default
  thresholds come from `Air_Metagenomics/config/config.yaml`.
- `audit.py`: JSON audit log with timestamp, inputs, parameters, commands, results,
  flags, source files, and external references.

## Quick start

```bash
# inspect a skill
python -c "from agent_skills.hooks import command_builder as cb; \
import json; print(json.dumps(cb.load_skill_yaml('agent_skills/skills/cre_plasmid_clustering.yaml')['skill']['display_name']))"

# run the offline benchmark suite (no LLM, no bioinformatics tools needed)
python agent_skills/evals/run_benchmarks.py
```

To drive a workflow with an agent, follow `prompts/use_skill_pack.md`.

## Caveats

All model outputs from this pack are suggestions, not biological, clinical,
regulatory, or diagnostic conclusions. Commands are built, not executed; the human
remains responsible for running them and interpreting results.
