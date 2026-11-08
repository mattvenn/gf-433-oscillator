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


# ---- drawing helpers: textbook sheets, every connection inside a sheet a drawn wire --------------
from xsch import Inst  # noqa: E402


def wl(d):
    """'1.2/5.33 ×6': W/L in um (3 significant figures), x multiplicity when m > 1."""
    return f"{d['w']:.3g}/{d['l']:.3g}" + (f" ×{d['m']}" if d.get('m', 1) > 1 else '')


def place(sch, name, x, y, flip=0, rot=0, val=None, hide=False, dev=None, inst_name=None):
    """Place vco_bias device `name` (MOS or resistor) at (x, y) with its W/L/m, no labels: the
    caller draws the wires. val: the readable value text (default W/L ×m)."""
    d = dev or DEV[name]
    nm = inst_name or name
    if 'fet' in d['model']:
        inst = gmos(sch, d['model'][0], x, y, W=d['w'], L=d['l'], m=d['m'], name=nm, flip=flip, rot=rot)
        inst.nets = dict(zip('DGSB', d['nets']))
    else:
        inst = gres(sch, d['model'], x, y, W=d['w'], L=d['l'], name=nm, flip=flip, rot=rot)
        inst.nets = dict(zip('MPB', d['nets']))    # the PDK symbol's netlist pin order is M P B
    inst.props['val'] = '"' + (val if val is not None else wl(d)) + '"'
    if hide:
        inst.props['hide_texts'] = 'true'
    return inst


def vmirror(sch, name, x, y, **kw):
    """A MOS mirrored top-to-bottom (rot 2 + flip): gate still on the left, D and S swapped in
    position (an NMOS with its source on top), so a pass device reads source-up."""
    return place(sch, name, x, y, rot=2, flip=1, **kw)


def supply(sch, pt, net):
    """VDD (devices/vdd.sym) or VSS (devices/gnd.sym, lab=VSS) symbol on a wire end / pin."""
    sym = 'symbols/vdd.sym' if net == 'VDD' else 'symbols/gnd.sym'
    sch.items.append(Inst(sym, pt[0], pt[1], 0, 0, {'name': sch._name('l'), 'lab': net}))


def outward(inst):
    """+1 if the MOS bulk points right (gate on the left), else -1."""
    return 1 if inst.pin('B')[0] > inst.pin('G')[0] else -1


def bulk(sch, inst, to=None, y=None, dx=20):
    """Bulk wire: a short stub away from the gate, then
       to='S'          : down/up to the source and into it (bulk tied to source)
       to='VSS'/'VDD'  : a supply symbol on the stub
       y=<rail y>      : on down/up to a horizontal rail at y; returns the tap point on the rail."""
    b = inst.pin('B')
    e = (b[0] + dx * outward(inst), b[1])
    sch.wire(b, e)
    if to == 'S':
        s = inst.pin('S')
        sch.route(e, (e[0], s[1]), s)
    elif to in ('VSS', 'VDD'):
        supply(sch, e, to)
    elif y is not None:
        sch.wire(e, (e[0], y))
        return (e[0], y)
    return e


def port(sch, pt, net, kind):
    """Sheet port at a wire end: kind 'in' (ipin, left edge), 'out' (opin, right edge),
    'io' / 'io_r' (iopin, text left / right)."""
    sym = {'in': 'ipin', 'out': 'opin', 'io': 'iopin', 'io_r': 'iopin'}[kind]
    flip = 1 if kind == 'io' else 0
    sch.items.append(Inst(f'devices/{sym}.sym', pt[0], pt[1], 0, flip, {'name': sch._name('p'), 'lab': net}))
    if not hasattr(sch, 'dirs'):
        sch.dirs = {}
    sch.dirs[net] = {'ipin': 'in', 'opin': 'out', 'iopin': 'inout'}[sym]


def lint(sch):
    """Geometry check of the drawing: every wire end on a pin or another wire end, no pin or wire
    end in the middle of a wire (xschem would join it there without a T split), no overlaps."""
    pins = []
    for it in sch.items:
        for nm in it.pins:
            pins.append((it.pin(nm), f"{it.props.get('name')}.{nm}"))
    ends = {}
    for (a, b, _) in sch.wires:
        for p in (a, b):
            ends[p] = ends.get(p, 0) + 1
    pinpts = {p for p, _ in pins}
    errs = []

    def inside(p, a, b):
        if a[0] == b[0] == p[0]:
            return min(a[1], b[1]) < p[1] < max(a[1], b[1])
        if a[1] == b[1] == p[1]:
            return min(a[0], b[0]) < p[0] < max(a[0], b[0])
        return False
    for (a, b, _) in sch.wires:
        if a[0] != b[0] and a[1] != b[1]:
            errs.append(f'diagonal wire {a} {b}')
        for p, nm in pins:
            if inside(p, a, b):
                errs.append(f'pin {nm} at {p} inside wire {a}-{b}')
        for p in ends:
            if inside(p, a, b):
                errs.append(f'wire end {p} inside wire {a}-{b}')
        for p in (a, b):
            if p not in pinpts and ends[p] < 2:
                errs.append(f'dangling wire end {p}')
    segs = [(min(a, b), max(a, b)) for a, b, _ in sch.wires]
    if len(segs) != len(set(segs)):
        errs.append('duplicate wires')
    return errs


def finish(sch, name, pins, left=(), right=(), top=(), bottom=(), width=200, label=None):
    """Symbol (pins per side, netlist order = pins), schematic, lint and the wire / label count."""
    sch.pin_order = pins
    write_symbol(os.path.join(XDIR, f'{name}.sym'), left=left, right=right, top=top, bottom=bottom, width=width,
                 order=list(pins), label=label or name, dirs=getattr(sch, 'dirs', None))
    errs = lint(sch)
    for e in errs:
        print(f'  LINT {name}: {e}')
    sch.write(os.path.join(XDIR, f'{name}.sch'))
    nlab = sum(1 for i in sch.items if i.sym == 'devices/lab_pin.sym')
    print(f'wrote xschem/{name}.sch, .sym: {len(sch.wires)} wires, {nlab} lab_pin, {len(errs)} lint errors')


def title(sch, x, y, lines):
    sch.text(x, y, lines[0], 0.7)
    for i, s in enumerate(lines[1:]):
        sch.text(x, y + 60 + i * 34, s, 0.42)
