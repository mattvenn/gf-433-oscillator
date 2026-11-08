#!/bin/bash
# Re-map the 433.92 codes on the extracted core with the lsdiv load (docs/handoff_remap.md):
#   1/3 codes   : 5 corners x codes 0..31 at vctrl 1.65            (160 points)
#   2/3 fine    : per corner the 4 codes around 433.92 x vctrl 0 / 1.0 / 2.3 / 3.3   (80 points)
#   3/3 summary : sim/lsdiv/results/remap.md + remap.csv
# Each step checks its own outputs (row count, no "singular" / "Transient op started" in the decks' logs).
# Status: build/remap/status.txt; ends with build/remap/DONE or build/remap/FAILED (+ log tail).
# Usage (repo root): JOBS=8 bash sim/lsdiv/run_remap.sh
cd "$(dirname "$0")/../.."
J=${JOBS:-8}
D=build/remap; mkdir -p $D; rm -f $D/DONE $D/FAILED
st=$D/status.txt; : > $st
fail() { { echo "$(date +%T) FAILED $1"; tail -20 "$2"; } | tee -a $st > $D/FAILED; exit 1; }
check() {  # check <tag> <expected rows> <log>
  python3 - "$D/$1.json" "$2" <<'PY' || fail "$1: row check" "$3"
import json, sys
r = json.load(open(sys.argv[1]))["rows"]; n = int(sys.argv[2])
bad = [x for x in r if not x.get("f_a0") or x.get("warn")]
print(f"{len(r)} rows (want {n}), {len(bad)} bad"); sys.exit(0 if len(r) == n and not bad else 1)
PY
  if grep -l -E "singular|Transient op started" build/lsdiv/map$1_*/deck.log 2>/dev/null | head -3 | grep -q .; then
    fail "$1: singular / Transient op started in a deck log" "$3"; fi
}
step() {  # step <n> <tag> <rows> <args...>
  local n=$1 tag=$2 rows=$3; shift 3
  echo "$(date +%T) start $n/3 $tag" >> $st
  python3 sim/lsdiv/remap.py $tag --jobs $J "$@" > $D/run_$tag.log 2>&1 || fail "$tag: remap.py exit" $D/run_$tag.log
  check $tag $rows $D/run_$tag.log
  echo "$(date +%T) done $n/3 $tag" >> $st
}
step 1 codes 160
step 2 fine 80
echo "$(date +%T) start 3/3 summary" >> $st
python3 sim/lsdiv/remap.py summary > $D/summary.log 2>&1 || fail "summary" $D/summary.log
test -s sim/lsdiv/results/remap.md || fail "summary: no remap.md" $D/summary.log
echo "$(date +%T) done 3/3 summary" >> $st
date +%T > $D/DONE
