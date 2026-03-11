# ABRicate

## What It Is

[ABRicate](https://github.com/tseemann/abricate) is a tool used for mass screening for amr/virulence genes.

## Description

ABRicate is a mass screening utility designed to quickly interrogate large numbers of contigs or genome assemblies for AMR and virulence genes. It aggregates several popular public databases internally, including ResFinder, CARD, ARG-ANNOT, and MegaRES.

## Basic Usage

```bash
abricate --db card assembly.fasta > card.out
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/tseemann/abricate
- **Main Usage:** Mass screening for AMR/virulence genes
