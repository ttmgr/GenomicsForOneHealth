# Seqtk

## What It Is

[Seqtk](https://github.com/lh3/seqtk) is a tool used for fast sequence processing toolkit.

## Description

Seqtk is a fast, C-based and lightweight toolkit for processing sequences in the FASTA and FASTQ formats. It is predominantly used for rapid random subsampling, format conversion, and simple sequence extraction.

## Basic Usage

```bash
seqtk sample -s100 read1.fq 10000 > sub1.fq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/lh3/seqtk
- **Main Usage:** Fast sequence processing toolkit
