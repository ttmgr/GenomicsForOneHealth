# Racon

## What It Is

[Racon](https://github.com/isovic/racon) is a tool used for assembly consensus polishing.

## Description

Racon is an ultrafast consensus module utilized for polishing raw de novo DNA assemblies of long, uncorrected reads. It takes an assembly draft, the original raw reads, and the read-to-assembly alignment data to compute a structurally improved, polished consensus sequence.

## Basic Usage

```bash
racon reads.fastq alignment.sam unpolished_assembly.fasta > polished_assembly.fasta
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/isovic/racon
- **Main Usage:** Assembly consensus polishing
