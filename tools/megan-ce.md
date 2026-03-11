# MEGAN-CE

## What It Is

[MEGAN-CE](https://github.com/husonlab/megan-ce) is a tool used for metagenomic analysis (lca taxonomy).

## Description

MEGAN (MEtaGenome ANalyzer) Community Edition is a comprehensive tool featuring both a GUI and command-line interfaces for analyzing microbiome data. It assigns taxonomic and functional labels to sequenced data directly from alignment outputs using the Lowest Common Ancestor (LCA) heuristic.

## Basic Usage

```bash
daa2rma -i matches.daa -o matches.rma --mapDB megan-map.db
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/husonlab/megan-ce
- **Main Usage:** Metagenomic analysis (LCA taxonomy)
