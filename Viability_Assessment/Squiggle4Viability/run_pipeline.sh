#!/usr/bin/env bash
set -e

echo "========================================="
echo " Squiggle4Viability Pipeline"
echo " Interactive Launcher"
echo "========================================="

echo "This pipeline has two primary modes:"
echo "1) AI Inference on Signals (Predict Live vs. Dead)"
echo "2) Metagenomics Analysis (Assembly & Classification)"
echo ""
read -p "Select Mode (1 or 2): " MODE

if [ "$MODE" = "1" ]; then
    echo ""
    echo "--- AI Inference Setup ---"
    read -p "Please provide the absolute path to your POD5 input directory: " IN_DIR
    if [ ! -d "$IN_DIR" ]; then
        echo "Error: Directory '$IN_DIR' does not exist."
        exit 1
    fi

    read -p "Please provide the absolute path for the output results directory [Default: $(pwd)/results]: " OUT_DIR
    OUT_DIR=${OUT_DIR:-"$(pwd)/results"}
    mkdir -p "$OUT_DIR"
    
    # We will use the default E.coli ResNet model bundled in the repository
    MODEL_PATH="$(pwd)/models/antibiotic_ecoli_ResNet_550ep.ckpt"
    if [ ! -f "$MODEL_PATH" ]; then
        echo "Warning: Default model not found at $MODEL_PATH."
        read -p "Please provide the absolute path to your custom model weights: " MODEL_PATH
    fi
    
    echo "Starting Inference (Variable Length)..."
    python3 AI_scripts/inference_variable_length.py \
        --model "$MODEL_PATH" \
        --inpath "$IN_DIR" \
        --outpath "$OUT_DIR" \
        --model_type ResNet1
        
    echo "Inference Complete. Results saved to: $OUT_DIR"

elif [ "$MODE" = "2" ]; then
    echo ""
    echo "--- Metagenomics Analysis Workflow ---"
    echo "Note: The scripts in metagenomics_analysis/ require Dorado, Porechop, Flye, and Kraken2."
    read -p "Press Enter to execute the default metagenomics workflow, or Ctrl+C to abort..."
    
    echo "Running Basecalling (dorado_basecalling.sh)..."
    bash metagenomics_analysis/dorado_basecalling.sh || echo "Skipped or failed."
    
    echo "Running Read Processing (readprocessing.sh)..."
    bash metagenomics_analysis/readprocessing.sh || echo "Skipped or failed."
    
    echo "Running Assembly & Polishing (assembly_polishing.sh)..."
    bash metagenomics_analysis/assembly_polishing.sh || echo "Skipped or failed."
    
    echo "Metagenomics default phases completed. Please check your output directories."
else
    echo "Invalid selection."
    exit 1
fi

 
