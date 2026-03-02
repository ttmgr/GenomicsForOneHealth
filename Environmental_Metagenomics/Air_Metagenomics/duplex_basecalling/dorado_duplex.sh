#!/usr/bin/env bash

# Define the absolute path to the configuration file, with fallback
CONFIG_FILE="${CONFIG_FILE:-dna_r10.4.1_e8.2_400bps_hac@v4.3.0}"
INPUT_DIR="${INPUT_DIR:-/path/to/raw/data/}"
DORADO_BIN="${DORADO_BIN:-dorado}"

# Step 1: Run dorado basecaller
echo "Running dorado basecaller..."
${DORADO_BIN} duplex ${CONFIG_FILE} -r "${INPUT_DIR}" > basecalled_duplex.bam -t 2

# Check if basecalling was successful
if [ $? -ne 0 ]; then
    echo "Error in basecalling step."
    exit 1
fi

echo "Process completed successfully."

