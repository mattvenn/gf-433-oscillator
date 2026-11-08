#!/bin/bash
# Block checks for a GDS, adapted from the mixed-signal-asic skill's check.sh to gf180mcuD:
#   magic DRC (full), KLayout DRC (PDK gf180mcu.drc, variant D), magic antenna on a flattened copy in its own
#   session, netgen LVS against a schematic .subckt that FAILS on property errors.
# v2 copy: also passes feol=true beol=true (the 2026.05 image deck ignores decks=).
# Usage (repo root): bash layout/gen/check_v2.sh [gds] [top] [source.spice] [outdir]
#   defaults: layout/ring_core.gds ring_core layout/ref/ring_core.spice build/check/ring_core
# Results: <outdir>/magic_drc.txt, klayout_drc.lyrdb (+ summary), antenna.txt, lvs.report, summary.txt
set -u
REPO=$(pwd)
GDS=$(realpath "${1:-layout/ring_core.gds}")
B=${2:-ring_core}
SRC=$(realpath "${3:-layout/ref/ring_core.spice}")
OUT=${4:-build/check/$B}
SKIP=${SKIP:-}          # e.g. SKIP=klayout,antenna
SRC_CELL=${SRC_CELL:-$B} # source .subckt name, if it differs from the layout top (check_v3.sh: ring_core_v3)
mkdir -p "$OUT"; OUT=$(realpath "$OUT"); cd "$OUT"
export PDK_ROOT=${PDK_ROOT:-/foss/pdks} PDK=gf180mcuD
RC=$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc
: > summary.txt
log() { echo "$*" | tee -a summary.txt; }
log "gds $GDS  top $B  source $SRC ($SRC_CELL)  magic $(magic --version)  netgen $(netgen -batch quit 2>/dev/null | grep -o 'Netgen [0-9.]*' | head -1)  klayout $(klayout -v)"

# ---- magic DRC + LVS extraction (from the GDS) ----
cat > magic.tcl <<EOF
gds read $GDS
load $B
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
set fp [open magic_drc.txt w]
puts \$fp "count [drc list count total]"
set sc [cif scale out]
foreach {why boxes} [drc listall why] {
  set loc {}
  foreach b [lrange \$boxes 0 2] { lappend loc [lmap v \$b {format %.2f [expr {\$v * \$sc}]}] }
  puts \$fp "[llength \$boxes]  \$why   at \$loc"
}
close \$fp
extract do local
extract unique notopports
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -o ${B}_lay.spice
feedback save extract_feedback.txt
quit -noprompt
EOF
t0=$(date +%s)
magic -dnull -noconsole -rcfile $RC magic.tcl > magic.log 2>&1
log "== magic DRC ($(( $(date +%s) - t0 )) s): $(head -1 magic_drc.txt)"; tail -n +2 magic_drc.txt | head -20 | tee -a summary.txt

# ---- antenna: flattened copy, fresh session, debug on ----
if [[ $SKIP != *antenna* ]]; then
mkdir -p ant; cd ant
cat > ant.tcl <<EOF
gds read $GDS
load $B
flatten ${B}_flat
load ${B}_flat
select top cell
extract do local
extract all
puts "ANTENNA_BEGIN"
antennacheck debug
antennacheck
puts "FEEDBACK [feedback count]"
puts "ANTENNA_END"
quit -noprompt
EOF
t0=$(date +%s)
magic -dnull -noconsole -rcfile $RC ant.tcl > ../antenna.log 2>&1
cd ..
sed -n '/ANTENNA_BEGIN/,/ANTENNA_END/p' antenna.log > antenna.txt
log "== antenna ($(( $(date +%s) - t0 )) s): violations $(grep -ci 'violation' antenna.txt), feedback $(grep FEEDBACK antenna.txt | cut -d' ' -f2)"
grep -i -A1 'violation' antenna.txt | head -8 | tee -a summary.txt
fi

# ---- KLayout DRC (PDK deck) ----
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

# ---- netgen LVS ----
t0=$(date +%s)
netgen -batch lvs "${B}_lay.spice $B" "$SRC $SRC_CELL" $PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl lvs.report > netgen.log 2>&1
log "== LVS ($(( $(date +%s) - t0 )) s):"
grep -E "Circuits match|do not match|Netlists match|Final result|roperty errors|failed pin" lvs.report | tail -6 | tee -a summary.txt
if grep -q "Final result: Circuits match uniquely" lvs.report && ! grep -qi "property errors" lvs.report \
   && ! grep -qi "do not match" lvs.report; then log "LVS PASS"; else log "LVS FAIL"; fi
