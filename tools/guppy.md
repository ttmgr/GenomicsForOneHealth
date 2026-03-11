# Guppy

## What It Is

[Guppy](https://community.nanoporetech.com/) is a tool used for ont legacy basecaller.

## Description

Guppy is the legacy basecaller for Oxford Nanopore sequencing data. While largely superseded by Dorado for new pipeline developments, it remains relevant for reproducing older analyses, processing older flow cell data, or working with specific hardware constraints.

## Basic Usage

```bash
guppy_basecaller -i fast5/ -s fastq_out/ -c dna_r10.4.1_e8.2_400bps_sup.cfg -x "cuda:all:100%"
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://community.nanoporetech.com/ (Distributed by ONT)
- **Main Usage:** ONT legacy basecaller
