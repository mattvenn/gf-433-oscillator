#!/bin/bash
# Parasitic extraction of the cgm_ref block (copy of pex_lsdiv.sh for layout/cgm_ref.gds).
# Usage (repo root): bash layout/gen/pex_ref.sh [c|rc|lvs] [gds]
#   c: devices + C (cthresh 0, coupling C kept), rc: + R (extresist), then layout/gen/rcfix.py -> cgm_ref_rcx.spice
#      (checked against cgm_ref_c.spice when it exists: run c first)
# Writes layout/pex/cgm_ref_<mode>.spice: .subckt cgm_ref VDD VSS vbn vbnf vctrl (the xschem port order + the vctrl
# feed-through, which has no device but carries coupling C), substrate tied to VSS; prints C on vbn / vbnf / vctrl.
# magic is pinned to 8.3.642 (MAGIC=...): 8.3.684 drops node-to-substrate C from ext2spice output.
# The n-well resistor is repainted as rnw on NWELL & RES_MK after gds read (magic's gf180mcuD cifinput has no rnw
# rule; see check_ref.sh).
set -eu
MODE=${1:-rc}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/cgm_ref.gds}")
B=cgm_ref
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
bash "$REPO/xschem/gen/netlist.sh" "$REPO/xschem" "$OUT/xsch" cgm_ref > /dev/null
sed -e 's/^\(\.subckt cgm_ref VDD VSS vbn vbnf\)$/\1 vctrl/' xsch/cgm_ref.spice > xsch/cgm_ref_ports.spice
python3 - "$GDS" > rnwfix.tcl <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); t = ly.top_cell()
r = db.Region(t.begin_shapes_rec(ly.find_layer(21, 0))) & db.Region(t.begin_shapes_rec(ly.find_layer(110, 5)))
for p in r.each():
    b = p.bbox().to_dtype(ly.dbu)
    print(f"box {b.left:.3f}um {b.bottom:.3f}um {b.right:.3f}um {b.top:.3f}um; paint rnw")
PYEOF
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
{
echo "gds read $GDS"
echo "load $B"
cat rnwfix.tcl
echo "flatten ${B}_flat"
echo "load ${B}_flat"
echo "cellname delete $B"
echo "cellname rename ${B}_flat $B"
echo "select top cell"
echo "extract do local"
echo "extract all"
echo "$EXT"
echo "ext2spice -o ${B}_raw.spice"
echo "quit -noprompt"
} > pex.tcl
t0=$(date +%s)
"$MAGIC" -dnull -noconsole -rcfile $RC pex.tcl > magic.log 2>&1
echo "magic $("$MAGIC" --version) $MODE extraction: $(( $(date +%s) - t0 )) s; rnw boxes $(grep -c paint rnwfix.tcl)"
DST=$REPO/layout/pex/${B}_$MODE.spice
python3 "$REPO/layout/gen/pexfix.py" ${B}_raw.spice xsch/cgm_ref_ports.spice "$DST"
sed -i "1a * extracted $(date -Iseconds) with magic $("$MAGIC" --version), mode $MODE, from $(basename $GDS)" "$DST"
grep -q " nwell r_width" "$DST" || { echo "ERROR: no nwell resistor in $DST"; exit 1; }
if [ "$MODE" = rc ]; then
  python3 "$REPO/layout/gen/rcfix.py" "$DST" "$REPO/layout/pex/${B}_rcx.spice" \
    $( [ -f "$REPO/layout/pex/${B}_c.spice" ] && echo --check "$REPO/layout/pex/${B}_c.spice" )
  DST=$REPO/layout/pex/${B}_rcx.spice
fi
# ---- C report: total C and the largest neighbours of vbn, vbnf, vctrl ----
python3 - "$DST" <<'PYEOF'
import re, sys
from collections import defaultdict
SUF = dict(a=1e-18, f=1e-15, p=1e-12, n=1e-9)
def val(v):
    m = re.fullmatch(r"([-+\d.eE]+?)([afpn]?)F?", v)
    return float(m.group(1)) * SUF.get(m.group(2), 1)
def grp(n):
    m = re.match(r"(.+)\.[tn]\d+$", n)
    return m.group(1) if m else n
pair = defaultdict(float)
for ln in open(sys.argv[1]):
    t = ln.split()
    if t and t[0][0] in "Cc" and len(t) >= 4:
        a, b = sorted((grp(t[1]), grp(t[2])))
        if a != b:
            pair[(a, b)] += val(t[3])
print("file", sys.argv[1])
for n in ("vbn", "vbnf", "vctrl"):
    d = {(b if a == n else a): c for (a, b), c in pair.items() if n in (a, b)}
    s = sorted(d.items(), key=lambda kv: -kv[1])
    print(f"C({n}) parasitic total {sum(d.values()) * 1e15:.2f} fF: " + ", ".join(f"{k} {v * 1e15:.2f}" for k, v in s[:5]))
PYEOF
