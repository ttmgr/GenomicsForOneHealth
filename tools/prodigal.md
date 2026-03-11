# Prodigal

## What It Is

[Prodigal](https://github.com/hyattpd/Prodigal) is a tool used for gene/orf prediction.

## Description

Prodigal (Prokaryotic Dynamic Programming Genefinding Algorithm) is a widely trusted, fast, and highly accurate microbial gene prediction framework. It often serves as the underlying gene-caller for larger annotation suites or is used individually to extract predicted protein files.

## Basic Usage

```bash
prodigal -i contigs.fasta -o genes.gff -a proteins.faa -p meta
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/hyattpd/Prodigal
- **Main Usage:** Gene/ORF prediction
