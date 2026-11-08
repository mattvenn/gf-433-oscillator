#!/bin/bash
# Parasitic extraction of the lsdiv block (copy of pex_v3.sh for layout/lsdiv.gds).
# Usage (repo root): bash layout/gen/pex_lsdiv.sh [c|rc|lvs] [gds]
#   c: devices + C (cthresh 0, coupling C kept: used for the Cc / C(a0) / C(lg) report), rc: + R (extresist)
# Writes layout/pex/lsdiv_<mode>.spice: .subckt lsdiv VDD VSS a0 ck (the xschem port order), substrate tied to VSS,
# then prints the Cc report (layout/gen/pex_lsdiv.sh c).
# magic is pinned to 8.3.642 (MAGIC=...): 8.3.684 drops node-to-substrate C from ext2spice output.
# The hi-res poly R1 extracts as ppolyf_u_1k (the only hi-res model in magic's gf180mcuD tech); the netlist keeps that
# name, sim/lsdiv/lsdiv.py --r1model chooses the model at simulation time.
set -eu
MODE=${1:-rc}
REPO=$(pwd)
GDS=$(realpath "${2:-layout/lsdiv.gds}")
B=lsdiv
MAGIC=${MAGIC:-$( [ -x $HOME/.local/magic642/bin/magic ] && echo $HOME/.local/magic642/bin/magic || echo magic)}
OUT=$REPO/build/pex/${B}_$MODE
mkdir -p "$OUT" "$REPO/layout/pex"; cd "$OUT"
rm -f *.ext *.res.ext *.sim *.nodes
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
bash "$REPO/xschem/gen/netlist.sh" "$REPO/xschem" "$OUT/xsch" lsdiv > /dev/null
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
python3 "$REPO/layout/gen/pexfix.py" ${B}_raw.spice xsch/lsdiv.spice "$DST"
sed -i "1a * extracted $(date -Iseconds) with magic $("$MAGIC" --version), mode $MODE, from $(basename $GDS)" "$DST"
# ---- Cc report: coupling a0-lg, a0 to everything else, lg to everything else (node names grouped by prefix) ----
python3 - "$DST" <<'PYEOF'
import re, sys
from collections import defaultdict
SUF = dict(a=1e-18, f=1e-15, p=1e-12, n=1e-9)
def val(v):
    m = re.fullmatch(r"([-+\d.eE]+?)([afpn]?)F?", v)
    return float(m.group(1)) * SUF.get(m.group(2), 1)
def grp(n):
    return n.split(".")[0].split("_n")[0] if re.match(r"(a0|lg|lf|ls)\b", n) else n
pair = defaultdict(float)
for ln in open(sys.argv[1]):
    t = ln.split()
    if t and t[0][0] in "Cc" and len(t) >= 4:
        a, b = sorted((grp(t[1]), grp(t[2])))
        pair[(a, b)] += val(t[3])
def tot(n):
    return {(b if a == n else a): c for (a, b), c in pair.items() if n in (a, b) and a != b}
for n in ("a0", "lg"):
    d = tot(n)
    s = sorted(d.items(), key=lambda kv: -kv[1])
    print(f"C({n}) total {sum(d.values()) * 1e15:.3f} fF: " + ", ".join(f"{k} {v * 1e15:.3f}" for k, v in s[:6]))
cc = pair.get(("a0", "lg"), 0)
a0x = sum(tot("a0").values()) - cc
lgx = sum(tot("lg").values()) - cc
print(f"Cc (a0-lg coupling) {cc * 1e15:.3f} fF   C(a0) to everything else {a0x * 1e15:.3f} fF   "
      f"C(lg) to everything else {lgx * 1e15:.3f} fF")
PYEOF
