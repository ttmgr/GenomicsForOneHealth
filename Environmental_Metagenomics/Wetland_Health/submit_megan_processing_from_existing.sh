#!/bin/bash

# --- User Configuration ---
INPUT_TYPE="reads" # Options: "reads" or "contigs"

# Parent directory that CONTAINS all the individual sample_analysis directories
PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR_READS="output_normal/minimap_processing_splitprefix"
PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR_CONTIGS="output_normal/minimap_processing_contigs_splitprefix"

SLURM_JOB_SCRIPT_TO_SUBMIT="./run_megan_post_alignment_from_existing.sh"

PROCESS_ONLY_BARCODE_ID=""
SKIP_BARCODE_ID=""
# --- End of User Configuration ---

if [ "${INPUT_TYPE}" == "reads" ]; then
    PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR="${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR_READS}"
    SLURM_LOG_DIR="/home/haicu/ttreska57/logs/minimap_megan_post_slurm"
    OUT_DIR_SUFFIX="_output"
elif [ "${INPUT_TYPE}" == "contigs" ]; then
    PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR="${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR_CONTIGS}"
    SLURM_LOG_DIR="/home/haicu/ttreska57/logs/contig_megan_post_slurm"
    OUT_DIR_SUFFIX="_contigs_output"
else
    echo "ERROR: Invalid INPUT_TYPE '${INPUT_TYPE}'."
    exit 1
fi

if [ ! -f "${SLURM_JOB_SCRIPT_TO_SUBMIT}" ]; then
    echo "ERROR: SLURM job script '${SLURM_JOB_SCRIPT_TO_SUBMIT}' not found."
    exit 1
fi
if [ ! -d "${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR}" ]; then
    echo "ERROR: Output parent directory '${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR}' not found."
    exit 1
fi

mkdir -p "${SLURM_LOG_DIR}"

echo ">>> Starting SLURM job submission for MEGAN Post-Alignment Processing (${INPUT_TYPE}) <<<"
echo "Looking for pre-processed directories in: ${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR}"

find "${PREVIOUS_PIPELINE_TOP_LEVEL_OUTPUT_DIR}" -mindepth 1 -maxdepth 1 -type d -name "*${OUT_DIR_SUFFIX}" | sort | while IFS= read -r current_sample_prev_output_dir_abs_path; do
    
    current_barcode_id=$(basename "${current_sample_prev_output_dir_abs_path}" "${OUT_DIR_SUFFIX}")

    process_this_sample=true
    if [ -n "${PROCESS_ONLY_BARCODE_ID}" ] && [ "${current_barcode_id}" != "${PROCESS_ONLY_BARCODE_ID}" ]; then
        process_this_sample=false
    elif [ -n "${SKIP_BARCODE_ID}" ] && [ "${current_barcode_id}" == "${SKIP_BARCODE_ID}" ]; then
        process_this_sample=false
    fi

    if ! ${process_this_sample}; then
        continue
    fi

    if [ "${INPUT_TYPE}" == "reads" ]; then
        input_sam_file="${current_sample_prev_output_dir_abs_path}/02_minimap2_sam/${current_barcode_id}.aligned.sam"
        input_sorted_fasta_file="${current_sample_prev_output_dir_abs_path}/01_sorted_fasta/${current_barcode_id}.sorted.fasta"
        sbatch_job_name="megan_post_${current_barcode_id}"
    else
        input_sam_file="${current_sample_prev_output_dir_abs_path}/02_minimap2_sam_contigs/${current_barcode_id}.contigs_aligned.sam"
        input_sorted_fasta_file="${current_sample_prev_output_dir_abs_path}/01_sorted_contigs_fasta/${current_barcode_id}.sorted_contigs.fasta"
        sbatch_job_name="megan_contigs_${current_barcode_id}"
    fi

    if [ ! -s "${input_sam_file}" ] || [ ! -s "${input_sorted_fasta_file}" ]; then
        echo "WARNING: Required input files for ${current_barcode_id} not found or empty. Skipping."
        continue
    fi

    echo "  Submitting SLURM job for ${current_barcode_id}..."
    sbatch_output=$(sbatch --parsable \
        --job-name="${sbatch_job_name}" \
        --output="${SLURM_LOG_DIR}/%x_%A.out" \
        --error="${SLURM_LOG_DIR}/%x_%A.err" \
        "${SLURM_JOB_SCRIPT_TO_SUBMIT}" \
        "${input_sam_file}" \
        "${input_sorted_fasta_file}" \
        "${current_barcode_id}" \
        "${current_sample_prev_output_dir_abs_path}" \
        "${INPUT_TYPE}")
    
    if [ $? -eq 0 ]; then
        echo "    Successfully submitted. SLURM Job ID: ${sbatch_output}"
    else
        echo "    ERROR: Failed to submit job for barcode ${current_barcode_id}"
    fi
    sleep 1
done
echo ">>> Done <<<"
