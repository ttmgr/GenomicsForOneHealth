#!/bin/bash
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --nice=10000
#SBATCH --mail-user=timthilomaria.reska@helmholtz-munich.de
#SBATCH --mail-type=FAIL
#SBATCH -o logs/%x_%A_%a.out
#SBATCH -e logs/%x_%A_%a.err
#SBATCH --mem=120G
#SBATCH -c 12
#SBATCH -t 24:00:00
#SBATCH --job-name=strain_map_5
# -----------------------------------------------------------------------------
# Step 81: Competitive mapping against the expanded reference
#          (4 L. mono + 3 non-mono Listeria + background species).
#          One SLURM array job per sample.
# Input:  Filtered FASTQs (from strain_filelist_5.txt) + expanded reference
# Output: BAM, coverage stats, MAPQ distribution, strain proportions
# Run:    sbatch --array=1-N scripts/81_strain_mapping_background.sh
# Filelist: $WORK_DIR/strain_filelist_5.txt (built by step 80)
# -----------------------------------------------------------------------------
SCRIPT_DIR="${SLURM_SUBMIT_DIR:+${SLURM_SUBMIT_DIR}/scripts}"
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
source "${SCRIPT_DIR}/pipeline.conf"

THREADS=${SLURM_CPUS_PER_TASK:-12}
SORT_THREADS=4

REF_DIR="${WORK_DIR}/processing/strain_analysis/references_5"
INDEX="${REF_DIR}/combined_lm_references_5.mmi"
GENOME_SIZES="${REF_DIR}/genome_sizes_5.tsv"
BAM_DIR="${WORK_DIR}/processing/strain_analysis/bam_5"
STATS_DIR="${WORK_DIR}/processing/strain_analysis/stats_5"
STRAIN_FILELIST="${WORK_DIR}/strain_filelist_5.txt"
RESULTS_ALL="${WORK_DIR}/processing/strain_analysis/strain_results_5.tsv"

mkdir -p "$BAM_DIR" "$STATS_DIR"

# ---- Sanity checks ----
if [ ! -f "$INDEX" ]; then
    echo "ERROR: Minimap2 index not found: $INDEX"
    echo "Run 80_prepare_background_refs.sh first."
    exit 1
fi

if [ ! -f "$STRAIN_FILELIST" ]; then
    echo "ERROR: File list not found: $STRAIN_FILELIST"
    echo "Run 80_prepare_background_refs.sh first."
    exit 1
fi

if [ ! -f "$GENOME_SIZES" ]; then
    echo "ERROR: Genome sizes file not found: $GENOME_SIZES"
    exit 1
fi

# ---- Get input file for this array task ----
INPUT_FASTQ=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$STRAIN_FILELIST")

if [ -z "$INPUT_FASTQ" ] || [ ! -f "$INPUT_FASTQ" ]; then
    echo "ERROR: Input file not found for task ${SLURM_ARRAY_TASK_ID}: $INPUT_FASTQ"
    exit 1
fi

# ---- Derive basename ----
FILENAME=$(basename "$INPUT_FASTQ")
if [[ "$FILENAME" == filtered_* ]]; then
    BASENAME="${FILENAME#filtered_}"
    BASENAME="${BASENAME%.fastq.gz}"
    BASENAME="${BASENAME%.fastq}"
else
    BASENAME="${FILENAME%.fastq.gz}"
    BASENAME="${BASENAME%.fastq}"
fi

OUT_BAM="${BAM_DIR}/strain_mapped_${BASENAME}.bam"

echo "=== Expanded Strain Mapping (background-aware) ==="
echo "Sample:    $BASENAME"
echo "Input:     $INPUT_FASTQ"
echo "Output:    $OUT_BAM"
echo "Threads:   $THREADS (sort: $SORT_THREADS)"
echo "Start:     $(date)"
echo ""

# ======================================================================
# PART 1: Competitive mapping with minimap2
# ======================================================================
# --secondary=no: each read maps to one best location only (best strain wins)
# -x map-ont: Nanopore long-read preset
minimap2 -a -x map-ont --secondary=no -t "$THREADS" "$INDEX" "$INPUT_FASTQ" \
    | samtools sort -@ "$SORT_THREADS" -o "$OUT_BAM"

samtools index "$OUT_BAM"

echo ""
echo "=== Mapping summary ==="
samtools flagstat "$OUT_BAM" | tee "${STATS_DIR}/flagstat_${BASENAME}.txt"

# ======================================================================
# PART 2: Per-strain statistics
# ======================================================================
echo ""
echo "=== Computing per-strain statistics ==="

samtools coverage "$OUT_BAM" > "${STATS_DIR}/coverage_${BASENAME}.tsv"
samtools idxstats "$OUT_BAM" > "${STATS_DIR}/idxstats_${BASENAME}.tsv"

# MAPQ distribution (primary alignments only)
samtools view -F 0x904 "$OUT_BAM" | awk '{print $5}' | sort -n | uniq -c \
    > "${STATS_DIR}/mapq_dist_${BASENAME}.tsv"

# ---- Per-strain mapped bases from BAM (primary alignments only) ----
BASES_TMP="${STATS_DIR}/bases_${BASENAME}.tsv"
samtools view -F 0x904 "$OUT_BAM" \
    | awk -F'\t' '{
        split($3, parts, "__")
        strain = parts[1]
        bases[strain] += length($10)
    }
    END {
        for (s in bases) print s "\t" bases[s]
    }' > "$BASES_TMP"

# ---- Aggregate by strain ----
SUMMARY="${STATS_DIR}/strain_summary_${BASENAME}.tsv"
echo -e "basename\tstrain\tmapped_reads\tmapped_bases\tproportion\tcoverage_breadth_pct\tmean_depth\tmean_mapq" > "$SUMMARY"

awk -F'\t' -v basename="$BASENAME" -v bases_file="$BASES_TMP" '
BEGIN {
    while ((getline line < bases_file) > 0) {
        split(line, f, "\t")
        bases[f[1]] = f[2]
    }
    close(bases_file)
}
NR == 1 { next }  # skip header
{
    rname = $1
    numreads = $4
    covbases = $5
    meandepth = $7
    meanmapq = $9
    endpos = $3

    split(rname, parts, "__")
    strain = parts[1]

    reads[strain] += numreads
    covb[strain] += covbases
    depth_sum[strain] += meandepth * endpos
    len_sum[strain] += endpos
    mapq_sum[strain] += meanmapq * numreads
    total_reads += numreads
}
END {
    for (s in reads) {
        prop = (total_reads > 0) ? reads[s] / total_reads : 0
        avg_depth = (len_sum[s] > 0) ? depth_sum[s] / len_sum[s] : 0
        avg_mapq = (reads[s] > 0) ? mapq_sum[s] / reads[s] : 0
        breadth = (len_sum[s] > 0) ? (covb[s] / len_sum[s]) * 100 : 0
        mb = (s in bases) ? bases[s] : 0
        printf "%s\t%s\t%d\t%d\t%.6f\t%.2f\t%.2f\t%.1f\n", \
            basename, s, reads[s], mb, prop, breadth, avg_depth, avg_mapq
    }
}
' "${STATS_DIR}/coverage_${BASENAME}.tsv" >> "$SUMMARY"

rm -f "$BASES_TMP"

echo ""
echo "=== Per-strain results ==="
column -t -s $'\t' "$SUMMARY"

# ---- Atomic append to shared results file ----
(
    flock -x 200
    if [ ! -s "$RESULTS_ALL" ]; then
        echo -e "basename\tstrain\tmapped_reads\tmapped_bases\tproportion\tcoverage_breadth_pct\tmean_depth\tmean_mapq" > "$RESULTS_ALL"
    fi
    tail -n +2 "$SUMMARY" >> "$RESULTS_ALL"
) 200>"${RESULTS_ALL}.lock"

echo ""
echo "Finished: $(date)"
