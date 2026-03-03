#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Dorado aligner -> sorted + indexed BAM
# ============================================================

# ------------------------------------------------------------
# Tool paths (edit as needed)
# ------------------------------------------------------------
DORADO_BIN="${DORADO_BIN:-dorado}"
SAMTOOLS_BIN="${SAMTOOLS_BIN:-samtools}"

# ------------------------------------------------------------
# Input / output
# ------------------------------------------------------------
REF_FASTA="${REF_FASTA:-/path/to/reference.fasta}"
READS_BAM="${READS_BAM:-/path/to/reads.bam}"
ALN_BAM="${ALN_BAM:-/path/to/aligned.sorted.bam}"

# ------------------------------------------------------------
# Parameters
# ------------------------------------------------------------
THREADS=20

# ------------------------------------------------------------
# Prepare output directory
# ------------------------------------------------------------
mkdir -p "$(dirname "$ALN_BAM")"

# ------------------------------------------------------------
# Run
# ------------------------------------------------------------
"$DORADO_BIN" aligner "$REF_FASTA" "$READS_BAM" \
  | "$SAMTOOLS_BIN" sort -@ "$THREADS" -o "$ALN_BAM"

"$SAMTOOLS_BIN" index -@ "$THREADS" "$ALN_BAM"

 
  
