# Reading Notes: anvi'o Workflows

These are working notes on the Snakemake-based workflow system available via `anvi-run-workflow`. The goal is not to reproduce the documentation but to record what each workflow family does, when I would reach for it, and what to watch out for.

## Contigs Workflow

**What it does:** Takes FASTA assemblies and produces annotated contigs databases—the foundational artifact that everything else in anvi'o builds on.

**When I would use it:** Any time I have assembled contigs and want to bring them into the anvi'o ecosystem. This is step one for almost any downstream analysis.

**What to watch:** Gene calling settings matter. The default gene caller (Prodigal) works well for most prokaryotic data, but metagenomic mode (`-p meta`) is needed for fragmented assemblies. Forgetting this can suppress gene calls on short contigs.

## Metagenomics Workflow

**What it does:** Orchestrates read recruitment (mapping reads against reference contigs), profile database creation, merging across samples, and optional binning. This is the workflow for multi-sample comparative metagenomics.

**When I would use it:** When I have multiple samples mapped against the same set of contigs (e.g., co-assembled environmental metagenomes) and want coverage profiles, detection metrics, and bins.

**What to watch:** Read recruitment quality depends heavily on aligner choice and mapping parameters. BWA-MEM is the default; settings that are too permissive will recruit reads from related but non-target organisms, inflating coverage.

## Pangenomics Workflow

**What it does:** Takes multiple genomes (isolates, MAGs, or a mix) and computes gene clusters—groups of genes shared across genomes. The output is a pan database that can be explored interactively.

**When I would use it:** When comparing accessory genome content across related organisms. Especially valuable for understanding resistance gene distribution, metabolic specialization, and horizontal transfer.

**What to watch:** Gene clustering parameters (MCL inflation, minbit) affect the granularity of clusters. Too aggressive clustering merges paralogous families; too conservative clustering fragments ortholog groups. There is no universal optimal setting.

## Phylogenomics Workflow

**What it does:** Extracts marker genes (typically single-copy core genes), aligns them, and constructs phylogenies. Useful for placing MAGs or genomes in evolutionary context.

**When I would use it:** When I have a set of MAGs or genomes and want to understand their evolutionary relationships beyond what 16S alone can provide.

**What to watch:** The choice and number of marker genes affects topology. Using too few markers can produce poorly supported trees; using too many from fragmented MAGs can introduce missing data artifacts.

## SRA Download Workflow

**What it does:** Automates downloading and preprocessing of public sequencing data from the NCBI Sequence Read Archive.

**When I would use it:** When building reference datasets, benchmarking pipelines, or incorporating published data into comparative analyses.

**What to watch:** SRA data can be large and downloads can be slow. Plan for storage and bandwidth before launching batch downloads.

## Cross-Cutting Observations

- All workflows use a **config file** (JSON or YAML) that controls parameters. Documenting and version-controlling these config files is essential for reproducibility.
- Workflows are designed for short-read data by default. Long-read integration is improving but may require manual adapter configuration.
- Snakemake's checkpointing means interrupted workflows can be resumed without re-running completed steps—a significant practical advantage for large analyses.

## Related Notes

- [anvi'o](../tools/anvio.md) — platform overview
- [From Classification to Calibration](../pipelines/from-classification-to-calibration.md) — where anvi'o fits in the analytical stack
