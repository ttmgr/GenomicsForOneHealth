#!/bin/bash
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --nice=10000
#SBATCH --mail-user=timthilomaria.reska@helmholtz-munich.de
#SBATCH --mail-type=FAIL
#SBATCH -o logs/%x_%A_%a.out
#SBATCH -e logs/%x_%A_%a.err
#SBATCH --mem=60G
#SBATCH -c 4
#SBATCH -t 2:00:00
#SBATCH --job-name=background_refs
# -----------------------------------------------------------------------------
# Step 80: Prepare expanded Listeria + background reference for competitive
#          mapping. 4 L. monocytogenes + 3 non-mono Listeria + 7 background
#          species (E. coli, P. mirabilis, Y. enterocolitica, Y. frederiksenii,
#          S. aureus, R. equi, P. aeruginosa) to absorb reads that were
#          previously mis-mapping onto Listeria references.
#
# Input:  L. mono FASTAs in $WORK_DIR/processing/nanofilt/
#         Non-mono Listeria FASTAs in $WORK_DIR
#         Background species FASTAs in $WORK_DIR
# Output: Combined FASTA (14 genomes), minimap2 index, strain map, file list
# Run:    sbatch scripts/80_prepare_background_refs.sh
# -----------------------------------------------------------------------------
SCRIPT_DIR="${SLURM_SUBMIT_DIR:+${SLURM_SUBMIT_DIR}/scripts}"
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
source "${SCRIPT_DIR}/pipeline.conf"

THREADS=${SLURM_CPUS_PER_TASK:-4}

REF_DIR="${WORK_DIR}/processing/strain_analysis/references_5"
RAW_DIR="${WORK_DIR}/processing/nanofilt"
COMBINED="${REF_DIR}/combined_lm_references_5.fasta"
STRAIN_MAP="${REF_DIR}/strain_map_5.tsv"
GENOME_SIZES="${REF_DIR}/genome_sizes_5.tsv"
INDEX="${REF_DIR}/combined_lm_references_5.mmi"
STRAIN_FILELIST="${WORK_DIR}/strain_filelist_5.txt"

# Non-mono Listeria reference genomes (already in repo)
L_INNOCUA="${WORK_DIR}/L_innocua_J5051.fasta"
L_IVANOVII="${WORK_DIR}/L_ivanovii_Nr26.fasta"
L_WELSHIMERI="${WORK_DIR}/L_welshimeri_Nr14.fasta"

# Background species references
E_COLI="${WORK_DIR}/E_coli.fasta"
P_MIRABILIS="${WORK_DIR}/P_mirabilis.fasta"
Y_ENTEROCOLITICA="${WORK_DIR}/Y_enterocolitica.fasta"
Y_FREDERIKSENII="${WORK_DIR}/Y_frederiksenii.fasta"
S_AUREUS="${WORK_DIR}/S_aureus.fasta"
R_EQUI="${WORK_DIR}/R_equi.fasta"
P_AERUGINOSA="${WORK_DIR}/P_aeruginosa.fasta"

# ---- Create output directories ----
mkdir -p "$REF_DIR"

# ---- Sanity checks ----
if [ ! -d "$RAW_DIR" ]; then
    echo "ERROR: Raw reference directory not found: $RAW_DIR"
    exit 1
fi

for ref in "$L_INNOCUA" "$L_IVANOVII" "$L_WELSHIMERI" \
           "$E_COLI" "$P_MIRABILIS" "$Y_ENTEROCOLITICA" "$Y_FREDERIKSENII" \
           "$S_AUREUS" "$R_EQUI" "$P_AERUGINOSA"; do
    if [ ! -f "$ref" ]; then
        echo "ERROR: Reference not found: $ref"
        echo "Place all non-mono Listeria + background FASTAs in $WORK_DIR"
        exit 1
    fi
done

REF_COUNT=$(find "$RAW_DIR" -maxdepth 1 \( -name "*.fasta" -o -name "*.fa" -o -name "*.fna" -o -name "*.fsa_nt" \) | wc -l)
echo "Found $REF_COUNT L. mono reference genome(s) in $RAW_DIR"
echo "Adding 3 non-mono Listeria species + 7 background species"
echo "Start time: $(date)"

# ---- Clear previous outputs ----
rm -f "$COMBINED" "$STRAIN_MAP" "$GENOME_SIZES" "$INDEX"

# ==========================================================================
# PART 1: Build combined reference (L. mono strains)
# ==========================================================================
echo -e "strain\tseq_name" > "$STRAIN_MAP"
echo -e "strain\tgenome_size_bp" > "$GENOME_SIZES"

for ref_file in "$RAW_DIR"/*.fasta "$RAW_DIR"/*.fa "$RAW_DIR"/*.fna "$RAW_DIR"/*.fsa_nt; do
    [ -f "$ref_file" ] || continue

    strain=$(basename "$ref_file")
    strain="${strain%.fasta}"
    strain="${strain%.fsa_nt}"
    strain="${strain%.fna}"
    strain="${strain%.fa}"

    echo "Processing strain: $strain ($(basename "$ref_file"))"

    sed "s/^>\(.*\)/>${strain}__\1/" "$ref_file" >> "$COMBINED"

    grep "^>" "$ref_file" | sed 's/^>//' | while read -r seqid; do
        seqid_clean=$(echo "$seqid" | awk '{print $1}')
        echo -e "${strain}\t${strain}__${seqid_clean}"
    done >> "$STRAIN_MAP"

    genome_bp=$(grep -v "^>" "$ref_file" | tr -d '\n' | wc -c)
    echo -e "${strain}\t${genome_bp}" >> "$GENOME_SIZES"
    echo "  Genome size: ${genome_bp} bp"
done

# ==========================================================================
# PART 2: Add non-mono Listeria + background references
# ==========================================================================
echo ""
echo "=== Adding non-L. mono references ==="

add_extra_ref() {
    local LABEL="$1"    # e.g. L_innocua_J5051 or B_cereus
    local FASTA="$2"    # full path to FASTA file
    local DESC="$3"     # e.g. "L. innocua J5051"

    echo "Processing: ${LABEL} (${DESC})"
    sed "s/^>\(.*\)/>${LABEL}__\1/" "$FASTA" >> "$COMBINED"
    grep "^>" "$FASTA" | sed 's/^>//' | while read -r seqid; do
        seqid_clean=$(echo "$seqid" | awk '{print $1}')
        echo -e "${LABEL}\t${LABEL}__${seqid_clean}"
    done >> "$STRAIN_MAP"
    genome_bp=$(grep -v "^>" "$FASTA" | tr -d '\n' | wc -c)
    echo -e "${LABEL}\t${genome_bp}" >> "$GENOME_SIZES"
    echo "  Genome size: ${genome_bp} bp"
}

add_extra_ref "L_innocua_J5051"    "$L_INNOCUA"         "L. innocua J5051"
add_extra_ref "L_ivanovii_Nr26"    "$L_IVANOVII"        "L. ivanovii Nr26"
add_extra_ref "L_welshimeri_Nr14"  "$L_WELSHIMERI"      "L. welshimeri Nr14"

add_extra_ref "E_coli"             "$E_COLI"            "Escherichia coli"
add_extra_ref "P_mirabilis"        "$P_MIRABILIS"       "Proteus mirabilis"
add_extra_ref "Y_enterocolitica"   "$Y_ENTEROCOLITICA"  "Yersinia enterocolitica"
add_extra_ref "Y_frederiksenii"    "$Y_FREDERIKSENII"   "Yersinia frederiksenii"
add_extra_ref "S_aureus"           "$S_AUREUS"          "Staphylococcus aureus"
add_extra_ref "R_equi"             "$R_EQUI"            "Rhodococcus equi"
add_extra_ref "P_aeruginosa"       "$P_AERUGINOSA"      "Pseudomonas aeruginosa"

# ==========================================================================
# PART 3: Index
# ==========================================================================
echo ""
echo "Combined reference: $COMBINED"
echo "Total sequences: $(grep -c "^>" "$COMBINED")"
echo "Total size: $(grep -v "^>" "$COMBINED" | tr -d '\n' | wc -c) bp"

echo ""
echo "Creating samtools faidx index..."
samtools faidx "$COMBINED"

echo "Building minimap2 index..."
minimap2 -d "$INDEX" -t "$THREADS" "$COMBINED"

# ==========================================================================
# PART 4: Build sample file list
# ==========================================================================
echo ""
echo "=== Building file list ==="

NANOFILT_DIR="${WORK_DIR}/processing/nanofilt"

find "$NANOFILT_DIR" -name "filtered_*.fastq" -size +0c | sort > "$STRAIN_FILELIST"
find "$NANOFILT_DIR" -name "S13_S14*.fastq" -size +0c >> "$STRAIN_FILELIST"

N_SAMPLES=$(wc -l < "$STRAIN_FILELIST")

echo "File list: $STRAIN_FILELIST"
echo "Total samples: $N_SAMPLES"

# ==========================================================================
# Summary
# ==========================================================================
echo ""
echo "=== Output files ==="
echo "Combined FASTA:  $COMBINED"
echo "FASTA index:     ${COMBINED}.fai"
echo "Minimap2 index:  $INDEX"
echo "Strain map:      $STRAIN_MAP"
echo "Genome sizes:    $GENOME_SIZES"
echo "File list:       $STRAIN_FILELIST ($N_SAMPLES samples)"
echo ""
echo "Strains included:"
tail -n +2 "$GENOME_SIZES" | while IFS=$'\t' read -r s bp; do
    printf "  %-25s %'d bp\n" "$s" "$bp"
done

echo ""
echo "=== Next step ==="
echo "sbatch --array=1-${N_SAMPLES} scripts/81_strain_mapping_background.sh"

echo ""
echo "Finished: $(date)"
