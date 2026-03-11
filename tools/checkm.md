# CheckM

## What It Is

[CheckM](https://github.com/Ecogenomics/CheckM) is a tool used for bin quality assessment.

## Description

CheckM supplies vital quality control and robust integrity checks for metagenome-assembled genomes (MAGs) and singular isolates alike. It evaluates rigorous benchmarks, principally completeness and contamination scores, by screening for deeply conserved lineage-specific single-copy marker genes.

## Basic Usage

```bash
checkm lineage_wf -t 16 -x fa bins_dir/ checkm_out/
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/Ecogenomics/CheckM
- **Main Usage:** Bin quality assessment
