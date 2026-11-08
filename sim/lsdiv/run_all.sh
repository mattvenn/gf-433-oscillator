#!/bin/bash
# main (5 corners x 27 C x codes 0/433.92/31) -> robust (ss/ff x 0/70 C x codes 0/31) -> VDD 3.15 V (ff 70 c0, ss 0 c31)
# each point with and without the block (c); 8 parallel ngspice. Status: build/lsdiv/status.txt
cd "$(dirname "$0")/../.."
st=build/lsdiv/status.txt
for r in main robust vdd; do
  echo "$(date +%T) start $r" >> $st
  python3 sim/lsdiv/lsdiv.py ring --runs $r --ls c --jobs 8 --tstop 1.2e-6 --worst "ff,70,0;ss,0,31" > build/lsdiv/run_$r.log 2>&1 || { echo FAILED $r >> $st; exit 1; }
  echo "$(date +%T) done $r" >> $st
done
python3 sim/lsdiv/summary.py build/lsdiv/ring_main_c.json build/lsdiv/ring_robust_c.json build/lsdiv/ring_vdd_c.json --div build/lsdiv/div.json > build/lsdiv/summary.log 2>&1
echo "$(date +%T) DONE" >> $st
