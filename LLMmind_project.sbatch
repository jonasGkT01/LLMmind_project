#!/bin/bash
#SBATCH --job-name=LLMmind
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=4G
#SBATCH --time=144:00:00
#SBATCH --output=logs/slurm/snakemake_%j.out
#SBATCH --error=logs/slurm/snakemake_%j.err

set -euo pipefail

mkdir -p logs/slurm

source ~/.bashrc

echo "Node: $(hostname)"
echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-unset}"
nvidia-smi

snakemake \
    --use-conda \
    --cores "${SLURM_CPUS_PER_TASK}" \
    --resources gpu=1 \
    --rerun-incomplete \
    --printshellcmds