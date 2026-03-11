# SeqKit

## What It Is

[SeqKit](https://github.com/shenwei356/seqkit) is a tool used for fasta/q manipulation toolkit.

## Description

SeqKit is a cross-platform, ultra-fast toolkit for manipulating FASTA and FASTQ sequences. It excels in operations such as calculating file statistics, sequence reverse-complementing, format conversion, and sophisticated sequence filtering.

## Basic Usage

```bash
seqkit stats input.fastq.gz
seqkit seq -m 1000 input.fastq > filtered.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/shenwei356/seqkit
- **Main Usage:** FASTA/Q manipulation toolkit
