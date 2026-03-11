# Cutadapt

## What It Is

[Cutadapt](https://github.com/marcelm/cutadapt) is a tool used for primer and adapter trimming.

## Description

Cutadapt is a versatile and classical bioinformatics tool used for finding and proactively removing adapter sequences, primers, poly-A tails, and other unwanted sequences from high-throughput sequencing reads.

## Basic Usage

```bash
cutadapt -a AACCGGTT -o trimmed.fastq input.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/marcelm/cutadapt
- **Main Usage:** Primer and adapter trimming
