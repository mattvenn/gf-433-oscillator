#!/usr/bin/env python3
"""vctrl pull-down: 200 kOhm of ppolyf_u_1k (1 um wide, 193.91 um long, sim/tune/mdac.py rv) from vctrl to VSS.

    python3 layout/gen/vctrl_pd.py [--out build/layout_vctrl_pd] [--gds layout/vctrl_pd.gds]

It keeps the fine NMOS leg (gate vctrl) off when ua[0] is open, so the on-chip medium DAC does the fine tuning
(docs/tx_fine_tune.md); ua[0] can still drive vctrl on the bench (200 kOhm load).
Serpentine of 7 horizontal strips (1.0 um, pitch 1.7 um as cgm_ref's RF and lsdiv's R1); magic's length is the
sum of the strip rectangles plus (n - 1) x pitch for the bars. Terminals: a (strip 6, right end) and b (strip 0,
left end), each a poly contact with M1 and a via1 to an M2 pin.
"""
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ring_core import Cell  # noqa: E402

REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "sim/tune"))
import mdac  # noqa: E402

RPITCH = 1700
NRS = 7


def build(c):
    rtot = int(round(mdac.rv_length(mdac.M["rv"]) * 1000 / 5.0)) * 5
    D = 2440
    Ls = (rtot - (NRS - 1) * RPITCH - 2 * D) // NRS // 10 * 10
    D0 = (rtot - (NRS - 1) * RPITCH - NRS * Ls) // 2 // 5 * 5
    D8 = rtot - (NRS - 1) * RPITCH - NRS * Ls - D0
    assert min(D0, D8) >= 2400, (D0, D8)
    xa = 610 + D0 + 400
    xb = xa + Ls
    ry0 = 600
    for i in range(NRS):
        ys = ry0 + i * RPITCH
        x0 = xa - D0 if i == 0 else xa
        x1 = xb + D8 if i == NRS - 1 else xb
        c.r("hires", x0, ys, x1, ys + 1000)
        if i < NRS - 1:
            if i % 2 == 0:
                c.r("hires", xb, ys, xb + 1000, ys + RPITCH + 1000)
            else:
                c.r("hires", xa - 1000, ys, xa, ys + RPITCH + 1000)
    ys0, ys6 = ry0, ry0 + (NRS - 1) * RPITCH
    xe0, xe6 = xa - D0, xb + D8
    # b: strip 0, left end
    c.r("poly", xe0 - 610, ys0, xe0, ys0 + 1000)
    c.r("pc", xe0 - 545, ys0 + 65, xe0 - 315, ys0 + 935)
    c.r("m1", xe0 - 610, ys0, xe0 - 250, ys0 + 1000)
    c.via1(xe0 - 430, ys0 + 500)
    c.label("b", "m2", xe0 - 430, ys0 + 500, port=True)
    # a: strip 6, right end
    c.r("poly", xe6, ys6, xe6 + 610, ys6 + 1000)
    c.r("pc", xe6 + 315, ys6 + 65, xe6 + 545, ys6 + 935)
    c.r("m1", xe6 + 250, ys6, xe6 + 610, ys6 + 1000)
    c.via1(xe6 + 430, ys6 + 500)
    c.label("a", "m2", xe6 + 430, ys6 + 500, port=True)
    return dict(a=(xe6 + 430, ys6 + 500), b=(xe0 - 430, ys0 + 500), w=xe6 + 610 + 400, h=ys6 + 1000 + 600,
                length_nm=rtot)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/layout_vctrl_pd")
    ap.add_argument("--gds", default="layout/vctrl_pd.gds")
    a = ap.parse_args()
    out = REPO / a.out
    out.mkdir(parents=True, exist_ok=True)
    c = Cell("vctrl_pd")
    g = build(c)
    gds = REPO / a.gds
    (out / "vctrl_pd.tcl").write_text("drc off\nsnap internal\n" + c.tcl() + f"gds write {gds}\nquit -noprompt\n")
    (out / "vctrl_pd_src.spice").write_text(
        ".subckt vctrl_pd a b\n"
        f"XRV a b VSUBS ppolyf_u_1k r_width=1e-6 r_length={g['length_nm'] / 1000:.3f}e-6\n.ends vctrl_pd\n")
    rc = "/foss/pdks/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
    subprocess.run([str(REPO / "tools/osic-mac"), "bash", "-c",
                    f"cd {out} && magic -dnull -noconsole -rcfile {rc} vctrl_pd.tcl > magic.log 2>&1"], check=False)
    print(f"vctrl_pd {g['w'] / 1000:.2f} x {g['h'] / 1000:.2f} um, a {g['a']}, b {g['b']}, L {g['length_nm']} nm -> {gds}")


if __name__ == "__main__":
    main()
