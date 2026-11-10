#!/usr/bin/env python3
"""Medium DAC (fine tuning) for the current-fed ring: schematic netlist and benches (docs/tx_fine_tune.md, phase A).

Circuit (all from the constant-gm reference, so the LSB tracks the coarse step):
  bias   : MB  = nbn coarse units (nfet 1.2/5.33, gate vbnf) sinking from pb;  MPB = nbp PMOS units, diode on pb.
           Dummy PMOS fingers (the unused slots of the binary rows, drain = source = VDD, gate pb) are in the layout
           and in the LVS source (layout/gen/mdac.py); they carry no current and are left out of the benches.
           One PMOS unit then carries I_L = Iu * nbn / nbp (Iu = one coarse unit's current).
  array  : PMOS unit (wu/lu, gate pb, source VDD) groups: 31 unary segments of 32 units (word[9:5], thermometer),
           binary 16/8/4/2/1 units (word[4:0]), one sigma-delta cell of 1 unit (sd), and `off` units always on.
           Each group's drain c<g> is steered by a PMOS pair: SW to mo (gate n<g>, the active-low control line from
           the macro: 0 V = on) and SD to md with its gate on mo. On (n<g> = 0): c<g> sits a few mV above mo, so SD
           has VSG ~ 0 and is off. Off (n<g> = VDD): c<g> rises to mo + |Vt| and SD carries the current to the dump.
           So one control line per group, the cell current never stops, and the bias line sees no load step.
  output : MD  = na coarse units, diode on mo;  MO = nb coarse units, gate mo, drain vg (sinks from the ring).
           MDD = a small diode on md (the dump; its voltage only needs to stay below the cells' compliance).
           I_out = (word + sd + off) * I_L * nb / na.
  vctrl  : RV (ppolyf_u_1k) from vctrl to VSS (the fine NMOS leg is off by default); ua[0] can still override it.

    python3 sim/tune/mdac.py ideal  [--corners ...]        # ideal current into vg: f vs I and the coarse steps
    python3 sim/tune/mdac.py fword  [--corners ...]        # transistor DAC: f vs word at the 433.92 code
    python3 sim/tune/mdac.py dc     --corner typical       # DAC output current vs every word (vg held), nominal
    python3 sim/tune/mdac.py mc     --corner typical --n 200 --jobs 26   # same, mismatch on, one sample per process
Outputs: build/tx_fine/mdac/<mode>_*.json
"""
import argparse, json, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "xschem/gen"))
import vco_bias as vb  # noqa: E402
OSIC = os.environ.get("OSIC", str(REPO / "tools/osic-mac"))
OUT = REPO / "build/tx_fine/mdac"
CORNERS = ("typical", "ss", "ff", "sf", "fs")
CODE433 = {"typical": 9, "ss": 11, "ff": 7, "sf": 9, "fs": 10}   # docs/remap_results.md (extracted); schematic: fs 9

# design point (phase A choice; see docs/tx_fine_tune.md)
M = dict(wu=1.0, lu=4.0,           # PMOS unit (um)
         nbn=1, nbp=64,            # bias: 1 coarse unit into a 64-unit PMOS diode -> I_L = Iu/64
         nseg=31, segu=32, nbin=5, # 5 unary MSB (31 x 32 units) + 5 binary LSB
         off=32,                   # always-on units (keeps MD alive at word 0)
         na=30, nb=3,              # output mirror: MD 30 coarse units, MO 3 -> FS 1023/64 x 3/30 = 1.6 Iu
         wsw=1.0, lsw=0.28,        # steering switches (PMOS)
         wdd=3.4, ldd=1.0, ndd=2,  # dump diode MDD: 2 fingers 3.4/1 (W/L 6.8, about MD's 30 x 1.2/5.33 = 6.75)
         rv=200e3)                 # vctrl pull-down (ohm)
VBNF = {"typical": 1.23197, "ss": 1.38407, "ff": 1.08278}


def base_p(sets=()):
    import common
    return common.params(sets)


def unit_n(p):
    """Coarse DAC unit W/L (um) exactly as vco_bias.netlist() topo=cfed."""
    kw, kl = max(p["kc"], 1.0), 1.0 / min(p["kc"], 1.0)
    kw, kl = kw * p["ka"] ** 0.5, kl * p["ka"] ** 0.5
    return p["wfu"] * kw, p["ls"] * kl


def groups(m):
    """[(name, units)] in word order: unary segments s1..s31, binary b4..b0, sd, off."""
    g = [(f"s{i}", m["segu"]) for i in range(1, m["nseg"] + 1)]
    g += [(f"b{b}", 1 << b) for b in reversed(range(m["nbin"]))]
    return g + [("sd", 1), ("off", m["off"])]


def word_bits(word, sd=0, m=M):
    """{group: 0/1} for a 10-bit word (+ sd bit). Unary: segments 1..(word>>5) on."""
    hi, lo = word >> m["nbin"], word & ((1 << m["nbin"]) - 1)
    st = {f"s{i}": int(i <= hi) for i in range(1, m["nseg"] + 1)}
    st.update({f"b{b}": (lo >> b) & 1 for b in range(m["nbin"])})
    st["sd"] = sd
    st["off"] = 1
    return st


def mdac_netlist(p, m=M, split=False, g="vbnf"):
    """The medium DAC as netlist lines (vco_bias fet() style). split=True: every m>1 device as unit instances (MC)."""
    wn, ln = unit_n(p)
    s = ""

    def dev(name, d, gg, src, b, typ, w, l, mm):
        if split and mm > 1:
            return "".join(vb.fet(f"{name}u{i}", d, gg, src, b, typ, w, l) for i in range(mm))
        return vb.fet(name, d, gg, src, b, typ, w, l, mm)
    s += dev("MB", "pb", g, "0", "0", "nfet_03v3", wn, ln, m["nbn"])
    s += dev("MPB", "pb", "pb", "vdd", "vdd", "pfet_03v3", m["wu"], m["lu"], m["nbp"])
    for name, n in groups(m):
        s += dev(f"MU{name}", f"c{name}", "pb", "vdd", "vdd", "pfet_03v3", m["wu"], m["lu"], n)
        if name == "off":
            s += f"Roff c{name} mo 1\n"
            continue
        s += vb.fet(f"SW{name}", f"c{name}", f"n{name}", "mo", "vdd", "pfet_03v3", m["wsw"], m["lsw"])
        s += vb.fet(f"SD{name}", f"c{name}", "mo", "md", "vdd", "pfet_03v3", m["wsw"], m["lsw"])
    s += dev("MD", "mo", "mo", "0", "0", "nfet_03v3", wn, ln, m["na"])
    s += dev("MDD", "md", "md", "0", "0", "nfet_03v3", m["wdd"], m["ldd"], m["ndd"])
    s += dev("MO", "vgo", "mo", "0", "0", "nfet_03v3", wn, ln, m["nb"])
    return s


def ctl_sources(m=M, word=512, sd=0, vdd=3.3):
    st = word_bits(word, sd, m)
    return "".join(f"vn{k} n{k} 0 {vdd * (1 - v)}\n" for k, v in st.items() if k != "off")


def ctl_alter(word, sd=0, m=M, vdd=3.3):
    st = word_bits(word, sd, m)
    return "".join(f"alter vn{k} {vdd * (1 - v)}\n" for k, v in st.items() if k != "off")


HDR = """.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
"""


def fmeas(tag, tstop=200e-9, extra=""):
    return f"""tran 5p {tstop} 0 5p
meas tran amin MIN v(a0) FROM=100n TO={tstop}
meas tran amax MAX v(a0) FROM=100n TO={tstop}
let vth = (amin + amax)/2
meas tran t1 WHEN v(a0)=$&vth RISE=1 TD=100n
meas tran t2 WHEN v(a0)=$&vth RISE=11 TD=100n
meas tran vga AVG v(vg) FROM=100n TO={tstop}
meas tran imo AVG i(vam) FROM=100n TO={tstop}
{extra}let f = 10/(t2-t1)
echo "F {tag} $&f $&vga $&imo $&amin $&amax"
destroy all
"""


def ring_deck(p, corner, temp, code, ctl, mdac=True, iideal=0.0, vctrl=None, m=M):
    """Ring + reference (+ medium DAC on vg through the ammeter vam). vctrl=None: the RV pull-down only."""
    body, ics = vb.netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 {3.3 if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else 3.3}\n"
                  for b in range(p["bits"]))
    vc = f"vctrl vctrl 0 {vctrl}\n" if vctrl is not None else ""
    rv = f"XRV vctrl 0 0 ppolyf_u_1k r_width=1e-6 r_length={rv_length(m['rv']):.2f}e-6\n"
    md = (mdac_netlist(p, m, g=vb.gnet(p)) + ctl_sources(m)) if mdac else f"Iid vgo 0 {iideal}\n"
    return f"""* mdac ring {corner} {temp}
{HDR.format(corner=corner)}vdd vdd 0 3.3
{vc}{rv}{src}{body}vam vg vgo 0
{md}.ic {ics}
.option temp={temp}
.control
{ctl}quit
.endc
.end
"""


def rv_length(r, w=1.0):
    rsh, dw, rt = vb.HRES["1k"]
    return (r - 2 * rt / (w - 2 * dw)) * (w - 2 * dw) / rsh


def run(decks, jobs=1, od=OUT):
    od.mkdir(parents=True, exist_ok=True)
    init = (REPO / ".spiceinit").read_text()
    (od / ".spiceinit").write_text(re.sub(r"num_threads=\d+", "num_threads=1", init))
    for n, t in decks:
        (od / f"{n}.cir").write_text(t)
    one = lambda n: subprocess.run([OSIC, "bash", "-c", f"cd {od} && ngspice -b {n}.cir > {n}.log 2>&1"], check=False)
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(one, [n for n, _ in decks]))
    logs = {}
    for n, _ in decks:
        lg = (od / f"{n}.log").read_text()
        if "singular" in lg.lower() or "transient op started" in lg.lower():
            print(f"WARN {n}: singular / transient op in log", file=sys.stderr)
        logs[n] = lg
    return logs


def parse_f(lg):
    out = {}
    for mm in re.finditer(r"^F (\S+) (\S*) (\S+) (\S+) (\S+) (\S+)$", lg, re.M):
        out[mm.group(1)] = dict(f=float(mm.group(2)) if mm.group(2) else float("nan"), vg=float(mm.group(3)),
                               imo=float(mm.group(4)), amin=float(mm.group(5)), amax=float(mm.group(6)))
    return out


def iu_deck(p, corner, temp):
    """One coarse unit's current at vds 1.9 V (gate vbnf from the full reference, op)."""
    body, _ = vb.netlist(dict(p, n=0))
    wn, ln = unit_n(p)
    return f"""* iu
{HDR.format(corner=corner)}vdd vdd 0 3.3
vctrl vctrl 0 0
{''.join(f'vbit{b} bit{b} 0 0{chr(10)}vbitb{b} bitb{b} 0 3.3{chr(10)}' for b in range(p['bits']))}{body}{vb.fet('XU', 'du', vb.gnet(p), '0', '0', 'nfet_03v3', wn, ln)}vdu du 0 1.9
.option temp={temp}
.control
op
let iu = -i(vdu)
let vbf = v({vb.gnet(p)})
echo "IU $&iu $&vbf"
quit
.endc
.end
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["ideal", "fword", "dc", "mc", "iu", "noise"])
    ap.add_argument("--corners", default=",".join(CORNERS))
    ap.add_argument("--corner", default="typical")
    ap.add_argument("--temp", type=float, default=27)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=5000)
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--words", default="0,1,31,32,256,511,512,513,767,1023")
    ap.add_argument("--set", action="append", default=[], help="medium DAC overrides k=v")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    p = base_p()
    m = dict(M)
    for kv in a.set:
        k, v = kv.split("="); m[k] = type(M[k])(float(v))
    corners = a.corners.split(",")
    tag = a.tag or a.mode
    if a.mode == "iu":
        logs = run([(f"iu_{c}", iu_deck(p, c, a.temp)) for c in corners], a.jobs)
        res = {}
        for c in corners:
            mm = re.search(r"^IU (\S+) (\S+)", logs[f"iu_{c}"], re.M)
            res[c] = dict(iu=float(mm.group(1)), vbnf=float(mm.group(2)))
            print(f"{c:8s} Iu {res[c]['iu']*1e6:.3f} uA  vbnf {res[c]['vbnf']:.4f} V")
        (OUT / "iu.json").write_text(json.dumps(res, indent=1))
        return
    if a.mode == "ideal":   # f at code c and c+1 (I=0), and code c with an ideal sink 0..2 Iu
        iu = json.loads((OUT / "iu.json").read_text())
        decks = []
        for c in corners:
            k = CODE433[c]
            ctl = ""
            for code in (k - 1, k, k + 1):
                ctl += vb_bits_alter(code) + "alter iid 0\n" + fmeas(f"c{code}_i0")
            for x in (0.25, 0.5, 1.0, 1.5, 2.0):
                ctl += vb_bits_alter(k) + f"alter iid {x * iu[c]['iu']}\n" + fmeas(f"c{k}_i{x}")
            decks.append((f"ideal_{c}", ring_deck(p, c, a.temp, k, ctl, mdac=False)))
        logs = run(decks, a.jobs)
        res = {}
        for c in corners:
            r = parse_f(logs[f"ideal_{c}"]); k = CODE433[c]; res[c] = r
            st = [r[f"c{k}_i0"]["f"] - r[f"c{k-1}_i0"]["f"], r[f"c{k+1}_i0"]["f"] - r[f"c{k}_i0"]["f"]]
            fi = {x: r[f"c{k}_i{x}"]["f"] - r[f"c{k}_i0"]["f"] for x in (0.25, 0.5, 1.0, 1.5, 2.0)}
            print(f"{c:8s} code {k}: f {r[f'c{k}_i0']['f']/1e6:.2f} MHz, steps {st[0]/1e6:.2f} / {st[1]/1e6:.2f} MHz; "
                  f"ideal sink (x Iu): " + " ".join(f"{x}: {v/1e6:+.2f}" for x, v in fi.items()))
        (OUT / f"{tag}.json").write_text(json.dumps(res, indent=1))
        return
    if a.mode == "fword":
        words = [int(w) for w in a.words.split(",")]
        decks = []
        for c in corners:
            k = CODE433[c]
            ctl = ""
            for code in (k, k + 1):
                ctl += vb_bits_alter(code) + ctl_alter(0, 0, m) + fmeas(f"c{code}_w0")
            for w in words:
                ctl += vb_bits_alter(k) + ctl_alter(w, 0, m) + fmeas(f"c{k}_w{w}")
            ctl += vb_bits_alter(k) + ctl_alter(512, 1, m) + fmeas(f"c{k}_w512sd")
            decks.append((f"fword_{c}", ring_deck(p, c, a.temp, k, ctl, mdac=True, m=m)))
        logs = run(decks, a.jobs)
        res = {}
        for c in corners:
            r = parse_f(logs[f"fword_{c}"]); k = CODE433[c]; res[c] = r
            step = r[f"c{k+1}_w0"]["f"] - r[f"c{k}_w0"]["f"]
            fs = r[f"c{k}_w1023"]["f"] - r[f"c{k}_w0"]["f"]
            lsb = fs / 1023
            print(f"{c:8s} code {k}: f(w0) {r[f'c{k}_w0']['f']/1e6:.2f}, f(w1023) {r[f'c{k}_w1023']['f']/1e6:.2f} MHz, "
                  f"range {fs/1e6:.2f} MHz = {fs/step:.2f} x step ({step/1e6:.2f}); LSB {lsb/1e3:.1f} kHz; "
                  f"sd cell {(r[f'c{k}_w512sd']['f']-r[f'c{k}_w512']['f'])/1e3:.1f} kHz; vg {r[f'c{k}_w512']['vg']:.3f}; "
                  f"swing {r[f'c{k}_w512']['amin']:.2f}-{r[f'c{k}_w512']['amax']:.2f}")
        (OUT / f"{tag}.json").write_text(json.dumps(dict(m=m, res=res), indent=1))
        return
    if a.mode == "noise":
        return noise_mode(a, p, m, corners)
    # dc / mc: DAC output current into vg held at the corner's operating point, every word
    vg = {"typical": 1.894, "ss": 1.680, "ff": 2.093, "sf": 1.85, "fs": 1.95}
    def dcdeck(seed):
        body = mdac_netlist(p, m, split=seed is not None, g="vbnf")
        words = "\n".join(f"{w}" for w in range(1024))
        return f"""* mdac dc {a.corner} seed {seed}
{HDR.format(corner=a.corner)}.param sw_stat_mismatch={1 if seed else 0}
.options seed={seed or 1}
vdd vdd 0 3.3
vbnf vbnf 0 {VBNF.get(a.corner, VBNF['typical'])}
vvg vgo 0 {vg[a.corner]}
{body}{ctl_sources(m, 0, 0)}.option temp={a.temp}
.control
let w = 0
while w < 1024
{dc_alter_loop(m)}  op
  let iv = -i(vvg)
  echo "IW $&w $&iv"
  destroy all
  let w = w + 1
end
alter vnsd 3.3
{word_alter_static(512, m)}op
let isd0 = -i(vvg)
echo "SD0 $&isd0"
alter vnsd 0
op
let isd1 = -i(vvg)
echo "SD1 $&isd1"
quit
.endc
.end
"""
    seeds = [None] if a.mode == "dc" else [a.seed0 + i for i in range(a.n)]
    od = OUT / f"{a.mode}_{a.corner}"
    logs = run([(f"s{s or 0}", dcdeck(s)) for s in seeds], a.jobs, od)
    rows = []
    for s in seeds:
        iw = [float(x) for x in re.findall(r"^IW \S+ (\S+)$", logs[f"s{s or 0}"], re.M)]
        if len(iw) != 1024:
            print(f"seed {s}: {len(iw)} words; log tail:\n" + "\n".join(logs[f's{s or 0}'].splitlines()[-8:])); continue
        sd = re.search(r"^SD0 (\S+)\n(?:.*\n)*?SD1 (\S+)", logs[f"s{s or 0}"], re.M)
        steps = [iw[i + 1] - iw[i] for i in range(1023)]
        lsb = (iw[1023] - iw[0]) / 1023
        dnl = [st / lsb - 1 for st in steps]
        rows.append(dict(seed=s, i0=iw[0], i1023=iw[1023], lsb=lsb, dnl_min=min(dnl), dnl_max=max(dnl),
                         dnl_argmin=dnl.index(min(dnl)), sd=(float(sd.group(2)) - float(sd.group(1))) / lsb if sd else None))
    if a.mode == "dc":
        r = rows[0]
        print(f"{a.corner}: I(0) {r['i0']*1e6:.3f} uA, I(1023) {r['i1023']*1e6:.3f} uA, LSB {r['lsb']*1e9:.2f} nA, "
              f"DNL {r['dnl_min']:+.3f}..{r['dnl_max']:+.3f} (min at {r['dnl_argmin']}), sd cell {r['sd']:.3f} LSB")
    else:
        mins = sorted(r["dnl_min"] for r in rows)
        ok = sum(r["dnl_min"] > -1 for r in rows)
        print(f"{a.corner} MC N={len(rows)}: DNL > -1 LSB in {ok}/{len(rows)} ({100*ok/len(rows):.1f} %); "
              f"worst DNL {mins[0]:+.3f}, 1st percentile {mins[max(0, len(mins)//100 - 1)]:+.3f}, median min {mins[len(mins)//2]:+.3f}; "
              f"LSB {min(r['lsb'] for r in rows)*1e9:.2f}..{max(r['lsb'] for r in rows)*1e9:.2f} nA; "
              f"sd cell {min(r['sd'] for r in rows):.3f}..{max(r['sd'] for r in rows):.3f} LSB")
    (OUT / f"{tag}_{a.corner}.json").write_text(json.dumps(dict(m=m, rows=rows), indent=1))


VG_OP = {"typical": 1.894, "ss": 1.680, "ff": 2.093, "sf": 1.85, "fs": 1.95}


def noise_deck(p, m, corner, temp, code, word, out):
    """Reference + filter + coarse DAC (drains on vg, held by vvg1) + medium DAC (drains on vgo, held by vvg2), no
    ring. out: coarse | med | sum -> .noise of the chosen current(s) through a 1 V/A CCVS (noiseless)."""
    body, _ = vb.netlist(dict(p, n=0))
    src = "".join(f"vbit{b} bit{b} 0 {3.3 if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else 3.3}\n"
                  for b in range(p["bits"]))
    outs = {"coarse": "Hc no 0 vvg1 1\n", "med": "Hm no 0 vvg2 1\n",
            "sum": "Hc nc 0 vvg1 1\nHm no nc vvg2 1\n"}[out]
    return f"""* mdac noise {corner} {temp} code {code} word {word} {out}
{HDR.format(corner=corner)}vdd vdd 0 dc 3.3 ac 1
vctrl vctrl 0 0
{src}{body.replace('Cvg vg 0', '* Cvg vg 0')}vvg1 vg 0 {VG_OP[corner]}
{mdac_netlist(p, m, g=vb.gnet(p))}vvg2 vgo 0 {VG_OP[corner]}
{ctl_sources(m, word, 0)}{outs}.option temp={temp}
.control
noise v(no) vdd dec 20 100 10Meg
setplot noise1
let fr = frequency
let sn = onoise_spectrum
wrdata noise_{corner}_c{code}_w{word}_{out}.txt sn
quit
.endc
.end
"""


def noise_mode(a, p, m, corners):
    """rms FM (1-10 kHz, 1-100 kHz) from each current's noise x K_I (df/dI of the ideal sink, ideal.json)."""
    ideal = json.loads((OUT / "ideal.json").read_text())
    iu = json.loads((OUT / "iu.json").read_text())
    od = OUT / "noise"
    decks, keys = [], []
    for c in corners:
        k = CODE433[c]
        for w in (0, 512, 1023):
            for o in ("coarse", "med", "sum"):
                decks.append((f"n_{c}_w{w}_{o}", noise_deck(p, m, c, a.temp, k, w, o))); keys.append((c, k, w, o))
    run(decks, a.jobs, od)
    res = []
    for c, k, w, o in keys:
        fn = od / f"noise_{c}_c{k}_w{w}_{o}.txt"
        d = [tuple(map(float, l.split()[:2])) for l in fn.read_text().splitlines() if l.strip()]
        fs = [x[0] for x in d]; sn = [x[1] ** 2 for x in d]    # A^2/Hz
        r = ideal[c]
        ki = (r[f"c{k}_i1.0"]["f"] - r[f"c{k}_i0"]["f"]) / iu[c]["iu"]   # Hz/A
        def band(lo, hi):
            tot = 0.0
            for i in range(len(fs) - 1):
                if fs[i] >= lo and fs[i + 1] <= hi:
                    tot += 0.5 * (sn[i] + sn[i + 1]) * (fs[i + 1] - fs[i])
            return math.sqrt(tot) * ki
        res.append(dict(corner=c, code=k, word=w, out=o, ki_hz_per_a=ki, fm_1k_10k=band(1e3, 1e4), fm_1k_100k=band(1e3, 1e5)))
        print(f"{c:8s} code {k:2d} word {w:4d} {o:6s}: rms FM {res[-1]['fm_1k_10k']/1e3:6.3f} kHz (1-10 kHz), "
              f"{res[-1]['fm_1k_100k']/1e3:6.3f} kHz (1-100 kHz)  [K_I {ki/1e12:.2f} MHz/uA]")
    (OUT / "noise.json").write_text(json.dumps(res, indent=1))


def vb_bits_alter(code, nb=5):
    return "".join(f"alter vbit{b} {3.3 if (code >> b) & 1 else 0}\nalter vbitb{b} {0 if (code >> b) & 1 else 3.3}\n"
                   for b in range(nb))


def word_alter_static(word, m=M):
    return ctl_alter(word, 0, m)


def dc_alter_loop(m=M):
    """ngspice control-language: set every group's switch sources from the loop variable w."""
    s = ""
    nb = m["nbin"]
    for i in range(1, m["nseg"] + 1):
        s += (f"  if floor(w/{1 << nb}) >= {i}\n    alter vns{i} 0\n  else\n"
              f"    alter vns{i} 3.3\n  end\n")
    for b in range(nb):
        s += (f"  if floor(w/{1 << b}) - 2*floor(w/{1 << (b + 1)}) > 0.5\n    alter vnb{b} 0\n"
              f"  else\n    alter vnb{b} 3.3\n  end\n")
    return s


if __name__ == "__main__":
    main()
