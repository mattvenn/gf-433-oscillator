#!/usr/bin/env python3
"""Ring-stage topology comparison (schematic): starved (baseline) vs stack vs cfed (current-fed ring).
See vco_bias.netlist() for the three topologies. The reference is the 2026-11-08 winner (filter off).

  python3 sim/vco/topo_cmp.py sweep --name stack --set topo=stack --set cw=3e-15 --jobs 8 [--corners ..] [--temps 0,70]
      codes {0,1,2,3,5,8,12,20,31} x vctrl {0,1.65,3.3} per corner x T at 3.3 V -> build/vco/topo_<name>/sweep.json
  python3 sim/vco/topo_cmp.py tc --name stack --set ... --code 5     # tt: 0/27/70 C at 3.3 V, 27 C at 3.25/3.35 V
  python3 sim/vco/topo_cmp.py settle --name cfed --set ...           # cfed: vg after a code step 31->0 and 0->31
f is measured at the a0 mid-swing crossing ((min+max)/2 over 100-200 ns), so a ring that swings vg..VDD is timed
correctly; swing = a0 min/max over the same window.
"""
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
import vco_bias as vb  # noqa: E402

WINNER = dict(rideal=0, lnp=100.0, lnw=3.665, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)
CODES = [0, 1, 2, 3, 5, 8, 12, 20, 31]
VCS = [0.0, 1.65, 3.3]
HDR = """.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
"""


def bits(code, vdd, nb=5):
    return "".join(f"alter vbit{b} {vdd if (code >> b) & 1 else 0}\nalter vbitb{b} {0 if (code >> b) & 1 else vdd}\n"
                   for b in range(nb))


def deck(p, corner, points, tstop=200e-9):
    body, ics = vb.netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p["bits"]))
    vgm = f"meas tran vga AVG v(vg) FROM=100n TO={tstop}\n" if p["topo"] == "cfed" else "let vga = 0\n"
    ctl = ""
    for (code, vc, t, vdd) in points:
        ctl += f"""option temp={t}
alter vdd {vdd}
alter vctrl {vc}
{bits(code, vdd)}tran 5p {tstop} 0 5p
meas tran amin MIN v(a0) FROM=100n TO={tstop}
meas tran amax MAX v(a0) FROM=100n TO={tstop}
let vth = (amin + amax)/2
meas tran t1 WHEN v(a0)=$&vth RISE=1 TD=100n
meas tran t2 WHEN v(a0)=$&vth RISE=11 TD=100n
meas tran iavg AVG i(vdd) FROM=100n TO={tstop}
{vgm}let f = 10/(t2-t1)
let pw = -iavg*{vdd}
echo "TOP {code} {vc} {t} {vdd} $&f $&pw $&amin $&amax $&vga"
destroy all
"""
    return f"""* topo_cmp {p['topo']} {corner}
{HDR.format(corner=corner)}vdd vdd 0 3.3
vctrl vctrl 0 1.65
{src}{body}.ic {ics}
.control
{ctl}quit
.endc
.end
"""


def settle_deck(p, corner, temp, c0, c1, tstep=100e-9, tstop=600e-9):
    """Code step c0 -> c1 at tstep (bit lines switch in 100 ps); vg and f afterwards."""
    body, ics = vb.netlist(p)
    src = ""
    for b in range(p["bits"]):
        v0, v1 = (3.3 if (c0 >> b) & 1 else 0), (3.3 if (c1 >> b) & 1 else 0)
        src += f"vbit{b} bit{b} 0 PWL(0 {v0} {tstep} {v0} {tstep + 1e-10} {v1})\n"
        src += f"vbitb{b} bitb{b} 0 PWL(0 {3.3 - v0} {tstep} {3.3 - v0} {tstep + 1e-10} {3.3 - v1})\n"
    return f"""* settle {corner} {temp} {c0}->{c1}
{HDR.format(corner=corner)}vdd vdd 0 3.3
vctrl vctrl 0 1.65
{src}{body}.ic {ics}
.control
option temp={temp}
tran 5p {tstop} 0 5p
wrdata settle_{c0}_{c1}.txt v(vg) v(a0)
quit
.endc
.end
"""


def parse(log):
    out = []
    for m in re.finditer(r"^TOP (\S+) (\S+) (\S+) (\S+) (\S*) (\S+) (\S+) (\S+) (\S+)$", log, re.M):
        g = m.groups()
        f = float(g[4]) if g[4] else float("nan")
        out.append(dict(code=int(g[0]), vctrl=float(g[1]), temp=float(g[2]), vdd=float(g[3]), f=f, p_w=float(g[5]),
                        amin=float(g[6]), amax=float(g[7]), vg=float(g[8])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "tc", "settle"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--corners", default=",".join(vb.CORNERS))
    ap.add_argument("--temps", default="0,70")
    ap.add_argument("--codes", default=",".join(map(str, CODES)))
    ap.add_argument("--vcs", default="0,1.65,3.3")
    ap.add_argument("--code", type=int, default=5)
    ap.add_argument("--tstop", type=float, default=200e-9, help="tran length; f and swing are measured from 100 ns")
    a = ap.parse_args()
    p = dict(vb.P, **WINNER)
    for kv in a.set:
        k, v = kv.split("=")
        p[k] = v if isinstance(vb.P[k], str) else type(vb.P[k])(float(v))
    out = REPO / f"build/vco/topo_{a.name}"
    if a.mode == "settle":
        decks = [(f"st_{c0}_{c1}", settle_deck(p, "typical", 27, c0, c1)) for c0, c1 in ((31, 0), (0, 31))]
        vb.run(out, decks, a.jobs)
        for n, _ in decks:
            import numpy as np
            d = np.loadtxt(out / f"settle{n[2:]}.txt")
            t, vg = d[:, 0], d[:, 1]
            # vg averaged over a sliding 10 ns window (removes the ring ripple); settle = last time it is > 2 % of
            # the final step away from the final value
            w = 10e-9
            tt = np.arange(60e-9, t[-1] - w, 1e-9)
            avg = np.array([vg[(t >= x) & (t < x + w)].mean() for x in tt])
            v0, v1 = avg[np.searchsorted(tt, 85e-9)], avg[-1]
            bad = np.abs(avg - v1) > 0.02 * abs(v1 - v0)
            ts = tt[np.where(bad)[0][-1]] + w / 2 - 100e-9 if bad.any() else float("nan")
            r = dict(step=n, vg_before=v0, vg_after=v1, t_settle_2pct_ns=ts * 1e9)
            print(r)
            (out / f"{n}.json").write_text(json.dumps(r))
        return
    if a.mode == "tc":
        cts = [("typical", [(a.code, 1.65, t, 3.3) for t in (0, 27, 70)] + [(a.code, 1.65, 27, d) for d in (3.25, 3.35)])]
    else:
        pts = lambda t: [(c, v, t, 3.3) for c in map(int, a.codes.split(",")) for v in map(float, a.vcs.split(","))]
        cts = [(f"{c}_t{t}", pts(float(t))) for c in a.corners.split(",") for t in a.temps.split(",")]
    decks = [(f"{a.mode}_{n}", deck(p, n.split("_")[0], pts_, a.tstop)) for n, pts_ in cts]
    vb.run(out, decks, a.jobs)
    rows = []
    for n, _ in decks:
        for r in parse((out / f"{n}.log").read_text()):
            rows.append(dict(corner=n.split("_")[1], **r))
    (out / f"{a.mode}.json").write_text(json.dumps(dict(p=p, rows=rows), indent=1))
    for r in rows:
        print(f"{r['corner']:8s} {r['temp']:3.0f} {r['vdd']:.2f} c{r['code']:2d} vc{r['vctrl']:.2f} f {r['f']/1e6:7.1f} "
              f"P {r['p_w']*1e3:5.2f} mW a0 {r['amin']:.2f}-{r['amax']:.2f} vg {r['vg']:.2f}")


if __name__ == "__main__":
    main()
