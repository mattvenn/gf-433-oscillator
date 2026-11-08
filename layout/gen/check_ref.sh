#!/bin/bash
# cgm_ref (constant-gm reference + vbn RC filter) checks with the xschem schematic as the LVS source (repo root, in
# the image):
#   1. netlist xschem/cgm_ref.sch headless (xschem/gen/netlist.sh) -> <outdir>/xsch/cgm_ref.spice (.subckt cgm_ref
#      VDD VSS vbn vbnf); LVS copy cgm_ref_lvs.spice = the same + "vctrl" appended to the .subckt port list (the
#      vctrl M2 feed-through is a port in the layout with no device on it; without the extra port netgen fails pin
#      matching) + XRBW r_length on the 5 nm grid (5.025 for 5.023)
#   2. the check_v2.sh steps (magic DRC, KLayout DRC with feol/beol true and the rules-run count, antenna on a
#      flattened copy, netgen LVS that fails on property errors), copied here with one addition: after "gds read"
#      the n-well resistor is repainted as rnw on NWELL & RES_MK (110/5). The PDK's magic cifinput has no rule for
#      rnw (and its GDS output writes no RES_MK on it: layout/gen/cgm_ref.py adds the marker), so without this RBW
#      would read back as plain n-well, a short. The boxes come from the GDS itself (KLayout), not the generator.
#   3. resistor sizes: netgen treats the PDK resistors as black boxes, so r_width / r_length of the extracted RBW
#      (nwell), RBN (nplus_u) and RF (ppolyf_u_1k) are compared with the source here (W 0.1 %, L 1 %; the n-well
#      length is drawn 5.025 um on the 5 nm grid for 5.023)
#   4. mutation: broken copies of the source against the same extraction must all FAIL:
#      XMN2s5 m 56 -> 55 (LVS), XMS3 source vbn -> net1 (LVS), XRBN r_length 100 -> 90 um (resistor size check)
# Usage: bash layout/gen/check_ref.sh [gds] [outdir]     defaults: layout/cgm_ref.gds build/check/cgm_ref
#   SKIP=klayout,antenna
# Results: <outdir>/summary.txt (last line CHECK OK / CHECK FAIL), lvs.report, lvs_mut*.report
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/cgm_ref.gds}")
OUT=${2:-build/check/cgm_ref}
B=cgm_ref
SKIP=${SKIP:-}
mkdir -p "$OUT/xsch"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc

# ---- 1. schematic netlist (+ the vctrl feed-through port) ----
NL=$(bash xschem/gen/netlist.sh xschem "$OUT/xsch" cgm_ref) || { echo "netlist failed: $NL"; exit 1; }
SRC0=$OUT/xsch/cgm_ref.spice
SRC=$OUT/xsch/cgm_ref_lvs.spice
# + XRBW r_length snapped to the 5 nm manufacturing grid (5.023 -> 5.025 um: 5.023 cannot be drawn; netgen compares
#   nwell lengths with zero tolerance). The resistor size check (step 3) still compares against the unsnapped source.
python3 - "$SRC0" "$SRC" <<'PYEOF'
import re, sys
t = open(sys.argv[1]).read()
t = re.sub(r"^(\.subckt cgm_ref VDD VSS vbn vbnf)$", r"\1 vctrl", t, flags=re.M)
def snap(m):
    v = float(m.group(2)) * 1e-6 if m.group(3) == "e-6" else float(m.group(2))
    return f"{m.group(1)}{round(v * 1e9 / 5) * 5 / 1000:.3f}e-6"
t = re.sub(r"^(XRBW .* r_length=)([\d.]+)(e-6)", snap, t, flags=re.M)
open(sys.argv[2], "w").write(t)
PYEOF

cd "$OUT"
: > summary.txt
log() { echo "$*" | tee -a summary.txt; }
log "gds $GDS  top $B  magic $(magic --version)  netgen $(netgen -batch quit 2>/dev/null | grep -o 'Netgen [0-9.]*' | head -1)  klayout $(klayout -v)"
log "== schematic: xschem/cgm_ref.sch; $NL; LVS copy: vctrl appended to the ports ($(grep -c '^\.subckt cgm_ref .* vctrl$' "$SRC") line), XRBW $(grep -o 'r_length=[^ ]*' <(grep '^XRBW' "$SRC0")) -> $(grep -o 'r_length=[^ ]*' <(grep '^XRBW' "$SRC"))"

# rnw repaint commands from the GDS (NWELL 21/0 & RES_MK 110/5)
python3 - "$GDS" > rnwfix.tcl <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); t = ly.top_cell()
r = db.Region(t.begin_shapes_rec(ly.find_layer(21, 0))) & db.Region(t.begin_shapes_rec(ly.find_layer(110, 5)))
for p in r.each():
    b = p.bbox().to_dtype(ly.dbu)
    print(f"box {b.left:.3f}um {b.bottom:.3f}um {b.right:.3f}um {b.top:.3f}um; paint rnw")
PYEOF
log "== rnw repaint from NWELL & RES_MK: $(grep -c paint rnwfix.tcl) box(es): $(tr '\n' ' ' < rnwfix.tcl)"

# ---- 2a. magic DRC + LVS extraction ----
{
echo "gds read $GDS"
echo "load $B"
cat rnwfix.tcl
cat <<'TCL'
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
set fp [open magic_drc.txt w]
puts $fp "count [drc list count total]"
set sc [cif scale out]
foreach {why boxes} [drc listall why] {
  set loc {}
  foreach b [lrange $boxes 0 2] { lappend loc [lmap v $b {format %.2f [expr {$v * $sc}]}] }
  puts $fp "[llength $boxes]  $why   at $loc"
}
close $fp
extract do local
extract unique notopports
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -o cgm_ref_lay.spice
feedback save extract_feedback.txt
quit -noprompt
TCL
} > magic.tcl
t0=$(date +%s)
magic -dnull -noconsole -rcfile $RC magic.tcl > magic.log 2>&1
log "== magic DRC ($(( $(date +%s) - t0 )) s): $(head -1 magic_drc.txt)"; tail -n +2 magic_drc.txt | head -20 | tee -a summary.txt

# ---- 2b. antenna: flattened copy, fresh session ----
if [[ $SKIP != *antenna* ]]; then
mkdir -p ant
{
echo "gds read $GDS"
echo "load $B"
cat rnwfix.tcl
cat <<'TCL'
flatten cgm_ref_flat
load cgm_ref_flat
select top cell
extract do local
extract all
puts "ANTENNA_BEGIN"
antennacheck debug
antennacheck
puts "FEEDBACK [feedback count]"
puts "ANTENNA_END"
quit -noprompt
TCL
} > ant/ant.tcl
t0=$(date +%s)
(cd ant && magic -dnull -noconsole -rcfile $RC ant.tcl > ../antenna.log 2>&1)
sed -n '/ANTENNA_BEGIN/,/ANTENNA_END/p' antenna.log > antenna.txt
log "== antenna ($(( $(date +%s) - t0 )) s): violations $(grep -ci 'violation' antenna.txt), feedback $(grep FEEDBACK antenna.txt | cut -d' ' -f2)"
grep -i -A1 'violation' antenna.txt | head -8 | tee -a summary.txt
fi

# ---- 2c. KLayout DRC (PDK deck, FEOL + BEOL) ----
if [[ $SKIP != *klayout* ]]; then
t0=$(date +%s)
klayout -b -r $PDK_ROOT/$PDK/libs.tech/klayout/tech/drc/gf180mcu.drc -rd input=$GDS -rd topcell=$B \
  -rd report=$OUT/klayout_drc.lyrdb -rd variant=D -rd run_mode=deep -rd threads=8 -rd decks=${KLDECKS:-all,-density} -rd feol=true -rd beol=true \
  > klayout_drc.log 2>&1
python3 - "$OUT/klayout_drc.lyrdb" <<'PYEOF' | tee klayout_drc_summary.txt
import sys, xml.etree.ElementTree as ET, collections
r = ET.parse(sys.argv[1]).getroot()
c = collections.Counter(i.findtext('category') for i in r.iter('item'))
print('count', sum(c.values()))
for k, v in c.most_common(): print(' ', v, k)
PYEOF
log "== KLayout DRC ($(( $(date +%s) - t0 )) s), decks ${KLDECKS:-all,-density}, $(grep -o 'executing [0-9]* deck(s)\|Running all [A-Z]* rules' klayout_drc.log | tr '\n' ' ') rules run $(grep -c 'Executing rule' klayout_drc.log): $(head -1 klayout_drc_summary.txt)"
tail -n +2 klayout_drc_summary.txt | head -20 >> summary.txt
fi

# ---- 2d. netgen LVS ----
lvs() {  # lvs <a> <cell_a> <b> <cell_b> <tag>  -> 0 if "match uniquely" with no property errors
  netgen -batch lvs "$1 $2" "$3 $4" $SETUP $5.report > $5.log 2>&1
  grep -q "Final result: Circuits match uniquely" $5.report && ! grep -qi "property errors" $5.report \
    && ! grep -qi "do not match" $5.report && ! grep -qi "failed pin matching" $5.report
}
why() { grep -E "Final result|roperty errors|do not match|pin matching" $1.report | sort -u | tr '\n' ' '; }
t0=$(date +%s)
if lvs cgm_ref_lay.spice $B "$SRC" cgm_ref lvs; then r=PASS; else r=FAIL; fi
log "== LVS ($(( $(date +%s) - t0 )) s):"
grep -E "Circuits match|do not match|Netlists match|Final result|roperty errors|failed pin|disconnected" lvs.report | sort -u | tail -6 | tee -a summary.txt
log "LVS $r"

# ---- 3. resistor sizes (black boxes in netgen) ----
rsize() {  # rsize <source.spice> -> PASS/FAIL line
python3 - "$1" cgm_ref_lay.spice <<'PYEOF'
import re, sys
SUF = dict(m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15)
def num(v):
    m = re.fullmatch(r"([-+\d.eE]+?)([munpf]?)", v.strip())
    return float(m.group(1)) * SUF.get(m.group(2), 1)
def res(path):
    txt = re.sub(r"\n\+", " ", open(path).read())
    out = {}
    for ln in txt.splitlines():
        t = ln.split()
        if not t or t[0][:1] not in "Xx":
            continue
        model = [x for x in t[1:] if "=" not in x][-1]
        if model in ("nwell", "nplus_u", "ppolyf_u_1k"):
            kv = dict(x.split("=", 1) for x in t if "=" in x)
            out.setdefault(model, []).append((num(kv["r_width"]), num(kv["r_length"])))
    return out
src, lay = res(sys.argv[1]), res(sys.argv[2])
ok, txt = True, []
for m in ("nwell", "nplus_u", "ppolyf_u_1k"):
    s, l = src.get(m, []), lay.get(m, [])
    good = len(s) == len(l) == 1 and abs(s[0][0] / l[0][0] - 1) < 1e-3 and abs(s[0][1] / l[0][1] - 1) < 0.01
    ok &= good
    f = lambda v: "/".join(f"{x * 1e6:.4g}" for x in v[0]) if v else "-"
    txt.append(f"{m} src {f(s)} lay {f(l)} um" + (f" ({(l[0][1] / s[0][1] - 1) * 100:+.3f} % L)" if s and l else "")
               + ("" if good else " BAD"))
print(("PASS" if ok else "FAIL") + "  " + "; ".join(txt))
PYEOF
}
rs=$(rsize "$SRC0")
log "== resistor size check (w/l): $rs"
rs_ok=0; [[ $rs == PASS* ]] && rs_ok=1

# ---- 4. mutation tests (reuse the layout extraction from step 2) ----
mut_ok=1
mutate() {  # mutate <tag> <sed expr> <description>
  sed -e "$2" "$SRC" > xsch/$1.spice
  if cmp -s "$SRC" xsch/$1.spice; then log "== mutation $3: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs cgm_ref_lay.spice cgm_ref xsch/$1.spice cgm_ref $1; then
    log "== mutation $3: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $3: FAIL (expected)  [$(why $1)]"; fi
}
mutate lvs_mut_m   '/^XMN2s5 /s/m=56$/m=55/'                "XMN2s5 m 56 -> 55 (one MN2 unit)"
mutate lvs_mut_net '/^XMS3 /s/^XMS3 net1 net2 vbn /XMS3 net1 net2 net1 /' "XMS3 source vbn -> net1"
sed -e '/^XRBN /s/r_length=100.0e-6/r_length=90.0e-6/' "$SRC" > xsch/res_mut.spice
if cmp -s "$SRC" xsch/res_mut.spice; then log "== mutation XRBN L 100 -> 90: NOT APPLIED (BAD)"; mut_ok=0
else
  r=$(rsize xsch/res_mut.spice)
  if [[ $r == PASS* ]]; then log "== mutation XRBN r_length 100 -> 90 um: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation XRBN r_length 100 -> 90 um: FAIL (expected)  [$r]"; fi
fi

lvs_ok=0; grep -q "^LVS PASS" summary.txt && lvs_ok=1
drc_ok=0; grep -q "^== magic DRC.*: count 0$" summary.txt && grep -q "^== KLayout DRC.*rules run [1-9][0-9]*: count 0$" summary.txt && drc_ok=1
[[ ${SKIP:-} == *klayout* ]] && grep -q "^== magic DRC.*: count 0$" summary.txt && drc_ok=1
ant_ok=1; [[ ${SKIP:-} != *antenna* ]] && ! grep -q "^== antenna.*violations 0," summary.txt && ant_ok=0
log "CHECK $([ $lvs_ok$drc_ok$ant_ok$rs_ok$mut_ok = 11111 ] && echo OK || echo FAIL)  (LVS vs xschem $lvs_ok, DRC $drc_ok, antenna $ant_ok, resistor sizes $rs_ok, mutations caught $mut_ok)"
