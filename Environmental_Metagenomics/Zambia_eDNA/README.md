# Zambia_eDNA
This site contains the main code I used for my research (Link coming soon)

This repository includes the main code I used for my environmental DNA research in Zambia for my PhD work.

## Analysis Pipeline Overview

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

It includes the script I used for merging and demultiplexing of nanopore and illumina data, scripts for read quality filtering, chimera removal, derreplication and OTU clustering, and a script to perform global aligment on a reference database. I include the original demultiplexing files I used as well as the command parameters used for this study. For more details on software or database versions please refer to my paper (Link coming soon) or write me to dgygax90@gmail.com
