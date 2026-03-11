# Mash

## What It Is

[Mash](https://github.com/marbl/Mash) is a tool used for fast genome/plasmid distance estimation.

## Description

Mash leverages computationally efficient MinHash dimensionality reduction algorithms to rapidly estimate global sequence similarity (Mash distances) across massive datasets. It heavily streamlines comparative genomics tasks like fast genome clustering and database searching.

## Basic Usage

```bash
mash sketch -m 2 reads.fastq
mash dist ref.msh reads.msh > distances.tab
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/marbl/Mash
- **Main Usage:** Fast genome/plasmid distance estimation
