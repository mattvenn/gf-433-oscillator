#!/bin/bash
# v3 ring core checks with the xschem schematic as the LVS source (repo root, in the image or via tools/osic-mac):
#   1. netlist xschem/ring_core_v3.sch headless (xschem/gen/netlist.sh): the hierarchical ring_core_v3 subckt
#   2. check_v2.sh on the GDS: magic DRC, KLayout DRC (FEOL+BEOL), antenna, netgen LVS layout vs that netlist
#   3. cross-check: netgen xschem netlist vs layout/ref/ring_core_v3.spice (the old LVS source, kept for this only)
#   4. mutation: two broken copies of the xschem netlist (FC_3 m 8 -> 7; XTN0 gate bit0 -> bitb0) against the same
#      layout extraction must both FAIL, so a PASS in step 2 means something
# Usage: bash layout/gen/check_v3.sh [gds] [outdir]     defaults: layout/ring_core_v3.gds build/check/ring_core_v3
#   XSCH_SET=wfu=0.25,wff=0.25  regenerate the sheets at those settings first (into <outdir>/xsch_src) instead of
#                               using the committed xschem/ (for a GDS made at another width)
#   SKIP=klayout,antenna        passed to check_v2.sh
# Antenna passes on 0 violations; its 6 "feedback" entries are the MOS decap fingers (S = D = VSS, "device missing
# 1 terminal"), expected.
# Results: <outdir>/summary.txt (all steps; last line CHECK OK / CHECK FAIL), lvs.report, lvs_ref.report, lvs_mut*.report
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/ring_core_v3.gds}")
OUT=${2:-build/check/ring_core_v3}
mkdir -p "$OUT/xsch"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl

# ---- 1. schematic netlist ----
SCH=xschem
if [ -n "${XSCH_SET:-}" ]; then
  SCH=$OUT/xsch_src; rm -rf "$SCH"; mkdir -p "$SCH"; cp -r xschem/symbols "$SCH/"
  XSCH_OUT=$SCH XSCH_SET=$XSCH_SET python3 xschem/gen/all.py || { echo "xschem/gen/all.py failed"; exit 1; }
fi
NL=$(bash xschem/gen/netlist.sh "$SCH" "$OUT/xsch" ring_core_v3) || { echo "netlist failed: $NL"; exit 1; }
SRC=$OUT/xsch/ring_core_v3.spice

# ---- 2. DRC / antenna / LVS against the schematic ----
SRC_CELL=ring_core_v3 bash layout/gen/check_v2.sh "$GDS" ring_core "$SRC" "$OUT"
cd "$OUT"
log() { echo "$*" | tee -a summary.txt; }
log "== schematic: $SCH/ring_core_v3.sch${XSCH_SET:+ (XSCH_SET=$XSCH_SET)}; $NL"

lvs() {  # lvs <a> <cell_a> <b> <cell_b> <tag>  -> 0 if "match uniquely" with no property errors
  netgen -batch lvs "$1 $2" "$3 $4" $SETUP $5.report > $5.log 2>&1
  grep -q "Final result: Circuits match uniquely" $5.report && ! grep -qi "property errors" $5.report \
    && ! grep -qi "do not match" $5.report
}
why() { grep -E "Final result|roperty errors|do not match" $1.report | sort -u | tr '\n' ' '; }

# ---- 3. cross-check against the old exported source ----
if lvs "$SRC" ring_core_v3 "$REPO/layout/ref/ring_core_v3.spice" ring_core lvs_ref; then ref=PASS; else ref=FAIL; fi
log "== cross-check xschem vs layout/ref/ring_core_v3.spice ($(sed -n 2p $REPO/layout/ref/ring_core_v3.spice | cut -c3-)): $ref  [$(why lvs_ref)]"
grep -E "^ *(W|L|M|m|w|l) " lvs_ref.report | sort -u | head -6 | sed 's/^/    /' | tee -a summary.txt

# ---- 4. mutation tests (reuse the layout extraction from step 2) ----
mut_ok=1
mutate() {  # mutate <tag> <sed expr> <description>
  sed -e "$2" "$SRC" > xsch/$1.spice
  if cmp -s "$SRC" xsch/$1.spice; then log "== mutation $3: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs ring_core_lay.spice ring_core xsch/$1.spice ring_core_v3 $1; then
    log "== mutation $3: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $3: FAIL (expected)  [$(why $1)]"; fi
}
mutate lvs_mut_m   '/^XFC_3 /s/m=8$/m=7/'          "FC_3 m 8 -> 7"
mutate lvs_mut_net '/^XTN0 /s/ bit0 / bitb0 /'      "XTN0 gate bit0 -> bitb0"

lvs_ok=0; grep -q "^LVS PASS" summary.txt && lvs_ok=1
drc_ok=0; grep -q "^== magic DRC.*: count 0$" summary.txt && grep -q "^== KLayout DRC.*: count 0$" summary.txt && drc_ok=1
[[ ${SKIP:-} == *klayout* ]] && grep -q "^== magic DRC.*: count 0$" summary.txt && drc_ok=1
ant_ok=1; [[ ${SKIP:-} != *antenna* ]] && ! grep -q "^== antenna.*violations 0," summary.txt && ant_ok=0
log "CHECK $([ $lvs_ok$drc_ok$ant_ok$mut_ok = 1111 ] && echo OK || echo FAIL)  (LVS vs xschem $lvs_ok, DRC $drc_ok, antenna $ant_ok, mutations caught $mut_ok; cross-check vs ref $ref, informational)"
