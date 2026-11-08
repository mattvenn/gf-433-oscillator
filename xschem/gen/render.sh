#!/bin/bash
# Render schematics to SVG + PNG headless (xvfb), into docs/img/xschem/, as a light textbook page:
# white background, black wires and symbols. Each render is under a timeout so a hung xvfb can't linger.
# Run in the image: tools/osic-mac xschem/gen/render.sh [names...]
cd "$(dirname "$0")/.."; mkdir -p ../docs/img/xschem
LIGHT='set dark_colorscheme 0; set draw_grid 0; set light_colors {
 "#ffffff" "#000000" "#dddddd" "#000000" "#000000" "#8a1c1c" "#000000" "#555555" "#000000" "#000000"
 "#000000" "#000000" "#000000" "#000000" "#000000" "#000000" "#000000" "#000000" "#000000" "#000000"
 "#000000" "#000000"}; xschem build_colors'
declare -A SIZE=([cfed_ring]="1800 1000" [cfed_dac]="2200 1100" [ring_core_v3]="1600 1000" [cgm_ref]="1600 1700" [vco_cfed]="1400 1200" [ls_ac]="1800 1300" [tspc_t1]="1800 1300" [tspc_t2]="1800 1300" [lsdiv]="1800 900" [vco_top]="2000 1200")
for s in ${@:-cfed_ring cfed_dac ring_core_v3 cgm_ref vco_cfed ls_ac tspc_t1 tspc_t2 lsdiv vco_top}; do
  timeout 90 xvfb-run -a xschem -q --command "$LIGHT; xschem zoom_full; \
    xschem print svg ../docs/img/xschem/$s.svg; xschem print png ../docs/img/xschem/$s.png ${SIZE[$s]:-1600 1000}; \
    xschem exit closewindow force" $s.sch > /dev/null 2>&1
  ls -la ../docs/img/xschem/$s.svg ../docs/img/xschem/$s.png 2>&1 | awk '{print $5, $NF}'
done
