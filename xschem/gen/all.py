"""Regenerate every schematic and symbol, leaves first: python3 xschem/gen/all.py"""
import cfed_ring, cfed_dac, ring_core_v3, cgm_ref, vco_cfed, lsdiv, vco_top

for m in (cfed_ring, cfed_dac, ring_core_v3, cgm_ref, vco_cfed, lsdiv, vco_top):
    m.build()
