#!/usr/bin/env bash
set -e

echo "========================================="
echo " Nanopore AMR Host Association Pipeline"
echo " Interactive Launcher"
echo "========================================="

# 1. Environment Check
echo "Checking environment dependencies..."
for cmd in dorado samtools chopper modkit nanomotif mob_recon amrfinder kraken2; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Warning: Required tool '$cmd' is not in your PATH."
        MISSING_TOOLS=1
    fi
done

if [ "$MISSING_TOOLS" = "1" ]; then
    echo "This pipeline requires Conda/Docker tools to be active."
    read -p "Press Enter to continue anyway, or Ctrl+C to abort..."
fi

# 2. Prompts
echo ""
read -p "Please provide the absolute path to your POD5 input directory: " IN_DIR
if [ ! -d "$IN_DIR" ]; then
    echo "Error: Directory '$IN_DIR' does not exist."
    exit 1
fi

read -p "Please provide the absolute path for the output results directory [Default: $(pwd)/results]: " OUT_DIR
OUT_DIR=${OUT_DIR:-"$(pwd)/results"}
mkdir -p "$OUT_DIR"

read -p "Please provide the absolute path to your Kraken2 Database: " KRAKEN_DB
if [ ! -d "$KRAKEN_DB" ]; then
    echo "Warning: Kraken DB path '$KRAKEN_DB' does not exist. The pipeline will fail at the taxonomy step if not resolved."
    read -p "Press Enter to continue anyway..."
fi

echo "========================================="
echo " Setting Pipeline Variables..."
echo "========================================="
export READS_DIR="$IN_DIR"
export OUTPUT_BAM="$OUT_DIR/basecalled/trimmed.bam"
export INPUT_BAM="$OUT_DIR/basecalled/trimmed.bam"
export OUTPUT_DIR="$OUT_DIR/demux"
export KRAKEN2_DB="$KRAKEN_DB"
export OUT_DIR="$OUT_DIR"

echo "========================================="
echo " Step 1. Basecalling"
echo "========================================="
bash basecall_dorado_sup.sh || echo "Basecalling failed or skipped."

echo "========================================="
echo " Step 2. Demultiplexing"
echo "========================================="
bash demux.sh || echo "Demultiplexing failed or skipped."

echo "========================================="
echo " Pipeline Orchestration Created"
echo "========================================="
echo "Note: Full end-to-end processing of this complex AI pipeline requires cluster access (SLURM) or significant compute."
echo "The initial inputs have been collected and the first two steps launched automatically via this wrapper."
echo "Please refer to the README.md to continue the subsequent contig-level matching steps."

 
