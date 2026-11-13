"""
rx_bb: the receiver baseband, one per arm (sim/rx/rx_bb.py block()).

  stage 1 (M1a / M1b, DC-coupled to the mixer, 10 kOhm loads) -> AC coupling 2 -> stage 2 (+ load caps C2a / C2b:
  pole 1) -> AC coupling 3 -> stage 3 (+ C3a / C3b: pole 2) -> outp / outn. Each AC coupling: a pfet gate cap and,
  to vb, a subthreshold pfet (gate vgr) in parallel with a two-pfet pseudo-resistor. vb / vgr from the gated divider
  and the replica at the left.

    python3 xschem/gen/rx_bb.py
"""
from rx_common import DEV, Sch, port, supply, finish, title, supplies, wl, couple_side, stage, vbias_draw

C = 'rx_bb'
PINS = ['VDD', 'VSS', 'inp', 'inn', 'outp', 'outn', 'nb', 'enb']


def chain(s, cell, x0, stages, couples, vbx, xr, yvb=330, yvgr=410, ynb=520):
    """Draw the stages (list of (tag, ip, im, op, om, tail, caps)) with the AC couplings (list of (tag, gp, gn))
    between them. The first stage's gates are returned for the caller to wire; the last stage's outputs leave
    right to xr. Returns (first (ip, im), last (op, om) track ends, vb / vgr / nb taps)."""
    vbt, vgt, nbt = [], [], []
    x = x0
    first = last = None
    for i, (tag, ip, im, op, om, tail, caps) in enumerate(stages):
        top, tom, tnb, gates = stage(s, cell, x, tag, ip, im, op, om, tail, caps=caps)
        nbt.append(tnb)
        if i == 0:
            first = gates
        else:
            s.route(prev_g[0], gates[0])
            s.route(prev_g[1], (gates[1][0] + 80, prev_g[1][1]), (gates[1][0] + 80, gates[1][1]), gates[1])
        if i < len(couples):
            ctag, gp, gn = couples[i]
            Xa, Xb = x + 500, x + 900
            ga, va, ra = couple_side(s, cell, ctag, 'a', Xa, top, gp, op)
            s.route(tom, (Xb - 40, tom[1]))
            gb, vb_, rb = couple_side(s, cell, ctag, 'b', Xb, (Xb - 40, tom[1]), gn, om, yout=-60)
            vbt += va + vb_
            vgt += ra + rb
            prev_g = (ga, gb)
            x += 1700
        else:
            last = (top, tom)
    s.route(last[0], (xr, last[0][1]))
    s.route(last[1], (xr, last[1][1]))
    return first, last, vbt, vgt, nbt


def build():
    s = Sch()
    xl, x0, xr = -1300, 0, 3900
    yvb, yvgr, ynb = 330, 410, 520
    enb_g, vb0, vg0, nb0, _ = vbias_draw(s, C, -800)
    first, last, vbt, vgt, nbt = chain(
        s, C, x0, [('1', 'inp', 'inn', 'o1p', 'o1n', 't1', False), ('2', 'g2p', 'g2n', 'o2p', 'o2n', 't2', True),
                   ('3', 'g3p', 'g3n', 'outp', 'outn', 't3', True)],
        [('2', 'g2p', 'g2n'), ('3', 'g3p', 'g3n')], -800, xr)
    for pts, y in ((vb0 + vbt, yvb), (vg0 + vgt, yvgr), ([nb0] + nbt, ynb)):
        xs = sorted({p[0] for p in pts})
        s.bus((xs[0], y), (xs[-1], y), sorted(set(pts)))
    s.wire((xl, ynb), (sorted({p[0] for p in [nb0] + nbt})[0], ynb)); port(s, (xl, ynb), 'nb', 'in')
    s.route(enb_g, (enb_g[0] - 40, enb_g[1]), (enb_g[0] - 40, -420), (xl, -420)); port(s, (xl, -420), 'enb', 'in')
    s.route((xl, -560), (-240, -560), (-240, 0), first[0]); port(s, (xl, -560), 'inp', 'in')
    s.route((xl, 640), (240, 640), (240, 0), first[1]); port(s, (xl, 640), 'inn', 'in')
    port(s, (xr, last[0][1]), 'outp', 'out'); port(s, (xr, last[1][1]), 'outn', 'out')
    s.text(-700, yvb - 24, 'vb', 0.3); s.text(-700, yvgr - 24, 'vgr', 0.3); s.text(-700, ynb - 24, 'nb', 0.3)
    supplies(s, xl, 900)
    d = DEV[C]
    title(s, xl, -900, ['rx_bb: baseband, three stages (one per arm)',
                        f"stage 1 {wl(d['M1a'])} um, 200 uA, 10 kOhm (DC-coupled to the mixer); stages 2 / 3 "
                        f"{wl(d['M2a'])} um, ~4 uA, 200 kOhm + {d['C2a']['w'] * d['C2a']['l'] * 4.07e-3:.1f} pF: "
                        "two poles near 230 kHz (-3 dB about 145 kHz)",
                        'AC couplings: pfet gate caps; Mr (gate vgr, ~60 MOhm) || pseudo-resistor to vb: high-pass '
                        'about 9 kHz in all; source: sim/rx/rx_bb.py block()'])
    finish(s, C, PINS, left=['inp', 'inn', 'nb', 'enb'], right=['outp', 'outn'], top=['VDD'], bottom=['VSS'],
           width=180, label='bb')


if __name__ == '__main__':
    build()
