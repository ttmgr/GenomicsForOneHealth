#!/usr/bin/env bash
set -e

echo "========================================="
echo " Listeria Adaptive Sampling Pipeline"
echo " Interactive Launcher"
echo "========================================="

# 1. Environment Check
echo "Checking environment..."
if [[ "$CONDA_DEFAULT_ENV" != "listeria_as" ]]; then
    echo "Warning: You are not in the 'listeria_as' conda environment."
    echo "We recommend running: mamba activate listeria_as"
    read -p "Press Enter to continue anyway or Ctrl+C to abort..."
fi

# 2. Path Prompts
echo ""
read -p "Please provide the absolute path to your folder containing BAM files: " user_bam
read -p "Please provide the absolute path to your working directory [Default: $(pwd)]: " user_work

user_work=${user_work:-$(pwd)}

# 3. Validation Pre-flight Check
echo ""
echo "Running pre-flight checks..."

if [ ! -d "$user_bam" ]; then
    echo "Error: The BAM directory '$user_bam' does not exist. Please check the path and try again."
    exit 1
fi

if [ ! -d "$user_work" ]; then
    echo "Error: The Working directory '$user_work' does not exist."
    exit 1
fi

COUNT=$(ls -1 "$user_bam"/*.bam 2>/dev/null | grep -v '\.sorted\.bam$' | wc -l || true)
if [ "$COUNT" -eq 0 ]; then
    echo "Error: No raw .bam files were found in '$user_bam'."
    exit 1
fi
echo "[OK] Found $COUNT BAM files to process."

# 4. Execution
export BAM_DIR="$user_bam"
export WORK_DIR="$user_work"

echo ""
echo "All checks passed. Passing paths to the pipeline orchestrator..."
cd "$WORK_DIR" && bash scripts/submit_pipeline.sh

 
  
 
