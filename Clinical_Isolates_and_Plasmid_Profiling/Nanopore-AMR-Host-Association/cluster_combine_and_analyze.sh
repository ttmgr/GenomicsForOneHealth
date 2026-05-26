#!/bin/bash
#SBATCH --job-name=integrate_plasmid
#SBATCH --output=logs/integrate_%j.out
#SBATCH --error=logs/integrate_%j.err
#SBATCH -p gpu_p
#SBATCH -q gpu_normal
#SBATCH --mem=100G
#SBATCH -t 18:00:00
#SBATCH --nice=10000
# #SBATCH --mail-user=your.email@institution.edu
#SBATCH --mail-type=END,FAIL
#SBATCH -c 10

# Run combine_array_inputs + analyze_plasmid_results on the cluster, pointing
# the combiner directly at the canonical *_results dirs via env vars — no
# symlinks. Both python scripts are pure stdlib.
#
# Upload the two python scripts + this sbatch script into $WORK first:
#   scp combine_array_inputs.py analyze_plasmid_results.py \
#       cluster_combine_and_analyze.sh \
#       user@cluster:$BASEDIR/integrated_run/
#
# Then submit from the cluster:
#   cd $BASEDIR/integrated_run
#   sbatch cluster_combine_and_analyze.sh

set -euo pipefail

BASEDIR="${BASEDIR:?Set BASEDIR to your project root}"
WORK="$BASEDIR/integrated_run"

cd "$WORK"
mkdir -p array_run

# Point combiner straight at the canonical cluster dirs — no symlinks, no copies.
export ABRICATE_DIR="$BASEDIR/abricate_results"
export INTEGRONFINDER_DIR="$BASEDIR/integronfinder_results"
export MOBSUITE_DIR="$BASEDIR/mobsuite_results"
export ISESCAN_DIR="$BASEDIR/isescan_results"
export FASTA_DIRS="$BASEDIR/wastewater_polished_nanomdbg:$BASEDIR/rectalswab_nanomotif_fasta"
export INTEGRATED_RUN_DIR="$WORK/array_run"

echo "==> Workdir : $WORK"
echo "==> Job     : ${SLURM_JOB_ID:-NA} on $(hostname) at $(date)"
echo

echo "==> Combining per-tool inputs (namespaces contigs as {SAMPLE}__{contig})"
python3 combine_array_inputs.py

echo
echo "==> Running analyzer"
(cd "$WORK/array_run" && python3 "$WORK/analyze_plasmid_results.py")

STAMP="$(date +%Y%m%d_%H%M%S)"
TARBALL="$WORK/array_run_${STAMP}.tgz"
tar czf "$TARBALL" -C "$WORK/array_run" .

echo
echo "==> Done. Integrated outputs:"
ls -lh "$WORK/array_run/"
echo
echo "Tarball ready for download:"
ls -lh "$TARBALL"
echo
echo "Mac-side recipe:"
echo "  scp user@cluster:$TARBALL ."
echo "  mkdir -p array_run && tar xzf $(basename "$TARBALL") -C array_run/"
