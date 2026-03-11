# VSEARCH

## What It Is

[VSEARCH](https://github.com/torognes/vsearch) is a tool used for sequence analysis (clustering, chimera removal).

## Description

VSEARCH is a highly versatile, open-source alternative to USEARCH. It executes numerous essential steps in metabarcoding pipelines, encompassing sequence clustering, rigorous chimera detection, global alignments, and dereplication.

## Basic Usage

```bash
vsearch --cluster_fast input.fasta --id 0.97 --centroids otus.fasta
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/torognes/vsearch
- **Main Usage:** Sequence analysis (clustering, chimera removal)
