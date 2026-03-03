# Tools and Software Referenced in This Repository

This file lists the bioinformatics tools used across the GenomicsForOneHealth pipelines, with links to their source code and documentation.

---

## Basecalling & Signal Processing

| Tool | Description | Link |
|------|-------------|------|
| **Dorado** | ONT basecaller (sup, hac, fast models) | [GitHub](https://github.com/nanoporetech/dorado) |
| **Guppy** | ONT legacy basecaller | Distributed by ONT (login required) |
| **Modkit** | Modified base analysis from BAM | [GitHub](https://github.com/nanoporetech/modkit) |

## Read Processing & QC

| Tool | Description | Link |
|------|-------------|------|
| **Porechop** | Adapter and barcode trimming | [GitHub](https://github.com/rrwick/Porechop) |
| **Chopper** | Quality and length filtering | [GitHub](https://github.com/wdecoster/chopper) |
| **NanoFilt** | Quality and length filtering for ONT reads | [GitHub](https://github.com/wdecoster/nanofilt) |
| **NanoStat** | Read quality statistics | [GitHub](https://github.com/wdecoster/NanoStat) |
| **Filtlong** | Quality-based long read filtering | [GitHub](https://github.com/rrwick/Filtlong) |
| **Cutadapt** | Primer and adapter trimming | [GitHub](https://github.com/marcelm/cutadapt) |
| **SeqKit** | FASTA/Q manipulation toolkit | [GitHub](https://github.com/shenwei356/seqkit) |
| **Seqtk** | Fast sequence processing toolkit | [GitHub](https://github.com/lh3/seqtk) |

## Assembly & Polishing

| Tool | Description | Link |
|------|-------------|------|
| **Flye** | Long-read de novo assembler (--meta for metagenomes) | [GitHub](https://github.com/mikolmogorov/Flye) |
| **metaMDBG** | Metagenomic assembler for long reads | [GitHub](https://github.com/GaetanBenoworkt/metaMDBG) |
| **Minimap2** | Long-read and assembly alignment | [GitHub](https://github.com/lh3/minimap2) |
| **Racon** | Assembly consensus polishing | [GitHub](https://github.com/isovic/racon) |
| **Medaka** | ONT-specific assembly polishing | [GitHub](https://github.com/nanoporetech/medaka) |

## Taxonomic Classification

| Tool | Description | Link |
|------|-------------|------|
| **Kraken2** | K-mer based taxonomic classification | [GitHub](https://github.com/DerrickWood/kraken2) |
| **DIAMOND** | Fast protein alignment (BLASTx/BLASTp) | [GitHub](https://github.com/bbuchfink/diamond) |
| **MEGAN-CE** | Metagenomic analysis (LCA taxonomy) | [GitHub](https://github.com/husonlab/megan-ce) |
| **OBITools** | eDNA metabarcoding toolkit | [GitHub](https://github.com/metabarcoding/obitools4) |
| **VSEARCH** | Sequence analysis (clustering, chimera removal) | [GitHub](https://github.com/torognes/vsearch) |

## AMR & Virulence Detection

| Tool | Description | Link |
|------|-------------|------|
| **AMRFinderPlus** | NCBI AMR gene detection | [GitHub](https://github.com/ncbi/amr) |
| **ABRicate** | Mass screening for AMR/virulence genes | [GitHub](https://github.com/tseemann/abricate) |
| **PlasmidFinder** | Plasmid identification from assemblies | [CGE Web](https://cge.food.dtu.dk/services/PlasmidFinder/) |

## Annotation

| Tool | Description | Link |
|------|-------------|------|
| **Prokka** | Prokaryotic genome annotation | [GitHub](https://github.com/tseemann/prokka) |
| **Bakta** | Rapid genome annotation | [GitHub](https://github.com/oschwengers/bakta) |
| **Prodigal** | Gene/ORF prediction | [GitHub](https://github.com/hyattpd/Prodigal) |
| **eggNOG-mapper** | Functional annotation | [GitHub](https://github.com/eggnogdb/eggnog-mapper) |

## Plasmid & Methylation Analysis

| Tool | Description | Link |
|------|-------------|------|
| **MOB-suite** | Plasmid reconstruction and typing | [GitHub](https://github.com/phac-nml/mob-suite) |
| **Nanomotif** | Methylation-based contig association | [GitHub](https://github.com/MicrobialDarkMatter/nanomotif) |
| **Pling** | Plasmid graph-based clustering | [GitHub](https://github.com/iqbal-lab-org/pling) |
| **Mash** | Fast genome/plasmid distance estimation | [GitHub](https://github.com/marbl/Mash) |

## Binning & MAGs

| Tool | Description | Link |
|------|-------------|------|
| **MetaWRAP** | Binning pipeline (MetaBAT2, MaxBin2, CONCOCT) | [GitHub](https://github.com/bxlab/metaWRAP) |
| **MetaBAT2** | Metagenome binning | [Bitbucket](https://bitbucket.org/berkeleylab/metabat) |
| **VAMB** | Variational autoencoder binning | [GitHub](https://github.com/RasmussenLab/vamb) |
| **CheckM** | Bin quality assessment | [GitHub](https://github.com/Ecogenomics/CheckM) |

## Virology & AIV

| Tool | Description | Link |
|------|-------------|------|
| **IRMA** | Iterative Refinement Meta-Assembler (flu) | [CDC GitHub](https://github.com/peterk87/irma) |
| **SAMtools** | SAM/BAM file manipulation | [GitHub](https://github.com/samtools/samtools) |
| **BCFtools** | Variant calling and consensus generation | [GitHub](https://github.com/samtools/bcftools) |

## AI / Deep Learning

| Tool | Description | Link |
|------|-------------|------|
| **Squiggle4Viability** | Viability inference from raw nanopore signals | [GitHub](https://github.com/Genomics4OneHealth/Squiggle4Viability) |

## Environment Management

| Tool | Description | Link |
|------|-------------|------|
| **Miniforge / Mamba** | Fast conda package manager | [GitHub](https://github.com/conda-forge/miniforge) |

 
  
 
