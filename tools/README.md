# Tool Reference Sheets

This directory contains concise per-tool reference sheets for every bioinformatics tool used across the **GenomicsForOneHealth** pipelines.

Each file covers:
- What the tool does and which pipeline(s) use it
- Key flags and typical command patterns
- Installation pointers (conda/pip/binary)
- Links to the official documentation or repository

These are **not standalone tutorials** — for full pipeline usage, see the README inside each pipeline subdirectory.

## Tools covered

| Tool | Purpose |
|---|---|
| `abricate.md` | AMR/virulence gene screening from assemblies |
| `amrfinderplus.md` | NCBI AMR gene detection (nucleotide + protein) |
| `anvio.md` | Integrated metagenomics analysis ecosystem |
| `bakta.md` | Rapid prokaryotic genome annotation |
| `bcftools.md` | VCF/BCF manipulation and variant calling |
| `checkm.md` | Genome bin completeness/contamination QC |
| `chopper.md` | Nanopore read quality and length filtering |
| `conifer.md` | Post-hoc confidence scoring for Kraken2 output |
| `cutadapt.md` | Adapter and primer trimming |
| `diamond.md` | Fast translated sequence alignment (BLASTx) |
| `dorado.md` | ONT basecaller (replacement for Guppy) |
| `eggnog-mapper.md` | Functional annotation via eggNOG ortholog database |
| `filtlong.md` | Long-read quality filtering |
| `flye.md` | De novo long-read assembler (metagenome mode) |
| `guppy.md` | ONT legacy basecaller |
| `irma.md` | Iterative refinement for influenza consensus assembly |
| `kraken2.md` | k-mer-based taxonomic classification |
| `mash.md` | MinHash-based genome/plasmid distance sketching |
| `medaka.md` | Nanopore polishing with neural networks |
| `megan-ce.md` | DIAMOND output parsing and taxonomic/functional assignment |
| `metabat2.md` | Metagenomic binning |
| `metamdbg.md` | High-accuracy metagenomic assembler for long reads |
| `metawrap.md` | Binning wrapper integrating MetaBAT2, MaxBin2, CONCOCT |
| `mgcalibrator.md` | Absolute abundance calibration for metagenomics |
| `miniforge.md` | Conda/mamba installation (preferred package manager) |
| `minimap2.md` | Fast pairwise sequence alignment |
| `mob-suite.md` | Plasmid reconstruction and typing |
| `modkit.md` | DNA base modification pileup from BAMs |
| `nanofilt.md` | Quality and length filtering for Nanopore reads |
| `nanomotif.md` | Methylation motif discovery and bin contamination detection |
| `nanostat.md` | Summary statistics for Nanopore data |
| `obitools.md` | eDNA metabarcoding toolkit (demux, filtering) |
| `plasmidfinder.md` | In silico plasmid replicon typing |
| `pling.md` | Plasmid network construction and clustering |
| `porechop.md` | Adapter trimming for Nanopore reads |
| `prodigal.md` | Prokaryotic gene prediction |
| `prokka.md` | Rapid prokaryotic genome annotation (legacy) |
| `racon.md` | Fast consensus sequence polishing |
| `samtools.md` | SAM/BAM/CRAM manipulation toolkit |
| `seqkit.md` | Fast FASTQ/FASTA processing toolkit |
| `seqtk.md` | Lightweight sequence subsampling and conversion |
| `vamb.md` | Variational autoencoder binning |
| `vsearch.md` | Fast sequence search, clustering, chimera detection |
