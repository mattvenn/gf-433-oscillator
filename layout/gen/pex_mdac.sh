#!/bin/bash
# Parasitic extraction of the medium DAC mdac (copy of pex_tx.sh for layout/mdac.gds).
# Usage (repo root): bash layout/gen/pex_mdac.sh [c|rc|lvs] [gds]
#   c: devices + C (cthresh 0, coupling C kept), rc: + R (extresist) -> mdac_rc.spice, then rcfix.py -> mdac_rcx.spice
set -eu
MODE=${1:-rc}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/mdac.gds}")
B=mdac
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
bash "$REPO/xschem/gen/netlist.sh" "$REPO/xschem" "$OUT/xsch" mdac > /dev/null
case $MODE in
  lvs) EXT='ext2spice lvs
ext2spice cthresh infinite' ;;
  c)   EXT='ext2spice lvs
ext2spice cthresh 0' ;;
  rc)  EXT='ext2sim labels on
ext2sim
extresist tolerance 10
extresist
ext2spice lvs
ext2spice cthresh 0
ext2spice extresist on' ;;
esac
cat > pex.tcl <<EOF
gds read $GDS
load $B
flatten ${B}_flat
load ${B}_flat
cellname delete $B
cellname rename ${B}_flat $B
select top cell
extract do local
extract all
$EXT
ext2spice -o ${B}_raw.spice
quit -noprompt
EOF
t0=$(date +%s)
"$MAGIC" -dnull -noconsole -rcfile $RC pex.tcl > magic.log 2>&1
echo "magic $("$MAGIC" --version) $MODE extraction: $(( $(date +%s) - t0 )) s"
DST=$REPO/layout/pex/${B}_$MODE.spice
python3 "$REPO/layout/gen/pexfix.py" ${B}_raw.spice xsch/mdac.spice "$DST"
sed -i "1a * extracted $(date -Iseconds) with magic $("$MAGIC" --version), mode $MODE, from $(basename $GDS)" "$DST"
# rc: remove magic's coupling double count on ports / split nets (docs/rc_extraction_fix.md) -> mdac_rcx.spice
if [ "$MODE" = rc ]; then
  python3 "$REPO/layout/gen/rcfix.py" "$DST" "$REPO/layout/pex/mdac_rcx.spice" \
    $( [ -f "$REPO/layout/pex/mdac_c.spice" ] && echo --check "$REPO/layout/pex/mdac_c.spice" )
fi
