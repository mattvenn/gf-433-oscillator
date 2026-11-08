#!/bin/bash
# Parasitic extraction of the whole vco_top (layout/vco_top.gds; copy of pex_ref.sh for the top level).
# Usage (repo root): bash layout/gen/pex_top.sh [c|rc|lvs] [gds]
#   c: devices + C (cthresh 0, coupling C kept); rc: + R (extresist), then layout/gen/rcfix.py -> vco_top_rcx.spice
#      (checked against vco_top_c.spice when it exists: run c first)
# Writes layout/pex/vco_top_<mode>.spice: .subckt vco_top <the xschem port order: VDD VDD_LS VSS vctrl bit0-4
# bitb0-4 ck a0 vbn vg>, substrate tied to VSS.
# - magic is pinned to 8.3.642 (MAGIC=...): 8.3.684 drops node-to-substrate C from ext2spice output.
# - the n-well resistor is repainted as rnw in cell cgm_ref on NWELL & RES_MK after gds read (magic's gf180mcuD
#   cifinput has no rnw rule; check_ref.sh / check_top.sh).
# - flatten -dotoplabels: only vco_top's pin labels name nets, so the blocks' own "VDD" labels can't join VDD and
#   VDD_LS by name. Internal nets get magic's generated names, except three monitor labels added in the extraction
#   session only (ls, q1, vbnf; see below).
set -eu
MODE=${1:-c}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/vco_top.gds}")
B=vco_top
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
bash "$REPO/xschem/gen/netlist.sh" "$REPO/xschem" "$OUT/xsch" vco_top > /dev/null
python3 - "$GDS" > rnwfix.tcl <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); c = ly.cell("cgm_ref")
r = db.Region(c.begin_shapes_rec(ly.find_layer(21, 0))) & db.Region(c.begin_shapes_rec(ly.find_layer(110, 5)))
print("load cgm_ref")
for p in r.each():
    b = p.bbox().to_dtype(ly.dbu)
    print(f"box {b.left:.3f}um {b.bottom:.3f}um {b.right:.3f}um {b.top:.3f}um; paint rnw")
print("load vco_top")
PYEOF
# monitor labels on three internal nets (in the flattened extraction cell only; the GDS is not changed): lsdiv's ls
# (level-shifter output) and q1 (first /2), cgm_ref's vbnf (filtered bias = the DAC gate). Placed at the blocks' own
# label points, transformed into vco_top; plain labels (not ports): sims probe them as v(x<inst>.ls) etc.
python3 - "$GDS" > monlabels.tcl <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); top = ly.cell("vco_top")
LAY = {34: "metal1", 36: "metal2", 42: "metal3"}
want = {"lsdiv": ("ls", "q1"), "cgm_ref": ("vbnf",)}
for inst in top.each_inst():
    c = ly.cell(inst.cell_index)
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        for s in c.shapes(li).each():
            if s.is_text() and s.text_string in want.get(c.name, ()):
                p = inst.dcplx_trans * s.dtext.position()
                print(f"box {p.x:.3f}um {p.y:.3f}um {p.x:.3f}um {p.y:.3f}um; label {s.text_string} c {LAY[info.layer]}")
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
cat rnwfix.tcl
echo "flatten -dotoplabels ${B}_flat"
echo "load ${B}_flat"
cat monlabels.tcl
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
python3 "$REPO/layout/gen/pexfix.py" ${B}_raw.spice xsch/vco_top.spice "$DST"
sed -i "1a * extracted $(date -Iseconds) with magic $("$MAGIC" --version), mode $MODE, from $(basename $GDS)" "$DST"
grep -q " nwell r_width" "$DST" || { echo "ERROR: no nwell resistor in $DST"; exit 1; }
if [ "$MODE" = rc ]; then
  python3 "$REPO/layout/gen/rcfix.py" "$DST" "$REPO/layout/pex/${B}_rcx.spice" \
    $( [ -f "$REPO/layout/pex/${B}_c.spice" ] && echo --check "$REPO/layout/pex/${B}_c.spice" )
  DST=$REPO/layout/pex/${B}_rcx.spice
fi
# ---- C report: total parasitic C on the ports (largest neighbours) ----
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
for n in ("a0", "ck", "vg", "vbn", "vbnf", "vctrl", "ls", "q1", "VDD_LS"):
    d = {(b if a == n else a): c for (a, b), c in pair.items() if n in (a, b)}
    s = sorted(d.items(), key=lambda kv: -kv[1])
    print(f"C({n}) parasitic total {sum(d.values()) * 1e15:.2f} fF: " + ", ".join(f"{k} {v * 1e15:.2f}" for k, v in s[:5]))
print(f"C(VDD-VDD_LS) coupling {pair.get(('VDD', 'VDD_LS'), 0) * 1e15:.3f} fF")
PYEOF
