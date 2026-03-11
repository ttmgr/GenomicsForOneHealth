# Nanomotif

## What It Is

[Nanomotif](https://github.com/MicrobialDarkMatter/nanomotif) is a tool used for methylation-based contig association.

## Description

Nanomotif intelligently utilizes Oxford Nanopore modified base calls (detectable methylation) to identify distinct bipartite motifs and establish contig associations. This proves exceptionally useful in metagenomic studies for securely linking separate plasmid contigs back to their correct host chromosomes.

## Basic Usage

```bash
nanomotif find_motifs --bam mapped.bam --contigs assembly.fasta --out nanomotif_out
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/MicrobialDarkMatter/nanomotif
- **Main Usage:** Methylation-based contig association
