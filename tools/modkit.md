# Modkit

## What It Is

[Modkit](https://github.com/nanoporetech/modkit) is a tool used for modified base analysis from bam.

## Description

Modkit is an official Oxford Nanopore tool for extracting, manipulating, and analyzing modified base information from BAM files produced by basecallers like Dorado. It enables users to aggregate modification probabilities into standard formats like bedMethyl or extract specific subsets of modified bases for downstream epigenetic analysis.

## Basic Usage

```bash
modkit pileup mapped.bam output.bedm --ref reference.fasta
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/nanoporetech/modkit
- **Main Usage:** Modified base analysis from BAM
