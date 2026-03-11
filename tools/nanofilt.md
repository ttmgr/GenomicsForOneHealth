# NanoFilt

## What It Is

[NanoFilt](https://github.com/wdecoster/nanofilt) is a tool used for quality and length filtering for ont reads.

## Description

NanoFilt is a python-based utility for streaming quality and length filtering of long-read sequencing data. It easily integrates into UNIX pipelines, allowing FASTQ streams directly from basecalling to be filtered before heavy downstream analysis.

## Basic Usage

```bash
gunzip -c reads.fastq.gz | NanoFilt -q 10 -l 500 > high_quality_reads.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/wdecoster/nanofilt
- **Main Usage:** Quality and length filtering for ONT reads
