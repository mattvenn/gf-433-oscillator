#!/bin/bash
# Parasitic extraction of the ring core for simulation (adapted from the mixed-signal-asic skill's pex.sh).
# v3 copy of pex_v2.sh: v3 GDS, LVS/port reference from export_core_v3.py (SETS="--set wfu=0.3" passes generator settings).
# Usage (repo root): bash layout/gen/pex_v2.sh [lvs|c|rc] [gds] [top]
#   lvs: devices only (connectivity check), c: + C (cthresh 0, coupling), rc: + R (extresist) and C
# Writes layout/pex/<top>_<mode>.spice (.subckt <top> in the schematic port order, substrate tied to VSS).
# magic is pinned to 8.3.642 (MAGIC=...): 8.3.684 drops node-to-substrate C from ext2spice output.
set -eu
MODE=${1:-rc}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/ring_core_v3.gds}")
TAG=${TAG:-v3}
B=${3:-ring_core}
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_${TAG}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
python3 "$REPO/layout/gen/export_core_v3.py" -o "$OUT/$B.sch.spice" --name $B ${SETS:-} > /dev/null
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
python3 "$REPO/layout/gen/pexfix.py" ${B}_raw.spice $B.sch.spice "$REPO/layout/pex/${B}_${TAG}_$MODE.spice"
sed -i "1a * extracted $(date -Iseconds) with magic $("$MAGIC" --version), mode $MODE, from $(basename $GDS)" \
  "$REPO/layout/pex/${B}_${TAG}_$MODE.spice"
# rc: magic lumps each port's / split net's total C (coupling included) to VSS and also writes the coupling caps:
# rcfix.py removes that double count (docs/rc_extraction_fix.md) -> <top>_<tag>_rcx.spice (use this one for sims)
if [ "$MODE" = rc ]; then
  CHK=$REPO/layout/pex/${B}_${TAG}_c.spice
  python3 "$REPO/layout/gen/rcfix.py" "$REPO/layout/pex/${B}_${TAG}_rc.spice" "$REPO/layout/pex/${B}_${TAG}_rcx.spice" \
    $( [ -f "$CHK" ] && echo --check "$CHK" )
fi
