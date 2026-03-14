# Environmental Metagenomics

This category covers nanopore metagenomics pipelines applied to environmental monitoring — characterizing microbial communities from air and water samples, detecting pathogens, antimicrobial resistance genes, and viruses in situ.

**Contact:** Tim Reska (PhD Student) & Dr. Lara Urban

> **Pipeline Selector:** If you need help deciding between Air Metagenomics and Wetland Health, start with the public [Pipeline Selector](https://ttmgr.github.io/GenomicsForOneHealth/).

---

## Pipelines

### [Air Metagenomics](./Air_Metagenomics/README.md)
*Air monitoring by nanopore sequencing for the detection of bioaerosol communities.*

Long-read metagenomic sequencing of air samples collected by liquid impingement. The pipeline covers basecalling, quality filtering, taxonomic classification (Kraken2), de novo assembly (Flye), metagenomic binning (MetaWRAP), and functional annotation (Prokka, eggNOG-mapper, AMRFinderPlus).

**Published in:** [ISME Communications, 2024](https://academic.oup.com/ismecommun/article/4/1/ycae099/7714796)

---

### [Wetland Health](./Wetland_Health/README.md)
*Real-time genomic pathogen, resistance, and host range characterization from passive water sampling of wetland ecosystems.*

Multi-modal pipeline processing DNA shotgun metagenomics, AIV RNA sequencing, viral metagenomics (DIAMOND/MEGAN), and 12S rRNA vertebrate metabarcoding from water samples collected at wetland sites across Europe.

**Published in:** [bioRxiv, 2025](https://www.biorxiv.org/content/10.1101/2025.09.05.674394v1)

---

## Environment

Both pipelines use a shared environment. See [`Air_Metagenomics/env/environment.yaml`](./Air_Metagenomics/env/environment.yaml) for the Air Metagenomics environment and [`Wetland_Health/env/environment.yaml`](./Wetland_Health/env/environment.yaml) for the Wetland Health environment.

A unified environment covering both pipelines is also available at the [repository root](../environment.yaml).
