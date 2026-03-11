# OBITools

## What It Is

[OBITools](https://github.com/metabarcoding/obitools4) is a tool used for edna metabarcoding toolkit.

## Description

OBITools is an expansive set of Python programs specifically tailored for analyzing environmental DNA (eDNA) metabarcoding data. It smoothly handles the entire amplicon pipeline, including demultiplexing, quality filtering, sequence clustering, and taxonomic assignment.

## Basic Usage

```bash
illuminapairedend -r reads.fastq > paired.fastq
ngsfilter -t sample_metadata.txt -u unidentified.fastq paired.fastq > identified.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/metabarcoding/obitools4
- **Main Usage:** eDNA metabarcoding toolkit
