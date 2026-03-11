# SAMtools

## What It Is

[SAMtools](https://github.com/samtools/samtools) is a tool used for sam/bam file manipulation.

## Description

SAMtools represents standard computational plumbing for robustly manipulating SAM, BAM, and CRAM alignment files—the universal output specifications of virtually all genome aligners. Utilizing it is frequently required for binary sorting, indexing, viewing, and calculating basic sequencing metrics.

## Basic Usage

```bash
samtools sort alignment.sam -o sorted.bam
samtools index sorted.bam
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/samtools/samtools
- **Main Usage:** SAM/BAM file manipulation
