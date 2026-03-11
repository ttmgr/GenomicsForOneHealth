# Kraken2

## What It Is

[Kraken2](https://github.com/DerrickWood/kraken2) is a tool used for k-mer based taxonomic classification.

## Description

Kraken2 is a state-of-the-art taxonomic classification system that utilizes exact k-mer matches down to the lowest common ancestor (LCA) to achieve outstanding accuracy and extreme classification speeds. It classifies reads by searching a centralized, pre-compiled reference database.

## Basic Usage

```bash
kraken2 --db /path/to/kraken2_db --threads 16 --report report.txt --output kraken_output.txt reads.fastq
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/DerrickWood/kraken2
- **Main Usage:** K-mer based taxonomic classification
