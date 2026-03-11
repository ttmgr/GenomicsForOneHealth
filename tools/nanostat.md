# NanoStat

## What It Is

[NanoStat](https://github.com/wdecoster/NanoStat) is a tool used for read quality statistics.

## Description

NanoStat is an exploratory tool that quickly generates comprehensive summary statistics for long-read sequencing datasets. It provides metrics such as N50, total yield, read length distributions, and quality score profiles from FASTQ, FASTA, or BAM files.

## Basic Usage

```bash
NanoStat --fastq reads.fastq.gz --threads 4
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/wdecoster/NanoStat
- **Main Usage:** Read quality statistics
