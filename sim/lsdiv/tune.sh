#!/bin/bash
# usage: sim/lsdiv/tune.sh TAG RUNS JOBS K=V ...   (block a unless LS=b)
cd "$(dirname "$0")/../.."
tag=$1 runs=$2 jobs=$3; shift 3
args=(); for kv in "$@"; do args+=(--set "$kv"); done
python3 sim/lsdiv/lsdiv.py ring --runs "$runs" --blocks blk --ls "${LS:-a}" --jobs "$jobs" --tstop "${TSTOP:-0.6e-6}" --tag "$tag" "${args[@]}" > build/lsdiv/tune_$tag.log 2>&1
python3 sim/lsdiv/show.py build/lsdiv/ring_${runs}${tag}_${LS:-a}.json
