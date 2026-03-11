# BCFtools

## What It Is

[BCFtools](https://github.com/samtools/bcftools) is a tool used for variant calling and consensus generation.

## Description

BCFtools functions effectively as a sibling package to SAMtools, heavily targeted toward manipulating and generating VCF (Variant Call Format) representations. Within modern workflows, it is universally used to call single nucleotide variants (SNVs), define critical indels, and output detailed consensus strings.

## Basic Usage

```bash
bcftools mpileup -Ou -f ref.fa sorted.bam | bcftools call -mv -Ob -o calls.bcf
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/samtools/bcftools
- **Main Usage:** Variant calling and consensus generation
