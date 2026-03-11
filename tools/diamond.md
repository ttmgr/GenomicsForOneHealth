# DIAMOND

## What It Is

[DIAMOND](https://github.com/bbuchfink/diamond) is a tool used for fast protein alignment (blastx/blastp).

## Description

DIAMOND is a robust sequence aligner optimized for protein and translated DNA searches. It is specifically designed for high-performance analysis of massive sequence datasets, completing BLASTp and BLASTx alignments magnitudes faster than traditional BLAST algorithms.

## Basic Usage

```bash
diamond blastx -d nr.dmnd -q reads.fasta -o matches.daa
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/bbuchfink/diamond
- **Main Usage:** Fast protein alignment (BLASTx/BLASTp)
