#!/bin/bash
# vco_top (ring_core_v3 + cgm_ref + lsdiv + VDD_LS decap) checks, the xschem top sheet as the LVS source (repo root,
# in the image). Modelled on check_ref.sh / check_lsdiv.sh:
#   1. netlist xschem/vco_top.sch headless (xschem/gen/netlist.sh) -> <outdir>/xsch/vco_top.spice (hierarchical:
#      vco_top, ring_core_v3, cfed_ring, cfed_dac, cgm_ref, lsdiv, ls_ac, tspc_t1, tspc_t2). LVS copy vco_top_lvs.spice
#      with the block checks' documented edits:
#        - lsdiv's "Cc a0 net1 2e-15" removed (Cc is drawn as M2/M3 fingers: parasitic C, not a device; check_lsdiv.sh)
#        - XRBW r_length snapped to the 5 nm grid, 5.023 -> 5.025 um (check_ref.sh)
#        - the vctrl port edit of check_ref.sh is NOT needed here: the layout is flattened, and cgm_ref's vctrl
#          feed-through is simply part of the top-level vctrl net (the source's vctrl reaches the core directly).
#   2. magic DRC (full) on the hierarchical vco_top; LVS extraction of a flattened copy (flatten -dotoplabels: only
#      vco_top's own pin labels survive, so the blocks' "VDD" labels can't merge VDD and VDD_LS by name);
#      antenna on the flattened copy; KLayout DRC (PDK deck, feol + beol; the rules-run count must be > 0).
#      After "gds read" the n-well resistor is repainted as rnw in cell cgm_ref on NWELL & RES_MK (cell-local boxes
#      taken from the GDS with KLayout): magic's gf180mcuD cifinput has no rnw rule (docs/ref_layout.md).
#   3. netgen LVS flat layout vs the source (fails on property errors, pin-matching failures, "do not match").
#   4. resistor sizes (netgen black-boxes the PDK resistors): every nwell / nplus_u / ppolyf_u_1k device of the
#      unsnapped source matched to one in the layout by model and length (W 0.1 %, L 1 %).
#   5. Metal4 / Metal5 / via3 / via4 must be absent from the GDS (TT's power stripes are Metal4).
#   6. mutations (each must FAIL): DCLS m 5 -> 4 (LVS), xls supply VDD_LS -> VDD (LVS: supplies merged),
#      XR1 (lsdiv) r_length 159.125 -> 140 um (resistor size check).
# Usage: bash layout/gen/check_top.sh [gds] [outdir]     defaults: layout/vco_top.gds build/check/vco_top
#   SKIP=klayout,antenna
# Results: <outdir>/summary.txt (last line CHECK OK / CHECK FAIL), lvs.report, lvs_mut*.report
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/vco_top.gds}")
OUT=${2:-build/check/vco_top}
B=vco_top
SKIP=${SKIP:-}
mkdir -p "$OUT/xsch"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc

# ---- 1. schematic netlist + LVS copy ----
NL=$(bash xschem/gen/netlist.sh xschem "$OUT/xsch" vco_top) || { echo "netlist failed: $NL"; exit 1; }
SRC0=$OUT/xsch/vco_top.spice
SRC=$OUT/xsch/vco_top_lvs.spice
python3 - "$SRC0" "$SRC" <<'PYEOF'
import re, sys
t = open(sys.argv[1]).read()
t, ncc = re.subn(r"^Cc a0 net1 2e-15\n", "", t, flags=re.M)
def snap(m):
    v = float(m.group(2)) * 1e-6
    return f"{m.group(1)}{round(v * 1e9 / 5) * 5 / 1000:.3f}e-6"
t, nrbw = re.subn(r"^(XRBW .* r_length=)([\d.]+)(e-6)", snap, t, flags=re.M)
assert ncc == 1 and nrbw == 1, (ncc, nrbw)
open(sys.argv[2], "w").write(t)
PYEOF
[ $? -eq 0 ] || { echo "LVS copy edits did not apply"; exit 1; }

cd "$OUT"
: > summary.txt
log() { echo "$*" | tee -a summary.txt; }
log "gds $GDS  top $B  magic $(magic --version)  netgen $(netgen -batch quit 2>/dev/null | grep -o 'Netgen [0-9.]*' | head -1)  klayout $(klayout -v)"
log "== schematic: xschem/vco_top.sch; $NL; LVS copy: removed $(( $(grep -c '^Cc a0 ' "$SRC0") - $(grep -c '^Cc a0 ' "$SRC") )) Cc line, XRBW $(grep -o 'r_length=[^ ]*' <(grep '^XRBW' "$SRC0")) -> $(grep -o 'r_length=[^ ]*' <(grep '^XRBW' "$SRC"))"

# rnw repaint commands, in cgm_ref's own coordinates (NWELL 21/0 & RES_MK 110/5 of that cell)
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
log "== rnw repaint in cgm_ref from NWELL & RES_MK: $(grep -c paint rnwfix.tcl) box(es): $(grep paint rnwfix.tcl | tr '\n' ' ')"

# ---- 5. no Metal4 / Metal5 ----
m45=$(python3 - "$GDS" <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); t = ly.top_cell()
bad = []
for li in ly.layer_indexes():
    i = ly.get_info(li)
    if (i.layer, i.datatype) in ((46, 0), (81, 0), (41, 0), (82, 0)) and not db.Region(t.begin_shapes_rec(li)).is_empty():
        bad.append(f"{i.layer}/{i.datatype}")
print("none" if not bad else "FOUND " + " ".join(bad))
PYEOF
)
log "== Metal4 (46/0), via3 (41/0), Metal5 (81/0), via4 (82/0) in the GDS: $m45"
m45_ok=0; [ "$m45" = none ] && m45_ok=1

# ---- 2a. magic DRC (hierarchical) + flattened LVS extraction ----
{
echo "gds read $GDS"
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
flatten -dotoplabels vco_top_flat
load vco_top_flat
cellname delete vco_top
cellname rename vco_top_flat vco_top
select top cell
extract do local
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -o vco_top_lay.spice
feedback save extract_feedback.txt
quit -noprompt
TCL
} > magic.tcl
t0=$(date +%s)
magic -dnull -noconsole -rcfile $RC magic.tcl > magic.log 2>&1
log "== magic DRC ($(( $(date +%s) - t0 )) s incl. extraction): $(head -1 magic_drc.txt)"; tail -n +2 magic_drc.txt | head -20 | tee -a summary.txt
log "   layout netlist: $(grep -c '^X' vco_top_lay.spice) X devices; ports: $(grep -m1 '^.subckt' vco_top_lay.spice | cut -d' ' -f3- )"

# ---- 2b. antenna: flattened copy, fresh session ----
if [[ $SKIP != *antenna* ]]; then
mkdir -p ant
{
echo "gds read $GDS"
cat rnwfix.tcl
cat <<'TCL'
flatten vco_top_flat
load vco_top_flat
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

# ---- 3. netgen LVS ----
lvs() {  # lvs <a> <cell_a> <b> <cell_b> <tag>  -> 0 if "match uniquely" with no property errors
  netgen -batch lvs "$1 $2" "$3 $4" $SETUP $5.report > $5.log 2>&1
  grep -q "Final result: Circuits match uniquely" $5.report && ! grep -qi "property errors" $5.report \
    && ! grep -qi "do not match" $5.report && ! grep -qi "failed pin matching" $5.report
}
why() { grep -E "Final result|roperty errors|do not match|pin matching" $1.report | sort -u | tr '\n' ' '; }
t0=$(date +%s)
if lvs vco_top_lay.spice $B "$SRC" vco_top lvs; then r=PASS; else r=FAIL; fi
log "== LVS ($(( $(date +%s) - t0 )) s):"
grep -E "Circuits match|do not match|Netlists match|Final result|roperty errors|failed pin|disconnected" lvs.report | sort -u | tail -6 | tee -a summary.txt
log "LVS $r"

# ---- 4. resistor sizes (black boxes in netgen) ----
rsize() {  # rsize <source.spice> -> PASS/FAIL line
python3 - "$1" vco_top_lay.spice <<'PYEOF'
import re, sys
SUF = dict(m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15)
MODELS = ("nwell", "nplus_u", "ppolyf_u_1k")
def num(v):
    m = re.fullmatch(r"([-+\d.eE]+?)([munpf]?)", v.strip())
    return float(m.group(1)) * SUF.get(m.group(2), 1)
def res(path):
    txt = re.sub(r"\n\+", " ", open(path).read())
    out = []
    for ln in txt.splitlines():
        t = ln.split()
        if not t or t[0][:1] not in "Xx":
            continue
        model = [x for x in t[1:] if "=" not in x][-1]
        if model in MODELS:
            kv = dict(x.split("=", 1) for x in t if "=" in x)
            out.append((model, num(kv["r_width"]), num(kv["r_length"])))
    return sorted(out)
src, lay = res(sys.argv[1]), res(sys.argv[2])
ok = len(src) == len(lay)
txt = []
for s, l in zip(src, lay):
    good = s[0] == l[0] and abs(s[1] / l[1] - 1) < 1e-3 and abs(s[2] / l[2] - 1) < 0.01
    ok &= good
    txt.append(f"{s[0]} src {s[1]*1e6:.4g}/{s[2]*1e6:.6g} lay {l[1]*1e6:.4g}/{l[2]*1e6:.6g} um ({(l[2]/s[2]-1)*100:+.3f} % L)"
               + ("" if good else " BAD"))
print(("PASS" if ok else "FAIL") + f"  {len(src)} source / {len(lay)} layout: " + "; ".join(txt))
PYEOF
}
rs=$(rsize "$SRC0")
log "== resistor size check (w/l): $rs"
rs_ok=0; [[ $rs == PASS* ]] && rs_ok=1

# ---- 6. mutation tests (reuse the layout extraction) ----
mut_ok=1
mutate() {  # mutate <tag> <sed expr> <description>
  sed -e "$2" "$SRC" > xsch/$1.spice
  if cmp -s "$SRC" xsch/$1.spice; then log "== mutation $3: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs vco_top_lay.spice $B xsch/$1.spice vco_top $1; then
    log "== mutation $3: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $3: FAIL (expected)  [$(why $1)]"; fi
}
mutate lvs_mut_m   '/^XDCLS /s/m=5$/m=4/'                     "DCLS m 5 -> 4 (one VDD_LS decap finger)"
mutate lvs_mut_sup '/^xls /s/^xls VDD_LS /xls VDD /'          "xls supply VDD_LS -> VDD (supplies merged)"
sed -e '/^XR1 /s/r_length=159.125e-6/r_length=140.0e-6/' "$SRC0" > xsch/res_mut.spice
if cmp -s "$SRC0" xsch/res_mut.spice; then log "== mutation XR1 L 159.125 -> 140: NOT APPLIED (BAD)"; mut_ok=0
else
  r=$(rsize xsch/res_mut.spice)
  if [[ $r == PASS* ]]; then log "== mutation XR1 r_length 159.125 -> 140 um: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation XR1 r_length 159.125 -> 140 um: FAIL (expected)  [${r:0:200}]"; fi
fi

lvs_ok=0; grep -q "^LVS PASS" summary.txt && lvs_ok=1
drc_ok=0; grep -q "^== magic DRC.*: count 0$" summary.txt && grep -q "^== KLayout DRC.*rules run [1-9][0-9]*: count 0$" summary.txt && drc_ok=1
[[ ${SKIP:-} == *klayout* ]] && grep -q "^== magic DRC.*: count 0$" summary.txt && drc_ok=1
ant_ok=1; [[ ${SKIP:-} != *antenna* ]] && ! grep -q "^== antenna.*violations 0," summary.txt && ant_ok=0
log "CHECK $([ $lvs_ok$drc_ok$ant_ok$rs_ok$mut_ok$m45_ok = 111111 ] && echo OK || echo FAIL)  (LVS vs xschem $lvs_ok, DRC $drc_ok, antenna $ant_ok, resistor sizes $rs_ok, mutations caught $mut_ok, no Metal4/5 $m45_ok)"
