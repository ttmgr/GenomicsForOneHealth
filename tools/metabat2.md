# MetaBAT2

## What It Is

[MetaBAT2](https://bitbucket.org/berkeleylab/metabat) is a tool used for metagenome binning.

## Description

MetaBAT2 is an incredibly robust, production-grade metagenomic binning tool. It systematically partitions and reconstructs individual candidate genomes from heavily mixed microbial communities, relying strictly on unique tetranucleotide frequencies and corresponding abundance profiles.

## Basic Usage

```bash
metabat2 -i assembly.fasta -a depth.txt -o bins_dir/bin
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://bitbucket.org/berkeleylab/metabat
- **Main Usage:** Metagenome binning
