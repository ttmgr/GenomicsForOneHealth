# Carbapenem-resistant Enterobacterales: Plasmid-clustering pipeline
This repository offers description of the analytical steps needed for plasmid-encoded resistance dynamics investigation using Oxford Nanopore reads. This README outlines what to do and which tools to use. There are also automated softwares that provide similar analyses for non-experts, but the tools and parameters that they use are usually not fully visible. This pipeline was used in the study xxx and the study sequences are available in the National Center for Biotechnology Information (NCBI) under BioProject accession number PRJNA1297122.

---

## Quick Start
To get results immediately without reading the full methodology, we have provided an interactive wrapper script that automates the steps below.

1. **Activate your environment** (Ensure Conda/Docker tools like Dorado, Flye, Medaka, AMRFinderPlus are active).
2. **Run the interactive script:**
    ```bash
    bash run_pipeline.sh
    ```
3. **Answer the prompts** (Provide your input FASTQ/POD5 paths and desired output directory).

### HPC Quick Start (SLURM)
For HPC clusters with SLURM, use the master pipeline script that submits per-sample dependency chains across multiple coverage levels:

1. **Adjust SLURM parameters** in `run_full_pipeline.sh` (partition, queue, email).
2. **Dry-run first:**
    ```bash
    ./run_full_pipeline.sh --input-dir /path/to/fastqs --dry-run
    ```
3. **Review** the dry-run output, then re-run without `--dry-run` to submit jobs.

See [Section 5: HPC / SLURM Pipeline](#5-hpc--slurm-pipeline-run_full_pipelinesh) for details.

---

## 1. Goal & Scope

Identify and compare plasmids (and chromosomes) from relevant bacterial isolates sequenced with the RBK114 library preparation kit on a R10.4.1 MinION flowcell:

- Reconstruct plasmids and annotate resistance/replicon markers
- Assess plasmid and chromosomal relatedness (SNP distances, plasmid clustering)
---

## 2. Workflow Overview

1. **Signal → Bases**: Basecall raw POD5 signals with Dorado
2. **Per-sample separation**: Demultiplex barcoded reads (Dorado demux)
3. **Read cleaning**: Adapter trimming & QC filtering (*optional if the newer dorado basecaller model handles it with the --trim adapter flag*)
4. **Read downsampling** *(HPC only)*: Subsample to target coverages with Rasusa
5. **Assembly**: De novo assembly (Flye)
6. **Consensus polishing**: Correct (Medaka v2.0.1 with `--bacteria` flag)
7. **Assembly QC** *(HPC only)*: Genome completeness & contamination check (CheckM2)
8. **Plasmid reconstruction & typing**: MOB-Suite (mob\_recon)
9. **AMR gene detection**: AMRFinderPlus
10. **Carbapenemase summary** *(HPC only)*: Automated extraction of carbapenemase-encoding plasmids
11. **Plasmid relatedness**: Mash first, then cluster (e.g. DCJ distance via Pling)
12. **Species ID & MLST**: GTDB-Tk or MLST-only *(HPC)*, or manually via Pathogenwatch/PubMLST
13. **Coverage sensitivity analysis** *(HPC only)*: Multi-coverage comparison for publication
14. **Miscellaneous**: Manual SNP/Mash matrices & visualizations

---

## 3. Inputs

- Raw POD5 or basecalled FASTQ (e.g., from MinKNOW)
- Barcode list (e.g. `01–24`)

---

## 4. Detailed Steps & Codes

> **Installation:** For the general installation of **Mamba**, **Dorado**, and large databases (**Kraken2**, **AMRFinderPlus**), please see the centralized [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) at the root of the repository. The commands below document the specific parameters used in this project.

> Note: Replace placeholder paths, models, parameters as appropriate. All software versions are listed below.

### 4.1 Basecalling

**Tool:** Dorado

```bash
DORADO_BIN="/path/to/dorado"
CONFIG_FILE="/path/to/dna_r10.4.1_e8.2_400bps_sup@v5.0.0"
INPUT_DIR="/path/to/pod5_dir"
OUTDIR="/path/to/output"
KIT="SQK-RBK114-24"

mkdir -p "$OUTDIR"
"$DORADO_BIN" basecaller "$CONFIG_FILE" "$INPUT_DIR" \
  --emit-fastq --kit-name "$KIT" -r --no-trim \
  > "$OUTDIR/basecalled.fastq"
```

### 4.2 Demultiplexing

**Tool:** Dorado demux

```bash
"$DORADO_BIN" demux \
  --output-dir "$OUTDIR/demux" \
  --emit-fastq --kit-name "$KIT" \
  "$OUTDIR/basecalled.fastq"
# yields files like demux/barcode01.fastq
```

### 4.3 Trimming & Filtering

**Tools:** Porechop, NanoFilt, Seqkit

```bash
BCLIST=$(seq -w 01 24)
RAW_PREFIX="$OUTDIR/demux/barcode"
PC_DIR="$OUTDIR/porechop"
NF_DIR="$OUTDIR/filtered_reads"
STATS_DIR="$OUTDIR/stats"
QMIN=8; LMIN=200
mkdir -p "$PC_DIR" "$NF_DIR" "$STATS_DIR"

for bc in $BCLIST; do
  in="${RAW_PREFIX}${bc}.fastq"; [[ -s "$in" ]] || continue
  trim="$PC_DIR/trimmed_${bc}.fastq"
  out="$NF_DIR/filtered_barcode${bc}.fastq"
  porechop -i "$in" -o "$trim"
  NanoFilt -q "$QMIN" -l "$LMIN" < "$trim" > "$out"
  rm -f "$trim"
done

for fq in "$NF_DIR"/*.fastq; do
  [[ -e "$fq" ]] || continue
  seqkit stats -T -a "$fq" > "$STATS_DIR/$(basename "${fq%.fastq}").txt"
done
```

Notes: 
* If you used multiple barcodes for the same sample and concatenated the reads you need to be careful with duplicated read IDs, as that might impair Flye from assembling properly. Thus, make sure to remove any duplicated reads before moving on to the assembly step.
* In case you want to read quality metric outputs, you could try seqkit (see here: https://github.com/shenwei356/seqkit for more information). Alternatively, newer dorado basecalling models offer a summary of basecalled data quality metrics. 

### 4.4 Assembly

**Tool:** Flye

```bash
GENOME_SIZE="5m"; THREADS=8
FLY_DIR="$OUTDIR/flye"; mkdir -p "$FLY_DIR"
for bc in $BCLIST; do
  reads="$NF_DIR/filtered_barcode${bc}.fastq"; [[ -s "$reads" ]] || continue
  flye --nano-hq "$reads" --out-dir "$FLY_DIR/barcode${bc}" \
       --genome-size "$GENOME_SIZE" --threads "$THREADS"
done
```
Note: I added the genome size, however for newer versions of Flye this might not be necessary anymore. 

### 4.5 Depth estimation and Polishing

**Tools:** Minimap2, Samtools, Medaka v2.0.1 (`--bacteria`)

```bash
MIN_DIR="$OUTDIR/minimap"
MEDAKA_DIR="$OUTDIR/medaka"
mkdir -p "$MIN_DIR" "$MEDAKA_DIR"

THREADS=8

for bc in $BCLIST; do
  asm="$FLY_DIR/barcode${bc}/assembly.fasta"
  reads="$NF_DIR/filtered_barcode${bc}.fastq"
  med_out="$MEDAKA_DIR/barcode${bc}"

  mkdir -p "$med_out"

  medaka_consensus -i "$reads" -d "$asm" -o "$med_out" \
    -t "$THREADS" --bacteria
done

> **Note:** The `--bacteria` flag improves assembly quality and reduces error rates in bacterial assemblies. Medaka v2+ is recommended; versions below v2 did not reliably improve assembly quality. Dorado also now includes polishing steps that may replace Medaka in future workflows.


# Run depth estimation using minimap2 + samtools
for bc in $BCLIST; do
  asm="$FLY_DIR/barcode${bc}/assembly.fasta"
  reads="$NF_DIR/filtered_barcode${bc}.fastq"
  bam="$COV_DIR/barcode${bc}.bam"
  depth_file="$COV_DIR/depth_barcode${bc}.txt"

  [[ -s "$asm" && -s "$reads" ]] || { echo "[Coverage] Missing files for barcode $bc. Skipping."; continue; }

  minimap2 -ax map-ont "$asm" "$reads" -t "$THREADS" \
    | samtools view -b - \
    | samtools sort -@ "$THREADS" -o "$bam" -

  samtools index "$bam"
  samtools depth "$bam" > "$depth_file"

  # Calculate and print average depth
  avg=$(awk '{sum += $3} END {if (NR > 0) print sum/NR; else print 0}' "$depth_file")
  echo "Barcode $bc average depth: $avg"
done
```

### 4.6 Plasmid Reconstruction & Typing

**Tool:** MOB‑Suite
Run Mob-Suite on polished assemblies.

```bash
MOB_DIR="$OUTDIR/mob"; mkdir -p "$MOB_DIR"
for bc in $BCLIST; do
  cns="$MEDAKA_DIR/barcode${bc}/consensus.fasta"; [[ -s "$cns" ]] || continue
  mob_recon --infile "$cns" --outdir "$MOB_DIR/barcode${bc}"
done
```

### 4.7 AMR Gene Detection

**Tool:** AMRFinderPlus
Run AMRFinderPlus on polished assemblies.

```bash
AMR_DIR="$OUTDIR/amr"; mkdir -p "$AMR_DIR"
for bc in $BCLIST; do
  cns="$MEDAKA_DIR/barcode${bc}/consensus.fasta"; [[ -s "$cns" ]] || continue
  amrfinder -n "$cns" -o "$AMR_DIR/barcode${bc}.amr.txt" \
    --threads "$THREADS" --plus
done
```

### 4.8 Chromosomal SNP Analysis

For more detailed information please refer to the methods section in our preprint cited above. 

### 4.9 Plasmid Clustering / Distances

**Tools:** Mash, Pling
Run Mash and Pling on polished plasmid assemblies of interest (e.g., IncN, IncL/M) etc. 

```bash
# 1) Compute Mash distances
PLASMID_TYPE="IncN"
OUT_TXT="$OUTDIR/clustering/mash_${PLASMID_TYPE}.txt"; > "$OUT_TXT"
for i in {1..24}; do
  for j in {1..24}; do
    [[ $i -lt $j ]] || continue
    f1=$(printf "plasmid_%s_barcode%02d.fasta" "$PLASMID_TYPE" "$i")
    f2=$(printf "plasmid_%s_barcode%02d.fasta" "$PLASMID_TYPE" "$j")
    [[ -f "$f1" && -f "$f2" ]] && mash dist "$f1" "$f2" >> "$OUT_TXT" \
      || echo "Missing: $f1 or $f2"
  done

done

# 2) DCJ-based clustering with Pling (after selecting pairs below threshold)
pling align --containment_distance 0.3 --cores 8 --sourmash plasmid.txt "$OUTDIR/clustering/pling_out"
```

### 4.10 Miscellaneous & Reporting

- SNP/Mash distance matrices and visualizations were done manually
- In general, I have had good experience with bandage (cited in the preprint) to get assembly visualisations and ProkSee for visualisation of functional annotations.
- Be careful when re-running assemblies and matching contigs previously annotated with MOB-Suite to the new assemblies (i.e., with regards to contig length etc.), as flye might change the contig-numbering when re-running again
- Species identification was conducted externally via Pathogenwatch and/or PubMLST (see corresponding publication)

---

## 5. HPC / SLURM Pipeline (`run_full_pipeline.sh`)

For large-scale analyses on HPC clusters, `run_full_pipeline.sh` submits one SLURM job per sample per step with automatic dependency chains. It extends the local workflow with multi-coverage downsampling, quality assessment, automated summaries, and taxonomy.

### 5.1 Dependency DAG

```text
rasusa -> flye -> medaka -> [checkm2, annotation] -> carba_summary -> [mash/pling, coverage_analysis]
                         -> taxonomy/MLST
```

### 5.2 Prerequisites

**Micromamba environments** (the script activates these per step):
- `assembly` — Flye, Medaka
- `amr_env` — AMRFinderPlus
- `mobsuite_env` — MOB-Suite
- `checkm2_env` — CheckM2

**Databases:**
- CheckM2 database (`--checkm2-db /path/to/checkm2_db`)
- GTDB-Tk database (`--gtdbtk-data /path/to/gtdbtk_db`, only if `--run-gtdb`)

**Helper scripts** (must be in the same directory as `run_full_pipeline.sh`):
- `build_carbapenemase_summary.py` — aggregates AMRFinder + MOB-suite results to identify carbapenemase-encoding plasmids
- `analyze_coverage_publication_fixed.py` — publication-ready multi-coverage comparison
- `run_mash_then_pling_by_group_v2.slurm` — Mash distance + Pling clustering wrapper
- `run_taxonomy_mlst_hybrid.sh` / `run_taxonomy_mlst_only.sh` — taxonomy and MLST scripts

### 5.3 Rasusa Downsampling

Subsamples reads to controlled coverage levels for sensitivity analysis. Runs per sample, per coverage.

```bash
rasusa reads -g 5m -c 30 -s 42 input.fastq > output_30x.fastq
```

Key parameters: `--coverages "30x 40x 60x"` (space-separated), `--genome-size 5m`

### 5.4 CheckM2 Quality Assessment

Verifies genome completeness and contamination after polishing. Runs per sample, per coverage.

```bash
checkm2 predict --threads 8 --input <fasta_dir> --output-directory <outdir> --extension fasta
```

Skip with `--skip-checkm2`.

### 5.5 Carbapenemase Summary

Aggregates AMRFinder + MOB-suite annotation results to extract carbapenemase-encoding plasmids. Runs once per coverage level after all annotation jobs complete. Uses `build_carbapenemase_summary.py`.

### 5.6 Taxonomy & MLST

Automated species identification, replacing manual Pathogenwatch/PubMLST.

- **Default (MLST-only):** runs `run_taxonomy_mlst_only.sh`
- **Full taxonomy:** add `--run-gtdb --gtdbtk-data /path/to/gtdbtk_db` to use GTDB-Tk

Runs once after all polishing jobs complete.

### 5.7 Coverage Sensitivity Analysis

Publication-ready comparison of results across coverage levels. Uses `analyze_coverage_publication_fixed.py`. Skip with `--skip-coverage-analysis`.

### 5.8 SLURM Configuration

- **Partition/queue:** `-p cpu_p -q cpu_normal` are site-specific defaults; edit in the script for your cluster
- **Dry-run mode:** `--dry-run` prints all sbatch commands without submitting
- **Monitoring:** `squeue -u $USER`
- **Cancel all:** job IDs are collected and printed at the end for easy cancellation

### 5.9 Full CLI Reference

```text
Usage: run_full_pipeline.sh --input-dir DIR [OPTIONS]

Required:
  --input-dir DIR            Directory containing raw FASTQ files

Pipeline control:
  --coverages "30x 40x 60x"  Space-separated coverage targets (default: "30x 40x 60x")
  --genome-size SIZE         Genome size for rasusa/flye (default: 5m)
  --skip-checkm2             Skip CheckM2 quality assessment
  --skip-pling               Skip Mash/PLING plasmid network analysis
  --skip-coverage-analysis   Skip coverage sensitivity analysis
  --run-gtdb                 Enable GTDB-Tk taxonomy (default: MLST only)
  --gtdbtk-data PATH         GTDB-Tk database path (required if --run-gtdb)

Parameters:
  --checkm2-db PATH          CheckM2 database path
  --mash-threshold FLOAT     Mash distance threshold (default: 0.005)
  --pling-containment FLOAT  PLING containment threshold (default: 0.3)

SLURM:
  --email ADDRESS            Email for SLURM notifications
  --work-dir DIR             Project root for outputs (default: parent of input-dir)
  --log-dir DIR              Directory for SLURM logs (default: ./logs)

Other:
  --dry-run                  Print sbatch commands without submitting
  --help                     Show this help
```

---

## 6. Suggested Folder Structure

### Local pipeline (`run_pipeline.sh`)

```text
project/
├─ raw/                     # POD5/FAST5 or raw FASTQs
├─ demux/
├─ filtered_reads/          # post-trim/filter
├─ flye/                    # raw assemblies
├─ medaka/                  # polished assemblies
├─ mob/                     # plasmid reconstruction
├─ amr/                     # AMR gene tables
├─ clustering/              # plasmid clustering & distances
└─ reports/                 # summary tables & figures
```

### HPC pipeline (`run_full_pipeline.sh`)

```text
project/
├─ raw/                              # input FASTQs
├─ 30x/ 40x/ 60x/                   # rasusa-downsampled reads (per coverage)
├─ flye_30x/ flye_40x/ ...          # Flye assemblies (per coverage)
├─ polished_fasta_30x/ ...          # Medaka-polished FASTAs (per coverage)
├─ checkm2_30x/ ...                 # CheckM2 quality reports (per coverage)
├─ annotation_30x/ ...              # AMRFinder + MOB-suite results (per coverage)
│   ├─ <sample>/amrfinder/
│   ├─ <sample>/mob_recon/
│   └─ summaries/                   # carbapenemase summary tables
├─ taxonomy_mlst_results/           # GTDB-Tk or MLST results
├─ clustering/                      # Mash + Pling plasmid networks
├─ coverage_publication_analysis/   # coverage sensitivity figures
└─ logs/                            # SLURM .out/.err logs
```

---

## 7. Software Checklist

**Core pipeline:**
- Dorado (v5.0)
- Porechop (v0.2.3), NanoFilt (v2.8.0), Seqkit (v2.10.0)
- Flye (v2.9.5)
- Minimap2 (v2.2.9), Samtools (v1.16.1)
- Medaka (v2.0.1)
- MOB-suite (v3.1.8)
- AMRFinderPlus (v4.0.3)
- Mash (v2.3), Pling (v1.0.1)

**HPC pipeline (additional):**
- Rasusa (v2.0+)
- CheckM2 (v1.0+)
- MLST (v2.23+)
- GTDB-Tk (v2.3+) *(optional, for full taxonomy)*
- Micromamba (for HPC environment management)

 
  
 
