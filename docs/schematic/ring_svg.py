#!/usr/bin/env python3
"""Hand-placed SVG schematics of one ring stage and the bias distribution (master leg, coarse switch).
Values from sim/vco/vco_bias.py P (the netlist is the source of truth). Writes docs/schematic/ring_{stage,bias}.svg"""
from pathlib import Path
OUT = Path(__file__).resolve().parent
INK, GRAY, ACC = "#222", "#777", "#c0392b"


class S:
    def __init__(self, w, h): self.w, self.h, self.e = w, h, []
    def line(self, *pts, c=INK, w=1.6):
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.e.append(f'<polyline points="{p}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round"/>')
    def text(self, x, y, t, a="start", s=13, c=INK, b=False):
        for i, ln in enumerate(t.split("\n")):
            self.e.append(f'<text x="{x}" y="{y + i * (s + 2)}" font-size="{s}" text-anchor="{a}" fill="{c}"'
                          f'{" font-weight=\"600\"" if b else ""} font-family="Helvetica,Arial,sans-serif">{ln}</text>')
    def dot(self, x, y): self.e.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{INK}"/>')
    def circ(self, x, y, r): self.e.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="{INK}" stroke-width="1.5"/>')
    def gnd(self, x, y):
        self.line((x, y), (x, y + 8)); self.line((x - 10, y + 8), (x + 10, y + 8))
        self.line((x - 6, y + 12), (x + 6, y + 12)); self.line((x - 2, y + 16), (x + 2, y + 16))
    def rail(self, x0, x1, y, t):
        self.line((x0, y), (x1, y), w=2.2); self.text(x0 - 6, y + 4, t, a="end", b=True)
    def fet(self, x, y, p=False):
        """x,y = channel centre. Returns dict of terminals: top (D for n, S for p), bot, g."""
        self.line((x - 4, y - 17), (x - 4, y + 17), w=2.2)           # channel
        self.line((x - 10, y - 14), (x - 10, y + 14), w=2.2)         # gate plate
        self.line((x - 4, y - 12), (x + 14, y - 12), (x + 14, y - 30))
        self.line((x - 4, y + 12), (x + 14, y + 12), (x + 14, y + 30))
        if p:
            self.circ(x - 15, y, 4.5); self.line((x - 19.5, y), (x - 34, y))
        else:
            self.line((x - 10, y), (x - 34, y))
        return dict(top=(x + 14, y - 30), bot=(x + 14, y + 30), g=(x - 34, y))
    def cap(self, x, y0, y1):
        m = (y0 + y1) / 2
        self.line((x, y0), (x, m - 4)); self.line((x - 12, m - 4), (x + 12, m - 4), w=2.2)
        self.line((x - 12, m + 4), (x + 12, m + 4), w=2.2); self.line((x, m + 4), (x, y1))
    def save(self, name):
        (OUT / name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                                f'viewBox="0 0 {self.w} {self.h}"><rect width="100%" height="100%" fill="white"/>'
                                + "".join(self.e) + "</svg>")


def foot(s, xs, ybus, gates, sizes, note=True):
    s.line((xs[0], ybus), (xs[-1], ybus))
    for xd, g, sz in zip(xs, gates, sizes):
        t = s.fet(xd - 14, ybus + 30)
        s.gnd(*t["bot"])
        s.line(t["g"], (t["g"][0] - 6, t["g"][1])); s.text(t["g"][0] - 10, t["g"][1] + 4, g, a="end", c=ACC, b=True)
        s.text(xd - 14, ybus + 96, sz, a="middle", s=11, c=GRAY)


# ---------------- one stage
s = S(660, 510)
s.text(20, 26, "One ring stage (×5): current-starved inverter", s=15, b=True)
s.rail(220, 420, 60, "VDD 3.3 V")
H = s.fet(250, 110, p=True); s.line((H["top"][0], 60), H["top"])
s.line(H["g"], (H["g"][0] - 8, H["g"][1])); s.text(H["g"][0] - 12, H["g"][1] + 4, "vbp", a="end", c=ACC, b=True)
s.text(290, 105, "H  head pfet  6 / 1 µm", s=12); s.text(290, 120, "current source from VDD", s=11, c=GRAY)
P = s.fet(250, 190, p=True); s.line(H["bot"], P["top"]); s.text(272, 152, "h", s=11, c=GRAY)
s.text(290, 190, "P  pfet  5 / 0.28", s=12)
N = s.fet(250, 280, p=False); s.line(P["bot"], N["top"])
s.text(290, 285, "N  nfet  2 / 0.28", s=12)
yo = (P["bot"][1] + N["top"][1]) / 2; xo = P["bot"][0]; s.dot(xo, yo)
s.line((xo, yo), (560, yo)); s.text(565, yo + 4, "out a(i+1)", b=True)
s.cap(500, yo, yo + 50); s.gnd(500, yo + 50); s.text(515, yo + 30, "Cw 2 fF + next gate", s=11, c=GRAY)
xi = 170; s.line(P["g"], (xi, P["g"][1]), (xi, N["g"][1]), N["g"]); ym = (P["g"][1] + N["g"][1]) / 2
s.dot(xi, ym); s.line((xi, ym), (100, ym)); s.text(95, ym + 4, "in a(i)", a="end", b=True)
s.text(115, ym - 50, "inverter", s=11, c=GRAY)
yb = 345; s.line(N["bot"], (N["bot"][0], yb)); s.dot(N["bot"][0], yb); s.text(N["bot"][0] + 6, yb - 6, "f", s=11, c=GRAY)
foot(s, [144, 264, 384], yb, ["vbn", "g0…g4", "vctrl"],
     ["base  16 × 0.25/1", "coarse 1,2,4,8,16 ×", "fine  0.25 / 4"])
s.text(20, 478, "foot legs in parallel set the pull-down current; the head sets the pull-up current.", s=12, c=GRAY)
s.text(20, 496, "Long L (1 µm) makes them good current sources. Red = bias / control inputs shared by all 5 stages.", s=12, c=GRAY)
s.save("ring_stage.svg")

# ---------------- master leg + coarse switch
s = S(1000, 400)
s.text(20, 26, "Bias distribution", s=15, b=True)
s.text(20, 48, "Master leg (×1): copies one foot, makes vbp", s=13, b=True)
s.rail(200, 300, 80, "VDD")
M = s.fet(250, 130, p=True); s.line((M["top"][0], 80), M["top"])
s.text(285, 125, "MPB  pfet diode", s=12); s.text(285, 140, "12 × 1 / 1 µm", s=11, c=GRAY)
yb = 200
s.line(M["bot"], (M["bot"][0], yb)); s.dot(M["bot"][0], 175)
s.line((M["bot"][0], 175), (190, 175), (190, M["g"][1]), M["g"]); s.dot(190, M["g"][1])
s.line((190, M["g"][1]), (120, M["g"][1])); s.text(115, M["g"][1] + 4, "vbp → 5 heads", a="end", c=ACC, b=True)
foot(s, [144, 264, 384], yb, ["vbn", "g0…g4", "vctrl"], ["base ×16", "coarse", "fine"])
s.text(20, 330, "Same legs and gates as a stage's foot, so it carries the same current at every code.", s=12, c=GRAY)
s.text(20, 347, "That current through the diode sets vbp, so the heads (pull-up) match the feet (pull-down):", s=12, c=GRAY)
s.text(20, 364, "equal rise and fall times as the code changes.", s=12, c=GRAY)
# switch
ox = 560
s.text(ox - 20, 48, "Coarse switch (×5, one per bit b)", s=13, b=True)
s.line((ox, 80), (ox + 140, 80)); s.dot(ox + 40, 80); s.line((ox - 20, 80), (ox, 80)); s.text(ox - 24, 84, "vbn", a="end", c=ACC, b=True)
TN = s.fet(ox + 26, 125); TP = s.fet(ox + 126, 125, p=True)
s.line((TN["top"][0], 80), TN["top"]); s.line((TP["top"][0], 80), TP["top"])
s.line(TN["g"], (TN["g"][0] - 6, TN["g"][1])); s.text(TN["g"][0] - 10, TN["g"][1] + 4, "bit", a="end", s=12)
s.line(TP["g"], (TP["g"][0] - 4, TP["g"][1])); s.text(TP["g"][0] - 7, TP["g"][1] - 10, "bitb", a="middle", s=12)
s.text(ox + 26, 180, "TN", a="middle", s=11, c=GRAY); s.text(ox + 126, 180, "TP", a="middle", s=11, c=GRAY)
yg = 170; s.line(TN["bot"], (TN["bot"][0], yg)); s.line(TP["bot"], (TP["bot"][0], yg))
s.line((TN["bot"][0], yg), (ox + 300, yg)); s.dot(ox + 220, yg)
s.text(ox + 305, yg + 4, "g(b)", c=ACC, b=True); s.text(ox + 305, yg + 20, "→ leg b gates", s=11, c=GRAY)
TD = s.fet(ox + 206, 230); s.line((ox + 220, yg), TD["top"]); s.gnd(*TD["bot"])
s.line(TD["g"], (TD["g"][0] - 6, TD["g"][1])); s.text(TD["g"][0] - 10, TD["g"][1] + 4, "bitb", a="end", s=12)
s.text(ox + 240, 235, "TD", s=11, c=GRAY)
s.text(ox - 20, 300, "bit = 1: TN + TP (a transmission gate) pass vbn → leg on", s=12, c=GRAY)
s.text(ox - 20, 317, "bit = 0: gate opens, TD pulls g(b) to 0 V → leg off", s=12, c=GRAY)
s.text(ox - 20, 334, "Legs are binary weighted (1,2,4,8,16 units) → 32 coarse steps", s=12, c=GRAY)
s.save("ring_bias.svg")

# ---------------- the loop
s = S(900, 200)
s.text(20, 26, "The ring: 5 stages in a loop", s=15, b=True)
x0, y = 60, 80
for i in range(5):
    x = x0 + i * 160
    s.dot(x + 20, y); s.text(x + 20, y - 12, f"a{i}", a="middle", b=True)
    s.line((x, y), (x + 50, y))
    s.e.append(f'<polygon points="{x+50},{y-22} {x+50},{y+22} {x+95},{y}" fill="white" stroke="{INK}" stroke-width="1.6"/>')
    s.circ(x + 100, y, 5); s.line((x + 105, y), (x + 160, y))
    s.text(x + 70, y + 40, f"stage {i}", a="middle", s=11, c=GRAY)
xe = x0 + 5 * 160
s.line((xe, y), (xe, y + 60), (x0 - 20, y + 60), (x0 - 20, y), (x0, y))
s.text(20, 172, "5 inversions round the loop (odd) means no stable state, so it oscillates: f = 1 / (2 · 5 · t_d).", s=12, c=GRAY)
s.text(20, 190, "a0 is the output to the divider/buffer. All stages share vbp, vbn, g0…g4 and vctrl.", s=12, c=GRAY)
s.save("ring_loop.svg")
