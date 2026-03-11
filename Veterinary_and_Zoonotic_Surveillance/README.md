# Veterinary & Zoonotic Surveillance

This category covers nanopore-based pipelines for veterinary virology and zoonotic disease surveillance — profiling avian influenza viruses (AIV) and tracking viral transmission across host species.

**Contact:** Dr. Albert Perlas & Dr. Lara Urban

---

## Pipelines

### [Avian Influenza Profiling](./Avian-Influenza-Profiling/README.md)
*Rapid avian influenza profiling using the latest RNA and DNA nanopore chemistries.*

Benchmarks RNA004, cDNA, and DNA nanopore approaches for AIV consensus sequence generation and subtyping. Includes de novo assembly (Flye), reference-based alignment, consensus generation (BCFTools, iVar), and IRMA-based influenza-specific assembly. Applied to environmental samples from a poultry farm.

**Published in:** [Virus Evolution, 2024](https://academic.oup.com/ve/article/11/1/veaf010/8020575)

---

### [From Feather to Fur](./From_feather_to_fur/README.md)
*Variant calling workflow tracking AIV transmission pathways from avian to mammalian hosts.*

Traces zoonotic transmission signatures by calling variants (Minimap2 + Clair3) across matched avian and mammalian host samples and comparing them against reference inocula. Consensus sequences are annotated using FluSurver for host-adaptation marker analysis.

**First Author:** Dr. Albert Perlas

---

## Environment

See the unified environment at the [repository root](../environment.yaml). Avian Influenza Profiling also includes per-script basecalling commands for each nanopore chemistry in its pipeline `.md` files.
