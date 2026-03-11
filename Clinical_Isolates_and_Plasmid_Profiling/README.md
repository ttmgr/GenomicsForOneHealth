# Clinical Isolates & Plasmid Profiling

This category covers nanopore-based pipelines for clinical genomic diagnostics — characterizing antimicrobial resistance (AMR), plasmid content, and resistance-host associations directly from sequencing data.

**Contacts:** Ela Sauerborn (PhD Student), Harika Ürel (PhD Student) & Dr. Lara Urban

---

## Pipelines

### [AMR Nanopore](./AMR_nanopore/README.md)
*Rapid and reliable clinical detection of Antimicrobial Resistance directly from nanopore sequencing data.*

Isolate-focused pipeline demonstrating how nanopore sequencing can detect low-abundance plasmid-mediated resistance in complex infection scenarios. Covers basecalling, de novo assembly (Flye), polishing (Medaka), AMR profiling (AMRFinderPlus), plasmid typing (MOB-Suite, Mash), and plasmid clustering (Pling).

**Published in:** [Nature Communications, 2024](https://www.nature.com/articles/s41467-024-49851-4)

---

### [CRE Plasmid Clustering](./CRE-Plasmid-clustering/README.md)
*Advanced characterization and clustering of plasmids in Carbapenem-resistant Enterobacterales (CRE) for clinical settings.*

Characterizes and clusters plasmids from CRE isolates using Mash distance estimation and Pling network analysis. Relevant for understanding plasmid transmission routes in hospital settings.

**First Author:** Ela Sauerborn

---

### [Nanopore AMR Host Association](./Nanopore-AMR-Host-Association/README.md)
*Nanopore metagenomic sequencing links clinically relevant resistance determinants to their pathogenic hosts via DNA methylation.*

Metagenomic pipeline that links plasmid-encoded AMR genes to their bacterial host using shared DNA methylation motifs (detected by Nanomotif/Modkit). Validated on clinical rectal swabs, achieving 91% accuracy at species level.

**Published in:** [bioRxiv, 2026](https://www.biorxiv.org/content/10.64898/2026.02.16.706128v1)

---

## Environment

The Nanopore AMR Host Association pipeline provides its own setup instructions in its README. For AMR Nanopore and CRE Plasmid Clustering, see the unified environment at the [repository root](../environment.yaml).
