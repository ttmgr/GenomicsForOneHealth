# Filtlong

## What It Is

[Filtlong](https://github.com/rrwick/Filtlong) is a tool used for quality-based long read filtering.

## Description

Filtlong is a quality filtering tool explicitly designed for Nanopore long reads. Unlike simple threshold-based filters, it employs a relative scoring system based on both read length and read quality, allowing users to retain the 'best' reads up to a given target coverage or percentage.

## Basic Usage

```bash
filtlong --min_length 1000 --keep_percent 90 input.fastq > best_reads.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/rrwick/Filtlong
- **Main Usage:** Quality-based long read filtering
