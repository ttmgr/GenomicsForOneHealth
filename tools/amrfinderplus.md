# AMRFinderPlus

## What It Is

[AMRFinderPlus](https://github.com/ncbi/amr) is a tool used for ncbi amr gene detection.

## Description

AMRFinderPlus serves to detect and classify antimicrobial resistance (AMR) genes, point mutations, and stress-response virulence factors in protein or nucleotide sequences. It utilizes NCBI's heavily curated reference databases and profile Hidden Markov Models (HMMs).

## Basic Usage

```bash
amrfinder -n assembly.fasta --plus -o amrfinder_results.tsv
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/ncbi/amr
- **Main Usage:** NCBI AMR gene detection
