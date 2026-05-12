#!/bin/bash
#SBATCH --job-name=abricate_array
#SBATCH --output=/home/haicu/ttreska57/logs/abricate_%A_%a.out
#SBATCH --error=/home/haicu/ttreska57/logs/abricate_%A_%a.err
#SBATCH -p cpu_p
#SBATCH -q cpu_normal
#SBATCH --mem=100G
#SBATCH -t 12:00:00
#SBATCH --nice=10000
#SBATCH --mail-user=timthilomaria.reska@helmholtz-munich.de
#SBATCH --mail-type=ALL
#SBATCH -c 15
#SBATCH --array=0-16

set -euo pipefail

echo "Job started on: $(hostname)"
echo "Date: $(date)"
echo "Job ID: ${SLURM_JOB_ID:-NA}, Array Task: ${SLURM_ARRAY_TASK_ID:-NA}"
echo "Working directory: $(pwd)"

BASEDIR="/lustre/groups/hpc/urban_lab/projects/tim/plasmids_virulence"

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
OUTDIR="${BASEDIR}/abricate_results"
THREADS="${SLURM_CPUS_PER_TASK:-15}"
MINID=90
MINCOV=80

mkdir -p "$OUTDIR"

if [[ ! -f "$FASTA" ]]; then
  echo "ERROR: FASTA file not found: $FASTA"
  exit 1
fi

echo "Sample: $SAMPLE"
echo "Input FASTA: $FASTA"
echo "Output directory: $OUTDIR"
echo "Threads: $THREADS"

echo "Running PlasmidFinder on $SAMPLE..."
abricate \
  --db plasmidfinder \
  --threads "$THREADS" \
  --minid "$MINID" \
  --mincov "$MINCOV" \
  "$FASTA" \
  > "$OUTDIR/${SAMPLE}_plasmidfinder.tsv"

echo "Running CARD on $SAMPLE..."
abricate \
  --db card \
  --threads "$THREADS" \
  --minid "$MINID" \
  --mincov "$MINCOV" \
  "$FASTA" \
  > "$OUTDIR/${SAMPLE}_card.tsv"

echo "Running VFDB on $SAMPLE..."
abricate \
  --db vfdb \
  --threads "$THREADS" \
  --minid "$MINID" \
  --mincov "$MINCOV" \
  "$FASTA" \
  > "$OUTDIR/${SAMPLE}_vfdb.tsv"

echo "Creating per-sample summaries..."
abricate --summary "$OUTDIR/${SAMPLE}_plasmidfinder.tsv" > "$OUTDIR/${SAMPLE}_summary_plasmidfinder.tsv"
abricate --summary "$OUTDIR/${SAMPLE}_card.tsv" > "$OUTDIR/${SAMPLE}_summary_card.tsv"
abricate --summary "$OUTDIR/${SAMPLE}_vfdb.tsv" > "$OUTDIR/${SAMPLE}_summary_vfdb.tsv"

echo "Done: $SAMPLE"
echo "Results:"
ls -lh "$OUTDIR/${SAMPLE}_"*.tsv

echo ""
echo "NOTE: After all array tasks complete, run combined summaries:"
echo "  abricate --summary ${OUTDIR}/*_plasmidfinder.tsv > ${OUTDIR}/summary_plasmidfinder_all.tsv"
echo "  abricate --summary ${OUTDIR}/*_card.tsv > ${OUTDIR}/summary_card_all.tsv"
echo "  abricate --summary ${OUTDIR}/*_vfdb.tsv > ${OUTDIR}/summary_vfdb_all.tsv"

echo "Job finished at: $(date)"
