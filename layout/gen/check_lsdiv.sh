#!/bin/bash
# lsdiv (level shifter + TSPC /4 + buffer) checks with the xschem schematic as the LVS source (repo root, in the image):
#   1. netlist xschem/lsdiv.sch headless (xschem/gen/netlist.sh) -> <outdir>/xsch/lsdiv.spice, then the LVS copy
#      lsdiv_lvs.spice with two documented edits:
#        - the "Cc a0 net1 2e-15" line removed: Cc is drawn as M2/M3 metal fingers, which extract as parasitic C,
#          not as a device (its value is checked by layout/gen/pex_lsdiv.sh instead);
#        - ppolyf_u_3k -> ppolyf_u_1k: magic's gf180mcuD tech extracts the hi-res poly layer only as ppolyf_u_1k
#          (the mask is the same; the sheet value is a process option, and the PDK's variant D LVS deck uses 1k).
#   2. check_v2.sh on the GDS: magic DRC, KLayout DRC (FEOL+BEOL; the summary line shows the rules that ran),
#      antenna, netgen LVS layout vs lsdiv_lvs.spice
#   3. R1 size: netgen treats the PDK resistor as a black box, so r_width / r_length of the extracted R1 are compared
#      with the source here (0.1 % tolerance)
#   4. mutation: three broken copies of the LVS source against the same extraction must all FAIL:
#      XL2n W 0.6 -> 0.7 (ls_ac), Xn3 gate clk -> net4 (tspc_t1), XB1p W 2.5 -> 2.0 (top)
# Usage: bash layout/gen/check_lsdiv.sh [gds] [outdir]     defaults: layout/lsdiv.gds build/check/lsdiv
#   SKIP=klayout,antenna   passed to check_v2.sh
# Results: <outdir>/summary.txt (last line CHECK OK / CHECK FAIL), lvs.report, lvs_mut*.report
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/lsdiv.gds}")
OUT=${2:-build/check/lsdiv}
mkdir -p "$OUT/xsch"; OUT=$(realpath "$OUT")
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
SETUP=$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl

# ---- 1. schematic netlist + LVS copy ----
NL=$(bash xschem/gen/netlist.sh xschem "$OUT/xsch" lsdiv) || { echo "netlist failed: $NL"; exit 1; }
SRC0=$OUT/xsch/lsdiv.spice
SRC=$OUT/xsch/lsdiv_lvs.spice
sed -e '/^Cc a0 /d' -e 's/ ppolyf_u_3k / ppolyf_u_1k /' "$SRC0" > "$SRC"
ncc=$(grep -c '^Cc a0 ' "$SRC0"); nr=$(grep -c ' ppolyf_u_3k ' "$SRC0")

# ---- 2. DRC / antenna / LVS ----
SRC_CELL=lsdiv bash layout/gen/check_v2.sh "$GDS" lsdiv "$SRC" "$OUT"
cd "$OUT"
log() { echo "$*" | tee -a summary.txt; }
log "== schematic: xschem/lsdiv.sch; $NL; LVS copy: removed $ncc Cc line(s), renamed $nr ppolyf_u_3k -> ppolyf_u_1k"

lvs() {  # lvs <a> <cell_a> <b> <cell_b> <tag>  -> 0 if "match uniquely" with no property errors
  netgen -batch lvs "$1 $2" "$3 $4" $SETUP $5.report > $5.log 2>&1
  grep -q "Final result: Circuits match uniquely" $5.report && ! grep -qi "property errors" $5.report \
    && ! grep -qi "do not match" $5.report
}
why() { grep -E "Final result|roperty errors|do not match" $1.report | sort -u | tr '\n' ' '; }

# ---- 3. R1 size (black box in netgen) ----
r1=$(python3 - "$SRC" lsdiv_lay.spice <<'PYEOF'
import re, sys
SUF = dict(m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15)
def num(v):
    m = re.fullmatch(r"([-+\d.eE]+?)([munpf]?)", v.strip())
    return float(m.group(1)) * SUF.get(m.group(2), 1)
def res(path):
    txt = re.sub(r"\n\+", " ", open(path).read())
    out = []
    for ln in txt.splitlines():
        if "ppolyf" in ln and ln[:1] in "Xx":
            kv = dict(x.split("=", 1) for x in ln.split() if "=" in x)
            model = [x for x in ln.split()[1:] if "=" not in x][-1]
            out.append((model, num(kv["r_width"]), num(kv["r_length"])))
    return out
src, lay = res(sys.argv[1]), res(sys.argv[2])
ok = len(src) == len(lay) == 1 and src[0][0] == lay[0][0] and all(abs(a / b - 1) < 1e-3 for a, b in zip(src[0][1:], lay[0][1:]))
print(("PASS" if ok else "FAIL") + f"  source {src}  layout {lay}  (w, l in m; model after the LVS rename)")
PYEOF
)
log "== R1 size check: $r1"
r1_ok=0; [[ $r1 == PASS* ]] && r1_ok=1

# ---- 4. mutation tests (reuse the layout extraction from step 2) ----
mut_ok=1
mutate() {  # mutate <tag> <sed expr> <description>
  sed -e "$2" "$SRC" > xsch/$1.spice
  if cmp -s "$SRC" xsch/$1.spice; then log "== mutation $3: NOT APPLIED (BAD)"; mut_ok=0; return; fi
  if lvs lsdiv_lay.spice lsdiv xsch/$1.spice lsdiv $1; then
    log "== mutation $3: PASS (BAD: not caught)"; mut_ok=0
  else log "== mutation $3: FAIL (expected)  [$(why $1)]"; fi
}
mutate lvs_mut_w   '/^XL2n /s/W=0.6u/W=0.7u/'                 "XL2n W 0.6 -> 0.7 (ls_ac)"
mutate lvs_mut_net '/subckt tspc_t1/,/ends/{/^Xn3 /s/ clk VSS / net4 VSS /}' "tspc_t1 Xn3 gate clk -> net4"
mutate lvs_mut_b1  '/^XB1p /s/W=2.5u/W=2.0u/'                 "XB1p W 2.5 -> 2.0"

lvs_ok=0; grep -q "^LVS PASS" summary.txt && lvs_ok=1
drc_ok=0; grep -q "^== magic DRC.*: count 0$" summary.txt && grep -q "^== KLayout DRC.*rules run [1-9][0-9]*: count 0$" summary.txt && drc_ok=1
[[ ${SKIP:-} == *klayout* ]] && grep -q "^== magic DRC.*: count 0$" summary.txt && drc_ok=1
ant_ok=1; [[ ${SKIP:-} != *antenna* ]] && ! grep -q "^== antenna.*violations 0," summary.txt && ant_ok=0
log "CHECK $([ $lvs_ok$drc_ok$ant_ok$r1_ok$mut_ok = 11111 ] && echo OK || echo FAIL)  (LVS vs xschem $lvs_ok, DRC $drc_ok, antenna $ant_ok, R1 size $r1_ok, mutations caught $mut_ok)"
