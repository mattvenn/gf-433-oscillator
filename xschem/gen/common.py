"""
Shared set-up for the GF180MCU xschem generators in xschem/gen/.

Source of truth: sim/vco/vco_bias.py netlist() at the chosen design (CHOSEN below). Every
device drawn is looked up by its vco_bias instance name in DEV, so W, L, m and the nets
come from the simulated netlist, not from numbers typed in here.

Net renames from vco_bias to the schematics: 0 -> VSS, vdd -> VDD, n1 -> vbn (vco_bias
joins them with a 1 ohm resistor, Rvbn, only to name the net), the series-array
internal nodes keep their names.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
XDIR = os.environ.get('XSCH_OUT') or os.path.join(REPO, 'xschem')   # XSCH_OUT: write a variant elsewhere
sys.path.insert(0, os.path.join(REPO, 'tools'))
sys.path.insert(0, os.path.join(REPO, 'sim', 'vco'))

import vco_bias  # noqa: E402
import xsch  # noqa: E402
xsch.XSCHEM_DIR = XDIR
from xsch import Sch, gmos, gres, ginv, ports, write_symbol, GF180_MODELS  # noqa: E402,F401

# winner reference (sim/results/2026-11-08/winner_sets.txt) with lnw = 5.023, plus the cfed core
WINNER = dict(rideal=0, lnp=100.0, lnw=5.023, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)
CFED = dict(topo='cfed', kc=0.75, k=6, cvg=3e-12, ka=16.0, wfu=0.30, wff=0.30, rf=1e6, cf=20e-12)
RENAME = {'0': 'VSS', 'vdd': 'VDD', 'n1': 'vbn'}


def params(sets=()):
    """vco_bias.P + CHOSEN; sets = ['k=v', ...] overrides (as --set)."""
    p = dict(vco_bias.P)
    p.update(WINNER)
    p.update(CFED)
    sets = list(sets) + [kv for kv in os.environ.get('XSCH_SET', '').split(',') if kv]   # e.g. XSCH_SET=wfu=0.25,wff=0.25
    for kv in sets:
        k, v = kv.split('=')
        p[k] = v if isinstance(p[k], str) else type(p[k])(float(v))
    return p


def _num(s):
    m = re.fullmatch(r'([-+\d.eE]+)([a-z]*)', s)
    return float(m.group(1)) * {'': 1, 'u': 1e-6, 'p': 1e-12, 'n': 1e-9, 'f': 1e-15}[m.group(2)]


def parse(body):
    """vco_bias netlist body -> {name: dict(nets=[...], model, w, l (um), m, ...)} (nets renamed)."""
    out = {}
    for ln in body.splitlines():
        t = ln.split()
        if not t:
            continue
        name = t[0]
        kv = dict(x.split('=') for x in t if '=' in x)
        pos = [x for x in t[1:] if '=' not in x]
        if name[0] in 'X':
            nets, model = pos[:-1], pos[-1]
            d = dict(nets=[RENAME.get(n, n) for n in nets], model=model)
            if 'fet' in model:
                d.update(w=_num(kv['w']) * 1e6, l=_num(kv['l']) * 1e6, m=int(kv.get('m', 1)))
            else:
                d.update(w=_num(kv['r_width']) * 1e6, l=_num(kv['r_length']) * 1e6)
            out[name[1:]] = d
        else:                      # R / C
            out[name] = dict(nets=[RENAME.get(n, n) for n in pos[:2]], model=name[0], value=pos[2])
    return out


P = params()
BODY, _ = vco_bias.netlist(P)
DEV = parse(BODY)


def decap_size(p=P):
    """(m, L, W) of the vg MOS decap: the same rule as layout/gen/ring_core_v3.py (the v3 layout)."""
    import importlib.util
    sys.path.append(os.path.join(REPO, 'layout', 'gen'))     # its own imports (ring_core, ring_core_v2)
    spec = importlib.util.spec_from_file_location('lay_ring_core_v3', os.path.join(REPO, 'layout', 'gen', 'ring_core_v3.py'))
    lay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lay)
    return lay.decap_size(dict(p, **lay.DECAP))


def place(sch, name, x, y, flip=0, label=True, skip=(), dev=None, **nets):
    """Place vco_bias device `name` (MOS or resistor) at (x, y) with its W/L/m, and label each
    pin with its vco_bias net (nets=... overrides; skip=pins left unlabelled for drawn wires)."""
    d = dev or DEV[name]
    if 'fet' in d['model']:
        inst = gmos(sch, d['model'][0], x, y, W=d['w'], L=d['l'], m=d['m'], name=name, flip=flip)
        pins = 'DGSB'
    else:
        inst = gres(sch, d['model'], x, y, W=d['w'], L=d['l'], name=name, flip=flip)
        pins = 'MPB'    # the PDK symbol's netlist pin order: M first, so the line reads as vco_bias's
    if label:
        for pin, net in zip(pins, d['nets']):
            if pin not in skip:
                net = nets.get(pin, net)
                if net:
                    sch.connect(inst, **{pin: net})
    return inst


def finish(sch, name, pins, left, right=(), top=(), bottom=(), width=200):
    """Ports (iopins, in symbol order), symbol, schematic."""
    sch.pin_order = pins
    write_symbol(os.path.join(XDIR, f'{name}.sym'), left=left, right=right, top=top, bottom=bottom, width=width)
    sch.write(os.path.join(XDIR, f'{name}.sch'))
    print(f'wrote xschem/{name}.sch, .sym')


def title(sch, x, y, lines):
    sch.text(x, y, lines[0], 0.6)
    for i, s in enumerate(lines[1:]):
        sch.text(x, y + 50 + i * 28, s, 0.35)
