# Prokka

## What It Is

[Prokka](https://github.com/tseemann/prokka) is a tool used for prokaryotic genome annotation.

## Description

Prokka is a rapid and highly automated software pipeline used for annotating draft bacterial, archaeal, and viral genomes. It takes a raw contig or assembly file and predicts genes, identifying coding sequences (CDS), rRNA, tRNA, and notable non-coding RNA.

## Basic Usage

```bash
prokka --outdir mydir --prefix mygenome contigs.fasta
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/tseemann/prokka
- **Main Usage:** Prokaryotic genome annotation
