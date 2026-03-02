!/bin/bash

#SBATCH -p gpu_p
#SBATCH -q gpu_normal
#SBATCH --gres=gpu:2
#SBATCH --job-name=process_vcf
#SBATCH --output=process_vcf_%j.log
#SBATCH --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --mem=4G

# Load Python module if necessary
module load python/3.x  # Load Python module depending on your cluster environment

# Arguments passed to the script
ANIMAL_VCF=$1
INOCULUM_VCF=$2
OUTPUT_EXCEL=$3
OUTPUT_VCF=$4

# Run the Python script with the provided arguments
python3 process_vcf.py --animal "$ANIMAL_VCF" --inoculum "$INOCULUM_VCF" \
       --output_excel "$OUTPUT_EXCEL" --output_vcf "$OUTPUT_VCF"
