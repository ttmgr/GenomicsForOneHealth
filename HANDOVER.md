# Handover

This document is the entry point for maintaining GenomicsForOneHealth after a maintainer
leaves. It records who owns what, how to keep the moving parts current, and where to look
first. Lines marked **TODO (fill in)** need a person's input before they are accurate.

## What this repository is

A collection of 10 Nanopore-based genomic-surveillance pipelines across 6 One Health
domains, plus a browser-based [Sequencing Advisor](https://ttmgr.github.io/GenomicsForOneHealth/)
served from `docs/`. Start with [`README.md`](./README.md); contribution rules are in
[`CONTRIBUTING.md`](./CONTRIBUTING.md); domain vocabulary is in [`CONTEXT.md`](./CONTEXT.md);
recorded design decisions are in [`adr/`](./adr/).

## People

- **Departing:** Tim Reska — last day **TODO (fill in date)**. Was lead on Environmental
  Metagenomics (Air & Wetland).
- **Staying / PI:** Prof. Dr. Lara Urban (Urban Lab, University of Zurich & Helmholtz AI).
- **TODO (fill in):** who else is staying, and who inherits the Environmental Metagenomics
  pipelines and the docs-site Advisor.

### Pipeline ownership

| Domain | Pipeline | Owner after handover |
|--------|----------|----------------------|
| Environmental Metagenomics | Air Metagenomics | **TODO** |
| Environmental Metagenomics | Wetland Health | **TODO** |
| Clinical Isolates & Plasmid Profiling | AMR (nanopore) | **TODO** |
| Clinical Isolates & Plasmid Profiling | CRE Plasmid clustering | **TODO** |
| Clinical Isolates & Plasmid Profiling | Nanopore AMR Host Association | **TODO** |
| Food Safety | Listeria Adaptive Sampling | **TODO** |
| Veterinary & Zoonotic Surveillance | Avian Influenza Profiling | **TODO** |
| Veterinary & Zoonotic Surveillance | From feather to fur | **TODO** |
| Viability Assessment | Squiggle4Viability | **TODO** |
| eDNA Metabarcoding | eDNA Metabarcoding | **TODO** |

## Contact routing

Questions about any pipeline should go to a [GitHub issue](https://github.com/ttmgr/GenomicsForOneHealth/issues)
or to the [Urban Lab](https://sites.google.com/view/urban-lab/home). Individual maintainer
names were removed from the pipeline READMEs so contacts do not break when people move on;
keep the table above as the single place that maps pipelines to people.

## Maintenance

### Reference databases

The pipelines depend on external databases installed per
[`INSTALL_AND_DATABASES.md`](./INSTALL_AND_DATABASES.md): Kraken2, AMRFinderPlus, DIAMOND,
and MIDORI2 (eDNA). These are intentionally **not** committed (see `.gitignore`).

- **TODO (fill in):** refresh cadence and owner for each database (e.g. "AMRFinderPlus
  database: update on each AMRFinderPlus release"; "Kraken2: rebuild when the NCBI taxonomy
  release changes"). Note where the maintained copies live on the cluster.

### Software environment

The unified conda/mamba environment is [`environment.yaml`](./environment.yaml) (some
pipelines also ship a pipeline-specific `env/environment.yaml`). When a pinned tool version
goes stale, update both per the rule in `CONTRIBUTING.md`. Dorado is installed as a manual
binary download, not via conda — see `INSTALL_AND_DATABASES.md`.

### Docs site (Sequencing Advisor)

The site under `docs/` is published with **GitHub Pages** at
`https://ttmgr.github.io/GenomicsForOneHealth/`. It is a static client-side app — no build
step. Key files:

- `docs/index.html` — landing page; embeds the Advisor.
- `docs/recommendation-engine.js` — the live scoring engine (canonical; see ADR-0001).
- `docs/app.js` — wires the question flow to the engine.
- `docs/recommendation_rules.json`, `docs/questions_v2.json`, `docs/data/` — the rules,
  question tree, and reference data the engine reads.

To change a recommendation, edit the rules/data JSON (not the engine logic) and reload the
page locally to test, then commit — Pages redeploys automatically on push to `main`.
`docs/advisor-ont.html` is a standalone full-page variant of the same Advisor; it is **not**
linked from the site and duplicates the embedded Advisor — decide whether to promote or
remove it. **TODO (fill in):** confirm the GitHub Pages source branch/folder in repo
Settings → Pages.

## Conventions

- Work on a feature branch off `main`; open a Pull Request (see `CONTRIBUTING.md`). Run
  `python verify_links.py` before opening a PR.
- New pipelines are accepted only when tied to an Urban Lab publication (`CONTRIBUTING.md`).
- Analysis/figure scripts are publication-adjacent and frozen — see ADR-0002 and ADR-0003
  before refactoring them.

## Related repositories

- The optional agent-skills harness that used to live in `agent_skills/` was extracted to
  [ttmgr/Tim_Reska → nanopore_agentic_system](https://github.com/ttmgr/Tim_Reska/tree/main/nanopore_agentic_system).
  It is not required to run any pipeline here.
