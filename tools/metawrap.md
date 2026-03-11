# MetaWRAP

## What It Is

[MetaWRAP](https://github.com/bxlab/metaWRAP) is a tool used for binning pipeline (metabat2, maxbin2, concoct).

## Description

MetaWRAP is an end-to-end, highly flexible pipeline utilized for comprehensive metagenomic analysis. It gracefully orchestrates read quality control, de novo assembly, aggressive binning (parallelizing MetaBAT2, MaxBin2, and CONCOCT), and final robust bin refinement.

## Basic Usage

```bash
metawrap binning -o INITIAL_BINS -t 16 -a assembly.fasta --metabat2 --maxbin2 --concoct reads_1.fastq reads_2.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/bxlab/metaWRAP
- **Main Usage:** Binning pipeline (MetaBAT2, MaxBin2, CONCOCT)
