#!/usr/bin/env python3
"""Run a sim/pad testbench at one corner (inside the image: tools/osic-mac python3 sim/pad/run.py tb_rdson tt).

Substitutes {PDK} {CORNER} {OUT} and any --set K=V into the deck, runs ngspice -b in build/pad/, prints the .meas lines.
"""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[1] / "build" / "pad"
CORNERS = {"tt": "typical", "ss": "ss", "ff": "ff", "sf": "sf", "fs": "fs"}


def run(tb, corner="tt", **kv):
    BUILD.mkdir(parents=True, exist_ok=True)
    tag = "_".join([tb, corner] + [f"{k}{Path(str(v)).stem}" for k, v in kv.items()])
    out = BUILD / f"{tag}.dat"
    deck = (HERE / f"{tb}.spice").read_text()
    subs = {"PDK": os.environ["PDK_ROOT"] + "/gf180mcuD/libs.tech/ngspice", "CORNER": CORNERS[corner], "OUT": str(out)}
    subs.update({k: str(v) for k, v in kv.items() if k != "MODELS"})
    for k, v in subs.items():
        deck = deck.replace("{" + k + "}", v)
    models = kv.get("MODELS")                     # MODELS=<netlist>: use it for both subckts (xschem check)
    if models:
        deck = deck.replace(".include tt_asw_5v0.spice", f".include {models}")
        deck = deck.replace(".include pad_model_gf180.spice\n", "")
        deck = deck.replace(".include pad_model_gf180.spice", "")
    deck = deck.replace(".include tt_asw_5v0.spice", f".include {HERE}/tt_asw_5v0.spice")
    deck = deck.replace(".include pad_model_gf180.spice", f".include {HERE}/pad_model_gf180.spice")
    cir = BUILD / f"{tag}.cir"
    cir.write_text(deck)
    p = subprocess.run(["ngspice", "-b", str(cir)], cwd=BUILD, capture_output=True, text=True)
    (BUILD / f"{tag}.log").write_text(p.stdout + p.stderr)
    meas = [l for l in p.stdout.splitlines() if "=" in l and not l.startswith(("Note", "Warning", "*", "Doing"))]
    return out, p.stdout + p.stderr, meas


if __name__ == "__main__":
    tb, corner = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "tt")
    kv = dict(a.split("=", 1) for a in sys.argv[3:])
    out, log, meas = run(tb, corner, **kv)
    print("\n".join(meas) or log[-3000:])
