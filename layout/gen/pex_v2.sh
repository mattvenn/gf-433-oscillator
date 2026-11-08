#!/bin/bash
# Parasitic extraction of the ring core for simulation (adapted from the mixed-signal-asic skill's pex.sh).
# v2 copy of pex.sh: TAG (default v2) goes into the output names so v1 extractions are kept.
# Usage (repo root): bash layout/gen/pex_v2.sh [lvs|c|rc] [gds] [top]
#   lvs: devices only (connectivity check), c: + C (cthresh 0, coupling), rc: + R (extresist) and C
# Writes layout/pex/<top>_<mode>.spice (.subckt <top> in the schematic port order, substrate tied to VSS).
# magic is pinned to 8.3.642 (MAGIC=...): 8.3.684 drops node-to-substrate C from ext2spice output.
set -eu
MODE=${1:-rc}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/ring_core_v2.gds}")
TAG=${TAG:-v2}
B=${3:-ring_core}
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_${TAG}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
python3 "$REPO/layout/gen/export_core.py" -o "$OUT/$B.sch.spice" --name $B > /dev/null
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
