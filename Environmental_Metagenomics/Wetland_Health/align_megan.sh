#!/bin/bash

# --- User Configuration ---
INPUT_TYPE="reads" # Options: "reads" or "contigs"

# Input directories based on input type
INPUT_FASTQ_DIR="output_normal/nanofilt" # Used if INPUT_TYPE="reads"
INPUT_CONTIGS_PARENT_DIR="output_normal/mdbg_unzipped" # Used if INPUT_TYPE="contigs"

# Main directory for all outputs based on input type
TOP_LEVEL_OUTPUT_DIR_READS="output_normal/minimap_processing_splitprefix"
TOP_LEVEL_OUTPUT_DIR_CONTIGS="output_normal/minimap_processing_contigs_splitprefix"

# Filtering logic:
PROCESS_ONLY_BARCODE=""  # Set to "barcode01" to ONLY process barcode01
SKIP_BARCODE=""          # Set to "barcode01" to SKIP barcode01

# Conda environment name
CONDA_ENV_NAME="diamond" # Environment with seqtk, seqkit, minimap2

# Minimap2 Database
MINIMAP2_NT_DB_MMI="/lustre/groups/hpc/urban_lab/datasets/mm_nt_db_ONT.mmi"
# --- End of User Configuration ---

if [ "${INPUT_TYPE}" == "reads" ]; then
    TOP_LEVEL_OUTPUT_DIR="${TOP_LEVEL_OUTPUT_DIR_READS}"
    SLURM_LOG_DIR="/home/haicu/ttreska57/logs/minimap_pipeline_slurm"
elif [ "${INPUT_TYPE}" == "contigs" ]; then
    TOP_LEVEL_OUTPUT_DIR="${TOP_LEVEL_OUTPUT_DIR_CONTIGS}"
    SLURM_LOG_DIR="/home/haicu/ttreska57/logs/contig_minimap_slurm"
else
    echo "ERROR: Invalid INPUT_TYPE '${INPUT_TYPE}'."
    exit 1
fi

mkdir -p "${TOP_LEVEL_OUTPUT_DIR}"
mkdir -p "${TOP_LEVEL_OUTPUT_DIR}/sbatch_scripts"
mkdir -p "${SLURM_LOG_DIR}"

echo "Starting job submission process for ${INPUT_TYPE}..."
echo "Top-level output directory: ${TOP_LEVEL_OUTPUT_DIR}"
if [ -n "${PROCESS_ONLY_BARCODE}" ]; then
    echo "Mode: Processing ONLY barcode: ${PROCESS_ONLY_BARCODE}"
elif [ -n "${SKIP_BARCODE}" ]; then
    echo "Mode: Skipping barcode: ${SKIP_BARCODE}"
else
    echo "Mode: Processing all found files."
fi
echo "---"

# Collect input files based on INPUT_TYPE
declare -a INPUT_FILES
if [ "${INPUT_TYPE}" == "reads" ]; then
    for f in "${INPUT_FASTQ_DIR}"/*fastq; do
        [ -s "$f" ] && INPUT_FILES+=("$f")
    done
elif [ "${INPUT_TYPE}" == "contigs" ]; then
    while IFS= read -r f; do
        [ -s "$f" ] && INPUT_FILES+=("$f")
    done < <(find "${INPUT_CONTIGS_PARENT_DIR}" -mindepth 2 -maxdepth 2 -name "contigs.fasta" | sort)
fi

for input_file_path in "${INPUT_FILES[@]}"; do
    if [ "${INPUT_TYPE}" == "reads" ]; then
        base_filename=$(basename "${input_file_path}" .fastq)
        current_barcode=$(echo "${base_filename}" | grep -oE 'barcode[0-9]+' || echo "")
        if [ -z "${current_barcode}" ]; then
            current_barcode="unknown_$(echo "${base_filename}" | cut -d'_' -f1)"
        fi
    else
        barcode_dir_path=$(dirname "${input_file_path}")
        current_barcode=$(basename "${barcode_dir_path}")
        base_filename="${current_barcode}_contigs"
    fi

    # Filtering logic
    process_this_file=true
    if [ -n "${PROCESS_ONLY_BARCODE}" ] && [ "${current_barcode}" != "${PROCESS_ONLY_BARCODE}" ]; then
        process_this_file=false
    elif [ -n "${SKIP_BARCODE}" ] && [ "${current_barcode}" == "${SKIP_BARCODE}" ]; then
        process_this_file=false
    fi

    if ! ${process_this_file}; then
        echo "Skipping job for ${base_filename} (barcode: ${current_barcode}) due to filter settings."
        continue
    fi

    # Define sample-specific output directory and SLURM parameters
    if [ "${INPUT_TYPE}" == "reads" ]; then
        SAMPLE_OUTPUT_DIR="${TOP_LEVEL_OUTPUT_DIR}/${current_barcode}_output"
        mkdir -p "${SAMPLE_OUTPUT_DIR}/00_fasta"
        mkdir -p "${SAMPLE_OUTPUT_DIR}/01_sorted_fasta"
        mkdir -p "${SAMPLE_OUTPUT_DIR}/02_minimap2_sam"
        JOBFILE="${TOP_LEVEL_OUTPUT_DIR}/sbatch_scripts/minimap_job_${current_barcode}.sbatch"
        JOB_NAME="mm_pipe_${current_barcode}"
        MEM="300G"
        TIME="36:00:00"
        CPUS="28"
    else
        SAMPLE_OUTPUT_DIR="${TOP_LEVEL_OUTPUT_DIR}/${current_barcode}_contigs_output"
        mkdir -p "${SAMPLE_OUTPUT_DIR}/01_sorted_contigs_fasta"
        mkdir -p "${SAMPLE_OUTPUT_DIR}/02_minimap2_sam_contigs"
        JOBFILE="${TOP_LEVEL_OUTPUT_DIR}/sbatch_scripts/minimap_contigs_job_${current_barcode}.sbatch"
        JOB_NAME="mm_contigs_${current_barcode}"
        MEM="200G"
        TIME="24:00:00"
        CPUS="20"
    fi

    echo "Preparing SLURM job for ${base_filename} (barcode: ${current_barcode})..."

    cat > "${JOBFILE}" <<EOF
#!/bin/bash
#SBATCH --job-name=${JOB_NAME}
#SBATCH --mem=${MEM}
#SBATCH -t ${TIME}
#SBATCH --qos=cpu_normal
#SBATCH --partition=cpu_p
#SBATCH --mail-user=timthilomaria.reska@helmholtz-munich.de
#SBATCH --mail-type=FAIL,END
#SBATCH -c ${CPUS}
#SBATCH -o ${SLURM_LOG_DIR}/%x_%A.out
#SBATCH -e ${SLURM_LOG_DIR}/%x_%A.err
#SBATCH --nice=10000

set -euo pipefail # Exit on error

echo "--- SLURM Job Start ---"
echo "Job ID: \${SLURM_JOB_ID}"
echo "Job Name: \${SLURM_JOB_NAME}"
echo "Input file: ${input_file_path}"
echo "Sample Barcode/ID: ${current_barcode}"
echo "Output Directory: ${SAMPLE_OUTPUT_DIR}"
echo "Timestamp: \$(date)"
echo "---"

source \$(conda info --base)/etc/profile.d/conda.sh || { echo "Failed to source conda.sh"; exit 1; }
conda activate "${CONDA_ENV_NAME}" || { echo "Failed to activate Conda env ${CONDA_ENV_NAME}"; exit 1; }
THREADS=\${SLURM_CPUS_PER_TASK:-10}

if [ "${INPUT_TYPE}" == "reads" ]; then
    RAW_FASTA_FILE="${SAMPLE_OUTPUT_DIR}/00_fasta/${current_barcode}.fasta"
    SORTED_FASTA_FILE="${SAMPLE_OUTPUT_DIR}/01_sorted_fasta/${current_barcode}.sorted.fasta"
    MINIMAP2_SAM_FILE="${SAMPLE_OUTPUT_DIR}/02_minimap2_sam/${current_barcode}.aligned.sam"
    MINIMAP2_LOG_FILE="${SAMPLE_OUTPUT_DIR}/02_minimap2_sam/${current_barcode}.minimap2.log"

    echo "[Step 1] Converting FASTQ to FASTA..."
    if [ ! -s "\${RAW_FASTA_FILE}" ]; then
        seqtk seq -a "${input_file_path}" > "\${RAW_FASTA_FILE}"
    fi

    echo "[Step 2] Sorting FASTA by read names..."
    if [ ! -s "\${SORTED_FASTA_FILE}" ]; then
        seqkit sort -n -w 0 --quiet "\${RAW_FASTA_FILE}" -o "\${SORTED_FASTA_FILE}"
    fi

    echo "[Step 3] Running Minimap2 alignment..."
    if [ ! -s "\${MINIMAP2_SAM_FILE}" ]; then
        TMP_DIR="${SAMPLE_OUTPUT_DIR}/minimap2_tmp_split_${current_barcode}_\${SLURM_JOB_ID}"
        mkdir -p "\${TMP_DIR}"
        minimap2 -ax map-ont -k 19 -w 10 -I 10G -g 5000 -r 2000 -N 100 --lj-min-ratio 0.5 -A 2 -B 5 -O 5,56 -E 4,1 -z 400,50 --sam-hit-only \\
            -t "\${THREADS}" \\
            --split-prefix "\${TMP_DIR}/temp_split_idx" \\
            "${MINIMAP2_NT_DB_MMI}" \\
            "\${SORTED_FASTA_FILE}" \\
            > "\${MINIMAP2_SAM_FILE}" 2> "\${MINIMAP2_LOG_FILE}"
        rm -rf "\${TMP_DIR}"
    fi

elif [ "${INPUT_TYPE}" == "contigs" ]; then
    SORTED_CONTIGS_FASTA="${SAMPLE_OUTPUT_DIR}/01_sorted_contigs_fasta/${current_barcode}.sorted_contigs.fasta"
    MINIMAP2_SAM_FILE="${SAMPLE_OUTPUT_DIR}/02_minimap2_sam_contigs/${current_barcode}.contigs_aligned.sam"
    MINIMAP2_LOG_FILE="${SAMPLE_OUTPUT_DIR}/02_minimap2_sam_contigs/${current_barcode}.contigs_minimap2.log"

    echo "[Step 1] Sorting Contig FASTA by record names..."
    if [ ! -s "\${SORTED_CONTIGS_FASTA}" ]; then
        seqkit sort -n -w 0 --quiet "${input_file_path}" -o "\${SORTED_CONTIGS_FASTA}"
    fi

    echo "[Step 2] Running Minimap2 alignment for contigs..."
    if [ ! -s "\${MINIMAP2_SAM_FILE}" ]; then
        TMP_DIR="${SAMPLE_OUTPUT_DIR}/minimap2_tmp_split_contigs/${current_barcode}_\${SLURM_JOB_ID}"
        mkdir -p "\${TMP_DIR}"
        minimap2 -ax asm10 \\
            -I 10G -g 5000 -r 2000 \\
            -N 20 \\
            --sam-hit-only \\
            --split-prefix "\${TMP_DIR}/temp_idx_prefix" \\
            -t "\${THREADS}" \\
            "${MINIMAP2_NT_DB_MMI}" \\
            "\${SORTED_CONTIGS_FASTA}" \\
            > "\${MINIMAP2_SAM_FILE}" 2> "\${MINIMAP2_LOG_FILE}"
        rm -rf "\${TMP_DIR}"
    fi
fi

echo "[Job End @ \$(date)] Processing finished for ${current_barcode}."
conda deactivate
EOF

    sbatch "${JOBFILE}"
    echo "Submitted SLURM job ${JOBFILE} for ${base_filename} (barcode: ${current_barcode})"
    echo "---"
    sleep 1

done

echo "All jobs submitted."
