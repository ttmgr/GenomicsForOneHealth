#!/usr/bin/env bash
set -e

echo "========================================="
echo " CRE Plasmid Clustering Pipeline"
echo " Interactive Launcher"
echo "========================================="

# 1. Environment Check
echo "Checking environment dependencies..."
for cmd in flye medaka_consensus mob_recon amrfinder mash pling porechop NanoFilt seqkit samtools minimap2; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Warning: Required tool '$cmd' is not in your PATH."
        MISSING_TOOLS=1
    fi
done

if [ "$MISSING_TOOLS" = "1" ]; then
    echo "This pipeline requires several conda environments or tools to be active."
    read -p "Press Enter to continue anyway, or Ctrl+C to abort and check dependencies..."
fi

# 2. Path Prompts
echo ""
read -p "Are you starting from raw POD5 signals (1) or demultiplexed FASTQs (2)? Enter 1 or 2: " START_TYPE

if [ "$START_TYPE" = "1" ]; then
    read -p "Please provide the absolute path to your Dorado binary [Default: dorado]: " DORADO_BIN
    DORADO_BIN=${DORADO_BIN:-dorado}
    read -p "Please provide the absolute path to your POD5 input directory: " INPUT_DIR
    read -p "Please provide the absolute path to your Dorado model (e.g. dna_r10.4.1_e8.2_400bps_sup@v5.0.0): " CONFIG_FILE
    
    if [ ! -d "$INPUT_DIR" ]; then
        echo "Error: POD5 directory '$INPUT_DIR' does not exist."
        exit 1
    fi
else
    read -p "Please provide the absolute path to your directory containing demultiplexed FASTQs: " DEMUX_DIR
    if [ ! -d "$DEMUX_DIR" ]; then
        echo "Error: FASTQ directory '$DEMUX_DIR' does not exist."
        exit 1
    fi
    INPUT_DIR="$DEMUX_DIR" # Just to store the root project path
fi

read -p "Please provide the absolute path for the output directory [Default: $(pwd)/results]: " OUTDIR
OUTDIR=${OUTDIR:-"$(pwd)/results"}
mkdir -p "$OUTDIR"

read -p "How many CPU threads should be used? [Default: 8]: " THREADS
THREADS=${THREADS:-8}

# 3. Execution
echo ""
echo "Starting Pipeline execution..."

if [ "$START_TYPE" = "1" ]; then
    echo "--- 1. Basecalling & Demultiplexing ---"
    KIT="SQK-RBK114-24" # Default from README
    mkdir -p "$OUTDIR/demux"
    
    "$DORADO_BIN" basecaller "$CONFIG_FILE" "$INPUT_DIR" \
      --emit-fastq --kit-name "$KIT" -r --no-trim \
      > "$OUTDIR/basecalled.fastq"
      
    "$DORADO_BIN" demux \
      --output-dir "$OUTDIR/demux" \
      --emit-fastq --kit-name "$KIT" \
      "$OUTDIR/basecalled.fastq"
      
    DEMUX_DIR="$OUTDIR/demux"
fi

echo "--- 2. Trimming & Filtering & Statistics ---"
PC_DIR="$OUTDIR/porechop"
NF_DIR="$OUTDIR/filtered_reads"
STATS_DIR="$OUTDIR/stats"
mkdir -p "$PC_DIR" "$NF_DIR" "$STATS_DIR"

# Try to find exactly what barcode formats we have
for fq in "$DEMUX_DIR"/*.f*q*; do
    [[ -e "$fq" ]] || continue
    bc=$(basename "$fq" | sed -E 's/\..+//') # extract filename without extension
    
    in="$fq"
    trim="$PC_DIR/trimmed_${bc}.fastq"
    out="$NF_DIR/filtered_${bc}.fastq"
    
    if command -v porechop &> /dev/null && command -v NanoFilt &> /dev/null; then
        porechop -i "$in" -o "$trim"
        NanoFilt -q 8 -l 200 < "$trim" > "$out"
        rm -f "$trim"
    else
        echo "Skipping Trim/Filter because porechop/NanoFilt are missing. Copying reads..."
        cp "$in" "$out"
    fi
    
    if command -v seqkit &> /dev/null; then
        seqkit stats -T -a "$out" > "$STATS_DIR/${bc}.txt"
    fi
done

echo "--- 3. Assembly (Flye) ---"
FLY_DIR="$OUTDIR/flye"
mkdir -p "$FLY_DIR"

for reads in "$NF_DIR"/*.fastq; do
    [[ -e "$reads" ]] || continue
    bc=$(basename "$reads" .fastq | sed 's/filtered_//')
    
    flye --nano-hq "$reads" --out-dir "$FLY_DIR/${bc}" --threads "$THREADS"
done

echo "--- 4. Polishing (Medaka) ---"
MEDAKA_DIR="$OUTDIR/medaka"
mkdir -p "$MEDAKA_DIR"

for reads in "$NF_DIR"/*.fastq; do
    [[ -e "$reads" ]] || continue
    bc=$(basename "$reads" .fastq | sed 's/filtered_//')
    asm="$FLY_DIR/${bc}/assembly.fasta"
    
    if [ -f "$asm" ]; then
        medaka_consensus -i "$reads" -d "$asm" -o "$MEDAKA_DIR/${bc}" -t "$THREADS" --bacteria
    else
        echo "Warning: No assembly found for ${bc}. Skipping Medaka."
    fi
done

echo "--- 5. Plasmid Typing (MOB-Suite) & AMR (AMRFinderPlus) ---"
MOB_DIR="$OUTDIR/mob"
AMR_DIR="$OUTDIR/amr"
mkdir -p "$MOB_DIR" "$AMR_DIR"

for bc_dir in "$MEDAKA_DIR"/*; do
    [[ -d "$bc_dir" ]] || continue
    bc=$(basename "$bc_dir")
    cns="$bc_dir/consensus.fasta"
    
    if [ -s "$cns" ]; then
        echo "Running MOB-suite for $bc..."
        mob_recon --infile "$cns" --outdir "$MOB_DIR/${bc}" || true
        
        echo "Running AMRFinderPlus for $bc..."
        amrfinder -n "$cns" -o "$AMR_DIR/${bc}.amr.txt" --threads "$THREADS" --plus || true
    fi
done

echo "========================================="
echo " Pipeline Complete."
echo " Output saved to: $OUTDIR"
echo " Note: See the README.md if you wish to run manual plasmid clustering with Mash/Pling."
echo "========================================="
