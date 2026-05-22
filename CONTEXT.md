# GenomicsForOneHealth — Context

Domain language for this repository: a collection of genomic-surveillance pipelines, an
agent-facing skill pack that drives them, and a browser-based advisor that recommends a
sequencing setup. This file names the concepts so code and conversation stay consistent.

## Language

### Pipelines and the skill pack

**Pipeline domain**:
One of the six One Health surveillance areas (Clinical Isolates & Plasmid Profiling,
Environmental Metagenomics, Food Safety, Veterinary & Zoonotic Surveillance, Viability
Assessment, eDNA Metabarcoding). Each holds protocols, scripts, and flowcharts.
_Avoid_: "project", "module" (reserved for the architecture sense: interface + implementation).

**Skill**:
A YAML workflow spec in `agent_skills/skills/` describing how one pipeline runs — its
parameters, `command_templates`, and declared hooks. The authoritative description of a run.
_Avoid_: "recipe", "playbook" (a Playbook is an Advisor concept, see below).

**Hook**:
A Python function that runs around a Skill: preflight (pre-run checks), command_builder
(parameter validation + command assembly), parsers (post-run output parsing), validation,
audit. Generic, project-agnostic hooks live in `agent_skills/core/hooks/`; tool-specific
hooks live in `agent_skills/project/hooks/`. `agent_skills/hooks/` is a backward-compatible
facade re-exporting both (see ADR-0004).
_Avoid_: "plugin", "middleware".

**Harness core / project layer / adapter**:
`agent_skills/core/` is the project-agnostic engine (hooks, schema, prompts, memory spec,
offline runner); `agent_skills/project/` is the GenomicsForOneHealth layer (tool parsers,
threshold validators, routing prompt, benchmark tasks); `agent_skills/adapters/claude_code/`
is the Claude Code adapter. The core never imports the project layer.
_Avoid_: calling the whole thing just "the skill pack" — the harness is reusable; the skills are the content.

**Memory store**:
The durable memory at `agent_skills/memory/` (format spec `agent_skills/core/memory/README.md`):
one fact per file with frontmatter, a `MEMORY.md` index, types decision/run/preference/reference.
_Avoid_: conflating it with the JSON **audit log** — the audit log is the full machine record; a memory file is the human-scannable distillation.

**Output parser**:
A Hook that turns a tool's output file into a dict. Generic ones (in `core/hooks/parsers.py`):
**VCF**, **generic TSV**. Tool-specific ones (in `project/hooks/parsers_genomics.py`):
**Kraken2 report**, **NanoStat summary**, **AMRFinderPlus table**.
_Avoid_: "loader", "reader" used interchangeably — a parser returns structured data, never raises.

### The Advisor (`docs/`)

**Advisor**:
The client-side web tool in `docs/` that recommends a Nanopore setup and pipeline from a
user's answers. Shipped as a "bonus tool" at the bottom of the GitHub Pages site.
_Avoid_: "wizard" (that names the UI step-flow, not the tool), "selector".

**Recommendation engine**:
The canonical, live Advisor engine (`recommendation-engine.js`). Scores kits, flowcells,
basecalling, and pipelines from rule bonuses in `recommendation_rules.json`. This is the
engine `index.html` loads and `app.js` calls.
_Avoid_: "selector engine" — that is a different, parked engine.

**Selector engine**:
A second, parked Advisor engine (`selector-engine.js`), example-anchored rather than
score-based. Not loaded by any page (see ADR-0001). Kept on disk as a design alternative.
_Avoid_: treating it as live, or conflating it with the Recommendation engine.

**Question spec**:
The page → question → option tree the Advisor renders (`questions_v2.json`).
_Avoid_: "form", "survey".

**Route** _(Selector-engine concept)_:
A `(sample_context, material_class, target_goal)` triple that anchors example-based selection.

**Example** _(Selector-engine concept)_:
A published, documented dataset/workflow instance that a Route matches to. Resolves to a
pipeline plus a Playbook.
_Avoid_: "sample".

**Playbook** _(Selector-engine concept)_:
Curated commands, entry actions, and preprocessing defaults attached to a pipeline/track.
_Avoid_: using "playbook" for a Skill — they are different layers.

**Matrix profile**:
A setup-bias and guidance bundle keyed to a sequencing matrix (e.g. low-biomass), used by
the guide page and the Selector engine.

## Relationships

- A **Pipeline domain** contains one or more **Skills**.
- A **Skill** is executed through **Hooks**: preflight → command_builder → parsers → validation → audit.
- The **Advisor** uses the **Recommendation engine** (canonical). The **Selector engine** is parked and unwired.
- _(Selector engine)_ A **Route** selects one or more **Examples**; an **Example** resolves to a pipeline + **Playbook**.

## Example dialogue

> **Dev:** "Should the Listeria parsing live in the **Skill** or in a **Hook**?"
> **Tim:** "The **Skill** only declares the commands and which **Output parser** to use. The parsing itself is a **Hook** — `parsers.py` — so every pipeline shares one Kraken2 reader."
>
> **Dev:** "When the **Advisor** shows a recommendation, is that the **Selector engine**?"
> **Tim:** "No — the live page runs the **Recommendation engine**. The **Selector engine** is parked; it's a richer example-anchored design we haven't wired in."

## Flagged ambiguities

- "engine" meant two different things — resolved: **Recommendation engine** (live, score-based) vs **Selector engine** (parked, example-anchored).
- "skill" (an `agent_skills/` YAML workflow) vs "playbook" (Advisor curated-command data) — distinct layers; do not interchange.
- "module" is reserved for the architecture sense (a thing with an interface and an implementation), not a Pipeline domain.
- "Kraken2 output" is ambiguous: the `--report` summary file (parsed by `hooks/parsers.py`) and the per-read **classified** file (parsed by the analysis scripts) are different formats. Name the format, not just "Kraken2 output" (see ADR-0002).
