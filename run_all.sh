#!/usr/bin/env bash

echo "========================================="
echo " GenomicsForOneHealth Master Execution Script"
echo "========================================="
echo "Select the pipeline you wish to run:"
echo "1) Listeria Adaptive Sampling"
echo "2) CRE Plasmid Clustering"
echo "3) Nanopore AMR Host Association"
echo "4) Squiggle4Viability"
echo "5) AMR Nanopore"
echo "6) Wetland Health Analysis"
echo "7) Air Metagenomics"
echo "8) Avian Influenza Profiling"
echo "9) From Feather to Fur"
echo "========================================="

read -p "Enter number (1-9): " choice

case $choice in
    1)
        echo "Starting Listeria pipeline..."
        cd Food_Safety/Listeria-Adaptive-Sampling/scripts && ./submit_pipeline.sh
        ;;
    2)
        echo "CRE Plasmid Clustering execution requires specific input paths. See Clinical_Isolates_and_Plasmid_Profiling/CRE-Plasmid-clustering/README.md"
        ;;
    3)
        echo "AMR Host Association requires fastq inputs and DB paths. See Environmental_Metagenomics/Nanopore-AMR-Host-Association/README.md"
        ;;
    4)
        echo "Running Squiggle4Viability Inference test..."
        cd Viability_Assessment/Squiggle4Viability/AI_scripts && python3 inference.py --help
        ;;
    5)
        echo "AMR Nanopore pipeline requires input configuration. See Clinical_Isolates_and_Plasmid_Profiling/AMR_nanopore/README.md"
        ;;
    6)
        echo "Wetland Health has multiple sub-workflows. See Wetland_Health documentation."
        ;;
    7)
        echo "Starting Air Metagenomics pipeline..."
        cd Environmental_Metagenomics/Air_Metagenomics && bash bash_scripts/run_pipeline.sh
        ;;
    8)
        echo "Avian Influenza profiling requires initial config mapping. See Veterinary_and_Zoonotic_Surveillance/Avian-Influenza-Profiling/README.md"
        ;;
    9)
        echo "From Feather to Fur requires config mapping. See Veterinary_and_Zoonotic_Surveillance/From_feather_to_fur/README.md"
        ;;
    *)
        echo "Invalid selection."
        ;;
esac

 
  
