#!/usr/bin/env bash
set -e

echo "========================================="
echo " AMR Nanopore Pipeline"
echo " Interactive Launcher"
echo "========================================="

# 1. Environment Check
echo "Checking environment dependencies..."
for cmd in guppy_basecaller porechop NanoFilt flye minimap2 racon; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Warning: Required tool '$cmd' is not in your PATH."
        MISSING_TOOLS=1
    fi
done

if [ "$MISSING_TOOLS" = "1" ]; then
    echo "This pipeline requires several conda environments or tools to be active."
    read -p "Press Enter to continue anyway, or Ctrl+C to abort..."
fi

# 2. Path Prompts
echo ""
read -p "Are you starting from raw FAST5/POD5 (1) or Basecalled FASTQ (2)? Enter 1 or 2: " START_TYPE

if [ "$START_TYPE" = "1" ]; then
    read -p "Please provide the absolute path to your raw input directory: " INPUT_DIR
    if [ ! -d "$INPUT_DIR" ]; then echo "Error: $INPUT_DIR not found"; exit 1; fi
else
    read -p "Please provide the absolute path to your basecalled FASTQ file: " FASTQ_IN
    if [ ! -f "$FASTQ_IN" ]; then echo "Error: $FASTQ_IN not found"; exit 1; fi
fi

read -p "Please provide the absolute path for the output directory [Default: $(pwd)/results]: " OUT_DIR
OUT_DIR=${OUT_DIR:-"$(pwd)/results"}
mkdir -p "$OUT_DIR"

# 3. Execution
echo ""
echo "Starting AMR Nanopore Pipeline..."

if [ "$START_TYPE" = "1" ]; then
    echo "--- 1. Basecalling (Guppy) ---"
    B_OUT="$OUT_DIR/basecalled"
    mkdir -p "$B_OUT"
    guppy_basecaller -i "$INPUT_DIR" -s "$B_OUT" --config dna_r9.4.1_450bps_hac.cfg || echo "Basecalling failed/skipped."
    FASTQ_IN="$B_OUT/pass/*.fastq" # Simplification for downstream, may need cat
    cat $FASTQ_IN > "$OUT_DIR/all_basecalled.fastq" 2>/dev/null || true
    FASTQ_IN="$OUT_DIR/all_basecalled.fastq"
fi

echo "--- 2. Trimming (Porechop) ---"
TRIMMED="$OUT_DIR/trimmed.fastq"
porechop -i "$FASTQ_IN" -o "$TRIMMED" || cp "$FASTQ_IN" "$TRIMMED"

echo "--- 3. Filtering (NanoFilt) ---"
FILTERED="$OUT_DIR/filtered.fastq"
cat "$TRIMMED" | NanoFilt -q 9 -l 200 > "$FILTERED" || cp "$TRIMMED" "$FILTERED"

echo "--- 4. Assembly (Flye) ---"
FLYE_DIR="$OUT_DIR/flye"
flye --nano-hq "$FILTERED" --out-dir "$FLYE_DIR" || echo "Assembly failed."

echo "--- 5. Alignment (Minimap2) ---"
ASM="$FLYE_DIR/assembly.fasta"
ALN="$OUT_DIR/alignment.sorted.bam"
if command -v minimap2 &> /dev/null && command -v samtools &> /dev/null && [ -f "$ASM" ]; then
    minimap2 -ax map-ont "$ASM" "$FILTERED" | samtools sort -o "$ALN"
fi

echo "--- 6. Polishing (Racon) ---"
POL="$OUT_DIR/assembly.polished.fasta"
if command -v racon &> /dev/null && [ -f "$ASM" ] && [ -f "$ALN" ]; then
    racon "$FILTERED" "$ALN" "$ASM" > "$POL"
fi

echo "========================================="
echo " Pipeline Complete."
echo " Output saved to: $OUT_DIR"
echo "========================================="

 
  
 
