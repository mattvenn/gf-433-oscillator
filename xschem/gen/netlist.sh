#!/bin/bash
# Netlist schematics headless (run in the image: tools/osic-mac xschem/gen/netlist.sh [schdir] [outdir] [names...]).
# Writes <outdir>/<name>.spice with the top .subckt uncommented (for netgen / simulation); fails on a missing symbol.
set -e
SCH=$(cd "${1:-xschem}" && pwd); mkdir -p "${2:-build/xsch}"; OUT=$(cd "${2:-build/xsch}" && pwd); shift 2 || true
cd "$SCH"
for s in ${@:-cfed_ring cfed_dac ring_core_v3 cgm_ref vco_cfed lsdiv}; do
  xschem -n -s -q -o "$OUT" $s.sch > "$OUT/$s.xlog" 2>&1
  sed -i -e 's/^\*\*\.subckt/.subckt/' -e 's/^\*\*\.ends/.ends/' "$OUT/$s.spice"
  if grep -q "IS MISSING" "$OUT/$s.spice"; then echo "MISSING symbol in $s"; exit 1; fi
  echo "netlisted $s: $(grep -c '^[XCR]' "$OUT/$s.spice") element lines"
done
