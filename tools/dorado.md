# Dorado

## What It Is

[Dorado](https://github.com/nanoporetech/dorado) is a tool used for ont basecaller (sup, hac, fast models).

## Description

Dorado is Oxford Nanopore's official state-of-the-art basecaller, developed to replace Guppy. It uses high-performance deep learning models (Fast, HAC, and SUP) to perform highly accurate basecalling and modified base detection (e.g., 5mC, 6mA) directly from raw signal data (POD5 files).

## Basic Usage

```bash
dorado basecaller sup pod5_dir/ > unmapped.bam
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/nanoporetech/dorado
- **Main Usage:** ONT basecaller (sup, hac, fast models)
