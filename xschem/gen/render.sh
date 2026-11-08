#!/bin/bash
# Render every schematic to SVG + PNG headless (xvfb), into docs/img/xschem/.
# Run in the image: tools/osic-mac xschem/gen/render.sh [names...]
cd "$(dirname "$0")/.."; mkdir -p ../docs/img/xschem
for s in ${@:-cfed_ring cfed_dac ring_core_v3 cgm_ref vco_cfed}; do
  timeout 90 xvfb-run -a xschem -q --command "xschem zoom_full; \
    xschem print svg ../docs/img/xschem/$s.svg; xschem print png ../docs/img/xschem/$s.png 1600 1000; \
    xschem exit closewindow force" $s.sch > /dev/null 2>&1
  ls -la ../docs/img/xschem/$s.svg ../docs/img/xschem/$s.png 2>&1 | awk '{print $5, $NF}'
done
