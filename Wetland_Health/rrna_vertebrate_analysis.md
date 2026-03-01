# rRNA Vertebrate Analysis


This pipeline describes how avian host DNA is recovered from environmental 12S rRNA amplicon sequencing data.

## Tools and Reference Databases

- **OBITools4 – `obimultiplex` (v1.3.1)**: demultiplexes reads using a tab‑delimited tag file that defines the 9 bp primer tags for each sample.
- **Cutadapt (v4.2)**: removes forward and reverse primer sequences from reads.
- **VSEARCH (v2.21)**: open‑source sequence analysis toolkit used for quality filtering, dereplication, chimera removal and OTU clustering.
- **MIDORI2 mitochondrial database – “Unique 266” release**: curated set of vertebrate mitochondrial sequences compiled from GenBank and BOLD; used for taxonomic identification.
- **eBird**: global bird‑occurrence database used to confirm the geographic plausibility of species assignments.

## Pipeline

1. **Demultiplex basecalled reads**
   - `obimultiplex` assigns reads to samples based on their 9 bp tags, allowing up to two mismatches.

2. **Trim primer sequences**
   - `cutadapt` removes anchored forward and reverse primers from each read.

3. **Filter and cluster sequences with VSEARCH**
   - **Quality filter** by expected error (`--fastq_maxee 1.0`).
   - **Dereplicate** sequences and discard singletons (`--minuniquesize 2`).
   - **Remove chimeras** de novo (`--uchime_denovo`).
   - **Cluster** remaining reads into operational taxonomic units (OTUs) at 97 % identity.

4. **Assign taxonomy**
   - OTU centroids are globally aligned against the MIDORI2 “Unique 266” database. Hits must cover ≥80 % of the query and have ≥98 % identity. OTUs with <5 reads are discarded.

5. **Validate and tally species**
   - Species not reported in the sampling region (checked with eBird) are collapsed to higher taxonomic ranks or removed. Read counts from multiple OTUs mapping to the same retained taxon are summed per sample.

Avian host detection from eDNA: Basecalled 12S rRNA amplicon reads were demultiplexed by their 9 bp primer tags using OBITools4 `obimultiplex` (version 1.3.1) (ref), allowing up to two mismatches in tag recognition. Primer sequences were trimmed from reads with Cutadapt (v4.2) (ref). The reads were then processed in VSEARCH (v2.21) (ref): we filtered reads by expected error (maxEE 1.0) to remove low-quality reads, dereplicated reads (discarding singletons), removed chimeras, and clustered the remaining sequences into operational taxonomic units (OTUs) at 97% similarity. Each OTU representative sequence was taxonomically identified by global alignment against the MIDORI2 reference database of mitochondrial sequences (version “Unique 266”) (ref). Assignments were limited to bird species (Aves class), and accepted as robust if an alignment covered ≥80% of the query, had ≥98% identity, and if a taxonomic assignment had at least five reads as hits after OTU aggregation of same species detection. When species-level calls were biogeographically implausible for our sampling sites (i.e., the species is not present in the sampled area), we collapsed the assignment to a higher rank (i.e., genus or family) or removed the record if no meaningful higher-rank assignment was possible. Regional occurrence (presence/absence) was assessed with eBird (https://ebird.org/home). Multiple OTUs mapping to the same retained taxon within a sample were summed to produce per-taxon read counts.


## Example command sequence

```bash

# 1. Demultiplex by 9 bp tags
obimultiplex --tags tagfile.txt --primerfile primers.fasta --allow-mismatch 2 \
    --input basecalled_reads.fastq --output demultiplexed.fastq

# 2. Remove primers
cutadapt -g ^PRIMER_FWD -G ^PRIMER_REV -o trimmed.fastq demultiplexed.fastq

# 3. Filter, dereplicate and cluster

# Demultiplex with OBITools
obimultiplex --tags tagfile.txt --primerfile primers.fasta --allow-mismatch 2 \
    --input basecalled_reads.fastq --output demultiplexed.fastq

# Trim primers with Cutadapt
cutadapt -g ^PRIMER_FWD -G ^PRIMER_REV -o trimmed.fastq demultiplexed.fastq

# Filter, dereplicate, and cluster with VSEARCH

vsearch --fastq_filter trimmed.fastq --fastq_maxee 1.0 --fastaout filtered.fasta
vsearch --derep_fulllength filtered.fasta --sizeout --minuniquesize 2 --output derep.fasta
vsearch --uchime_denovo derep.fasta --nonchimeras nochimeras.fasta
vsearch --cluster_size nochimeras.fasta --id 0.97 --centroids otus.fasta

# 4. Taxonomic assignment against MIDORI2
vsearch --usearch_global otus.fasta --db MIDORI2_unique_266.fasta --id 0.98 \
    --blast6out assignments.b6

# 5. Downstream processing
#   Summarize assiments, check against eBird, and aggregate read counts per taxon
==
# Assign taxonomy with MIDORI2 reference database
vsearch --usearch_global otus.fasta --db MIDORI2_unique_266.fasta --id 0.98 \
    --blast6out assignments
```

