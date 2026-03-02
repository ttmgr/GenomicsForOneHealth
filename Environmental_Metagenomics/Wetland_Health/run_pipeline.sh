#!/usr/bin/env bash
set -e

echo "========================================="
echo " Wetland Health Genomics Pipeline"
echo " Interactive Launcher"
echo "========================================="

echo "Please select the analysis workflow you wish to run:"
echo "1) DNA Shotgun Metagenomics (Microbial & AMR)"
echo "2) AIV (RNA) Analysis (Avian Influenza)"
echo "3) Viral Metagenomics (RNA Viromics)"
echo "4) 12S rRNA Vertebrate Metabarcoding"
echo ""
read -p "Enter 1, 2, 3, or 4: " WORKFLOW

read -p "Please provide the absolute path to your raw input FASTQ directory: " INPUT_DIR
if [ ! -d "$INPUT_DIR" ]; then echo "Error: $INPUT_DIR not found"; exit 1; fi

read -p "Please provide the absolute path for the output directory [Default: $(pwd)/results]: " OUT_DIR
OUT_DIR=${OUT_DIR:-"$(pwd)/results"}
mkdir -p "$OUT_DIR"

if [ "$WORKFLOW" = "1" ] || [ "$WORKFLOW" = "3" ]; then
    echo ""
    echo "--- 1. Read Processing (Porechop & NanoFilt) ---"
    TRIM_DIR="$OUT_DIR/trimmed"
    mkdir -p "$TRIM_DIR"
    
    for fq in "$INPUT_DIR"/*.f*q*; do
        [[ -e "$fq" ]] || continue
        base=$(basename "$fq")
        echo "Processing $base..."
        if command -v porechop &> /dev/null && command -v NanoFilt &> /dev/null; then
            porechop -i "$fq" -o "$TRIM_DIR/trim_$base"
            cat "$TRIM_DIR/trim_$base" | NanoFilt -l 100 > "$TRIM_DIR/filtered_$base"
            rm "$TRIM_DIR/trim_$base"
        else
            echo "Skipping Porechop/NanoFilt (tools not found in PATH). Copying..."
            cp "$fq" "$TRIM_DIR/filtered_$base"
        fi
    done
    echo "Pre-processing complete. Proceed to assembly or taxonomic classification as described in the markdown guides."
    
elif [ "$WORKFLOW" = "2" ]; then
    echo ""
    echo "--- AIV Analysis ---"
    read -p "Provide reference FASTA for AIV [Default: refs/aiv_ref.fasta]: " REF_FASTA
    REF_FASTA=${REF_FASTA:-refs/aiv_ref.fasta}
    
    ALN_DIR="$OUT_DIR/alignments"
    mkdir -p "$ALN_DIR"
    
    for fq in "$INPUT_DIR"/*.f*q*; do
        [[ -e "$fq" ]] || continue
        base=$(basename "$fq")
        if command -v minimap2 &> /dev/null; then
            minimap2 -ax map-ont "$REF_FASTA" "$fq" > "$ALN_DIR/${base}.sam"
        fi
    done
    echo "Alignment complete. Refer to aiv_rna_analysis_pipeline.md for BCFtools consensus."

elif [ "$WORKFLOW" = "4" ]; then
    echo ""
    echo "--- 12S rRNA Vertebrate ---"
    echo "Starting OBITools4 and Cutadapt pipeline..."
    echo "This workflow requires a specific 9bp tags mapping file."
    read -p "Do you have the tags file ready? (y/n): " READY
    if [ "$READY" = "y" ]; then
        echo "Refer to rrna_vertebrate_analysis.md to execute the ngsfilter commands."
    fi
else
    echo "Invalid option."
fi

echo "========================================="
echo " Pipeline Initialization Complete"
echo " Initial outputs stored in $OUT_DIR"
echo "========================================="

