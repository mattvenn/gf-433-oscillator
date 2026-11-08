"""
cfed_ring: the current-fed ring, 5 plain inverters (vco_bias P0..P4 / N0..N4).
PMOS sources on VDD, NMOS sources on the shared node vg (fed by cfed_dac), stage i
drives a(i+1), a4 drives a0.

    python3 xschem/gen/cfed_ring.py
"""
from common import DEV, P, Sch, ginv, ports, finish, title

PINS = ['VDD', 'vg', 'VSS'] + [f'a{i}' for i in range(P['n'])]


def build():
    s = Sch()
    n, dx = P['n'], 260
    ytop, ybot = -160, 160
    pt, nt, g, d = [], [], [], []
    for i in range(n):
        dp, dn = DEV[f'P{i}'], DEV[f'N{i}']
        assert dp['nets'][1] == dn['nets'][1] == f'a{i}' and dp['nets'][2] == 'VDD' and dn['nets'][2] == 'vg'
        p_, n_, gi, di = ginv(s, 100 + i * dx, 0, dict(W=dp['w'], L=dp['l'], m=dp['m'], name=f'P{i}'),
                              dict(W=dn['w'], L=dn['l'], m=dn['m'], name=f'N{i}'))
        s.connect(p_, B='VDD')
        s.connect(n_, B='VSS')
        pt.append(p_.pin('S')); nt.append(n_.pin('S')); g.append(gi); d.append(di)
    x1, x2 = g[0][0] - 60, d[-1][0] + 60
    s.rail(ytop, x1, x2, pt, net='VDD')
    s.rail(ybot, x1, x2, nt, net='vg')
    for i in range(n):
        s.label(g[i], f'a{i}')
        if i < n - 1:
            s.wire(d[i], g[i + 1])
        else:
            s.label(d[i], 'a0', right=True)      # a4's stage closes the loop on a0
    ports(s, x1 - 200, -120, PINS)
    title(s, x1 - 200, -420, ['cfed_ring: 5-stage current-fed ring',
                              f"P {DEV['P0']['w']:g}/{DEV['P0']['l']:g} um, N {DEV['N0']['w']:g}/{DEV['N0']['l']:g} um "
                              '(sim/vco/vco_bias.py, topo=cfed)',
                              'N sources share vg: cfed_dac sinks the ring current, decap holds vg',
                              'the ring swings vg..VDD; a4 -> a0 closes the loop'])
    finish(s, 'cfed_ring', PINS, left=['VDD', 'vg', 'VSS'], right=PINS[3:], width=160)


if __name__ == '__main__':
    build()
