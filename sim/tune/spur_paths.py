#!/usr/bin/env python3
"""Which block carries the 25 MHz supply spur? (docs/tx_fine_tune.md, Fig. 3c; STATUS item 3)

    python3 sim/tune/spur_paths.py [run [case ...]|analyse]        -> build/tx_fine/spur_paths/{<case>/, result.json}

The c4 bench of phase_c.py with the r12 macro's measured clock charge (4.48 pC per 25 MHz cycle) on the tile supply
(3.3 V through the 1.32 ohm power switch, 9.8 pF decap). Each case leaves the ripple on one group's VDD connection
and moves every other group to a clean 3.3 V (net vddc):
  all     : every group on the rippled vdd (the c4q result, -45.5 dBc)
  none    : every group clean (the SD cell's own toggling, the control)
  ring    : the ring inverters' PMOS (XP0-4)
  mdac    : the medium DAC: unit sources, bias diode, steering-pair bodies (XMU*, XMPB, XSW*, XSD*)
  cdac    : the coarse DAC's transmission-gate PMOS bodies (XTP*)
The reference (XMP1/2, XMS1) only feeds vbn, and vbnf is held by a source in this bench (phase_c.ring_tran), so its
path is not tested here; neither are ground resistance, substrate coupling or routing coupling in the layout.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/tune"))
import phase_c as pc  # noqa: E402

OUT = REPO / "build/tx_fine/spur_paths"
GROUPS = {"ring": r"XP[0-4]", "mdac": r"X(MU\w+|MPB|SW\w+|SD\w+)", "cdac": r"XTP[0-4]", "ref": r"X(MP1|MP2|MS1)"}
CASES = {"all": set(GROUPS), "none": set(), "ring": {"ring"}, "mdac": {"mdac"}, "cdac": {"cdac"}}
# the fix to test: vg's 3 pF decap returned to VDD (rippled) instead of VSS, so vg follows the supply at 25 MHz and
# the ring's own supply (VDD - vg) stays quiet; cvg6: 6 pF
FIX = {"cvg_vdd": "Cvg vg vdd 3e-12", "cvg6_vdd": "Cvg vg vdd 6e-12"}


def deck(rippled, cvg="Cvg vg 0 3e-12"):
    """The path-isolation cases are the circuit they were run on (2026-11-12): the decap to VSS. vco_bias writes
    it to VDD since (cvg_to="vdd"), so put the old one back unless cvg says otherwise."""
    (_, text), = pc.jobs_c4(pc.QCLK["q_r12"], "x")
    assert "Cvg vg vdd 3e-12\n" in text
    text = text.replace("Cvg vg vdd 3e-12\n", cvg + "\n")
    text = text.replace("v(a0) v(vdd) v(vg)", "v(a0) v(vdd) v(vg) v(mo) v(pb)")
    text = text.replace("Rpg vsup vdd 1.32\n", "Rpg vsup vdd 1.32\nvclean vddc 0 3.3\n")
    out = []
    for ln in text.splitlines():
        g = next((k for k, rx in GROUPS.items() if re.match(rx + r"\s", ln)), None)
        if g and g not in rippled:
            ln = re.sub(r"(?<=\s)vdd(?=\s)", "vddc", ln)
        out.append(ln)
    return "\n".join(out) + "\n"


def run(which=None):
    jobs = [(OUT / c, deck(r)) for c, r in CASES.items()] + \
           [(OUT / c, deck(set(GROUPS), ln)) for c, ln in FIX.items()]
    jobs = [j for j in jobs if which is None or j[0].name in which]
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))


def analyse():
    res = {}
    for c in list(CASES) + list(FIX):
        if not (OUT / c / "deck.log").exists():
            continue
        r = pc.c4_result(OUT / c)
        res[c] = r
        s = r.get("spur_25m")
        print(f"{c:5s} spur 25 MHz {s[1] if s else float('nan'):7.1f} dBc   phase rms {r.get('phase_rms', 0)*1e3:.2f} mrad"
              f"   vdd p-p {r.get('vdd_pp', 0)*1e3:.1f} mV")
    (OUT / "result.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "run":
        run(sys.argv[2:] or None)
    analyse()
