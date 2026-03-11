# metaMDBG

## What It Is

[metaMDBG](https://github.com/GaetanBenoworkt/metaMDBG) is a tool used for metagenomic assembler for long reads.

## Description

metaMDBG is a memory-efficient metagenomic assembler optimized for long reads (PacBio HiFi and ONT). By leveraging a multi-k de Bruijn graph framework, it effectively minimizes misassemblies in highly complex microbial communities while still producing contiguous assemblies.

## Basic Usage

```bash
rust-mdbg --in reads.fastq --out output_dir --threads 16
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/GaetanBenoworkt/metaMDBG
- **Main Usage:** Metagenomic assembler for long reads
