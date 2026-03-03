#!/usr/bin/env bash
set -e

echo "========================================="
echo " Air Metagenomics Pipeline"
echo " Interactive Launcher"
echo "========================================="
echo "This wrapper will prompt you for the necessary paths and launch the full pipeline."
echo "If you prefer to run the pipeline manually or execute individual stages step-by-step,"
echo "you can interact directly with the scripts in the 'bash_scripts/' directory as described in the README."
echo "========================================="
echo ""

# 1. Environment Check
echo "Checking environment dependencies..."
if [[ "$CONDA_DEFAULT_ENV" != "air_metagenomics" ]]; then
    echo "Warning: You are not in the 'air_metagenomics' conda environment."
    read -p "Press Enter to continue anyway or Ctrl+C to abort..."
fi

# 2. Prompts
read -p "Please provide the absolute path to your demultiplexed FASTQ directory: " INPUT_FASTQ_DIR
if [ ! -d "$INPUT_FASTQ_DIR" ]; then
    echo "Error: Directory '$INPUT_FASTQ_DIR' does not exist."
    exit 1
fi

read -p "Please provide the absolute path for the output results directory [Default: $(pwd)/processing]: " OUTPUT_BASE_DIR
OUTPUT_BASE_DIR=${OUTPUT_BASE_DIR:-"$(pwd)/processing"}
mkdir -p "$OUTPUT_BASE_DIR"

read -p "How many CPU threads should be used? [Default: 24]: " THREADS
THREADS=${THREADS:-24}

echo ""
echo "Database Configurations:"
read -p "Path to Kraken2 Database: " KRAKEN2_DB_PATH
read -p "Path to AMRFinderPlus Database: " AMRFINDER_DB_PATH
read -p "Path to Bakta Database: " BAKTA_DB_PATH
read -p "Path to eggNOG Data Directory: " EGGNOG_DATA_DIR

export OUTPUT_BASE_DIR
export INPUT_FASTQ_DIR
export THREADS
export KRAKEN2_DB_PATH
export AMRFINDER_DB_PATH
export BAKTA_DB_PATH
export EGGNOG_DATA_DIR

echo ""
echo "========================================="
echo " Launching automated pipeline..."
echo "========================================="
bash bash_scripts/run_pipeline.sh

 
  
 
