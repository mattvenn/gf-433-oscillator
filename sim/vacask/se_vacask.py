#!/usr/bin/env python3
"""VACASK cross-check of the ISF phase noise of the 'se' ring (sim/pn/isf.py): netlist generator.

VACASK bdb6df9 has no PSS/pnoise (only op/dc/ac/noise/tran/hb, HB is driven-only), so this uses
transient noise (tran with noisefmax>0) and measures edge-time jitter.

ng2vc.py can't convert the GF180 libs (quoted .lib names; int(version) crash on "4.5"; no level-54 map), so
this script hand-converts: it reads the ngspice BSIM4 bins for nfet_03v3/pfet_03v3 (typical) straight from
the PDK, evaluates the .param expressions, picks the bin for each (W, L) used, and emits sp_bsim4v8 models
(the ngspice BSIM4 code compiled to OSDI, so the device equations match ngspice).

Usage (inside the image, repo root):
  python3 sim/vacask/se_vacask.py <out.sim> --mode {full,quiet_bias,hf_only} [--tran args...]
mode full       : the ngspice netlist as is (bias mirror + gate switches are real, noisy FETs)
mode quiet_bias : vbp and g0..g3 driven by ideal sources (like isf.py's noise_deck) -> no bias noise
mode hf_only    : quiet_bias + the inverter FETs (MP/MN) use a noiseless model copy -> head + foot noise only,
                  the same device set as the ISF 'device-only' number
"""
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/pn"))
D = "/foss/pdks/gf180mcuD/libs.tech/ngspice/"
SUF = dict(t=1e-12, g=1e-9, meg=1e6, k=1e3, m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15)


def num(s):
    m = re.fullmatch(r"([-+]?[\d.]+(?:e[-+]?\d+)?)(meg|[tgkmunpf])?\w*", s.strip().lower())
    return float(m.group(1)) * (SUF[m.group(2)] if m.group(2) else 1) if m else None


def joined(text):
    out = []
    for l in text.splitlines():
        l = l.split("$")[0].rstrip()
        if l.lstrip().startswith("*") or not l.strip():
            continue
        if l.lstrip().startswith("+") and out:
            out[-1] += " " + l.lstrip()[1:]
        else:
            out.append(l.strip())
    return out


def params():
    p = {}
    src = open(D + "design.ngspice").read()
    lib = open(D + "sm141064.ngspice").read()
    i = lib.lower().index(".lib noise_corner")
    src += "\n" + lib[i:i + 2000].split(".ENDL")[0].split(".endl")[0]
    for l in joined(src):
        if l.lower().startswith(".param"):
            for k, v in re.findall(r"(\w+)\s*=\s*('[^']*'|\S+)", l[6:]):
                v = v.strip("'")
                n = num(v)
                p[k.lower()] = n if n is not None else eval(v, {}, p)
    return p


def models(dtype, P):
    lib = open(D + "sm141064.ngspice").read().splitlines()
    i = next(k for k, l in enumerate(lib) if re.match(rf"\.lib\s+{dtype}_t\s*$", l, re.I))
    j = next(k for k in range(i + 1, len(lib)) if lib[k].lower().startswith(".endl"))
    bins = []
    for l in joined("\n".join(lib[i + 1:j])):
        m = re.match(rf"\.model\s+{dtype}\.(\d+)\s+([np]mos)\s+(.*)", l, re.I)
        if not m:
            continue
        kv = {}
        for k, v in re.findall(r"(\w+)\s*=\s*('[^']*'|\S+)", m.group(3)):
            k = k.lower(); v = v.strip("'")
            n = num(v)
            kv[k] = n if n is not None else float(eval(v.lower(), {}, P))
        kv.pop("level", None); kv.pop("version", None)
        kv["type"] = 1 if m.group(2).lower() == "nmos" else -1
        bins.append((int(m.group(1)), kv))
    return bins


def pick(bins, w, l):
    for b, kv in bins:
        if kv["lmin"] <= l < kv["lmax"] and kv["wmin"] <= w < kv["wmax"]:
            return b, kv
    sys.exit(f"no bin for w={w} l={l}")


def g(x):
    # VACASK parses an exponent-free integer literal with stoi: 3000000000 -> std::out_of_range crash
    return str(int(x)) if x == int(x) and abs(x) < 1e9 else f"{x:.10e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--mode", default="full", choices=["full", "quiet_bias", "hf_only"])
    ap.add_argument("--vbp", type=float, default=None, help="ideal vbp for quiet modes")
    ap.add_argument("--control", default="", help="file with the control block body")
    a = ap.parse_args()
    import isf
    v = isf.VARIANTS["se"]
    net, ic, _ = isf.circuit(v, "typical")
    P = params()
    B = {t: models(t, P) for t in ("nfet_03v3", "pfet_03v3")}
    used, inst, srcs = {}, [], []
    for l in net.splitlines():
        t = l.split()
        if not t or l.startswith("."):
            continue
        if t[0].lower().startswith("v"):
            srcs.append(f"{t[0]} ({t[1]} {t[2]}) vsrc dc={t[3]}")
        elif t[0].lower().startswith("c"):
            inst.append(f"{t[0]} ({t[1]} {t[2]}) cap c={t[3]}")
        elif t[0].upper().startswith("XM"):
            name, d, gg, s, bb, dev = t[:6]
            kw = {k: num(x) for k, x in (z.split("=") for z in t[6:])}
            if a.mode != "full":
                if re.match(r"XM(PB|B|B_\d|TN\d|TP\d|PD\d)$", name):
                    continue        # bias mirror and gate switches -> ideal sources below
            b, kv = pick(B[dev], kw["w"], kw["l"])
            quiet = a.mode == "hf_only" and re.match(r"XM[PN]a\d$", name)
            mname = f"{dev}_{b}" + ("_q" if quiet else "")
            used[mname] = dict(kv, **(dict(ntnoi=0, noia=0, noib=0, noic=0) if quiet else {}))
            inst.append(f"{name} ({d} {gg} {s} {bb}) {mname} " + " ".join(f"{k}={g(x)}" for k, x in kw.items()))
    if a.mode != "full":
        srcs.append(f"vvbp (vbp 0) vsrc dc={a.vbp}")
        for bit in range(4):
            on = (v["code"] >> bit) & 1
            srcs.append(f"vg{bit} (g{bit} 0) vsrc dc={v['vctrl'] if on else 0}")
    mods = [f"model {n} sp_bsim4v8 (\n" + "\n".join(f"  {k}={g(x)}" for k, x in kv.items()) + "\n)" for n, kv in used.items()]
    ctl = Path(a.control).read_text() if a.control else ""
    ics = re.findall(r"v\((\w+)\)=(\S+)", ic)
    ctl = ctl.replace("@IC@", "[" + "; ".join(f'"{n}"; {x}' for n, x in ics) + "]")
    Path(a.out).write_text(f"""se ring VCO ({a.mode}), GF180 typical, generated by sim/vacask/se_vacask.py

load "spice/bsim4v8.osdi"
load "capacitor.osdi"
model vsrc vsource
model isrc isource
model cap capacitor

{chr(10).join(mods)}

{chr(10).join(srcs)}
// start-up kick from the metastable op point (an ic= list on the ring nodes aborts VACASK's tran)
ikick (0 a2) isrc type="pulse" val0=0 val1=200u delay=0.1n rise=10p fall=10p width=0.3n period=1
{chr(10).join(inst)}

control
  options temp=27 tnom=27
{ctl}
endc
""")


if __name__ == "__main__":
    main()
