# Minimap2

## What It Is

[Minimap2](https://github.com/lh3/minimap2) is a tool used for long-read and assembly alignment.

## Description

Minimap2 is a versatile, fast, and highly accurate sequence alignment program. While it can map DNA or mRNA sequences against huge reference databases, in our pipelines, it is predominantly used to map raw long reads back onto de novo assemblies for consensus polishing and depth profiling.

## Basic Usage

```bash
minimap2 -ax map-ont reference.fasta reads.fastq > alignment.sam
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/lh3/minimap2
- **Main Usage:** Long-read and assembly alignment
