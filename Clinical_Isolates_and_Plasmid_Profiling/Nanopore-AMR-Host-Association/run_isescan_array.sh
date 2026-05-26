#!/bin/bash
#SBATCH --job-name=isescan_array
#SBATCH --output=logs/isescan_%A_%a.out
#SBATCH --error=logs/isescan_%A_%a.err
#SBATCH -p cpu_p
#SBATCH -q cpu_normal
#SBATCH --mem=100G
#SBATCH -t 48:00:00
#SBATCH --nice=10000
# #SBATCH --mail-user=your.email@institution.edu
#SBATCH --mail-type=ALL
#SBATCH -c 15
#SBATCH --array=0-16

# NOTE: ISEScan runs FragGeneScan + hmmsearch per contig. On the full metagenome
# assemblies (~210-250k contigs each) this is far slower than the other tools, hence
# -t 48:00:00. If jobs time out, raise --time and/or move to a longer QOS/partition;
# raising -c together with --nthread speeds up the FragGeneScan/hmmer steps.

set -euo pipefail

echo "Job started on: $(hostname)"
echo "Date: $(date)"
echo "Job ID: ${SLURM_JOB_ID:-NA}, Array Task: ${SLURM_ARRAY_TASK_ID:-NA}"
echo "Working directory: $(pwd)"

# --- Activate the ISEScan environment (adjust to how you installed it on the cluster) ---
# conda install: keep as-is and set ISESCAN_ENV if your env has a different name.
# module/pip install: replace these two lines with your `module load ...` or venv activation.
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ISESCAN_ENV:-isescan_x86}"

BASEDIR="${BASEDIR:?Set BASEDIR to your project root}"

FASTAS=(
  wastewater_polished_nanomdbg/G1.fasta
  wastewater_polished_nanomdbg/G2.fasta
  wastewater_polished_nanomdbg/G3.fasta
  wastewater_polished_nanomdbg/R1.fasta
  wastewater_polished_nanomdbg/R2.fasta
  wastewater_polished_nanomdbg/R3.fasta
  wastewater_polished_nanomdbg/S1.fasta
  wastewater_polished_nanomdbg/S2.fasta
  wastewater_polished_nanomdbg/S3.fasta
  rectalswab_nanomotif_fasta/RS1.fasta
  rectalswab_nanomotif_fasta/RS2.fasta
  rectalswab_nanomotif_fasta/RS3.fasta
  rectalswab_nanomotif_fasta/RS4.fasta
  rectalswab_nanomotif_fasta/RS5.fasta
  rectalswab_nanomotif_fasta/RS6.fasta
  rectalswab_nanomotif_fasta/RS7.fasta
  rectalswab_nanomotif_fasta/RS8.fasta
)

FASTA="${BASEDIR}/${FASTAS[$SLURM_ARRAY_TASK_ID]}"
SAMPLE=$(basename "$FASTA" .fasta)
OUTDIR="${BASEDIR}/isescan_results/${SAMPLE}"
THREADS="${SLURM_CPUS_PER_TASK:-15}"

mkdir -p "$OUTDIR"

if [[ ! -f "$FASTA" ]]; then
  echo "ERROR: FASTA file not found: $FASTA"
  exit 1
fi

echo "Sample: $SAMPLE"
echo "Input FASTA: $FASTA"
echo "Output directory: $OUTDIR"
echo "Threads: $THREADS"
echo "ISEScan: $(command -v isescan.py) ($(isescan.py --version 2>&1 | tr -d '\n'))"

echo "Running ISEScan on $SAMPLE..."
isescan.py \
  --seqfile "$FASTA" \
  --output "$OUTDIR" \
  --nthread "$THREADS"

echo "ISEScan final output files for $SAMPLE:"
find "$OUTDIR" -maxdepth 1 -type f -name "${SAMPLE}.fasta.*" | sort

echo "Done: $SAMPLE"
echo ""
echo "NOTE: per-sample primary call table is ${OUTDIR}/${SAMPLE}.fasta.tsv"
echo "      After the array completes, download each isescan_results/<SAMPLE>/ into"
echo "      array_downloads/isescan/<SAMPLE>/ locally so combine_array_inputs.py can ingest it."

echo "Job finished at: $(date)"
