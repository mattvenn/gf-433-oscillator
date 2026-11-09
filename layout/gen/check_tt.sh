#!/bin/bash
# LVS of the Tiny Tapeout wrapper (gds/tt_um_mattvenn_gf433_vco.gds) against lvs/tt_um_mattvenn_gf433_vco.spice
# (lvs/make_source.py: the xschem vco_top netlist with the documented edits + inv_1 / tiel / antenna + the TT top).
# Runs locally (in the image) and in CI (.github/workflows/lvs.yaml); repo-relative, PDK from $PDK_ROOT.
#   1. magic: gds read; repaint the n-well resistor as rnw in cell cgm_ref from NWELL & RES_MK (magic's gf180mcuD
#      cifinput has no rnw rule, docs/ref_layout.md; boxes taken from the GDS with KLayout's Python module);
#      flatten -dotoplabels (only the wrapper's own pin labels survive, so the blocks' VDD labels can't join
#      VDD and VDD_LS by name), extract, ext2spice lvs.
#   2. netgen LVS, flat layout vs the source: pass = "Final result: Circuits match uniquely." with no property
#      errors, no pin-matching failure and no "do not match".
#   3. resistor sizes (netgen black-boxes the PDK resistors): each nwell / nplus_u / ppolyf_u_1k in the source
#      matched to one in the layout by model and size (W 0.1 %, L 1 %).
#   4. mutations, each must FAIL: (a) ui_in[0] and ui_in[1] swapped at the inverters, (b) ck moved from uo_out[0]
#      to uo_out[1] (and its tiel to uo_out[0]), (c) the VDD_LS decap m 5 -> 4 (property error), (d) the TX
#      driver's outputs swapped (ua[2] <-> ua[3]), (e) its enables swapped (ui_in[5] <-> ui_in[6]).
# Usage: bash layout/gen/check_tt.sh [gds] [source] [outdir]
#   defaults gds/tt_um_mattvenn_gf433_vco.gds lvs/tt_um_mattvenn_gf433_vco.spice build/check/tt
#   env: PDK_ROOT (default /foss/pdks), MAGIC (default: magic; use 8.3.642, see CLAUDE.md), NETGEN (default netgen)
# Exit 0 only if LVS passes, the resistor sizes match and every mutation is caught. Summary: <outdir>/summary.txt
set -u
T=tt_um_mattvenn_gf433_vco
GDS=$(realpath "${1:-gds/$T.gds}")
SRC=$(realpath "${2:-lvs/$T.spice}")
OUT=${3:-build/check/tt}
mkdir -p "$OUT/mut"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
MAGIC=${MAGIC:-magic}
NETGEN=${NETGEN:-netgen}
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
for f in "$GDS" "$SRC" "$SETUP" "$RC"; do [ -f "$f" ] || { echo "missing $f"; exit 2; }; done
cd "$OUT"
: > summary.txt
log() { echo "$*" | tee -a summary.txt; }
log "gds $GDS  source $SRC  PDK_ROOT $PDK_ROOT"
log "magic $($MAGIC --version 2>/dev/null)  $($NETGEN -batch quit 2>/dev/null | grep -o 'Netgen [0-9.]*' | head -1)"

# ---- 1. rnw repaint commands (cgm_ref's own coordinates) + extraction ----
python3 - "$GDS" > rnwfix.tcl <<'PYEOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); c = ly.cell("cgm_ref")
r = db.Region(c.begin_shapes_rec(ly.find_layer(21, 0))) & db.Region(c.begin_shapes_rec(ly.find_layer(110, 5)))
print("load cgm_ref")
for p in r.each():
    b = p.bbox().to_dtype(ly.dbu)
    print(f"box {b.left:.3f}um {b.bottom:.3f}um {b.right:.3f}um {b.top:.3f}um; paint rnw")
PYEOF
[ "$(grep -c 'paint rnw' rnwfix.tcl)" -ge 1 ] || { log "rnw repaint: no NWELL & RES_MK box found"; exit 1; }
log "== rnw repaint in cgm_ref: $(grep -c 'paint rnw' rnwfix.tcl) box(es)"
{
echo "gds read $GDS"
cat rnwfix.tcl
cat <<TCL
load $T
flatten -dotoplabels ${T}_flat
load ${T}_flat
cellname delete $T
cellname rename ${T}_flat $T
select top cell
extract do local
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -o ${T}_lay.spice
quit -noprompt
TCL
} > extract.tcl
t0=$(date +%s)
$MAGIC -dnull -noconsole -rcfile "$RC" extract.tcl > magic.log 2>&1
[ -s ${T}_lay.spice ] || { log "extraction failed (magic.log)"; tail -20 magic.log; exit 1; }
log "== extraction ($(( $(date +%s) - t0 )) s): $(grep -c '^X' ${T}_lay.spice) X devices, $(grep -c '^D' ${T}_lay.spice) D devices"
log "   layout ports: $(awk '/^.subckt/{f=1; n=NF-2; next} f && /^\+/{n+=NF-1; next} f{print n; exit}' ${T}_lay.spice)"

# ---- 2. netgen LVS ----
# The PDK setup declares the two-terminal resistors permutable (pins 1 2) but lists nwell_1p5, not nwell: the
# mirrored placement swaps RBW's terminals in the extraction, so permute nwell's pins 1 2 the same way.
cat > lvs_setup.tcl <<TCL
source $SETUP
foreach c {1 2} {
    if {[lsearch [set cells\$c] nwell] >= 0} { permute "-circuit\$c nwell" 1 2 }
}
TCL
lvs() {  # lvs <source> <tag> -> 0 if "match uniquely" with no property errors / pin failures
  $NETGEN -batch lvs "${T}_lay.spice $T" "$1 $T" lvs_setup.tcl "$2.report" > "$2.log" 2>&1
  grep -q "Final result: Circuits match uniquely" "$2.report" && ! grep -qi "property errors" "$2.report" \
    && ! grep -qi "do not match" "$2.report" && ! grep -qi "failed pin matching" "$2.report"
}
why() { grep -E "Final result|roperty errors|do not match|pin matching" "$1.report" | sort -u | tr '\n' ' '; }
t0=$(date +%s)
if lvs "$SRC" lvs; then r=PASS; else r=FAIL; fi
log "== LVS ($(( $(date +%s) - t0 )) s):"
grep -E "Final result|roperty errors|failed pin|do not match|Netlists match|Circuits match" lvs.report | sort -u \
  | tee -a summary.txt
log "LVS $r"

# ---- 3. resistor sizes ----
rs=$(python3 - "$SRC" ${T}_lay.spice <<'PYEOF'
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
ok = len(src) == len(lay) > 0
txt = []
for s, l in zip(src, lay):
    good = s[0] == l[0] and abs(s[1] / l[1] - 1) < 1e-3 and abs(s[2] / l[2] - 1) < 0.01
    ok &= good
    txt.append(f"{s[0]} {s[1]*1e6:.4g}/{s[2]*1e6:.6g} vs {l[1]*1e6:.4g}/{l[2]*1e6:.6g} um" + ("" if good else " BAD"))
print(("PASS" if ok else "FAIL") + f"  {len(src)} source / {len(lay)} layout: " + "; ".join(txt))
PYEOF
)
log "== resistor sizes: $rs"

# ---- 4. mutations ----
mut_ok=1
mutate() {  # mutate <tag> <description> <sed expr>...
  local tag=$1 desc=$2; shift 2
  local args=(); for e in "$@"; do args+=(-e "$e"); done
  sed "${args[@]}" "$SRC" > mut/$tag.spice
  if cmp -s "$SRC" mut/$tag.spice; then log "== mutation $desc: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs mut/$tag.spice mut/$tag; then log "== mutation $desc: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $desc: FAIL (expected)  [$(why mut/$tag)]"; fi
}
mutate swap "ui_in[0] <-> ui_in[1] at the inverters" \
  '/^xinv0 /s/^xinv0 ui_in\[0\]/xinv0 ui_in[1]/' '/^xinv1 /s/^xinv1 ui_in\[1\]/xinv1 ui_in[0]/'
mutate ck "ck on uo_out[1], its tiel on uo_out[0]" \
  '/^xvco /s/ uo_out\[0\] / uo_out[1] /' '/^xtie_uo_out_1 /s/ uo_out\[1\] / uo_out[0] /'
mutate dcls "VDD_LS decap m 5 -> 4" '/^XDCLS /s/m=5$/m=4/'
mutate txout "tx_drv out_p <-> out_n (ua[3] <-> ua[2])" '/^xtx /s/ ua\[3\] ua\[2\] / ua[2] ua[3] /'
mutate txen "tx_drv en_p <-> en_n (ui_in[5] <-> ui_in[6])" '/^xtx /s/ ui_in\[5\] ui_in\[6\] / ui_in[6] ui_in[5] /'

ok=0; [[ $r == PASS && $rs == PASS* && $mut_ok == 1 ]] && ok=1
log "CHECK $([ $ok = 1 ] && echo OK || echo FAIL)  (LVS $r, resistor sizes ${rs%% *}, mutations caught $mut_ok)"
[ $ok = 1 ]
