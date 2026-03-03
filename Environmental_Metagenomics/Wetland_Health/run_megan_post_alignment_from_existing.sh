#!/bin/bash
#SBATCH --job-name=megan_post_align_job
#SBATCH -t 16:00:00
#SBATCH --qos=gpu_normal
#SBATCH --partition=gpu_p
#SBATCH --mail-user=timthilomaria.reska@helmholtz-munich.de
#SBATCH --mail-type=FAIL,END
#SBATCH -c 20
#SBATCH --mem=200G

set -euo pipefail

INPUT_SAM_FULL_PATH="$1"
INPUT_SORTED_FASTA_FULL_PATH="$2"
CURRENT_BARCODE_ID="$3"
SAMPLE_SPECIFIC_OUTPUT_DIR="$4"
INPUT_TYPE="${5:-reads}" # 5th argument: 'reads' or 'contigs'

if [ -z "${INPUT_SAM_FULL_PATH}" ] || [ -z "${INPUT_SORTED_FASTA_FULL_PATH}" ]; then
    echo "ERROR: Missing arguments"
    exit 1
fi

CONDA_ENV_NAME="diamond"
MINIMAP_MEGAN_SCRIPTS_DIR="/lustre/groups/hpc/urban_lab/projects/tim/pb-metagenomics-tools/Taxonomic-Profiling-Minimap-Megan/scripts"
C2C_CONVERTER_BASE_DIR="/lustre/groups/hpc/urban_lab/projects/tim/pb-metagenomics-tools/pb-metagenomics-scripts/Convert-to-kreport-mpa"
MEGAN_MAP_DB_NUC="/lustre/groups/hpc/urban_lab/datasets/megan/megan-nucl-Feb2022.db"

THREADS=${SLURM_CPUS_PER_TASK:-10}
PYTHON_EXEC="python3"
SAMPLE_NAME="${CURRENT_BARCODE_ID}"

if [ "${INPUT_TYPE}" == "reads" ]; then
    RMA_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/03_rma_files"
    R2C_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/04_r2c_reports"
    C2C_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/05_c2c_reports"
    FINAL_REPORTS_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/06_final_reports"

    FILTERED_RMA_FILE="${RMA_DIR}/${SAMPLE_NAME}.filtered.nucleotide.readCount.rma"
    UNFILTERED_RMA_FILE="${RMA_DIR}/${SAMPLE_NAME}.unfiltered.nucleotide.readCount.rma"
    LOG_SAM2RMA_FILTERED="${RMA_DIR}/${SAMPLE_NAME}.filtered.sam2rma.log"
    LOG_SAM2RMA_UNFILTERED="${RMA_DIR}/${SAMPLE_NAME}.unfiltered.sam2rma.log"
    NCBI_C2C_FILE="${C2C_DIR}/${SAMPLE_NAME}.NCBI_Taxonomy.c2c.txt"
    R2C_NCBI_OUT="${R2C_DIR}/${SAMPLE_NAME}.NCBI_Taxonomy.r2c.txt"
    LOG_R2C_NCBI="${R2C_DIR}/${SAMPLE_NAME}.NCBI_Taxonomy.r2c.log"
    LOG_C2C_NCBI="${C2C_DIR}/${SAMPLE_NAME}.NCBI_Taxonomy.c2c.log"

    KRAKEN_REPORT_FILE="${FINAL_REPORTS_DIR}/${SAMPLE_NAME}.ncbi.kreport"
    MPA_REPORT_FILE="${FINAL_REPORTS_DIR}/${SAMPLE_NAME}.ncbi.mpa.txt"

    SAM2RMA_COMMON_PARAMS="-lg -alg longReads -t ${THREADS} -mdb ${MEGAN_MAP_DB_NUC} -ram readCount"
    SAM2RMA_MIN_SUPPORT_FILTERED=0.01
    SAM2RMA_MIN_SUPPORT_UNFILTERED=0
    MIN_PERCENT_COVER_ARG=""
elif [ "${INPUT_TYPE}" == "contigs" ]; then
    RMA_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/03_rma_files_contigs"
    R2C_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/04_r2c_reports_contigs"
    C2C_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/05_c2c_reports_contigs"
    FINAL_REPORTS_DIR="${SAMPLE_SPECIFIC_OUTPUT_DIR}/06_final_reports_contigs"

    FILTERED_RMA_FILE="${RMA_DIR}/${SAMPLE_NAME}.contigs.filtered.nucleotide.readCount.rma"
    UNFILTERED_RMA_FILE="${RMA_DIR}/${SAMPLE_NAME}.contigs.unfiltered.nucleotide.readCount.rma"
    LOG_SAM2RMA_FILTERED="${RMA_DIR}/${SAMPLE_NAME}.contigs.filtered.sam2rma.log"
    LOG_SAM2RMA_UNFILTERED="${RMA_DIR}/${SAMPLE_NAME}.contigs.unfiltered.sam2rma.log"
    NCBI_C2C_FILE="${C2C_DIR}/${SAMPLE_NAME}.contigs.NCBI_Taxonomy.c2c.txt"
    R2C_NCBI_OUT="${R2C_DIR}/${SAMPLE_NAME}.contigs.NCBI_Taxonomy.r2c.txt"
    LOG_R2C_NCBI="${R2C_DIR}/${SAMPLE_NAME}.contigs.NCBI_Taxonomy.r2c.log"
    LOG_C2C_NCBI="${C2C_DIR}/${SAMPLE_NAME}.contigs.NCBI_Taxonomy.c2c.log"

    # NOTE: Output names are partly created by the python script for contigs, but we map them to the same variables conceptually
    KRAKEN_REPORT_FILE="${FINAL_REPORTS_DIR}/${SAMPLE_NAME}.contigs.ncbi.kreport"
    MPA_REPORT_FILE="${FINAL_REPORTS_DIR}/${SAMPLE_NAME}.contigs.ncbi.mpa.txt"

    SAM2RMA_COMMON_PARAMS="-lg -alg longReads -t ${THREADS} -mdb ${MEGAN_MAP_DB_NUC} -ram readCount"
    SAM2RMA_MIN_SUPPORT_FILTERED=0.01
    SAM2RMA_MIN_SUPPORT_UNFILTERED=0
    MIN_PERCENT_COVER_ARG="--minPercentReadCover 0"
else
    echo "ERROR: Invalid INPUT_TYPE '${INPUT_TYPE}'"
    exit 1
fi

mkdir -p "${RMA_DIR}" "${R2C_DIR}" "${C2C_DIR}" "${FINAL_REPORTS_DIR}"

source "$(conda info --base)/etc/profile.d/conda.sh" || { echo "Failed to source conda.sh"; exit 1; }
conda activate "${CONDA_ENV_NAME}" || { echo "Failed to activate Conda env ${CONDA_ENV_NAME}"; exit 1; }

echo "--- Convert SAM to RMA (Filtered) ---"
if [ ! -s "${FILTERED_RMA_FILE}" ]; then
    sam2rma -i "${INPUT_SAM_FULL_PATH}" -r "${INPUT_SORTED_FASTA_FULL_PATH}" -o "${FILTERED_RMA_FILE}" \
        ${SAM2RMA_COMMON_PARAMS} ${MIN_PERCENT_COVER_ARG} --minSupportPercent "${SAM2RMA_MIN_SUPPORT_FILTERED}" -v > "${LOG_SAM2RMA_FILTERED}" 2>&1
fi

echo "--- Convert SAM to RMA (Unfiltered) ---"
if [ ! -s "${UNFILTERED_RMA_FILE}" ]; then
    sam2rma -i "${INPUT_SAM_FULL_PATH}" -r "${INPUT_SORTED_FASTA_FULL_PATH}" -o "${UNFILTERED_RMA_FILE}" \
        ${SAM2RMA_COMMON_PARAMS} ${MIN_PERCENT_COVER_ARG} --minSupportPercent "${SAM2RMA_MIN_SUPPORT_UNFILTERED}" -v > "${LOG_SAM2RMA_UNFILTERED}" 2>&1
fi

echo "--- Extract r2c ---"
if [ ! -s "${R2C_NCBI_OUT}" ] && [ -s "${FILTERED_RMA_FILE}" ]; then
    rma2info -i "${FILTERED_RMA_FILE}" -o "${R2C_NCBI_OUT}" -r2c Taxonomy -n > "${LOG_R2C_NCBI}" 2>&1
fi

echo "--- Extract c2c ---"
if [ ! -s "${NCBI_C2C_FILE}" ] && [ -s "${FILTERED_RMA_FILE}" ]; then
    rma2info -i "${FILTERED_RMA_FILE}" -c2c Taxonomy -n -r -o "${NCBI_C2C_FILE}" > "${LOG_C2C_NCBI}" 2>&1
fi

echo "--- Convert c2c to Kraken/MPA ---"
if [ ! -s "${KRAKEN_REPORT_FILE}" ] && [ -s "${NCBI_C2C_FILE}" ]; then
    SEQ_COUNT=$(grep -c ">" "${INPUT_SORTED_FASTA_FULL_PATH}")
    
    if [ "${INPUT_TYPE}" == "reads" ]; then
        SAMPLE_READ_COUNT_FILE="${C2C_DIR}/${SAMPLE_NAME}.read_count.txt"
        echo -e "${SAMPLE_NAME}\t${SEQ_COUNT}" > "${SAMPLE_READ_COUNT_FILE}"
        
        C2C_CONVERTER_PY_SCRIPT="${MINIMAP_MEGAN_SCRIPTS_DIR}/Convert_MEGAN_RMA_NCBI_c2c-snake.py"
        "${PYTHON_EXEC}" "${C2C_CONVERTER_PY_SCRIPT}" \
            --input "${NCBI_C2C_FILE}" \
            --outname1 "${C2C_DIR}/${SAMPLE_NAME}.names.temp.txt" \
            --outname2 "${C2C_DIR}/${SAMPLE_NAME}.codes.temp.txt" \
            --mpa "${MPA_REPORT_FILE}" \
            --kreport "${KRAKEN_REPORT_FILE}" \
            --readsfile "${SAMPLE_READ_COUNT_FILE}"
    elif [ "${INPUT_TYPE}" == "contigs" ]; then
        C2C_CONVERTER_PY_SCRIPT="${C2C_CONVERTER_BASE_DIR}/Convert_MEGAN-NCBI-c2c_to_kreport-mpa.py"
        (
            cd "${FINAL_REPORTS_DIR}"
            "${PYTHON_EXEC}" "${C2C_CONVERTER_PY_SCRIPT}" \
                -i "${NCBI_C2C_FILE}" \
                -c three \
                -l "${SAMPLE_NAME}.contigs" \
                -r "${SEQ_COUNT}"
        )
        echo "Check ${FINAL_REPORTS_DIR} for files prefixed with '${SAMPLE_NAME}.contigs'."
    fi
fi

echo "Workflow completed for ${SAMPLE_NAME}"
conda deactivate

 
  
 
