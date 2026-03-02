# Manual Execution Guide for GenomicsForOneHealth
This guide provides the core `bash` commands to execute the key steps of each pipeline *manually*, without using the automated wrapper scripts. It is designed for advanced users who want to run specific steps line-by-line, adapt parameters dynamically, or integrate the tools into custom workflows.

---

## 🌍 1. Environmental Metagenomics

### Nanopore AMR Host Association
Identify antimicrobial resistance genes and link them directly to taxonomic hosts using long reads.

```bash
# 1. Basecalling (optional if starting from raw data)
dorado basecaller sup models/dna_r10.4.1_e8.2_400bps_sup input_pod5_dir/ > unaligned.bam

# 2. Convert BAM to FASTQ
samtools fastq -@ 20 unaligned.bam > input.fastq

# 3. Filter Reads (Chopper)
cat input.fastq | chopper -q 10 -l 500 --threads 20 > filtered.fastq

# 4. Metagenomic Assembly (metaFlye)
flye --meta --nano-hq filtered.fastq --out-dir flye_output --threads 20

# 5. Taxonomic Classification of Assembly (Kraken2)
kraken2 --db /path/to/kraken_db --use-names --threads 20 --report kraken_report.txt flye_output/assembly.fasta > classified.txt

# 6. AMR Gene Detection (AMRFinderPlus)
amrfinder -n flye_output/assembly.fasta --threads 20 > amr_results.tsv
```

### Air Metagenomics & Wetland Health
*(These pipelines share core Metagenomic logic similar to above, including filtering, Flye/metaMDBG assembly, Kraken2 taxonomy, and AMRFinderPlus.)*

---

## 🧬 2. eDNA Metabarcoding

### Zambia eDNA
Process Illumina and Nanopore amplicon reads, demultiplex, and classify operational taxonomic units (OTUs).

```bash
# 1. Merge Paired-End Illumina Reads (obipairing)
obipairing --min-identity 0.90 --min-overlap 20 --forward-reads R1.fastq.gz --reverse-reads R2.fastq.gz --out merged.fastq.gz

# 2. Filter Internal Matches (obigrep)
obigrep --predicate 'annotations.mode == "alignment"' --out merged_acgt.fastq.gz merged.fastq.gz

# 3. Demultiplex Merged Reads (obimultiplex)
obimultiplex merged_acgt.fastq.gz -t sample_tags.tsv -o demux.fastq.gz -u unknown.fastq.gz -e 2 --fastq-output

# 4. Global Alignment / Taxonomy (VSEARCH)
vsearch --makeudb_usearch MIDORI2_database.fasta --output MIDORI2.udb
vsearch --usearch_global clustered_otus.fa --db MIDORI2.udb --strand both --id 0.90 --query_cov 0.80 --maxaccepts 1 --blast6out alignment_results.tsv --threads 32
```

---

## 🍽️ 3. Food Safety

### Listeria Adaptive Sampling
Perform high-resolution genomic profiling, assembly, and typing of *Listeria monocytogenes*.

```bash
# 1. Convert BAM to FASTQ
samtools fastq -@ 4 input.bam > reads.fastq

# 2. Trim Adapters (Porechop)
porechop -i reads.fastq -o trimmed.fastq -t 20

# 3. Read Length & Quality Filtering (NanoFilt)
NanoFilt -q 9 -l 100 < trimmed.fastq > filtered.fastq

# 4. Whole-sample Taxonomy Analysis (Kraken2)
kraken2 --db /path/to/kraken_db --use-names --threads 8 --report kraken_report.txt --output kraken_classified.txt filtered.fastq

# 5. Extract Listeria Target Reads (Seqtk)
# (Assuming list of expected read IDs is generated from kraken output)
seqtk subseq filtered.fastq listeria_read_ids.txt > listeria_target.fastq

# 6. Metagenomic Target Assembly (metaFlye)
flye --meta --nano-hq listeria_target.fastq --out-dir assembly_out --threads 8

# 7. Polishing with Dorado
dorado aligner assembly_out/assembly.fasta listeria_target.fastq | samtools sort -o aligned.bam
samtools index aligned.bam
dorado polish --bacteria aligned.bam assembly_out/assembly.fasta > polished.fasta

# 8. Pathogen Profiling (AMRFinderPlus with Virulence)
amrfinder --plus -n polished.fasta --threads 8 > listeria_amr_virulence_report.tsv
```

---

## 🏥 4. Clinical Isolates & Plasmid Profiling

### AMR Nanopore & CRE Plasmid Clustering
Rapid pipeline for clinical isolate assembly, antibiotic resistance evaluation, and plasmid tracking.

```bash
# 1. Basecalling (Guppy / Dorado)
guppy_basecaller -i raw_fast5 -s basecalled_dir --config dna_r9.4.1_450bps_hac.cfg
cat basecalled_dir/pass/*.fastq > all_reads.fastq

# 2. Trim Adapters
porechop -i all_reads.fastq -o trimmed.fastq

# 3. Quality Filtering
cat trimmed.fastq | NanoFilt -q 9 -l 200 > filtered.fastq

# 4. Assembly (Flye)
flye --nano-hq filtered.fastq --out-dir assembly_out

# 5. Rapid Alignment to Draft (Minimap2)
minimap2 -ax map-ont assembly_out/assembly.fasta filtered.fastq | samtools sort -o alignment.bam

# 6. Fast Polishing (Racon)
racon filtered.fastq alignment.bam assembly_out/assembly.fasta > polished.fasta
```

---

## 🦆 5. Veterinary & Zoonotic Surveillance (Virome)

### Avian Influenza Profiling
Detailed variant sequence generation and subtyping of viral genomes against reference databases.

```bash
# 1. Fast Length Filtering (SeqKit)
seqkit seq -m 50 input_viral_reads.fastq > filtered.fastq

# 2. Align to Influenza Segment Reference
minimap2 -ax map-ont reference_segment.fa filtered.fastq > aln.sam
samtools view -bS aln.sam | samtools sort -o sorted.bam
samtools index sorted.bam

# 3. Identify the Best Matching Reference (idxstats)
samtools idxstats sorted.bam > stats.txt
# (Use awk to find the max mapped reference)
samtools view -b -o best_ref.bam sorted.bam "BEST_REF_NAME"

# 4. Generate Consensus (BCFTools)
bcftools mpileup -Ou -f reference_segment.fa sorted.bam | bcftools call -Oz -mv -o variants.vcf.gz
bcftools index variants.vcf.gz
bcftools consensus -f reference_segment.fa variants.vcf.gz > viral_consensus_bcftools.fasta

# 5. Generate Alternative Consensus (iVar)
samtools mpileup -aa -A -d 0 -Q 0 sorted.bam | ivar consensus -m 0 -q 0 -p viral_consensus_ivar.fasta
```

---

## 🔬 6. Viability Assessment (Squiggle-level)

### Squiggle4Viability
Direct interrogation of `FAST5/POD5` raw signals via AI to deduce bacterial viability without full assembly.

```bash
# 1. Inference Generation via ResNet API
# (Requires custom python implementations from the AI_scripts directory)
python3 Viability_Assessment/Squiggle4Viability/AI_scripts/inference.py \
    --input_dir /path/to/fast5_or_pod5 \
    --model_weights models/antibiotic_ecoli_ResNet_550ep.ckpt \
    --output results.csv
```
