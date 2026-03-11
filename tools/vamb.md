# VAMB

## What It Is

[VAMB](https://github.com/RasmussenLab/vamb) is a tool used for variational autoencoder binning.

## Description

VAMB (Variational Autoencoders for Metagenomic Binning) uses sophisticated deep learning to perform scalable metagenomic binning. By encoding spatial sequence composition alongside intricate co-abundance variance into a collapsed latent space, VAMB can frequently resolve confusing, closely related strains.

## Basic Usage

```bash
vamb --outdir vamb_bins --fasta assembly.fasta --bam alignments/*.bam
```

## Usage in This Repository

This tool is integrated into the GenomicsForOneHealth pipelines for robust analysis. 
Please refer to the pipeline specific documentation (`pipelines/`) and the manual execution guides for exact command-line usage and parameters.

## Links & Resources

- **Source / Documentation:** https://github.com/RasmussenLab/vamb
- **Main Usage:** Variational autoencoder binning
