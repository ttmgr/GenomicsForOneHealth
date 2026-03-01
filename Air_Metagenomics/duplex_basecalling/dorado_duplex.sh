# Define the absolute path to the configuration file
CONFIG_FILE="/home/YOUR_USERNAME/dorado/dorado-0.5.0-linux-x64/bin/dna_r10.4.1_e8.2_400bps_hac@v4.3.0"

# Step 1: Run dorado basecaller
echo "Running dorado basecaller..."
${DORADO_BIN} duplex  ${CONFIG_FILE} -r /path/to/hpc/backup/barcelona_air/valle_dhebron/ > basecalled_duplex.bam -t 2

# Check if basecalling was successful
if [ $? -ne 0 ]; then
    echo "Error in basecalling step."
    exit 1
fi

echo "Process completed successfully."
