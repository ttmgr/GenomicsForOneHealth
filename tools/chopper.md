# Chopper

## What It Is

[Chopper](https://github.com/wdecoster/chopper) is a tool used for quality and length filtering.

## Description

Chopper is a high-performance, Rust-based tool designed for filtering and trimming long-read sequencing data. It is highly optimized for speed and allows for flexible filtering of reads based on minimum length, maximum length, and average Phred quality scores.

## Basic Usage

```bash
zcat reads.fastq.gz | chopper -q 10 -l 1000 > filtered_reads.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/wdecoster/chopper
- **Main Usage:** Quality and length filtering
