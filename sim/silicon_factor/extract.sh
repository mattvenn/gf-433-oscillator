#!/bin/bash
# GF silicon factor: fetch tt_um_algofoogle_vgaringosc (ttgf0p2, mux 614) from the shuttle repo and extract it.
# Usage (repo root, inside the image: tools/osic-mac bash sim/silicon_factor/extract.sh [c|rc]):
#   c : devices + all C (cthresh 0, coupling)   -> build/silicon_factor/vgaringosc_c.spice
#   rc: + R (extresist)                         -> build/silicon_factor/vgaringosc_rc.spice
# The layout is the shuttle's OASIS file at a pinned commit, so the netlist matches the measured silicon
# (ROM commit ff701baa on chip 1; the project's own GDS is from algofoogle/ttgf0p2-vga-ring-osc cdefb8e).
# magic 8.3.642 (8.3.684 drops substrate C). The whole 1x1 tile is extracted flat, std cells included.
# NOTE (docs/rc_extraction_fix.md): magic rc mode double-counts coupling C on ports/split nets. For this check we
# use the c netlist as the main result; the rc netlist is a secondary check on the shortest rings only.
set -eu
MODE=${1:-c}
REPO=$(pwd)
SHUTTLE_SHA=4150e9654790addc851ad2e6db8d7b6d9663e6ff   # TinyTapeout/tinytapeout-gf-0p2 main, 2026-11-09
TOP=tt_um_algofoogle_vgaringosc
OUT=$REPO/build/silicon_factor; mkdir -p "$OUT"; cd "$OUT"
if [ ! -s $TOP.gds ]; then
  curl -sfL -o $TOP.oas \
    "https://raw.githubusercontent.com/TinyTapeout/tinytapeout-gf-0p2/$SHUTTLE_SHA/projects/$TOP/$TOP.oas"
  python3 - <<EOF
import klayout.db as db
ly = db.Layout(); ly.read("$TOP.oas"); ly.write("$TOP.gds")
print("gds:", [c.name for c in ly.top_cells()])
EOF
fi
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
case $MODE in
  c)  EXT='ext2spice lvs
ext2spice cthresh 0' ;;
  rc) EXT='ext2sim labels on
ext2sim
extresist tolerance 10
extresist
ext2spice lvs
ext2spice cthresh 0
ext2spice extresist on' ;;
  *) echo "mode c|rc"; exit 2 ;;
esac
mkdir -p $MODE; cd $MODE; rm -f *.ext *.res.ext *.sim *.nodes
cat > pex.tcl <<EOF
gds read ../$TOP.gds
load $TOP
flatten ${TOP}_flat
load ${TOP}_flat
cellname delete $TOP
cellname rename ${TOP}_flat $TOP
select top cell
extract do local
extract all
$EXT
ext2spice -o ../vgaringosc_$MODE.spice
quit -noprompt
EOF
t0=$(date +%s)
magic -dnull -noconsole -rcfile $RC pex.tcl > magic.log 2>&1
N=$(grep -ci '^[xm]' ../vgaringosc_$MODE.spice || true)
echo "magic $(magic --version) $MODE: $(( $(date +%s) - t0 )) s, $N device lines -> build/silicon_factor/vgaringosc_$MODE.spice"
grep -m1 -i "^\.subckt" ../vgaringosc_$MODE.spice | cut -c1-400
[ "$N" -gt 1000 ] || { echo "FAIL: too few devices"; tail -20 magic.log; exit 1; }
