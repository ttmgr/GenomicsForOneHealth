#!/usr/bin/env bash
# =============================================================================
# run_full_pipeline.sh -- CRE carbapenemase analysis master pipeline
#
# Submits ONE SLURM JOB PER SAMPLE per step, with per-sample dependency chains.
# One command, full pipeline: rasusa -> flye -> medaka -> checkm2 -> annotation
#                              -> taxonomy/MLST -> mash/pling -> coverage analysis
#
# Usage:  ./run_full_pipeline.sh --input-dir /path/to/fastqs [OPTIONS]
# =============================================================================
set -euo pipefail

# --- version guard ---
if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
    echo "ERROR: bash 4+ required (associative arrays). Found: ${BASH_VERSION}" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# =============================================================================
# Defaults
# =============================================================================
COVERAGES="30x 40x 60x"
GENOME_SIZE="5m"
CHECKM2_DB="/path/to/checkm2_db"
RUN_GTDB=0
GTDBTK_DATA=""
MASH_THRESHOLD="0.005"
PLING_CONTAINMENT="0.3"
EMAIL="your-email@example.com"
INPUT_DIR=""
WORK_DIR=""
LOG_DIR=""
SKIP_CHECKM2=0
SKIP_PLING=0
SKIP_COVERAGE_ANALYSIS=0
DRY_RUN=0

# =============================================================================
# Usage
# =============================================================================
usage() {
    cat <<'USAGE'
Usage: run_full_pipeline.sh --input-dir DIR [OPTIONS]

Submits one SLURM job per sample per step with per-sample dependency chains.

Required:
  --input-dir DIR            Directory containing raw FASTQ files

Pipeline control:
  --coverages "30x 40x 60x"  Space-separated coverage targets (default: "30x 40x 60x")
  --genome-size SIZE         Genome size for rasusa/flye (default: 5m)
  --skip-checkm2             Skip CheckM2 quality assessment
  --skip-pling               Skip Mash/PLING plasmid network analysis
  --skip-coverage-analysis   Skip coverage sensitivity analysis
  --run-gtdb                 Enable GTDB-Tk taxonomy (default: MLST only)
  --gtdbtk-data PATH         GTDB-Tk database path (required if --run-gtdb)

Parameters:
  --checkm2-db PATH          CheckM2 database path (default: /path/to/checkm2_db)
  --mash-threshold FLOAT     Mash distance threshold (default: 0.005)
  --pling-containment FLOAT  PLING containment threshold (default: 0.3)

SLURM:
  --email ADDRESS            Email for SLURM notifications (default: your-email@example.com)
  --work-dir DIR             Project root for outputs (default: parent of input-dir)
  --log-dir DIR              Directory for SLURM .out/.err logs (default: ./logs)

Other:
  --dry-run                  Print sbatch commands without submitting
  --help                     Show this help
USAGE
    exit 0
}

# =============================================================================
# Argument parsing
# =============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-dir)        INPUT_DIR="$2";             shift 2 ;;
        --work-dir)         WORK_DIR="$2";              shift 2 ;;
        --coverages)        COVERAGES="$2";             shift 2 ;;
        --genome-size)      GENOME_SIZE="$2";           shift 2 ;;
        --checkm2-db)       CHECKM2_DB="$2";            shift 2 ;;
        --run-gtdb)         RUN_GTDB=1;                 shift   ;;
        --gtdbtk-data)      GTDBTK_DATA="$2";          shift 2 ;;
        --mash-threshold)   MASH_THRESHOLD="$2";        shift 2 ;;
        --pling-containment) PLING_CONTAINMENT="$2";    shift 2 ;;
        --email)            EMAIL="$2";                 shift 2 ;;
        --log-dir)          LOG_DIR="$2";               shift 2 ;;
        --skip-checkm2)     SKIP_CHECKM2=1;             shift   ;;
        --skip-pling)       SKIP_PLING=1;               shift   ;;
        --skip-coverage-analysis) SKIP_COVERAGE_ANALYSIS=1; shift ;;
        --dry-run)          DRY_RUN=1;                  shift   ;;
        --help|-h)          usage ;;
        *) echo "ERROR: unknown option: $1" >&2; exit 1 ;;
    esac
done

# =============================================================================
# Validation
# =============================================================================
errors=0

if [[ -z "$INPUT_DIR" ]]; then
    echo "ERROR: --input-dir is required" >&2
    errors=1
elif [[ ! -d "$INPUT_DIR" ]]; then
    echo "ERROR: --input-dir does not exist: $INPUT_DIR" >&2
    errors=1
fi

if [[ "$RUN_GTDB" -eq 1 && -z "$GTDBTK_DATA" ]]; then
    echo "ERROR: --gtdbtk-data is required when --run-gtdb is set" >&2
    errors=1
fi

if [[ "$RUN_GTDB" -eq 1 && -n "$GTDBTK_DATA" && ! -d "$GTDBTK_DATA" ]]; then
    echo "ERROR: --gtdbtk-data directory does not exist: $GTDBTK_DATA" >&2
    errors=1
fi

if [[ "$SKIP_CHECKM2" -eq 0 && ! -d "$CHECKM2_DB" ]]; then
    echo "WARNING: CheckM2 database not found at $CHECKM2_DB -- CheckM2 jobs may fail" >&2
fi

# Check required scripts exist
for script in build_carbapenemase_summary.py analyze_coverage_publication_fixed.py \
              run_mash_then_pling_by_group_v2.slurm; do
    if [[ ! -f "${SCRIPT_DIR}/${script}" ]]; then
        echo "ERROR: required script not found: ${SCRIPT_DIR}/${script}" >&2
        errors=1
    fi
done

if [[ "$RUN_GTDB" -eq 1 ]]; then
    TAXONOMY_SCRIPT="${SCRIPT_DIR}/run_taxonomy_mlst_hybrid.sh"
else
    TAXONOMY_SCRIPT="${SCRIPT_DIR}/run_taxonomy_mlst_only.sh"
fi
if [[ ! -f "$TAXONOMY_SCRIPT" ]]; then
    echo "ERROR: taxonomy script not found: $TAXONOMY_SCRIPT" >&2
    errors=1
fi

(( errors )) && exit 1

# Resolve paths
INPUT_DIR="$(cd "$INPUT_DIR" && pwd)"
[[ -z "$WORK_DIR" ]] && WORK_DIR="$(dirname "$INPUT_DIR")"
WORK_DIR="$(cd "$WORK_DIR" && pwd)"
[[ -z "$LOG_DIR" ]] && LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# =============================================================================
# Discover samples
# =============================================================================
shopt -s nullglob
FASTQ_FILES=("${INPUT_DIR}"/*.fastq "${INPUT_DIR}"/*.fastq.gz)
shopt -u nullglob

if [[ ${#FASTQ_FILES[@]} -eq 0 ]]; then
    echo "ERROR: no FASTQ files found in $INPUT_DIR" >&2
    exit 1
fi

# Build sample list: original filename -> stem (stripped of extension + _filtered/_merged)
declare -a SAMPLE_STEMS=()
declare -A STEM_TO_FILE=()

for f in "${FASTQ_FILES[@]}"; do
    bn="$(basename "$f")"
    stem="${bn%.fastq.gz}"
    stem="${stem%.fastq}"
    [[ "$stem" == *"_filtered" ]] && stem="${stem%_filtered}"
    [[ "$stem" == *"_merged"   ]] && stem="${stem%_merged}"
    SAMPLE_STEMS+=("$stem")
    STEM_TO_FILE["$stem"]="$f"
done

N_SAMPLES=${#SAMPLE_STEMS[@]}
N_COVERAGES=$(echo $COVERAGES | wc -w | tr -d ' ')

echo "================================================================"
echo "CRE Full Pipeline (per-sample jobs)"
echo "================================================================"
echo "Input:      $INPUT_DIR"
echo "Work dir:   $WORK_DIR"
echo "Log dir:    $LOG_DIR"
echo "Samples:    $N_SAMPLES"
echo "Coverages:  $COVERAGES ($N_COVERAGES levels)"
echo "Genome:     $GENOME_SIZE"
echo "Email:      $EMAIL"
echo "GTDB-Tk:    $(( RUN_GTDB ? 1 : 0 ))"
echo "Dry run:    $(( DRY_RUN ? 1 : 0 ))"
echo "================================================================"
echo "Total per-sample jobs: ~$(( N_SAMPLES * N_COVERAGES * 4 )) (rasusa+flye+medaka+annot)"
echo "================================================================"
echo

# =============================================================================
# Helper functions
# =============================================================================
DRY_COUNTER=0
declare -a ALL_JOB_IDS=()

# Job counters per step
declare -A STEP_COUNTS=()

submit_inline() {
    local job_name="$1"
    local dependency="$2"
    local mem="$3"
    local time="$4"
    local cpus="$5"
    local script_body="$6"

    local sbatch_args=(
        --parsable
        --job-name="${job_name}"
        --chdir="${WORK_DIR}"
        -p cpu_p -q cpu_normal   # Site-specific: adjust partition and QOS for your cluster
        --mem="${mem}" --time="${time}" -c "${cpus}"
        --nice=10000
        -o "${LOG_DIR}/%x_%j.out"
        -e "${LOG_DIR}/%x_%j.err"
        --mail-user="${EMAIL}" --mail-type=END,FAIL
    )

    if [[ -n "$dependency" ]]; then
        sbatch_args+=(--dependency="${dependency}")
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        DRY_COUNTER=$((DRY_COUNTER + 1))
        echo "DRY_${DRY_COUNTER}"
        return 0
    fi

    local job_id
    job_id=$(sbatch "${sbatch_args[@]}" <<< "$script_body")
    if [[ $? -ne 0 || -z "$job_id" ]]; then
        echo "ERROR: failed to submit job '${job_name}'" >&2
        exit 1
    fi
    ALL_JOB_IDS+=("$job_id")
    echo "$job_id"
}

submit_script() {
    local job_name="$1"
    local dependency="$2"
    local mem="$3"
    local time="$4"
    local cpus="$5"
    local script="$6"
    shift 6
    local extra_args=("$@")

    local sbatch_args=(
        --parsable
        --job-name="${job_name}"
        --chdir="${WORK_DIR}"
        -p cpu_p -q cpu_normal   # Site-specific: adjust partition and QOS for your cluster
        --mem="${mem}" --time="${time}" -c "${cpus}"
        --nice=10000
        -o "${LOG_DIR}/%x_%j.out"
        -e "${LOG_DIR}/%x_%j.err"
        --mail-user="${EMAIL}" --mail-type=END,FAIL
    )

    if [[ -n "$dependency" ]]; then
        sbatch_args+=(--dependency="${dependency}")
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        DRY_COUNTER=$((DRY_COUNTER + 1))
        echo "DRY_${DRY_COUNTER}"
        return 0
    fi

    local job_id
    job_id=$(sbatch "${sbatch_args[@]}" "${script}" "${extra_args[@]}")
    if [[ $? -ne 0 || -z "$job_id" ]]; then
        echo "ERROR: failed to submit job '${job_name}'" >&2
        exit 1
    fi
    ALL_JOB_IDS+=("$job_id")
    echo "$job_id"
}

build_dep_string() {
    local dep_type="$1"; shift
    local ids=("$@")
    if [[ ${#ids[@]} -eq 0 ]]; then echo ""; return; fi
    local dep="${dep_type}"
    for id in "${ids[@]}"; do dep="${dep}:${id}"; done
    echo "$dep"
}

# =============================================================================
# Per-sample pipeline: rasusa -> flye -> medaka -> annotation
# =============================================================================

# Collect job IDs for aggregation steps
declare -a ALL_MEDAKA_JIDS=()
declare -a ALL_ANNOT_JIDS=()
declare -a ALL_SUMMARY_JIDS=()

for cov in $COVERAGES; do
    cov_num="${cov%x}"

    echo "--- Coverage: ${cov} ---"
    MEDAKA_JIDS_THIS_COV=()
    ANNOT_JIDS_THIS_COV=()
    n_submitted=0

    for stem in "${SAMPLE_STEMS[@]}"; do
        orig_file="${STEM_TO_FILE[$stem]}"
        orig_bn="$(basename "$orig_file")"
        # Post-rasusa sample name: {stem}_{cov}
        rasusa_sample="${stem}_${cov}"

        # ---- Step 1: Rasusa (per sample, per coverage) ----
        rasusa_body="#!/bin/bash
set -euo pipefail

SEED=42
G=\"${GENOME_SIZE}\"
TARGET_COV=\"${cov_num}\"

# Parse genome size to bp
G_BP=\$(awk -v s=\"\$G\" 'BEGIN{
  unit=\"\"
  if (s ~ /[kK]\$/) unit=\"k\"
  else if (s ~ /[mM]\$/) unit=\"m\"
  else if (s ~ /[gG]\$/) unit=\"g\"
  g=s; sub(/[kKmMgG]\$/, \"\", g); val=g+0.0
  mult=(unit==\"k\"?1e3:(unit==\"m\"?1e6:(unit==\"g\"?1e9:1)))
  printf(\"%.0f\", val*mult)
}')

INPUT_FQ=\"${orig_file}\"
OUTDIR=\"${WORK_DIR}/${cov}\"
mkdir -p \"\$OUTDIR\"

# Decompress if gzipped
is_gz=0
if head -c2 \"\$INPUT_FQ\" 2>/dev/null | od -An -t x1 | tr -d ' \n' | grep -q '^1f8b\$'; then
  is_gz=1
fi

if [[ \$is_gz -eq 1 ]]; then
  tmpfq=\"\$(mktemp --suffix=.fastq)\"
  gzip -cd \"\$INPUT_FQ\" > \"\$tmpfq\"
  src=\"\$tmpfq\"
else
  src=\"\$INPUT_FQ\"
  tmpfq=\"\"
fi

# Count bases
bases=\$(awk 'NR%4==2{n+=length(\$0)} END{print n+0}' \"\$src\")

# Check coverage
if (( bases < TARGET_COV * G_BP )); then
  echo \"SKIP: ${stem} has \${bases} bases, need \$(( TARGET_COV * G_BP )) for ${cov}\"
  [[ -n \"\$tmpfq\" ]] && rm -f \"\$tmpfq\"
  exit 0
fi

# Subsample
OUT_FQ=\"\${OUTDIR}/${rasusa_sample}.fastq\"
rasusa reads -g \"\$G\" -c \"\$TARGET_COV\" -s \"\$SEED\" \"\$src\" > \"\$OUT_FQ\"
echo \"OK: ${stem} -> \$OUT_FQ\"

[[ -n \"\$tmpfq\" ]] && rm -f \"\$tmpfq\"
"
        rasusa_jid=$(submit_inline "rasusa_${stem}_${cov}" "" "8G" "02:00:00" "4" "$rasusa_body")

        # ---- Step 2: Flye (per sample, per coverage) ----
        flye_body="#!/bin/bash
set -euo pipefail
eval \"\$(micromamba shell hook --shell=bash)\"
micromamba activate assembly

THREADS=\${SLURM_CPUS_PER_TASK:-16}
FQ=\"${WORK_DIR}/${cov}/${rasusa_sample}.fastq\"
DRAFT_DIR=\"${WORK_DIR}/flye_${cov}/${rasusa_sample}_flye\"

if [[ ! -f \"\$FQ\" ]]; then
  echo \"SKIP: input FASTQ not found (sample was likely filtered by rasusa): \$FQ\"
  exit 0
fi

mkdir -p \"\$DRAFT_DIR\"

if [[ -s \"\${DRAFT_DIR}/assembly.fasta\" ]]; then
  echo \"SKIP: assembly already exists for ${rasusa_sample}\"
  exit 0
fi

flye --nano-hq \"\$FQ\" \\
     --out-dir \"\$DRAFT_DIR\" \\
     --genome-size \"${GENOME_SIZE}\" \\
     --threads \"\$THREADS\"

echo \"OK: Flye ${rasusa_sample}\"
"
        flye_jid=$(submit_inline "flye_${stem}_${cov}" "afterok:${rasusa_jid}" "32G" "12:00:00" "16" "$flye_body")

        # ---- Step 3: Medaka (per sample, per coverage) ----
        medaka_body="#!/bin/bash
set -euo pipefail
eval \"\$(micromamba shell hook --shell=bash)\"
micromamba activate assembly

THREADS=\${SLURM_CPUS_PER_TASK:-16}
MEDAKA_MODEL=\"\${MEDAKA_MODEL:-r1041_e82_400bps_bacterial_methylation}\"

FQ=\"${WORK_DIR}/${cov}/${rasusa_sample}.fastq\"
DRAFT=\"${WORK_DIR}/flye_${cov}/${rasusa_sample}_flye/assembly.fasta\"
POLISHED_DIR=\"${WORK_DIR}/polished_flye_${cov}/${rasusa_sample}_medaka\"
POLISHED_FASTA_DIR=\"${WORK_DIR}/polished_fasta_${cov}\"
FINAL=\"\${POLISHED_FASTA_DIR}/${rasusa_sample}.fasta\"

if [[ ! -f \"\$FQ\" ]]; then
  echo \"SKIP: reads not found (filtered by rasusa): \$FQ\"
  exit 0
fi

if [[ ! -s \"\$DRAFT\" ]]; then
  echo \"SKIP: Flye draft not found for ${rasusa_sample}: \$DRAFT\"
  exit 0
fi

mkdir -p \"\$POLISHED_DIR\" \"\$POLISHED_FASTA_DIR\"

if [[ -s \"\${POLISHED_DIR}/consensus.fasta\" ]]; then
  echo \"SKIP: polished assembly already exists for ${rasusa_sample}\"
else
  medaka_consensus \\
    -i \"\$FQ\" \\
    -d \"\$DRAFT\" \\
    -o \"\$POLISHED_DIR\" \\
    -t \"\$THREADS\" \\
    -m \"\$MEDAKA_MODEL\" \\
    > \"\${POLISHED_DIR}/medaka.log\" 2>&1
fi

if [[ -s \"\${POLISHED_DIR}/consensus.fasta\" ]]; then
  ln -sfn \"\$(realpath \"\${POLISHED_DIR}/consensus.fasta\")\" \"\$FINAL\"
  echo \"OK: Medaka ${rasusa_sample} -> \$FINAL\"
else
  echo \"FAIL: Medaka ${rasusa_sample}\"
  exit 1
fi
"
        medaka_jid=$(submit_inline "medaka_${stem}_${cov}" "afterok:${flye_jid}" "32G" "12:00:00" "16" "$medaka_body")
        MEDAKA_JIDS_THIS_COV+=("$medaka_jid")
        ALL_MEDAKA_JIDS+=("$medaka_jid")

        # ---- Step 4: CheckM2 (per sample, per coverage, optional) ----
        if [[ "$SKIP_CHECKM2" -eq 0 ]]; then
            checkm2_body="#!/bin/bash
set -euo pipefail
export CHECKM2DB=\"${CHECKM2_DB}\"
eval \"\$(micromamba shell hook --shell=bash)\"
micromamba activate checkm2_env

FASTA=\"${WORK_DIR}/polished_fasta_${cov}/${rasusa_sample}.fasta\"
OUTDIR=\"${WORK_DIR}/checkm2_${cov}/${rasusa_sample}\"

if [[ ! -f \"\$FASTA\" ]]; then
  echo \"SKIP: polished FASTA not found for ${rasusa_sample}\"
  exit 0
fi

mkdir -p \"\$OUTDIR\"
# CheckM2 needs a directory with FASTA files; create a temp symlink dir
TMPINPUT=\"\$(mktemp -d)\"
ln -s \"\$(realpath \"\$FASTA\")\" \"\${TMPINPUT}/${rasusa_sample}.fasta\"

checkm2 predict \\
    --threads \${SLURM_CPUS_PER_TASK:-8} \\
    --input \"\$TMPINPUT\" \\
    --output-directory \"\$OUTDIR\" \\
    --extension fasta \\
    --force

rm -rf \"\$TMPINPUT\"
echo \"OK: CheckM2 ${rasusa_sample}\"
"
            submit_inline "checkm2_${stem}_${cov}" "afterok:${medaka_jid}" "16G" "02:00:00" "8" "$checkm2_body" > /dev/null
            STEP_COUNTS[checkm2]=$(( ${STEP_COUNTS[checkm2]:-0} + 1 ))
        fi

        # ---- Step 5a: Annotation per sample (AMRFinder + MOBsuite) ----
        annot_body="#!/bin/bash
set -euo pipefail
eval \"\$(micromamba shell hook --shell=bash)\"

THREADS=\${SLURM_CPUS_PER_TASK:-8}
ASM=\"${WORK_DIR}/polished_fasta_${cov}/${rasusa_sample}.fasta\"
OUTROOT=\"${WORK_DIR}/annotation_${cov}\"
OUTDIR=\"\${OUTROOT}/${rasusa_sample}\"
AMRDIR=\"\${OUTDIR}/amrfinder\"
MOBDIR=\"\${OUTDIR}/mob_recon\"

if [[ ! -f \"\$ASM\" ]]; then
  echo \"SKIP: polished FASTA not found for ${rasusa_sample}\"
  exit 0
fi

mkdir -p \"\$OUTROOT\" \"\$OUTDIR\" \"\$AMRDIR\" \"\$MOBDIR\"

echo \"==> AMRFinder: ${rasusa_sample}\"
micromamba run -n amr_env amrfinder \\
  -n \"\$ASM\" \\
  --threads \"\$THREADS\" \\
  > \"\${AMRDIR}/${rasusa_sample}_assembly_amrfinder.tsv\" \\
  2> \"\${AMRDIR}/${rasusa_sample}_assembly_amrfinder.log\" || \\
  echo \"AMRFinder failed for ${rasusa_sample}\" >> \"\${OUTDIR}/pipeline_warnings.txt\"

echo \"==> MOBsuite: ${rasusa_sample}\"
micromamba run -n mobsuite_env mob_recon \\
  --infile \"\$ASM\" \\
  --outdir \"\$MOBDIR\" \\
  --force \\
  2>> \"\${OUTDIR}/pipeline_warnings.txt\" || \\
  echo \"MOB-recon failed for ${rasusa_sample}\" >> \"\${OUTDIR}/pipeline_warnings.txt\"

echo \"OK: Annotation ${rasusa_sample}\"
"
        annot_jid=$(submit_inline "annot_${stem}_${cov}" "afterok:${medaka_jid}" "16G" "04:00:00" "8" "$annot_body")
        ANNOT_JIDS_THIS_COV+=("$annot_jid")
        ALL_ANNOT_JIDS+=("$annot_jid")

        ((n_submitted++))
    done

    echo "  Submitted $n_submitted samples x 4 steps for ${cov}"

    # ---- Step 5b: Carbapenemase summary (per coverage, after ALL annotation jobs) ----
    ALL_ANNOT_DEP_COV=$(build_dep_string "afterok" "${ANNOT_JIDS_THIS_COV[@]}")
    summary_body="#!/bin/bash
set -euo pipefail

OUTROOT=\"${WORK_DIR}/annotation_${cov}\"
POLISHED_DIR=\"${WORK_DIR}/polished_fasta_${cov}\"
SUMMARY_DIR=\"\${OUTROOT}/summaries\"
CARB_DIR=\"\${OUTROOT}/carbapenemase_encoding_plasmids\"
mkdir -p \"\$SUMMARY_DIR\" \"\$CARB_DIR\"

python3 \"${SCRIPT_DIR}/build_carbapenemase_summary.py\" \\
  --annotation-root \"\$OUTROOT\" \\
  --assembly-root \"\$POLISHED_DIR\" \\
  --coverage \"${cov}\"

echo \"OK: Carbapenemase summary ${cov}\"
"
    summary_jid=$(submit_inline "carba_summary_${cov}" "$ALL_ANNOT_DEP_COV" "8G" "01:00:00" "4" "$summary_body")
    ALL_SUMMARY_JIDS+=("$summary_jid")
    echo "  Submitted carba_summary_${cov} (depends on ${#ANNOT_JIDS_THIS_COV[@]} annotation jobs)"
    echo

    # Track counts
    STEP_COUNTS[rasusa]=$(( ${STEP_COUNTS[rasusa]:-0} + n_submitted ))
    STEP_COUNTS[flye]=$(( ${STEP_COUNTS[flye]:-0} + n_submitted ))
    STEP_COUNTS[medaka]=$(( ${STEP_COUNTS[medaka]:-0} + n_submitted ))
    STEP_COUNTS[annotation]=$(( ${STEP_COUNTS[annotation]:-0} + n_submitted ))
    STEP_COUNTS[summary]=$(( ${STEP_COUNTS[summary]:-0} + 1 ))
done

# =============================================================================
# Step 6: Taxonomy & MLST (single job, depends on ALL medaka)
# =============================================================================
echo "--- Step 6: Taxonomy & MLST ---"
ALL_MEDAKA_DEP=$(build_dep_string "afterok" "${ALL_MEDAKA_JIDS[@]}")

local_export="ALL,INPUT_GLOB=polished_fasta_*,OUTROOT=taxonomy_mlst_results,RUN_GTDB=${RUN_GTDB}"
if [[ "$RUN_GTDB" -eq 1 ]]; then
    local_export="${local_export},GTDBTK_DATA_PATH=${GTDBTK_DATA}"
fi

mlst_body="#!/bin/bash
set -euo pipefail
export INPUT_GLOB=\"polished_fasta_*\"
export OUTROOT=\"taxonomy_mlst_results\"
export RUN_GTDB=\"${RUN_GTDB}\"
$(if [[ "$RUN_GTDB" -eq 1 ]]; then echo "export GTDBTK_DATA_PATH=\"${GTDBTK_DATA}\""; fi)

bash \"${TAXONOMY_SCRIPT}\"
"
MLST_JOB_ID=$(submit_inline "taxonomy_mlst" "$ALL_MEDAKA_DEP" "64G" "12:00:00" "16" "$mlst_body")
echo "  Submitted taxonomy_mlst (depends on ${#ALL_MEDAKA_JIDS[@]} medaka jobs)"
echo

# =============================================================================
# Step 7: Mash/PLING -- plasmid network (single job, depends on ALL summaries)
# =============================================================================
if [[ "$SKIP_PLING" -eq 0 ]]; then
    echo "--- Step 7: Mash/PLING (plasmid grouping & network) ---"
    ALL_SUMMARY_DEP=$(build_dep_string "afterok" "${ALL_SUMMARY_JIDS[@]}")

    mash_body="#!/bin/bash
set -euo pipefail
export ANNOT_GLOB=\"annotation_*\"
export MASH_THRESHOLD=\"${MASH_THRESHOLD}\"
export PLING_CONTAINMENT=\"${PLING_CONTAINMENT}\"
export THREADS=\${SLURM_CPUS_PER_TASK:-16}

bash \"${SCRIPT_DIR}/run_mash_then_pling_by_group_v2.slurm\"
"
    MASH_JOB_ID=$(submit_inline "mash_pling" "$ALL_SUMMARY_DEP" "64G" "24:00:00" "16" "$mash_body")
    echo "  Submitted mash_pling (depends on ${#ALL_SUMMARY_JIDS[@]} summary jobs)"
    echo
else
    echo "--- Step 7: Mash/PLING -- SKIPPED ---"
    echo
fi

# =============================================================================
# Step 8: Coverage sensitivity analysis (single job, depends on ALL summaries)
# =============================================================================
if [[ "$SKIP_COVERAGE_ANALYSIS" -eq 0 ]]; then
    echo "--- Step 8: Coverage sensitivity analysis ---"
    ALL_SUMMARY_DEP=$(build_dep_string "afterok" "${ALL_SUMMARY_JIDS[@]}")

    cov_analysis_body="#!/bin/bash
set -euo pipefail
eval \"\$(micromamba shell hook --shell=bash)\"
micromamba activate base

python3 \"${SCRIPT_DIR}/analyze_coverage_publication_fixed.py\" \\
    --summary-glob \"annotation_*/summaries/carbapenemase_summary_*.tsv\" \\
    --outdir coverage_publication_analysis

echo \"Coverage analysis complete\"
"
    COV_ANALYSIS_JID=$(submit_inline "cov_analysis" "$ALL_SUMMARY_DEP" "32G" "04:00:00" "16" "$cov_analysis_body")
    echo "  Submitted cov_analysis (depends on ${#ALL_SUMMARY_JIDS[@]} summary jobs)"
    echo
else
    echo "--- Step 8: Coverage analysis -- SKIPPED ---"
    echo
fi

# =============================================================================
# Summary
# =============================================================================
echo "================================================================"
echo "CRE Pipeline -- Job Submission Summary"
echo "================================================================"
printf "%-6s %-30s %s\n" "Step" "Description" "Jobs"
printf "%-6s %-30s %s\n" "----" "-----------" "----"
printf "%-6s %-30s %s\n" "1"    "Rasusa (per sample)"          "${STEP_COUNTS[rasusa]:-0}"
printf "%-6s %-30s %s\n" "2"    "Flye (per sample)"            "${STEP_COUNTS[flye]:-0}"
printf "%-6s %-30s %s\n" "3"    "Medaka (per sample)"          "${STEP_COUNTS[medaka]:-0}"
if [[ "$SKIP_CHECKM2" -eq 0 ]]; then
printf "%-6s %-30s %s\n" "4"    "CheckM2 (per sample)"         "${STEP_COUNTS[checkm2]:-0}"
else
printf "%-6s %-30s %s\n" "4"    "CheckM2"                      "SKIPPED"
fi
printf "%-6s %-30s %s\n" "5a"   "Annotation (per sample)"      "${STEP_COUNTS[annotation]:-0}"
printf "%-6s %-30s %s\n" "5b"   "Carbapenemase summary"        "${STEP_COUNTS[summary]:-0}"
printf "%-6s %-30s %s\n" "6"    "Taxonomy & MLST"              "1"
if [[ "$SKIP_PLING" -eq 0 ]]; then
printf "%-6s %-30s %s\n" "7"    "Mash/PLING"                   "1"
else
printf "%-6s %-30s %s\n" "7"    "Mash/PLING"                   "SKIPPED"
fi
if [[ "$SKIP_COVERAGE_ANALYSIS" -eq 0 ]]; then
printf "%-6s %-30s %s\n" "8"    "Coverage analysis"            "1"
else
printf "%-6s %-30s %s\n" "8"    "Coverage analysis"            "SKIPPED"
fi
echo "================================================================"
echo "Total SLURM jobs submitted: ${#ALL_JOB_IDS[@]}"
echo "================================================================"
echo
echo "Monitor:    squeue -u \$USER"
echo "Cancel all: scancel ${ALL_JOB_IDS[*]}"
echo
if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "(DRY RUN -- no jobs were actually submitted)"
fi
