#!/bin/bash
# run_experiments.sh — Automate scheduling simulation across all algorithms,
# patron counts, and seeds for reproducible comparative data.

set -e

# Configuration
PATRON_COUNTS=(10 20 30 50)
SEEDS=(1 2 3 4 5)
SCHEDULERS=(0 1 2 3)                     # 0=FCFS, 1=SJF, 2=Priority, 3=MLFQ
SCHED_NAMES=("FCFS" "SJF" "PRIORITY" "MLFQ")
SWITCH_TIME=0                             # context-switch overhead (ms)

mkdir -p results

TOTAL=$(( ${#PATRON_COUNTS[@]} * ${#SEEDS[@]} * ${#SCHEDULERS[@]} ))
COUNT=0

echo "=== Allegra the Barman — Experiment Runner ==="
echo "Patron counts : ${PATRON_COUNTS[*]}"
echo "Seeds         : ${SEEDS[*]}"
echo "Schedulers    : ${SCHED_NAMES[*]}"
echo "Total runs    : $TOTAL"
echo "================================================"

for PATRONS in "${PATRON_COUNTS[@]}"; do
    for SCHED in "${SCHEDULERS[@]}"; do
        for SEED in "${SEEDS[@]}"; do
            COUNT=$((COUNT + 1))
            echo ""
            echo "[$COUNT/$TOTAL] ${SCHED_NAMES[$SCHED]} | patrons=$PATRONS | seed=$SEED"
            make run ARGS="$PATRONS $SCHED $SWITCH_TIME $SEED"
        done
    done
done

echo ""
echo "================================================"
echo "All $TOTAL runs complete. Results in results/"
echo "================================================"
ls -lh results/
