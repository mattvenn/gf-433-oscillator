#!/bin/bash
# Full ISF phase-noise sweep: variants x corners x temperatures, PAR cases at once, JOBS ngspice each.
# PAR x JOBS should be <= the CPU budget (sim pod: 28 -> PAR=7 JOBS=4).
# Usage (repo root): [M=60] [PAR=7] [JOBS=4] [OUT=build/pn] [VARIANTS="se diff cgm"] [CORNERS="typical ss ff sf fs"]
#                    [TEMPS=27] sim/pn/run_all.sh
M=${M:-60}; PAR=${PAR:-7}; JOBS=${JOBS:-4}; OUT=${OUT:-build/pn}
VARIANTS=${VARIANTS:-se diff cgm}; CORNERS=${CORNERS:-typical ss ff sf fs}; TEMPS=${TEMPS:-27}
cd "$(dirname "$0")/../.."
mkdir -p "$OUT"
for v in $VARIANTS; do for c in $CORNERS; do for t in $TEMPS; do echo "$v $c $t"; done; done; done |
  xargs -P "$PAR" -L 1 bash -c 'python3 sim/pn/isf.py "$0" --corner "$1" --temp "$2" --m '"$M"' --jobs '"$JOBS"' --out '"$OUT"' > '"$OUT"'/"$0"_"$1"_t"$2".out 2>&1; echo "$(date +%T) done $0 $1 $2: $(tail -1 '"$OUT"'/"$0"_"$1"_t"$2".out)"'
python3 sim/pn/summary.py "$OUT"
