# Porechop

## What It Is

[Porechop](https://github.com/rrwick/Porechop) is a tool used for adapter and barcode trimming.

## Description

Porechop is a widely used tool specifically designed for demultiplexing and adapter trimming of Oxford Nanopore reads. It works by aligning reads against a comprehensive database of known adapter sequences, ensuring clean contiguous sequences for downstream assembly and mapping steps.

## Basic Usage

```bash
porechop -i input.fastq -o trimmed.fastq --discard_middle
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/rrwick/Porechop
- **Main Usage:** Adapter and barcode trimming
