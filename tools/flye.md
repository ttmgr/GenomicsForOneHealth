# Flye

## What It Is

[Flye](https://github.com/mikolmogorov/Flye) is a tool used for long-read de novo assembler (--meta for metagenomes).

## Description

Flye is a rapid and highly accurate de novo assembler tailored for single-molecule sequencing reads (both PacBio and Oxford Nanopore). In environmental studies, its specialized `--meta` mode is critical as it handles the highly uneven coverage profiles typical of complex metagenomic communities.

## Basic Usage

```bash
flye --nano-hq reads.fastq --out-dir flye_assembly --meta --threads 16
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/mikolmogorov/Flye
- **Main Usage:** Long-read de novo assembler (--meta for metagenomes)
