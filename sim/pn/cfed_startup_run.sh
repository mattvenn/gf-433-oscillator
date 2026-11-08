#!/bin/bash
# Driver for docs/handoff_cfed_startup_mc.md: 1 calibration (tt 27 C, code 0, 10 us ramp at two max steps: picks the
# step and the run length) -> 2 the 36 power-on runs -> 3 summary table + worst-case plots.
# Run from the repo root as ONE tracked background command (Bash tool run_in_background):
#   eval "$(grep GITHUB_TOKEN ~/.bashrc)"; export GITHUB_TOKEN; bash sim/pn/cfed_startup_run.sh
# Env: CSU_OUT (build/cfed_startup), CSU_JOBS (20), CSU_START (first step, to resume), CSU_NOPUSH=1, CSU_FAILTEST=1.
# Corner config: the block in the handoff, parsed below (MAIN_CORNERS / MAIN_TEMPS / ROBUST_CORNERS / ROBUST_TEMPS /
# CODES); the ramps are 10 us and 1 us.
set -u
cd "$(dirname "$0")/../.."
OUT=${CSU_OUT:-build/cfed_startup}
JOBS=${CSU_JOBS:-20}
START=${CSU_START:-1}
HANDOFF=docs/handoff_cfed_startup_mc.md
mkdir -p "$OUT/logs"; rm -f "$OUT/DONE" "$OUT/FAILED"
status() { echo "$(date '+%F %T') $*" | tee -a "$OUT/status.txt"; }
cfg() { grep -o "$1 = [^;#]*" "$HANDOFF" | head -1 | sed "s/$1 = //; s/ *$//"; }
MC=$(cfg MAIN_CORNERS); MT=$(cfg MAIN_TEMPS); RC=$(cfg ROBUST_CORNERS); RT=$(cfg ROBUST_TEMPS); CODES=$(cfg CODES)
PY="python3 sim/pn/cfed_startup.py --out $OUT --jobs $JOBS"
CASES=(--main-corners "$MC" --main-temps "$MT" --robust-corners "$RC" --robust-temps "$RT" --codes "$CODES" --ramps "10e-6 1e-6")

push_line() {
  [ -n "${CSU_NOPUSH:-}" ] && return 0
  python3 - "$HANDOFF" "$1" <<'PYEOF'
import sys; from pathlib import Path
f = Path(sys.argv[1]); ls = f.read_text().split("\n")
if ls[0].startswith("> "): ls[0] = "> " + sys.argv[2]
else: ls.insert(0, "> " + sys.argv[2]); ls.insert(1, "")
f.write_text("\n".join(ls))
PYEOF
  local cred=()
  [ -n "${GITHUB_TOKEN:-}" ] && cred=(-c "credential.helper=!f(){ echo username=x-access-token; echo password=\$GITHUB_TOKEN; }; f")
  { git commit -q -m "cfed start-up status: $1" -- "$HANDOFF" && git "${cred[@]}" pull -q --rebase --autostash \
      && git "${cred[@]}" push -q; } >> "$OUT/logs/push.log" 2>&1 || status "WARN status push failed: $1 (see logs/push.log)"
}

step() {   # step N name eta_min cmd...
  local n=$1 name=$2 eta=$3; shift 3
  [ "$n" -lt "$START" ] && { status "step $n/3 $name skipped (CSU_START=$START)"; return 0; }
  status "step $n/3 $name started (ETA $(date -d "+$eta min" +%H:%M))"
  push_line "Running: step $n/3 ($name) since $(date +%H:%M), ETA $(date -d "+$eta min" +%H:%M)"
  local log="$OUT/logs/step$n.log"
  : > "$log"
  for cmd in "$@"; do
    echo "## $cmd" >> "$log"
    if ! eval "$cmd" >> "$log" 2>&1 || grep -q "^FAIL\|^Traceback" "$log"; then
      status "step $n/3 $name FAILED"
      { echo "step $n/3 $name failed at $(date '+%F %T'): $cmd"; tail -30 "$log"; } > "$OUT/FAILED"
      push_line "Failed: step $n/3 ($name) at $(date +%H:%M), see build/cfed_startup/FAILED on the pod"
      exit 1
    fi
  done
  status "step $n/3 $name done"
}

T0=$(date +%s)
status "driver start (out $OUT, jobs $JOBS, start $START; corners main [$MC] x [$MT], robust [$RC] x [$RT], codes [$CODES])"
[ -z "$MC" ] || [ -z "$CODES" ] && { echo "config block not found in $HANDOFF" > "$OUT/FAILED"; status "FAILED: no config"; exit 1; }
if [ -n "${CSU_FAILTEST:-}" ]; then
  step 1 "calibration failtest" 1 "$PY run ${CASES[*]@Q}"       # no calib.json in a fresh out dir -> must fail
else
  step 1 "calibration" 40 "$PY calib"
fi
step 2 "36 power-on runs" "$(cat "$OUT/eta_min.txt" 2>/dev/null || echo 60)" "$PY run ${CASES[*]@Q}"
step 3 "summary" 2 "$PY summary"
status "all steps done in $(( ($(date +%s) - T0) / 60 )) min"
push_line "Running: sims done $(date +%H:%M), write-up in progress"
date '+%F %T' > "$OUT/DONE"
