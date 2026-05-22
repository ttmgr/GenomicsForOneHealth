# Food Safety

This category covers pipelines for genomic surveillance of foodborne pathogens using nanopore sequencing — enabling rapid, high-resolution detection and characterization directly from complex food safety samples.

**Contact:** Dr. Lara Urban

> **Pipeline Selector:** To route food-safety samples against the wider collection first, use the public [Pipeline Selector](https://ttmgr.github.io/GenomicsForOneHealth/).

---

## Pipelines

### [A metagenomic framework for rapid *Listeria monocytogenes* surveillance in food production environments](./Listeria-Adaptive-Sampling/README.md)
*High-resolution genomic analysis of Listeria monocytogenes from complex food safety samples using Oxford Nanopore Adaptive Sampling.*

Uses adaptive sampling to selectively enrich *Listeria monocytogenes* reads in real time during sequencing. The pipeline covers basecalling, quality control, Kraken2-based taxonomic profiling, target read extraction, de novo assembly with multiple assemblers (Flye, metaMDBG, Myloasm), Dorado polishing, and AMRFinderPlus virulence profiling. Outputs enable direct benchmarking of adaptive sampling versus native sequencing.

**Publication:** Muchaamba F, Reska T, Biggel M, Locken KM, Weilguny L, Corti S, Kelbert L, Roger S, Urban L. *A metagenomic framework for rapid Listeria monocytogenes surveillance in food production environments.* [bioRxiv, 2026](https://www.biorxiv.org/content/10.64898/2026.04.23.720354v1). DOI: [10.64898/2026.04.23.720354](https://doi.org/10.64898/2026.04.23.720354)

---

## Environment

See [`Listeria-Adaptive-Sampling/env/environment.yaml`](./Listeria-Adaptive-Sampling/env/environment.yaml), or use the unified environment at the [repository root](../environment.yaml).
