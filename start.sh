#!/bin/bash

FILENAME=logs/$(date +"%Y%m%d%H%M").log 
echo "Starting 3pseatBot... log in $FILENAME"
touch $FILENAME
source ~/miniconda3/etc/profile.d/conda.sh
conda activate py36 && (python bot.py 2>&1 | tee $FILENAME) &