# Pipeline Reference

Practical reference for the tools and workflows used across GenomicsForOneHealth. Each section covers what the tool does, a representative command, and links to documentation.

For the full tool list with GitHub links, see [TOOLS.md](./TOOLS.md). For installation of Mamba, Dorado, and large databases, see [INSTALL_AND_DATABASES.md](./INSTALL_AND_DATABASES.md).

---

## Basecalling

### Dorado

ONT's current basecaller. Replaces Guppy. Runs SUP (highest accuracy), HAC, or FAST models on POD5 input.

```bash
dorado basecaller sup pod5_dir/ --kit-name SQK-NBD114-96 > calls.bam
```

- [Dorado GitHub](https://github.com/nanoporetech/dorado)
- [ONT basecalling models](https://community.nanoporetech.com/docs/prepare/library_prep_protocols/dorado-models)
- [ONT community — basecalling](https://community.nanoporetech.com/tags/basecalling)

### Demultiplexing

```bash
dorado demux calls.bam --output-dir demux/ --kit-name SQK-NBD114-96
```

---

## Read QC & Filtering

### Chopper

Quality and length filtering for nanopore reads. Pipe from samtools for BAM input.

```bash
samtools fastq input.bam | chopper --quality 10 --minlength 1000 > filtered.fastq
```

- [Chopper GitHub](https://github.com/wdecoster/chopper)

### NanoStat

Summary statistics for nanopore reads.

```bash
NanoStat --fastq filtered.fastq --threads 8
```

- [NanoStat GitHub](https://github.com/wdecoster/NanoStat)

---

## Assembly

### Flye (metaFlye)

Long-read de novo assembler. Use `--meta` for metagenomic samples.

```bash
flye --nano-hq filtered.fastq --meta --out-dir flye_out --threads 16
```

- [Flye GitHub](https://github.com/mikolmogorov/Flye)

### metaMDBG

Metagenomic assembler optimized for long reads.

```bash
metaMDBG asm --in-hifi filtered.fastq --out-dir mdbg_out --threads 16
```

- [metaMDBG GitHub](https://github.com/GaetanBenoworkt/metaMDBG)

### Dorado Polish

Assembly polishing using the Dorado polishing model directly on BAM alignments.

```bash
dorado polish aligned.bam assembly.fasta --model m6A --threads 16 > polished.fasta
```

- [ONT polishing documentation](https://community.nanoporetech.com/docs/prepare/library_prep_protocols/dorado-polish)

---

## Taxonomic Classification

### Kraken2

K-mer based taxonomic classification. Requires a pre-built database.

```bash
kraken2 --db /path/to/kraken2_db --threads 16 --output kraken_out.txt \
  --report kraken_report.txt --use-names input.fastq
```

- [Kraken2 GitHub](https://github.com/DerrickWood/kraken2)
- Database download: see [INSTALL_AND_DATABASES.md](./INSTALL_AND_DATABASES.md)

---

## AMR & Virulence Detection

### AMRFinderPlus

NCBI's tool for identifying AMR genes, stress response genes, and virulence factors.

```bash
amrfinder --nucleotide assembly.fasta --threads 16 --plus \
  --output amrfinder_results.tsv
```

- [AMRFinderPlus GitHub](https://github.com/ncbi/amr)
- [NCBI AMR reference gene database](https://www.ncbi.nlm.nih.gov/pathogens/antimicrobial-resistance/AMRFinder/)

### ABRicate

Mass screening of contigs against multiple databases (CARD, VFDB, PlasmidFinder, NCBI, etc.).

```bash
# Screen against CARD (AMR)
abricate --db card --threads 15 --minid 90 --mincov 80 assembly.fasta > card.tsv

# Screen against VFDB (virulence)
abricate --db vfdb --threads 15 --minid 90 --mincov 80 assembly.fasta > vfdb.tsv

# Screen against PlasmidFinder (replicons)
abricate --db plasmidfinder --threads 15 --minid 90 --mincov 80 assembly.fasta > plasmidfinder.tsv

# Cross-sample summary
abricate --summary *_card.tsv > summary_card.tsv
```

Available databases: `abricate --list`

- [ABRicate GitHub](https://github.com/tseemann/abricate)
- [CARD database](https://card.mcmaster.ca/)
- [VFDB](http://www.mgc.ac.cn/VFs/)
- [PlasmidFinder](https://cge.food.dtu.dk/services/PlasmidFinder/)

---

## Plasmid Analysis

### MOB-suite (mob_typer / mob_recon)

Plasmid typing and reconstruction. `mob_typer` classifies pre-assembled contigs; `mob_recon` reconstructs plasmids from assemblies.

```bash
# Typing (classify contigs)
mob_typer --multi --infile assembly.fasta \
  --out_file mob_typer.tsv --mge_report_file mob_mge_report.tsv

# Reconstruction (separate chromosome vs plasmid)
mob_recon --infile assembly.fasta --outdir mobsuite_recon/
```

- [MOB-suite GitHub](https://github.com/phac-nml/mob-suite)

### IntegronFinder

Detects integrons (gene capture platforms associated with AMR cassettes) in assembled sequences.

```bash
integron_finder assembly.fasta --local-max --func-annot --cpu 15 --outdir integron_out/
```

- [IntegronFinder GitHub](https://github.com/gem-pasteur/Integron_Finder)
- [IntegronFinder documentation](https://integronfinder.readthedocs.io/)

---

## Methylation & Host Association

### Modkit

Extracts modified base information (5mC, 6mA) from Dorado BAM output.

```bash
modkit pileup input.bam pileup.bed --ref assembly.fasta --threads 16
```

- [Modkit GitHub](https://github.com/nanoporetech/modkit)
- [ONT modified bases](https://community.nanoporetech.com/docs/prepare/library_prep_protocols/modified-bases)

### Nanomotif

Identifies methylation motifs per contig and uses shared motif patterns to associate plasmids with their bacterial hosts.

```bash
nanomotif find_motifs --assembly assembly.fasta --pileup pileup.bed \
  --out_dir nanomotif_out/ --threads 16
```

- [Nanomotif GitHub](https://github.com/MicrobialDarkMatter/nanomotif)

---

## eDNA Metabarcoding

### OBITools + VSEARCH

For eDNA workflows (vertebrate biodiversity monitoring).

```bash
# Demultiplex
obitools ngsfilter -t sample_sheet.txt -u unassigned.fastq input.fastq > demux.fasta

# Chimera removal
vsearch --uchime_denovo derep.fasta --nonchimeras clean.fasta
```

- [OBITools GitHub](https://github.com/metabarcoding/obitools4)
- [VSEARCH GitHub](https://github.com/torognes/vsearch)

---

## Virology (AIV)

### IRMA

Iterative Refinement Meta-Assembler for influenza genome assembly from nanopore data.

```bash
IRMA FLU reads.fastq irma_out/
```

- [IRMA CDC](https://wonder.cdc.gov/amd/flu/irma/)

---

## Deep Learning

### Squiggle4Viability

Viability inference directly from raw nanopore electrical signals.

```bash
python run_pipeline.sh  # interactive launcher
```

- [Squiggle4Viability GitHub](https://github.com/Genomics4OneHealth/Squiggle4Viability)

---

## ONT Resources

- [Nanopore Community](https://community.nanoporetech.com/)
- [Nanopore protocols](https://community.nanoporetech.com/protocols)
- [EPI2ME workflows](https://labs.epi2me.io/)
- [Nanopore store — sequencing kits](https://store.nanoporetech.com/)
- [ONT GitHub](https://github.com/nanoporetech)
