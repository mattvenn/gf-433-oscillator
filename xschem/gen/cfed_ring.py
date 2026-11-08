"""
cfed_ring: the current-fed ring, 5 plain inverters (vco_bias P0..P4 / N0..N4).
PMOS sources on VDD, NMOS sources on the shared node vg (fed by cfed_dac), stage i
drives a(i+1), a4 drives a0.

Drawn as a textbook ring: the five inverters in a row, the loop a wire (the feedback a4 stage -> a0
under the row), VDD rail on top, vg rail under the NMOS sources; outputs tapped up to the right edge.

    python3 xschem/gen/cfed_ring.py
"""
from common import DEV, P, Sch, ginv, finish, title, bulk, port, supply

N = P['n']
PINS = ['VDD', 'vg', 'VSS'] + [f'a{i}' for i in range(N)]


def build():
    s = Sch()
    dx, x0 = 300, 200
    ytop, yvg, yfb = -170, 170, 250
    pt, nt, g, d, pb = [], [], [], [], []
    for i in range(N):
        dp, dn = DEV[f'P{i}'], DEV[f'N{i}']
        assert dp['nets'][1] == dn['nets'][1] == f'a{i}' and dp['nets'][2] == 'VDD' and dn['nets'][2] == 'vg'
        assert dp['nets'][0] == dn['nets'][0] == f'a{(i + 1) % N}' and dp['nets'][3] == 'VDD' and dn['nets'][3] == 'VSS'
        p_, n_, gi, di = ginv(s, x0 + i * dx, 0, dict(W=dp['w'], L=dp['l'], m=dp['m'], name=f'P{i}'),
                              dict(W=dn['w'], L=dn['l'], m=dn['m'], name=f'N{i}'))
        p_.props['val'] = f'"{dp["w"]:g}/{dp["l"]:g}"'
        n_.props['val'] = f'"{dn["w"]:g}/{dn["l"]:g}"'
        pb.append(bulk(s, p_, y=ytop))          # PMOS bulk up to the VDD rail
        bulk(s, n_, to='VSS')                   # NMOS bulk to VSS (its source is vg, not VSS)
        pt.append(p_.pin('S')); nt.append(n_.pin('S')); g.append(gi); d.append(di)
    xl = x0 - 260                                # left edge (ports)
    # VDD rail on top (P sources and bulks), vg rail under the N sources
    for p in pt:
        s.wire(p, (p[0], ytop))
    s.bus((xl, ytop), (pb[-1][0], ytop), [(p[0], ytop) for p in pt] + pb)
    port(s, (xl, ytop), 'VDD', 'io')
    s.rail(yvg, xl, nt[-1][0], nt)
    port(s, (xl, yvg), 'vg', 'io')
    # VSS port: tied to the bulk ground symbols by name
    s.wire((xl, yfb + 80), (xl + 60, yfb + 80))
    port(s, (xl, yfb + 80), 'VSS', 'io')
    supply(s, (xl + 60, yfb + 80), 'VSS')
    # the loop: stage i output -> stage i+1 input, taps up to the outputs on the right edge
    xr = d[-1][0] + 260
    for i in range(N):
        out = f'a{(i + 1) % N}'
        tx = d[i][0] + 130
        h = ytop - 70 - (N - 1 - i) * 40           # leftmost tap highest: no crossings between taps
        if i < N - 1:
            s.bus(d[i], g[i + 1], [(tx, 0)])
        else:
            fx = d[i][0] + 200                     # a4's stage closes the loop on a0, under the row
            s.bus(d[i], (fx, 0), [(tx, 0)])
            s.route((fx, 0), (fx, yfb), (x0 - 100, yfb), (x0 - 100, 0), g[0], vfirst=True)
        s.route((tx, 0), (tx, h), (xr, h), vfirst=True)
        port(s, (xr, h), out, 'out')
    title(s, xl, -620, ['cfed_ring: 5-stage current-fed ring oscillator',
                        'NMOS sources share vg: cfed_dac sinks the ring current, so the ring swings vg..VDD',
                        'P 5/0.28, N 2/0.28 um (sim/vco/vco_bias.py, topo=cfed)'])
    finish(s, 'cfed_ring', PINS, left=['vg'], right=[f'a{i}' for i in range(N)], top=['VDD'], bottom=['VSS'],
           width=160, label='ring')


if __name__ == '__main__':
    build()
