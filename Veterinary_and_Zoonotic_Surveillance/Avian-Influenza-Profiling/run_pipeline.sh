#!/usr/bin/env bash
set -e

echo "========================================="
echo " Avian Influenza Profiling Pipeline"
echo " Interactive Launcher"
echo "========================================="

echo "Please select the analysis workflow you wish to run:"
echo "1) Basecalling (Dorado/Guppy)"
echo "2) De novo Assembly (Flye)"
echo "3) Reference-based Pipeline (Minimap2)"
echo "4) IRMA Consensus Sequence Generation"
echo ""
read -p "Enter 1, 2, 3, or 4: " WORKFLOW

if [ "$WORKFLOW" = "1" ]; then
    echo ""
    echo "--- Basecalling ---"
    echo "Select data type:"
    echo "  a) Direct RNA002"
    echo "  b) Direct RNA004"
    echo "  c) cDNA"
    echo "  d) RNA Mod Basecalling (dRNA004 m6A)"
    read -p "Enter a, b, c, or d: " BTYPE
    
    # We will just direct the user to the script or run it if they provide paths.
    echo "Running basecalling scripts requires editing the hardcoded paths in the script files first."
    echo "Depending on your choice, please edit and run:"
    case "$BTYPE" in
        a) echo "bash base_calling_RNA002.sh" ;;
        b) echo "bash base_calling_RNA004.sh" ;;
        c) echo "bash base_calling_cDNA.sh" ;;
        d) echo "bash RNA_mod_base_calling_dRNA004.sh" ;;
        *) echo "Invalid choice." ;;
    esac

elif [ "$WORKFLOW" = "2" ]; then
    echo ""
    echo "--- De novo Assembly ---"
    read -p "Run standard Flye (1) or meta-Flye (2)? " FTYPE
    if [ "$FTYPE" = "1" ]; then
        echo "Please execute: bash denovo_flye.sh"
    else
        echo "Please execute: bash denovo_meta_flye.sh"
    fi

elif [ "$WORKFLOW" = "3" ]; then
    echo ""
    echo "--- Reference-based Pipeline ---"
    read -p "Is your data cDNA (1) or RNA002/RNA004 (2)? " RTYPE
    if [ "$RTYPE" = "1" ]; then
        echo "Please execute: bash flu_ref_based_new.sh"
    else
        echo "Please execute: bash flu_ref_based_new_RNA.sh"
    fi

elif [ "$WORKFLOW" = "4" ]; then
    echo ""
    echo "--- IRMA Consensus ---"
    echo "Executing IRMA. Please ensure IRMA is in your PATH and you edit irma.sh if needed."
    echo "Run: bash irma.sh"
else
    echo "Invalid option."
fi

echo "========================================="
echo " Initial guidance complete. Note that these scripts contain hardcoded variables"
echo " that you must edit per your data locations before execution, per developer design."
echo "========================================="

