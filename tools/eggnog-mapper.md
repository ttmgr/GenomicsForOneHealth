# eggNOG-mapper

## What It Is

[eggNOG-mapper](https://github.com/eggnogdb/eggnog-mapper) is a tool used for functional annotation.

## Description

eggNOG-mapper allows for the rapid functional annotation of uncharacterized sequences based on precomputed orthology assignments from the robust eggNOG database. It maps query proteins to orthologous groups, conferring precise COG, GO, and KEGG biological terminology.

## Basic Usage

```bash
emapper.py -i proteins.faa --output annotation_results -m diamond
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/eggnogdb/eggnog-mapper
- **Main Usage:** Functional annotation
