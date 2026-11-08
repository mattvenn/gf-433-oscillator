#!/bin/bash
# Driver for docs/handoff_cfed_sizing.md: Job 1 (null, check, pick) -> Job 2 (map) -> Job 3 (noise) -> summary.
# Run from the repo root as ONE tracked background command (Bash tool run_in_background), e.g.
#   eval "$(grep GITHUB_TOKEN ~/.bashrc)"; bash sim/pn/cfed_sizing_run.sh
# Env: CFS_OUT (build/cfed_sizing), CFS_JOBS (20 CPUs), CFS_START (first step, 1-4, to resume after a failure),
#      CFS_NOPUSH=1 (no status commits), CFS_FAILTEST=1 (step 1 reads a missing file: must end in FAILED).
# Each step writes <out>/status.txt lines, logs to <out>/logs/step<N>.log, and checks its own outputs (cfed_sizing.py
# exits 1 on missing rows / "singular" / "Transient op started"). On failure: <out>/FAILED with the log tail, stop.
# At each step change the "> Running: step N/4 since HH:MM, ETA HH:MM" line at the top of the handoff is committed
# and pushed (GITHUB_TOKEN from the environment, never stored).
set -u
cd "$(dirname "$0")/../.."
OUT=${CFS_OUT:-build/cfed_sizing}
JOBS=${CFS_JOBS:-20}
START=${CFS_START:-1}
HANDOFF=docs/handoff_cfed_sizing.md
PY="python3 sim/pn/cfed_sizing.py --out $OUT --jobs $JOBS"
EST=(0 70 15 15 1)                       # minutes per step (estimates; for the ETA line)
mkdir -p "$OUT/logs"; rm -f "$OUT/DONE" "$OUT/FAILED"
status() { echo "$(date '+%F %T') $*" | tee -a "$OUT/status.txt"; }

push_line() {   # $1 = the status line (without "> ")
  [ -n "${CFS_NOPUSH:-}" ] && return 0
  python3 - "$HANDOFF" "$1" <<'EOF'
import sys; from pathlib import Path
f = Path(sys.argv[1]); ls = f.read_text().split("\n")
if ls[0].startswith("> "): ls[0] = "> " + sys.argv[2]
else: ls.insert(0, "> " + sys.argv[2]); ls.insert(1, "")
f.write_text("\n".join(ls))
EOF
  local cred=()
  [ -n "${GITHUB_TOKEN:-}" ] && cred=(-c "credential.helper=!f(){ echo username=x-access-token; echo password=\$GITHUB_TOKEN; }; f")
  { git commit -q -m "cfed sizing status: $1" -- "$HANDOFF" && git "${cred[@]}" pull -q --rebase --autostash \
      && git "${cred[@]}" push -q; } >> "$OUT/logs/push.log" 2>&1 || status "WARN status push failed: $1 (see logs/push.log)"
}

eta() {   # ETA of the whole run from the start of step $1
  local m=0; for ((i = $1; i <= 4; i++)); do m=$((m + EST[i])); done; date -d "+$m min" +%H:%M
}

step() {   # step N name cmd...
  local n=$1 name=$2; shift 2
  [ "$n" -lt "$START" ] && { status "step $n/4 $name skipped (CFS_START=$START)"; return 0; }
  status "step $n/4 $name started"
  push_line "Running: step $n/4 ($name) since $(date +%H:%M), ETA $(eta "$n")"
  local log="$OUT/logs/step$n.log"
  : > "$log"
  for cmd in "$@"; do
    echo "## $cmd" >> "$log"
    if ! bash -c "$cmd" >> "$log" 2>&1 || grep -q "^FAIL\|^Traceback" "$log"; then
      status "step $n/4 $name FAILED"
      { echo "step $n/4 $name failed at $(date '+%F %T'): $cmd"; tail -30 "$log"; } > "$OUT/FAILED"
      push_line "Failed: step $n/4 ($name) at $(date +%H:%M), see build/cfed_sizing/FAILED on the pod"
      exit 1
    fi
  done
  status "step $n/4 $name done"
}

T0=$(date +%s)
status "driver start (out $OUT, jobs $JOBS, start step $START)"
if [ -n "${CFS_FAILTEST:-}" ]; then
  step 1 "job1 failtest" "$PY pick"            # no check.json in a fresh out dir -> must fail
else
  step 1 "job1 null+check+pick" "$PY null --iters 8" "$PY check" "$PY pick"
fi
step 2 "job2 map" "$PY map"
step 3 "job3 noise" "$PY noise --m 80"
step 4 "summary" "$PY summary"
status "all steps done in $(( ($(date +%s) - T0) / 60 )) min"
push_line "Running: sims done $(date +%H:%M), write-up in progress"
date '+%F %T' > "$OUT/DONE"
