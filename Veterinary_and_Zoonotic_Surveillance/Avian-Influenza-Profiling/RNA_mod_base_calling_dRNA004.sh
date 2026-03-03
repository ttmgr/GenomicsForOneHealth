#!/bin/bash

# SLURM directives
#SBATCH --ntasks=1
#SBATCH -p gpu_p
#SBATCH -q gpu_short
#SBATCH --gres=gpu:1

# Read command-line arguments
input_dir=$1
output_bam_file=$2

DORADO_BIN="${DORADO_BIN:-dorado}"
DORADO_MOD_MODEL="${DORADO_MOD_MODEL:-rna004_130bps_sup@v3.0.1_m6A_DRACH@v1}"
REF_FASTA="${REF_FASTA:-italy_ref_plot.fasta}"
DORADO_BASE_MODEL="${DORADO_BASE_MODEL:-rna004_130bps_sup@v3.0.1}"

# Dorado basecalling and call m6a modifications
"$DORADO_BIN" basecaller \
    --modified-bases-models "$DORADO_MOD_MODEL" \
    --reference "$REF_FASTA" \
    "$DORADO_BASE_MODEL" \
    "$input_dir" \
    > "$output_bam_file"

 
