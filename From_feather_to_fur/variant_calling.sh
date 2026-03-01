#!/bin/bash

#SBATCH -p gpu_p
#SBATCH -q gpu_normal
#SBATCH --mem=128G
#SBATCH -t 24:00:00
#SBATCH --nice=10000
#SBATCH --gres=gpu:2
#SBATCH --job-name=avian_influenza_variant_call
#SBATCH -c 8

# Define paths using positional parameters
REFERENCE=$1        # Path to the reference genome
READS=$2            # Path to the raw reads file
OUTPUT_DIR=$3       # Output directory for results
CLAIR3_MODEL=$4     # Path to the specific Clair3 model

# Check if all required arguments are provided
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <REFERENCE> <READS> <OUTPUT_DIR> <CLAIR3_MODEL>"
    exit 1
fi

# Step 1: Filtering reads by quality and length with Filtlong
echo "Running Filtlong to filter reads by quality and length..."
filtlong --min_mean_q 8 --min_length 150 $READS > ${OUTPUT_DIR}/temp_filtered.fastq

# Step 2: Removing adapters with Porechop
echo "Running Porechop to remove adapters..."
porechop -i ${OUTPUT_DIR}/temp_filtered.fastq -o ${OUTPUT_DIR}/cleaned_reads.fastq

# Clean up the temporary file
rm ${OUTPUT_DIR}/temp_filtered.fastq

# Step 3: Mapping cleaned reads to the reference genome with minimap2
echo "Mapping reads with minimap2..."
minimap2 -ax map-ont $REFERENCE $OUTPUT_DIR/cleaned_reads.fastq | samtools view -Sb - > $OUTPUT_DIR/mapped.bam

# Step 4: Sorting and indexing the BAM file
echo "Sorting BAM file..."
samtools sort -o $OUTPUT_DIR/mapped_sorted.bam $OUTPUT_DIR/mapped.bam
samtools index $OUTPUT_DIR/mapped_sorted.bam

# Step 5: Running Clair3 for variant calling with GPU
echo "Running Clair3 for variant calling with GPU support..."

run_clair3.sh \
  --bam_fn=${OUTPUT_DIR}/mapped_sorted.bam \
  --ref_fn=${REFERENCE} \
  --threads=8 \
  --platform="ont" \
  --model_path=${CLAIR3_MODEL} \
  --output=${OUTPUT_DIR}/clair3_output \
  --include_all_ctgs

# Final message
echo "Pipeline complete. Results are in $OUTPUT_DIR."


#Extra, needs to modify -> use bcftools to generate a readable file with the variants always from merge_output 

bcftools view merge_output.vcf.gz > all_variants.vcf
