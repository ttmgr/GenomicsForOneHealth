# Manual Execution Guide for GenomicsForOneHealth
This guide provides the core `bash` commands to execute the key steps of each pipeline *manually*, without using the automated wrapper scripts. It is designed for advanced users who want to run specific steps line-by-line, adapt parameters dynamically, or integrate the tools into custom workflows.

---

## 1. Environmental Metagenomics

### Wetland Health (DNA Shotgun Metagenomics)
Sequence environmental DNA for community analysis, assembly, and AMR/pathogen detection.

```bash
# 1. Basecalling & Demultiplexing (Dorado)
dorado basecaller sup,6mA,4mC_5mC /path/to/pod5_dir/ --models-directory /path/to/dorado/models --kit-name SQK-RBK114-24 --verbose --trim all --emit-moves > basecalled.bam
dorado demux --output-dir demux_output/ basecalled.bam

# 2. Convert BAM to FASTQ
samtools fastq -@ 20 demux_output/barcode01.bam > input.fastq

# 3. Adapter Trimming (Porechop)
porechop -i input.fastq -o trimmed.fastq --threads 20

# 4. Quality & Length Filtering (NanoFilt)
cat trimmed.fastq | NanoFilt -q 9 -l 100 > filtered.fastq

# 5. Taxonomic Classification (Kraken2 - Community Analysis)
kraken2 --db /path/to/kraken2_db --threads 20 --use-names --report kraken_report.txt --output kraken_output.txt filtered.fastq

# 6. Metagenomic Assembly (nanoMDBG)
metaMDBG asm --out-dir nanomdbg_assembly --in-ont filtered.fastq --threads 20

# 7. Alignment to NT Database for MEGAN (Reads or Contigs)
# Edit align_megan.sh configuration parameters (e.g. INPUT_TYPE="reads" or "contigs") then run:
./align_megan.sh

# 8. MEGAN Taxonomic Classification Output (SAM -> RMA -> r2c/c2c -> Kraken/MPA)
# First edit submit_megan_processing_from_existing.sh to match INPUT_TYPE, then run:
./submit_megan_processing_from_existing.sh

# 9. AMR & Plasmid Detection (AMRFinderPlus & PlasmidFinder)
amrfinder --plus -n nanomdbg_assembly/assembly.fasta --threads 20 > amr_results.tsv
# (Optional integration with PlasmidFinder and VFDB)
```

### Wetland Health (AIV RNA Analysis)
Align reads to reference genomes and generate consensus sequences for Avian Influenza Virus.

```bash
# 1. File Quality Filtering
filtlong --min_mean_q 8 --min_length 150 reads.fastq > filtered_reads.fastq

# 2. Map to AIV Reference Database
minimap2 -ax map-ont /path/to/reference_segment.fa filtered_reads.fastq | samtools view -b -o mapped.bam -
samtools sort -o mapped_sorted.bam mapped.bam
samtools index mapped_sorted.bam

# 3. Pick Best Reference Contig
samtools idxstats mapped_sorted.bam > idxstats.txt
# (Use best ref to extract FASTA)
samtools faidx /path/to/reference_segment.fa BEST_REF > best_reference.fasta

# 4. Subset BAM & Variant Calling (Clair3)
samtools view -b -o best_ref.bam mapped_sorted.bam BEST_REF
samtools sort -o best_ref_sorted.bam best_ref.bam
samtools index best_ref_sorted.bam
run_clair3.sh --bam_fn=best_ref_sorted.bam --ref_fn=best_reference.fasta --threads=8 --platform="ont" --model_path=/path/to/clair3_models --output=clair3 --include_all_ctgs

# 5. Consensus Generation
bcftools view clair3/merge_output.vcf.gz > variants.vcf
bgzip -c variants.vcf > variants.vcf.gz
bcftools index variants.vcf.gz
samtools depth -a best_ref_sorted.bam | awk '$3==0 { printf "%s\t%d\t%d\n", $1, $2-1, $2 }' > zero_coverage.bed
bcftools consensus --mask zero_coverage.bed --fasta-ref best_reference.fasta -o consensus.fasta variants.vcf.gz
```

### Wetland Health (Viral Metagenomics)
Taxonomic classification via translated alignment to characterize RNA viromes.

```bash
# 1. Read Quality Filtering
filtlong --min_mean_q 7 --min_length 100 cdna_reads.fastq > filtered_cdna.fastq

# 2. Convert FASTQ to FASTA
seqkit fq2fa filtered_cdna.fastq > filtered_cdna.fasta

# 3. DIAMOND BLASTx Alignment against NCBI NR Database
diamond blastx --db /path/to/diamond_nr --query filtered_cdna.fasta --out diamond_results.tsv --outfmt 6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore stitle --max-target-seqs 1 --id 80 --threads 16 --sensitive

# 4. Extract and Classify Viral Hits (via Python script)
python classify_viral_hits.py
```

### Wetland Health (12S rRNA Vertebrate Metabarcoding)
Identify vertebrate species from 12S rRNA amplicons.

```bash
# 1. Demultiplex Basecalled Reads (OBITools4)
obimultiplex --tags tagfile.txt --primerfile primers.fasta --allow-mismatch 2 --input basecalled_reads.fastq --output demultiplexed.fastq

# 2. Trim Primer Sequences (Cutadapt)
cutadapt -g ^PRIMER_FWD -G ^PRIMER_REV -o trimmed.fastq demultiplexed.fastq

# 3. VSEARCH Filtering, Dereplication, Clustering
vsearch --fastq_filter trimmed.fastq --fastq_maxee 1.0 --fastaout filtered.fasta
vsearch --derep_fulllength filtered.fasta --sizeout --minuniquesize 2 --output derep.fasta
vsearch --uchime_denovo derep.fasta --nonchimeras nochimeras.fasta
vsearch --cluster_size nochimeras.fasta --id 0.97 --centroids otus.fasta

# 4. Assign Taxonomy (MIDORI2)
vsearch --usearch_global otus.fasta --db MIDORI2_unique_266.fasta --id 0.98 --blast6out assignments.b6
```

### Air Metagenomics
Metagenomic analysis of bioaerosols collected via air sampling to monitor microbial communities.

```bash
# 1. Basecalling (Guppy / Dorado)
# For Guppy (pilot):
guppy_basecaller -i input/fast5/ -r -s output/ --detect_barcodes -c dna_r10.4.1_e8.2_400bps_hac.cfg
# For Dorado (urban):
dorado basecaller dna_r10.4.1_e8.2_400bps_hac@v5.0.0 -r input/pod5/ --emit-fastq > basecalled.fastq --kit-name SQK-RBK114-24 --no-trim

# 2. Read Processing (Porechop & NanoFilt)
porechop -i basecalled.fastq -o trimmed.fastq --threads 20
cat trimmed.fastq | NanoFilt -q 9 -l 500 > filtered.fastq

# 3. Quality Control (NanoStat)
NanoStat --fastq filtered.fastq > nanostats.txt

# 4. Taxonomic Classification (Kraken2)
kraken2 --db /path/to/kraken2_db --threads 20 --use-names --report kraken_report.txt --output kraken_output.txt filtered.fastq

# 5. De novo Assembly (metaFlye)
flye --nano-hq filtered.fastq -o flye_out_dir --threads 20 --meta

# 6. Assembly Polishing (Minimap2 & Racon)
minimap2 -ax map-ont -t 20 flye_out_dir/assembly.fasta filtered.fastq > aligned.sam
racon -t 20 filtered.fastq aligned.sam flye_out_dir/assembly.fasta > polished.fasta

# 7. Assembly Statistics
assembly-stats polished.fasta > assemblystats.txt

# 8. Metagenome Binning (MetaWRAP)
metawrap binning -o binning_out -t 20 -a polished.fasta --metabat2 --maxbin2 --concoct filtered.fastq
metawrap bin_refinement -o bin_refinement_out -t 20 -A binning_out/metabat2_bins/ -B binning_out/maxbin2_bins/ -C binning_out/concoct_bins/ -c 50 -x 10

# 9. Functional Annotation (Prokka & Bakta)
prokka --outdir prokka_out --prefix sample --cpus 20 polished.fasta
bakta --db /path/to/bakta_db --output bakta_out polished.fasta --threads 20

# 10. Gene Prediction & Functional Annotation (Prodigal & eggNOG-mapper)
prodigal -i polished.fasta -a proteins.faa -p meta -q
emapper.py -i proteins.faa --output eggnog_out -m diamond --cpu 20 --data_dir /path/to/eggnog_data --override

# 11. AMR Gene Detection (Abricate & AMRFinderPlus)
abricate --threads 20 polished.fasta > abricate_contigs.txt
amrfinder --threads 20 -n polished.fasta -d /path/to/amrfinder_db > amrfinder_contigs.txt
```

---

## 2. eDNA Metabarcoding

### Zambia eDNA
Vertebrate eDNA metabarcoding of Zambian water samples using nanopore and Illumina sequencing.

#### Option A: Nanopore Single-End Demultiplexing
```bash
# 1. Demultiplex 12S
obimultiplex <Path_To_Zambia_12s_Fastq> -t ./zambia_12_ngs_dmx_final.tsv -o ONT_12S/demuxed_12S.fastq.gz -u ONT_12S/unknown_12S.fastq.gz -e 2 --fastq-output --compress --output-OBI-header --max-cpu 1 --no-order

# 2. Demultiplex 16S
obimultiplex <Path_To_Zambia_16s_Fastq> -t ./zambia_16_ngs_dmx_final.tsv -o ONT_16S/demuxed_16S.fastq.gz -u ONT_16S/unknown_16S.fastq.gz -e 2 --fastq-output --compress --output-OBI-header --max-cpu 1 --no-order
```

#### Option B: Illumina Paired-End Merge & Demultiplexing
```bash
# 1. Merge Paired-End Reads (Example for 12S L1)
obipairing --max-cpu 8 --compress --min-identity 0.90 --min-overlap 20 --forward-reads path/Zambia_12s_FKDN..._L1_1.fq.gz --reverse-reads path/Zambia_12s_FKDN..._L1_2.fq.gz --out merged_12S_L1.fastq.gz

# 2. Filter for ACGT-only Internal Matches
obigrep --predicate 'annotations.mode == "alignment"' --max-cpu 8 --compress --out merged_12S_L1_acgt.fastq.gz merged_12S_L1.fastq.gz

# 3. Demultiplex Merged Reads
obimultiplex merged_12S_L1_acgt.fastq.gz -t ./zambia_12_ngs_dmx_final.tsv -o demux/12S/L1/demux.fastq.gz -u demux/12S/L1/unknown.fastq.gz -e 2 --fastq-output --compress --max-cpu 8 --no-order
```

#### Common OTU Clustering & Alignment (Illumina or Nanopore)
```bash
# 1. Trim Primer Pair
cutadapt -g <Forward_Primer_Sequence> -a <Reverse_Primer_Sequence> --revcomp --error-rate 0.1 --cores 32 -o trimmed.fastq input.fastq.gz

# 2. Length & Quality Filter
vsearch --fastq_filter trimmed.fastq --fastq_minlen 80 --fastq_maxlen 150 --fastq_maxns 0 --fastq_maxee 1 --fastq_qmax 64 --fastaout filtered.fa --fasta_width 0 --threads 32

# 3. Dereplication
vsearch --derep_fulllength filtered.fa --minuniquesize 2 --sizein --sizeout --fasta_width 0 --output derep.fa --threads 32

# 4. Chimera Removal
vsearch --uchime3_denovo derep.fa --nonchimeras nochimera.fa --threads 32

# 5. OTU Clustering
vsearch --cluster_size nochimera.fa --id 0.99 --sizein --sizeout --centroids otus.fa --threads 32

# 6. Global Alignment to MIDORI2 Database
vsearch --makeudb_usearch MIDORI2.fasta --output MIDORI2.udb
vsearch --usearch_global otus.fa --db MIDORI2.udb --strand both --id 0.90 --query_cov 0.80 --maxaccepts 1 --blast6out global_alignment_results.tsv --threads 32
```

---

## 3. Food Safety

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

## 4. Clinical Isolates & Plasmid Profiling

### Nanopore AMR Host Association
Nanopore metagenomic sequencing links clinically relevant resistance determinants to pathogens via DNA methylation patterns.

```bash
# 1. Basecalling (Dorado)
dorado basecaller sup,6mA,4mC_5mC /path/to/pod5_dir/ --models-directory /path/to/dorado/models --kit-name SQK-RBK114-24 --verbose --trim all --emit-moves > basecalled.bam

# 2. Demultiplexing
dorado demux --output-dir demux_output/ basecalled.bam

# 3. Convert BAM to FASTQ
samtools fastq -@ 20 demux_output/barcode01.bam > reads.fastq

# 4. Filter Reads (Chopper)
chopper -q 9 -l 200 -i reads.fastq > filtered.fastq

# 5. Filter BAM to Match Fastq (requires scripts/filter_bam_by_fastq.py)
python filter_bam_by_fastq.py --fastq filtered.fastq --bam demux_output/barcode01.bam --out filtered.bam

# 6. Metagenomic Assembly (metaFlye or metaMDBG)
# Option A: metaFlye
flye --nano-hq filtered.fastq -o metaflye_assembly --threads 20 --meta
# Option B: metaMDBG
metaMDBG asm --out-dir nanomdbg_assembly --in-ont filtered.fastq --threads 20

# 7. Align Reads to Unpolished Assembly (Dorado Aligner)
dorado aligner assembly.fasta filtered.bam | samtools sort -@ 20 -o aligned.bam
samtools index -@ 20 aligned.bam

# 8. Assembly Polishing (Dorado Polish)
dorado polish aligned.bam assembly.fasta --ignore-read-groups --bacteria > polished.fasta

# 9. Modification Pileup (Modkit)
# (Re-align reads to polished assembly first)
dorado aligner polished.fasta filtered.bam | samtools sort -@ 20 -o aligned_polished.bam
samtools index -@ 20 aligned_polished.bam
modkit pileup --ref polished.fasta --threads 20 aligned_polished.bam modkit_pileup_out/sample.pileup.bed

# 10. Nanomotif (Motif Discovery & Contamination Scoring)
python make_contig_bins.py --fasta polished.fasta --out contig2bin.tsv
nanomotif motif_discovery polished.fasta modkit_pileup_out/sample.pileup.bed -c contig2bin.tsv --out nanomotif_output -t 20 --threshold_valid_coverage 10
nanomotif detect_contamination --pileup modkit_pileup_out/sample.pileup.bed --assembly polished.fasta --bin_motifs nanomotif_output/bin-motifs.tsv --contig_bins contig2bin.tsv --out nanomotif_output

# 11. MobSuite (Plasmid Identification)
mob_recon --infile polished.fasta --outdir mobsuite_output --force

# 12. AMR Gene Detection (AMRFinderPlus)
amrfinder --nucleotide polished.fasta > amrfinder_output.txt

# 13. Taxonomic Classification (Kraken2)
kraken2 --db /path/to/kraken2_db --threads 12 --report kraken2.report --output kraken2.out --use-names polished.fasta

# 14. AMR Host Association Inference
python amr_host_association.py --nanomotif-dir nanomotif_output --mobsuite-dir mobsuite_output --amr-dir amrfinder_output.txt --kraken-dir kraken2_output --outdir final_results
```

### AMR Nanopore & CRE Plasmid Clustering
Rapid pipeline for clinical isolate assembly, antibiotic resistance evaluation, and plasmid tracking.

```bash
# 1. Basecalling (Dorado)
dorado basecaller /path/to/dna_r10.4.1_e8.2_400bps_sup@v5.0.0 /path/to/pod5_dir/ --emit-fastq --kit-name SQK-RBK114-24 -r --no-trim > basecalled.fastq

# 2. Demultiplexing
dorado demux --output-dir demux/ --emit-fastq --kit-name SQK-RBK114-24 basecalled.fastq

# 3. Adapter Trimming & Filtering
porechop -i demux/barcode01.fastq -o trimmed_01.fastq
NanoFilt -q 8 -l 200 < trimmed_01.fastq > filtered_01.fastq

# 4. Assembly (Flye)
flye --nano-hq filtered_01.fastq --out-dir flye_out --genome-size 5m --threads 8

# 5. Polishing (Medaka + Bacteria mode)
medaka_consensus -i filtered_01.fastq -d flye_out/assembly.fasta -o medaka_out -t 8 --bacteria

# 6. Depth Estimation (Minimap2 + Samtools)
minimap2 -ax map-ont flye_out/assembly.fasta filtered_01.fastq -t 8 | samtools view -b - | samtools sort -@ 8 -o coverage.bam -
samtools index coverage.bam
samtools depth coverage.bam > depth.txt

# 7. Plasmid Typing (MOB-Suite)
mob_recon --infile medaka_out/consensus.fasta --outdir mob_out

# 8. AMR Gene Detection (AMRFinderPlus)
amrfinder -n medaka_out/consensus.fasta -o amr.txt --threads 8 --plus

# 9. Plasmid Distances (Mash)
mash dist plasmid_IncN_barcode01.fasta plasmid_IncN_barcode02.fasta > mash_distances.txt

# 10. Plasmid Clustering (Pling)
pling align --containment_distance 0.3 --cores 8 --sourmash plasmid_mash_list.txt pling_out
```

---

## 5. Veterinary & Zoonotic Surveillance (Virome)

### Avian Influenza Profiling
Detailed variant sequence generation and subtyping of viral genomes against reference databases using IRMA, BCFTools, and iVar.

```bash
# 1. Basecalling specific to chemistry (e.g. RNA004, cDNA, etc.)
# RNA004: dorado basecaller rna004_130bps_sup@v3.0.1 /path/to/pod5 > output.bam
# Convert to fastq: samtools fastq output.bam > input_viral_reads.fastq

# 2. Fast Length Filtering (SeqKit)
seqkit seq -m 50 input_viral_reads.fastq > filtered.fastq

# 3. De novo Assembly (Flye)
flye --nano-hq filtered.fastq --out-dir flye_out --threads 8

# 4. Align to Influenza Segment Reference
minimap2 -ax map-ont reference_segment.fa filtered.fastq > aln.sam
samtools view -bS aln.sam | samtools sort -o sorted.bam
samtools index sorted.bam

# 5. Identify the Best Matching Reference (idxstats)
samtools idxstats sorted.bam > stats.txt
# (Extract BEST_REF_NAME, then filter)
samtools view -b -o best_ref.bam sorted.bam "BEST_REF_NAME"

# 6. Generate Consensus (BCFTools)
bcftools mpileup -Ou -f reference_segment.fa sorted.bam | bcftools call -Oz -mv -o variants.vcf.gz
bcftools index variants.vcf.gz
bcftools consensus -f reference_segment.fa variants.vcf.gz > viral_consensus_bcftools.fasta

# 7. Generate Alternative Consensus (iVar)
samtools mpileup -aa -A -d 0 -Q 0 sorted.bam | ivar consensus -m 0 -q 0 -p viral_consensus_ivar.fasta

# 8. Generation Consensus using IRMA (Influenza specific)
IRMA FLU filtered.fastq irma_out
```

### From Feather to Fur
Variant calling workflow tracking transmission pathways from avian to mammalian hosts using Clair3 and FluSurver.

```bash
# 1. Variant Calling pipeline (Minimap2 + Clair3)
minimap2 -ax map-ont reference.fasta sample.fastq.gz | samtools view -b - | samtools sort -o sorted.bam -
samtools index sorted.bam
run_clair3.sh --bam_fn=sorted.bam --ref_fn=reference.fasta --threads=8 --platform="ont" --model_path=/path/to/models --output=clair3_out

# 2. Compare Animal vs Inoculum variants (Custom Script interaction)
# We assume custom variant filtering logic here generating filtered_variants_mink2.vcf

# 3. Compress and index the filtered VCF
bgzip filtered_variants_mink2.vcf
bcftools index filtered_variants_mink2.vcf.gz

# 4. Create a consensus FASTA
bcftools consensus -f reference.fasta -s - -o qsp_mink2.fasta filtered_variants_mink2.vcf.gz

# 5. Check variants with FluSurver (Manual GUI Step)
# Upload qsp_mink2.fasta to https://flusurver.bii.a-star.edu.sg/
# Download results:
wget https://flusurver.bii.a-star.edu.sg/tmp/flusurver_result.txt -O flusurver_mink2.txt
```

---

## 6. Viability Assessment (Squiggle-level)

### Squiggle4Viability
Direct interrogation of raw Nanopore `POD5` signals via AI to deduce bacterial viability without full assembly.

```bash
# 1. Segment Signals
python AI_scripts/segment.py --path_dir /path/to/pod5_files --out_dir /path/to/output --chunk_size 10000 --start_index 1500

# 2. Pre-process for Deep Learning (Normalizing and saving PyTorch Tensors)
python AI_scripts/preprocess.py -i /path/to/chunked_pod5 -o /path/to/tensors -dt pos -b 1000 -sl 10000

# 3. Concatenate Tensors
python AI_scripts/concat.py --preprocessed_pos_folder /path/to/pos --preprocessed_neg_folder /path/to/neg --save_pos train_pos.pt --save_neg train_neg.pt

# 4. Train Model (ResNet/Transformer)
python AI_scripts/trainer.py -tt train_pos.pt -nt train_neg.pt -tv val_pos.pt -nv val_neg.pt -o trained_model/my_model.ckpt -m ResNet1 -e 100

# 5. Run Inference on Full-Length Variable Signals (No Chunking)
python AI_scripts/inference_variable_length.py --model models/antibiotic_ecoli_ResNet_550ep.ckpt --inpath /path/to/pod5_dir --outpath /path/to/results --model_type ResNet1

# 6. Generate Class Activation Maps (CAMs) for Explainable AI
python AI_scripts/generate_cam.py --ground_truth_file truth.txt --model_weights models/antibiotic_ecoli_ResNet_550ep.ckpt --cam_folder /path/to/cams --pod5_path target.pod5

# 7. XAI Anomaly/Drop Detection
python AI_scripts/detect_drops.py --out_path drops.tsv --in_path /path/to/pod5_folder --figure_path /path/to/figures
```

 
  
 
