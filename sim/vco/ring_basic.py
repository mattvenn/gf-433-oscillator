#!/usr/bin/env python3
"""Phase-1 probe: plain GF180 3.3 V inverter ring (nfet/pfet_03v3).

Frequency, supply current and df/dVDD vs stage count, corner and temperature.
Run from the repo root on the host:  python3 sim/vco/ring_basic.py [--quick]
Decks and logs go to build/vco/ring_basic/. One ngspice per corner (the corner is a .lib
section); stage count / VDD / temp are swept inside that process where possible.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "build/vco/ring_basic"
OSIC = os.environ.get("OSIC", str(REPO / "tools/osic-mac"))

# device geometry
L = 0.28      # um, min L for 03v3
SAB = 0.5     # um, S/D diffusion length used for AD/AS (estimate, calibrate after layout)
CW = 2e-15    # F, wiring C per ring node (estimate, calibrate after first extraction)


def inv_line(name, a, y, wn, wp):
    adn, adp = wn * SAB, wp * SAB
    pdn, pdp = 2 * (wn + SAB), 2 * (wp + SAB)
    return (f"XMP{name} {y} {a} vdd vdd pfet_03v3 w={wp}u l={L}u ad={adp}p as={adp}p pd={pdp}u ps={pdp}u\n"
            f"XMN{name} {y} {a} 0 0 nfet_03v3 w={wn}u l={L}u ad={adn}p as={adn}p pd={pdn}u ps={pdn}u\n"
            f"C{name} {y} 0 {CW}\n")


def deck(corner, n, wn, wp, temps, vdds):
    nodes = [f"n{i}" for i in range(n)]
    body = "".join(inv_line(i, nodes[i], nodes[(i + 1) % n], wn, wp) for i in range(n))
    meas = []
    for t in temps:
        for v in vdds:
            tag = f"{corner}_n{n}_t{t}_v{int(v*100)}"
            meas.append(f"""
option temp={t}
alter vdd {v}
tran 2p {20+3*n}n 0 2p uic
meas tran per TRIG v(n0) VAL={v/2} RISE=5 TARG v(n0) VAL={v/2} RISE=15
meas tran iavg AVG i(vdd) FROM=10n TO={20+3*n}n
let f = 10/per
let p = -iavg*{v}
echo "RES {tag} {t} {v} $&f $&p"
destroy all""")
    ics = " ".join(f"v(n{i})={0 if i % 2 == 0 else 3.3}" for i in range(n))
    return f"""* ring {n} stages {corner}
.include {{PDK_ROOT}}/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib {{PDK_ROOT}}/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
vdd vdd 0 3.3
{body}
.ic {ics}
.control
{''.join(meas)}
quit
.endc
.end
"""


def run(decks):
    OUT.mkdir(parents=True, exist_ok=True)
    names = []
    for name, text in decks:
        (OUT / f"{name}.cir").write_text(text.replace("{PDK_ROOT}", "/foss/pdks"))
        names.append(name)
    rel = OUT.relative_to(REPO)
    script = " ; ".join(f"ngspice -b {rel}/{n}.cir > {rel}/{n}.log 2>&1" for n in names)
    subprocess.run([OSIC, "bash", "-c", f"cd {REPO} && {script}"], check=False)
    rows = []
    for n in names:
        log = (OUT / f"{n}.log").read_text()
        if "Transient op started" in log or "singular" in log:
            print(f"WARN {n}: op problem", file=sys.stderr)
        for m in re.finditer(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+)", log, re.M):
            rows.append((m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))))
        if not re.search(r"^RES", log, re.M):
            print(f"ERROR {n}: no results; tail:\n" + "\n".join(log.splitlines()[-15:]), file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--wn", type=float, default=2.0)
    ap.add_argument("--wp", type=float, default=5.0)
    a = ap.parse_args()
    if a.quick:
        corners, stages, temps, vdds = ["typical"], [5, 9], [27], [3.3]
    else:
        corners = ["typical", "ss", "ff", "sf", "fs"]
        stages = [5, 7, 9, 11, 13, 15]
        temps = [0, 27, 70]
        vdds = [3.15, 3.3, 3.45]
    decks = [(f"ring_{c}_n{n}", deck(c, n, a.wn, a.wp, temps, vdds)) for c in corners for n in stages]
    rows = run(decks)
    print(f"{'case':28s} {'T':>4s} {'VDD':>5s} {'f MHz':>8s} {'P mW':>6s}")
    for tag, t, v, f, p in rows:
        print(f"{tag:28s} {t:4.0f} {v:5.2f} {f/1e6:8.1f} {p*1e3:6.2f}")


if __name__ == "__main__":
    main()
