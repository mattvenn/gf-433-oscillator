#!/bin/bash
# Phase C driver (docs/handoff_rx_schematic.md): every chain job in parallel, one status line per finished job,
# DONE / FAILED at the end. Corners from the handoff's config: tt (the FSK, noise and real-LO runs are tt only).
# (p1db ran in the first pass, 2026-11-13 02:52, and is kept; the LO sources now carry full precision: the 6-digit
# pulse parameters made two breakpoints coincide at 15.26 us and every ideal-LO run stopped there.)
# Usage: bash sim/rx/run_chain.sh   (from the repo root; run with the Bash tool's run_in_background)
cd "$(dirname "$0")"
B=../../build/rx/chain; mkdir -p $B; rm -f $B/DONE $B/FAILED; ST=$B/status.txt
echo "start $(date +%H:%M)" > $ST
job() { local n=$1; shift; ( python3 rx_chain.py "$@" > $B/$n.log 2>&1; echo "$n exit $? $(date +%H:%M)" >> $ST ) & }
job fsk95 fsk --level -95 --tag chain
job fsk70 fsk --level -70 --tag chain
job noise noise --level -105 --nf 7.3 --nbits 3 --tstop 65e-6 --tag chain
job reallo reallo --level -70 --tstop 25e-6 --tag chain
job blocker blocker --tag chain
wait
fail=0
for n in fsk95 fsk70 noise reallo blocker; do
  grep -q '"error"\|Traceback' $B/$n.log && { echo "$n FAILED" >> $ST; fail=1; }
  grep -l 'singular\|Transient op started' $B/*/deck.log >> $ST 2>/dev/null
done
if [ $fail = 0 ]; then date > $B/DONE; else tail -5 $B/*.log > $B/FAILED; fi
