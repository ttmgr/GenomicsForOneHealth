# Medaka

## What It Is

[Medaka](https://github.com/nanoporetech/medaka) is a tool used for ont-specific assembly polishing.

## Description

Medaka is a neural-network-based tool created by Oxford Nanopore to craft highly accurate consensus sequences and variant calls directly from nanopore sequencing data. It parses mapped read pileups to effectively resolve local insertion and deletion errors commonly produced by initial assemblers.

## Basic Usage

```bash
medaka_consensus -i reads.fastq -d assembly.fasta -o medaka_output -t 8 -m r1041_e82_400bps_sup_v4.2.0
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/nanoporetech/medaka
- **Main Usage:** ONT-specific assembly polishing
