#!/bin/bash
# Full ISF phase-noise sweep: 3 variants x 5 corners at 27 C, PAR cases at once, JOBS ngspice each.
# PAR x JOBS should be <= the CPU count (sim pod: 28 -> PAR=7 JOBS=4).
# Usage (repo root): sim/pn/run_all.sh [M=60] [PAR=7] [JOBS=4] [OUT=build/pn]
M=${M:-60}; PAR=${PAR:-7}; JOBS=${JOBS:-4}; OUT=${OUT:-build/pn}
cd "$(dirname "$0")/../.."
mkdir -p "$OUT"
for v in se diff cgm; do for c in typical ss ff sf fs; do echo "$v $c"; done; done |
  xargs -P "$PAR" -L 1 bash -c 'python3 sim/pn/isf.py "$0" --corner "$1" --m '"$M"' --jobs '"$JOBS"' --out '"$OUT"' > '"$OUT"'/"$0"_"$1".out 2>&1; echo "done $0 $1: $(tail -1 '"$OUT"'/"$0"_"$1".out)"'
python3 sim/pn/summary.py "$OUT"
