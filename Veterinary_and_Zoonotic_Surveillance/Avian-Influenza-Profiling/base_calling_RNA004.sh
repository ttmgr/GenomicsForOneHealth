#!/bin/bash

# SLURM directives
#SBATCH -p gpu_p
#SBATCH -q gpu_short
#SBATCH --gres=gpu:1

# Read command-line arguments for input directory and output file
input_dir=$1
output_fastq_file=$2

DORADO_BIN="${DORADO_BIN:-dorado}"
DORADO_MODEL="${DORADO_MODEL:-rna004_130bps_hac@v3.0.1}"

# Dorado basecalling command 
"$DORADO_BIN" basecaller \
    --emit-fastq \
    "$DORADO_MODEL" \
    "$input_dir" \
    > "$output_fastq_file"

 
  
 
