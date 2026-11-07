#!/bin/bash
# run inside the image: run_tn.sh <mode> <seed>  -> build/vacask/tn_<mode>_s<seed>/tn.raw
set -e
cd "$(dirname "$0")/../../build/vacask"; d=tn_$1_s$2; mkdir -p $d; cd $d
python3 ../../../sim/vacask/se_vacask.py se.sim --mode $1 --vbp 0.21738 --control ../../../sim/vacask/ctl_tn$2.txt
/usr/bin/time -f "%e s" vacask -qp se.sim > log.txt 2>&1
