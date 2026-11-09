#!/bin/bash
# GF silicon factor driver (docs/handoff_gf_silicon_factor.md). Run from the repo root, inside the image:
#   JOBS=8 CORNERS="typical ss ff sf fs" bash sim/silicon_factor/run.sh
# Steps: 1 extract c -> 2 typical, all configs -> 3 other corners -> 4 extract rc + rc check -> 5 summary.
# Writes build/silicon_factor/status.txt per step, results.csv, and DONE or FAILED (with the log tail).
set -u
REPO=$(pwd); B=$REPO/build/silicon_factor; mkdir -p $B; cd $REPO
rm -f $B/DONE $B/FAILED
JOBS=${JOBS:-8}
CORNERS=${CORNERS:-"typical ss ff sf fs"}
CFGS=${CFGS:-"t161 t65 t33 t9 t5 t3 inv1x5 inv4x5"}   # longest first, so they start early
RC_CFGS=${RC_CFGS:-"inv1x5 t3"}
RES=$B/results.csv
step() { echo "$(date -Iseconds) step $1: $2" | tee -a $B/status.txt; }
fail() { { echo "FAILED at step $1: $2"; tail -30 $B/driver.log 2>/dev/null; } > $B/FAILED; step "$1" "FAILED"; exit 1; }
check_rows() {  # $1 step, $2 expected count, $3 grep pattern for the rows
  local n; n=$(grep -c "$3" $RES || true)
  [ "$n" -ge "$2" ] || fail "$1" "expected $2 rows matching '$3', got $n"
  if grep "$3" $RES | grep -vq ",ok$"; then step "$1" "WARNING: non-ok rows: $(grep "$3" $RES | grep -v ',ok$' | cut -d, -f1,5,6,14 | tr '\n' ' ')"; fi
  grep -l "singular\|Transient op started" $B/runs/*/ngspice.log 2>/dev/null | head -3 | sed 's/^/  log flag: /' | tee -a $B/status.txt
}
run_set() {  # $1 mode, $2 corners, $3 cfgs
  for c in $2; do for g in $3; do echo "$g $c $1"; done; done | \
    xargs -P $JOBS -L 1 sh -c 'python3 sim/silicon_factor/tb.py --cfg $0 --corner $1 --mode $2 >> '"$RES"
}
[ -f $RES ] || echo "cfg,clksel2,clksel,stages,corner,mode,temp,f_Hz,f_sd_pct,n_periods,vmin,vmax,runtime_s,status" > $RES

step 1/5 "extract c"
bash sim/silicon_factor/extract.sh c  >> $B/driver.log 2>&1 || fail 1/5 "extract c"

step 2/5 "typical, all configs (c)"
run_set c typical "$CFGS"
check_rows 2/5 $(echo $CFGS | wc -w) ",typical,c,"

OTHER=$(echo $CORNERS | tr ' ' '\n' | grep -v '^typical$' | tr '\n' ' ')
step 3/5 "corners: $OTHER (c)"
run_set c "$OTHER" "$CFGS"
check_rows 3/5 $(( $(echo $OTHER | wc -w) * $(echo $CFGS | wc -w) )) ",\(ss\|ff\|sf\|fs\),c,"

step 4/5 "extract rc + rc check, typical: $RC_CFGS"
bash sim/silicon_factor/extract.sh rc >> $B/driver.log 2>&1 || fail 4/5 "extract rc"
run_set rc typical "$RC_CFGS"
check_rows 4/5 $(echo $RC_CFGS | wc -w) ",typical,rc,"

step 5/5 "summary"
python3 sim/silicon_factor/summary.py > $B/summary.md 2>>$B/driver.log || fail 5/5 "summary"
cp $B/summary.md sim/silicon_factor/results.md; cp $RES sim/silicon_factor/results.csv
date -Iseconds > $B/DONE; step 5/5 "DONE"
