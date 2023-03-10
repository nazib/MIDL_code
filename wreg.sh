#!/usr/bin/env bash
#PBS -N wreg_att
#PBS -l ncpus=1
#PBS -l mem=64GB
#PBS -l ngpus=1
#PBS -l gputype=A100
#PBS -l walltime=22:00:00
#PBS -o wreg.out
#PBS -e wreg_err.out

module load cuda/11.3.1
export CUDA_VISIBLE_DEVICES=0
source /home/nazib/miniconda3/etc/profile.d/conda.sh
conda activate medical
cd ~/Medical/MIDL_code
python train.py --model_name Wreg_attn_raw --loss Wreg --isprob yes