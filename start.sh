#!/bin/bash

FILENAME=logs/$(date +"%Y%m%d%H%M").log 
echo "Starting 3pseatBot... log in $FILENAME"
mkdir -p logs
touch $FILENAME
#source ~/miniconda3/etc/profile.d/conda.sh
#conda activate py36 && python -u bot.py > $FILENAME &
python -u bot.py > $FILENAME 2>&1 &
