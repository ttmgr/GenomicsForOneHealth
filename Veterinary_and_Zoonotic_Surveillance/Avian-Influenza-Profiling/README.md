# Avian Influenza Profiling Pipeline

Rapid avian influenza virus (AIV) characterization using the latest RNA and DNA Oxford Nanopore sequencing chemistries. This pipeline benchmarks multiple approaches — direct RNA, cDNA, and DNA sequencing — for AIV consensus sequence generation, subtyping, and phylogenetic analysis.

**First Author:** Dr. Albert Perlas | **Corresponding Author:** Dr. Lara Urban
**Published in:** [Virus Evolution, 2024](https://academic.oup.com/ve/article/11/1/veaf010/8020575)

> **Abstract:** Avian influenza virus (AIV) currently causes a panzootic with extensive mortality in wild birds, poultry, and wild mammals, underscoring the need for efficient monitoring. We systematically investigate AIV genetic characterization through rapid, portable nanopore sequencing by comparing the latest DNA and RNA nanopore sequencing approaches and various computational pipelines for viral consensus sequence generation and phylogenetic analysis. We show that the latest direct RNA nanopore sequencing updates improve consensus sequence generation, but that the application of the latest DNA nanopore chemistry after reverse transcription and amplification outperforms native viral RNA sequencing by achieving higher sequencing accuracy and throughput. We applied these sequencing approaches together with portable AIV diagnosis and quantification tools to environmental samples from a poultry farm.

---

## Quick Start

1. **Install dependencies** — see the centralized [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) for Dorado and tool setup. All other tools are available via the unified [environment.yaml](../../environment.yaml) at the repository root (`conda activate genomics-onehealth`).
2. **Run the interactive wrapper**, which guides you to the correct script for your data type and workflow mode:
   ```bash
   bash run_pipeline.sh
   ```
3. **Or run individual scripts directly** (see below).

---

## Pipeline Structure

This pipeline contains separate scripts for each sequencing chemistry and analysis approach. Choose the one that matches your data:

### Basecalling

| Script | Chemistry | Use case |
|---|---|---|
| `base_calling_RNA002.sh` | Direct RNA002 | Basecall legacy direct-RNA data |
| `base_calling_RNA004.sh` | Direct RNA004 | Basecall latest direct-RNA data |
| `base_calling_cDNA.sh` | cDNA (ms-RT-PCR + RBK) | Basecall cDNA data from rapid barcoding kit |
| `RNA_mod_base_calling_dRNA004.sh` | Direct RNA004 | Basecall + detect m6A RNA modifications |

```bash
# Example: basecall RNA004 data
bash base_calling_RNA004.sh /path/to/pod5 /path/to/output.fastq

# Example: basecall cDNA data
bash base_calling_cDNA.sh /path/to/pod5 /path/to/output.fastq

# Example: basecall + m6A detection
bash RNA_mod_base_calling_dRNA004.sh /path/to/pod5 /path/to/output_dir
```

### Assembly

| Script | Mode | Use case |
|---|---|---|
| `denovo_flye.sh` | De novo (standard) | Assemble reads, polish with Minimap2 + Racon |
| `denovo_meta_flye.sh` | De novo (metagenomic) | Same, with Flye `--meta` for complex samples |

```bash
bash denovo_flye.sh /path/to/reads.fastq /path/to/output_dir
bash denovo_meta_flye.sh /path/to/reads.fastq /path/to/output_dir
```

### Reference-Based Consensus & Variant Calling

| Script | Input chemistry | Use case |
|---|---|---|
| `flu_ref_based_new.sh` | cDNA | Align to AIV reference, call variants (BCFTools), generate consensus |
| `flu_ref_based_new_RNA.sh` | RNA002 / RNA004 | Same, optimized for direct-RNA data |

Both scripts align reads to a provided reference FASTA, identify the best-matching segment reference, call variants with BCFTools, and generate a consensus sequence.

```bash
bash flu_ref_based_new.sh /path/to/reads.fastq /path/to/output_dir /path/to/reference.fasta
bash flu_ref_based_new_RNA.sh /path/to/reads.fastq /path/to/output_dir /path/to/reference.fasta
```

### IRMA Consensus Assembly

IRMA is an influenza-specific iterative tool that outperforms generic variant callers for segment reconstruction.

```bash
bash irma.sh /path/to/reads.fastq /path/to/output_dir
```

---

## Tools Used

| Tool | Version | Purpose |
|---|---|---|
| Dorado | ≥0.7 | Basecalling (RNA002, RNA004, cDNA) |
| Minimap2 | ≥2.28 | Read alignment to AIV references |
| Samtools | ≥1.19 | BAM manipulation |
| BCFTools | ≥1.19 | Variant calling and consensus generation |
| Flye | ≥2.9.4 | De novo assembly |
| Racon | ≥1.5.0 | Rapid consensus polishing |
| IRMA | ≥1.1.4 | Influenza-specific consensus assembly |

Install all tools (except Dorado) via the unified environment at the repository root:
```bash
mamba env create -f ../../environment.yaml
conda activate genomics-onehealth
```
