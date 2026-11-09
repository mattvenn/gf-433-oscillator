#!/bin/bash
# tx_drv (dipole TX driver) checks with the xschem schematic as the LVS source (repo root, in the image):
#   1. netlist xschem/tx_drv.sch headless (xschem/gen/netlist.sh) -> <outdir>/xsch/tx_drv.spice (hierarchical:
#      tx_split, tx_arm x 2, the decap DC; netgen flattens it against the flat layout)
#   2. check_v2.sh on the GDS: magic DRC, KLayout DRC (FEOL + BEOL; the summary shows the rules that ran),
#      antenna, netgen LVS layout vs the schematic
#   3. mutation: three broken copies of the LVS source against the same extraction must all FAIL:
#      XM5n W 8 -> 7.2 (tx_arm), XTGn gate VDD -> VSS (tx_split), XDC m 24 -> 23 (top)
# Usage: bash layout/gen/check_tx.sh [gds] [outdir]     defaults: layout/tx_drv.gds build/check/tx_drv
#   SKIP=klayout,antenna   passed to check_v2.sh
# Results: <outdir>/summary.txt (last line CHECK OK / CHECK FAIL), lvs.report, lvs_mut*.report
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/tx_drv.gds}")
OUT=${2:-build/check/tx_drv}
mkdir -p "$OUT/xsch"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl

NL=$(bash xschem/gen/netlist.sh xschem "$OUT/xsch" tx_drv) || { echo "netlist failed: $NL"; exit 1; }
SRC=$OUT/xsch/tx_drv_lvs.spice
sed -e ':a;N;$!ba;s/\n+/ /g' "$OUT/xsch/tx_drv.spice" > "$SRC"     # one line per device (for the mutations)

bash layout/gen/check_v2.sh "$GDS" tx_drv "$SRC" "$OUT"
cd "$OUT"
log() { echo "$*" | tee -a summary.txt; }
log "== schematic: xschem/tx_drv.sch; $NL"

lvs() {
  netgen -batch lvs "$1 $2" "$3 $4" $SETUP $5.report > $5.log 2>&1
  grep -q "Final result: Circuits match uniquely" $5.report && ! grep -qi "property errors" $5.report \
    && ! grep -qi "do not match" $5.report
}
why() { grep -E "Final result|roperty errors|do not match" $1.report | sort -u | tr '\n' ' '; }
mut_ok=1
mutate() {
  sed -e "$2" "$SRC" > xsch/$1.spice
  if cmp -s "$SRC" xsch/$1.spice; then log "== mutation $3: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs tx_drv_lay.spice tx_drv xsch/$1.spice tx_drv $1; then
    log "== mutation $3: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $3: FAIL (expected)  [$(why $1)]"; fi
}
mutate lvs_mut_w   '/^XM5n /s/W=8.0u/W=7.2u/'               "XM5n W 8 -> 7.2 (tx_arm)"
mutate lvs_mut_net '/^XTGn /s/^\(XTGn [^ ]*\) VDD /\1 VSS /' "XTGn gate VDD -> VSS (tx_split)"
mutate lvs_mut_dc  '/^XDC /s/m=24/m=23/'                    "XDC m 24 -> 23 (top)"

lvs_ok=0; grep -q "^LVS PASS" summary.txt && lvs_ok=1
drc_ok=0; grep -q "^== magic DRC.*: count 0$" summary.txt && grep -q "^== KLayout DRC.*rules run [1-9][0-9]*: count 0$" summary.txt && drc_ok=1
[[ ${SKIP:-} == *klayout* ]] && grep -q "^== magic DRC.*: count 0$" summary.txt && drc_ok=1
ant_ok=1; [[ ${SKIP:-} != *antenna* ]] && ! grep -q "^== antenna.*violations 0," summary.txt && ant_ok=0
log "CHECK $([ $lvs_ok$drc_ok$ant_ok$mut_ok = 1111 ] && echo OK || echo FAIL)  (LVS vs xschem $lvs_ok, DRC $drc_ok, antenna $ant_ok, mutations caught $mut_ok)"
