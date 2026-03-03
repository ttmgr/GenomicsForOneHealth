#!/usr/bin/env bash
set -e

echo "========================================="
echo " From Feather to Fur Pipeline"
echo " Interactive Launcher"
echo "========================================="

echo "Please select the phase of the analysis you wish to run:"
echo "1) Variant Calling (minimap2 + clair3)"
echo "2) Variant Filtering & FASTA prep for FluSurver"
echo ""
read -p "Enter 1 or 2: " PHASE

if [ "$PHASE" = "1" ]; then
    echo ""
    echo "--- 1. Variant Calling ---"
    read -p "Absolute path to your raw sample FASTQ file: " FASTQ
    read -p "Absolute path to your reference FASTA: " REF
    read -p "Absolute path for the output directory: " OUTDIR
    
    if [ ! -f "$FASTQ" ] || [ ! -f "$REF" ]; then
        echo "Error: FASTQ or Reference file not found."
        exit 1
    fi
    
    mkdir -p "$OUTDIR"
    echo "Executing variant_calling.sh..."
    bash variant_calling.sh "$FASTQ" "$REF" "$OUTDIR"

elif [ "$PHASE" = "2" ]; then
    echo ""
    echo "--- 2. Variant Filtering & Consensus ---"
    echo "Note: This step requires BCFTools in your environment."
    read -p "Absolute path to your ANIMAL VCF: " ANIMAL_VCF
    read -p "Absolute path to your INOCULUM VCF: " INOCULUM_VCF
    read -p "Prefix for output files (e.g. mink2): " PREFIX
    read -p "Absolute path to your Reference FASTA for consensus: " REF
    
    if [ ! -f "$ANIMAL_VCF" ] || [ ! -f "$INOCULUM_VCF" ] || [ ! -f "$REF" ]; then
        echo "Error: One of the VCFs or Reference was not found."
        exit 1
    fi
    
    echo "Calling run_process_vcf.sh (Locally, not via SLURM for this interactive wrapper)..."
    # Execute locally instead of SLURM for broad interactive compatibility 
    bash run_process_vcf.sh "$ANIMAL_VCF" "$INOCULUM_VCF" "filtered_variants_${PREFIX}.txt" "filtered_variants_${PREFIX}.vcf"
    
    echo "Compressing and Indexing..."
    bgzip -c "filtered_variants_${PREFIX}.vcf" > "filtered_variants_${PREFIX}.vcf.gz"
    bcftools index "filtered_variants_${PREFIX}.vcf.gz"
    
    echo "Generating Consensus FASTA..."
    bcftools consensus -f "$REF" -s - -o "qsp_${PREFIX}.fasta" "filtered_variants_${PREFIX}.vcf.gz"
    
    echo "========================================="
    echo " PHASE 2 COMPLETE"
    echo " Output FASTA: qsp_${PREFIX}.fasta"
    echo " NEXT STEP: "
    echo " 1. Upload this FASTA to https://flusurver.bii.a-star.edu.sg/"
    echo " 2. Download the annotations text file."
    echo " 3. Use the Python script documented in the README manually to merge the outputs."
    echo "========================================="
else
    echo "Invalid option."
fi

 
  
