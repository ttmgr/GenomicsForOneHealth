# Zambia eDNA Metabarcoding Pipeline

This repository contains the code and workflows used for environmental DNA research in Zambia. The pipeline covers merging and demultiplexing of Nanopore and Illumina sequencing data, read quality filtering, chimera removal, dereplication, and OTU clustering, followed by global alignment mapping against a reference database.

The original demultiplexing reference files and command parameters used for this pipeline are included for reproducibility.


```mermaid
flowchart TD
    %% Input Sources
    A1[Illumina Paired-End Reads<br/>12S & 16S] --> B1[Merge & Pair<br/>obipairing]
    A2[Nanopore Single-End Reads<br/>12S & 16S fastq] --> B2[Demultiplexing<br/>obimultiplex]
    
    %% Illumina Processing
    B1 --> C1[Filter Internal Matches<br/>obigrep]
    C1 --> D1[Demultiplexing<br/>obimultiplex]
    
    %% Common Downstream Read Processing
    D1 --> E[Merged & Demultiplexed Reads]
    B2 --> E
    
    E --> F[Primer Trimming<br/>cutadapt]
    F --> G[Length & Quality Filter<br/>vsearch --fastq_filter]
    G --> H[Dereplication<br/>vsearch --derep_fulllength]
    H --> I[Chimera Removal<br/>vsearch --uchime3_denovo]
    
    %% OTU & Taxonomy
    I --> J[OTU Clustering 99%<br/>vsearch --cluster_size]
    J --> K[Taxonomic Assignment<br/>vsearch --usearch_global<br/>vs MIDORI2]

    %% Styling
    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef output fill:#ffe0b2,stroke:#e65100,stroke-width:2px,color:#000
    
    class A1,A2 input
    class B1,B2,C1,D1,F,G,H,I process
    class J,K output
    class E input
```

## Data Files

The [`data/`](./data/) directory contains the sample demultiplexing reference tables used in this study:

| File | Description |
|---|---|
| `zambia_12_ngs_dmx_final.tsv` | Tag and primer definitions for 12S rRNA demultiplexing |
| `zambia_16_ngs_dmx_final.tsv` | Tag and primer definitions for 16S rRNA demultiplexing |

These files are passed directly to `obimultiplex` via the `-t` flag. They are included here so that the exact demultiplexing parameters used in the publication are fully reproducible.

## Setup

Install all pipeline tools via the unified environment at the repository root:
```bash
mamba env create -f ../environment.yaml
conda activate genomics-onehealth
```

The MIDORI2 reference database for taxonomic assignment must be downloaded separately:
- [MIDORI2 Download](https://www.reference-midori.info/download.php)
