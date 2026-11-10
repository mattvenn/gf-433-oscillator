#!/usr/bin/env python3
"""Tiny Tapeout wrapper: vco_top in the gf180mcuD analog 2x2 tile, top cell tt_um_mattvenn_gf433_vco.

    python3 layout/gen/tt_wrapper.py [--def <tt_analog_2x2.def>] [--no-png]

Writes gds/tt_um_mattvenn_gf433_vco.gds, lef/tt_um_mattvenn_gf433_vco.lef, build/tt/meta.json and
docs/img/tt_wrapper.png.

The assembly is done with KLayout on the GDS layers, like vco_top.py: layout/vco_top.gds is copied in byte for byte
(a magic GDS round trip would drop cgm_ref's n-well resistor, see docs/ref_layout.md), the standard cells come from
the PDK's GDS, and the LEF is written here from the same pin and stripe rectangles (magic's "lef write" needs the
layout as a .mag with port records; the precheck only needs the TT template's pin rectangles, the power stripes and
an obstruction, which are simple to write directly).

Template: tt-support-tools tech/gf180mcuD/def/analog/tt_analog_2x2.def (die 711.20 x 325.36 um; every pin is a
Metal4 rectangle: ua[0..7] 3 x 1 um on the bottom edge, the digital pins 0.3 x 1 um on the top edge). The default
--def is downloaded from tt-support-tools main into build/tt/ if it is not there.

Floorplan (um, tile coordinates):
  - vco_top mirrored left-right (x -> -x) at origin (602.94, 14.0): bbox x 297.0 ... 703.68, y 10.0 ... 80.795.
    The mirror puts vctrl / vbn (the reference's edge, originally the right edge) on the left edge, next to the
    analog pads ua[1] (x 283.64) and ua[0] (x 327.32).
  - ua[0] <- vctrl: M2 stub from the macro edge, via2, M3 down to y 5, M3 under the macro to the pad, via3s, Metal4
    pad drop.  ua[1] <- vbn: M2, via2s, M3 down to y 3 and left to the pad, via3s, Metal4 drop.
  - five inv_1 cells (bitb = not ui_in) in one row (y 90.16) right above the macro's bit pins, fillties at each end
    and between the inverters; above it (y 94.08, FS) a row with one antenna-diode cell per bit net (the KLayout
    antenna deck flags the ~280 um bit lines otherwise); the bit M3 risers go on up to M2 tracks (y 100 ... 108)
    and over to ui_in[0..4].
  - ck: the macro's M3 riser up to an M2 track (y 112) and over to uo_out[0] (x 200.2).
  - tx_drv (layout/tx_drv.gds, the dipole TX driver) mirrored in y above lsdiv: origin (597.15, 158.915), bbox
    x 597.15 ... 670.12, y 120.0 ... 225.9; its pin edge (ls, en_p, en_n) faces down. ls: vco_top's ls M3 riser
    (tile x 624.35) straight up into it. out_n / out_p: the out bars (M2 + M3) out of both edges, up beside the block,
    left over it (M2, y 232...240 / 244...252, 8 um wide) and down (M3) to ua[2] (out_n) / ua[3] (out_p), about
    750 um each, clear of the ring and the reference. en_p <- ui_in[5], en_n <- ui_in[6]: Metal4 drop, M3 down, M2
    under tx_drv (y 115...116) to the pins, with one antenna cell each in a 4-cell row at y 113.68 (x 652).
    Its own stripes: VGND at x 659.65 (via3s on its VSS rail and the macro's VSS strap) and VDPWR at x 663.65 (via3s
    on its VDD rail), joined to the other VDPWR stripes only by the star bar at the top.
  - 23 tiel cells in one row (y 317.52) under uo_out[1..7], uio_out[0..7], uio_oe[0..7], each with a filltie and
    fill; ZN -> via1/2/3 stack -> Metal4 up to its pin.
  - Metal4 power stripes (2 um, y 5 ... 320.36, the template's span): VDPWR at x 420 and 540, VGND at x 426 and
    590 (via3s on the macro's VDD M3 strap at its top edge and the VSS M3 strap at its bottom edge; the x 540 / 590
    pair also feeds the inverter row), VDPWR at x 649.14 for VDD_LS alone (via3s on its M3 pad: a separate branch
    to the tile's VDPWR pin), and a 1.6 um VGND / VDPWR pair at x 85 / 87.6 for the tiel row. The VDPWR stripes are
    joined only by an M2 bar at the top of the tile (y 319.4 ... 320.36, via2 + via3 at each stripe), a star point
    at the pin edge: VDPWR is one net inside the tile (LVS) and VDD_LS doesn't share the ring's supply path.
    (VGND needs no bar: the stripes meet through the macro's VSS strap and the substrate taps.)
"""
import argparse, json, re, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOP = "tt_um_mattvenn_gf433_vco"
DEF_URL = "https://raw.githubusercontent.com/TinyTapeout/tt-support-tools/main/tech/gf180mcuD/def/analog/tt_analog_2x2.def"
SC = "gf180mcu_fd_sc_mcu7t5v0__"

# layers (GDS layer, datatype)
LY = dict(bnd=(0, 0), m1=(34, 0), v1=(35, 0), m2=(36, 0), v2=(38, 0), m3=(42, 0), v3=(40, 0), m4=(46, 0),
          m4t=(46, 10))
CUT, PAD = 260, 380              # via cut (V*.1 0.26) and metal pad over it (0.06 enclosure all round)
PITCH = 660                      # via array pitch (0.40 space)

# vco_top placement: mirrored in x, origin here (nm)
X0, Y0 = 602940, 14000
VT = dict(xl=-100740, xr=305940, yb=-4000, yt=66795)   # vco_top bbox (own coordinates)


def mx(x):
    """vco_top x -> tile x (mirrored)."""
    return X0 - x


# vco_top pin geometry (own coordinates, from layout/vco_top.gds / docs/top_layout.md)
BITS = {  # name: M3 riser (x0, x1) at the top edge
    "bitb0": (30450, 30830), "bit0": (33090, 33470), "bitb1": (34150, 34530), "bit1": (36790, 37170),
    "bitb2": (37850, 38230), "bit2": (40490, 40870), "bitb3": (41550, 41930), "bit3": (44190, 44570),
    "bitb4": (45250, 45630), "bit4": (47890, 48270)}
CK = (-44390, -44010)            # ck M3 riser at the top edge
LS_PIN = (-21600, -21220)        # ls M3 riser at the top edge (lsdiv's ls port, layout/gen/vco_top.py)
VDDLS = (-47800, -46600, 64395, 66795)   # VDD_LS M3 pad
VDD_STRAP = (56500, 305940, 62880, 66795)  # VDD M3 strap
VSS_STRAP = [(-100740, 28400), (29980, 305940)]  # VSS M3 strap x ranges, y -2400 ... 0
VCTRL_M2 = (300000, 305940, 12745, 13125)
VBN_M2 = (302880, 305940, 44190, 47085)

# tx_drv (layout/tx_drv.gds), mirrored in y (pins ls / en_p / en_n face down), placed above lsdiv
TXD = dict(w=72970, yb=-67000, yt=38915, ls=27200, en_n=22940, en_p=45460,   # own coordinates (layout/gen/tx_drv.py)
           out_b=12970, out_t=14970, vdd=(36515, 38915), vss=(-2400, 0))
TX_PIN_Y = 120000                # tile y of tx_drv's pin edge (its VDD rail): above the ck track (y 112)
TX_X = 624350 - 27200            # its ls pin over vco_top's ls riser (tile x 624.35)
TX_Y = TX_PIN_Y + 38915          # instance origin: tile y = TX_Y - y
OUT_W = 8000                     # out_p / out_n route width (M2 horizontals, M3 verticals): 7.3 mA |avg| (ff) at 2.09 mA/um
ANT_ROW_Y = 113680               # DEF row 29: the two enable antenna diodes, under tx_drv

# medium DAC (layout/mdac.gds), vctrl pull-down (layout/vctrl_pd.gds), digital macro (macro/tx_fine): tile origins
MDAC = (335000, 118000)          # above vco_top, between the bit risers and the VDPWR stripe at x 540
MDAC_PINS = REPO / "layout/mdac_pins.json"
VPD = (252000, 13000)            # left of vco_top, under the vctrl / vbn routes
MAC = (600, 45000)               # left strip; its VDD / VSS Metal4 strap pairs at macro x 55.92 / 58.52 and
                                 # 135.92 / 138.52 land between pin drops: extended, they are the tile stripes there
MAC_LEF = REPO / "macro/tx_fine/lef/tx_fine.lef"
MAC_GDS = REPO / "macro/tx_fine/gds/tx_fine.gds"
TOPPINS = {"clk": "clk", "rst_n": "rst_n", "sclk": "uio_in[0]", "mosi": "uio_in[1]", "cs_n": "uio_in[2]",
           "miso": "uio_out[3]", "fsk": "ui_in[7]", "ck_o": "uo_out[0]", "div16": "uo_out[1]", "div64": "uo_out[2]",
           "div1024": "uo_out[3]"}
VG_TOP = (29000, 29380)          # vco_top's vg / vbnf M3 risers at its top edge (own x)
VBNF_TOP = (51810, 52190)
JOG_X = (192500, 231800)         # the M3 jog channel between the TX risers (x 181...189 and 236...244)
HOP_X = (331000, 333400)         # M3 antenna hop on every DAC control line, between the ui_in drops and the DAC

# std-cell rows
ROW_H = 3920
INV_ROW_Y = 90160                # DEF ROW_22 (N)
TIE_ROW_Y = 317520               # DEF ROW_80 (N)
STRIPE_Y = (5000, 320360)        # template stripe span
STRIPES = [  # (net, x0, width)
    ("VDPWR", 56520, 1600), ("VGND", 59120, 1600),            # the macro's strap pairs, extended (MAC)
    ("VDPWR", 136520, 1600), ("VGND", 139120, 1600),
    ("VDPWR", 420000, 2000), ("VGND", 426000, 2000),
    ("VDPWR", 540000, 2000), ("VGND", 590000, 2000),
    ("VDPWR", 649140, 2000),
    ("VGND", 659650, 2000), ("VDPWR", 663650, 2000)]          # tx_drv: its VSS rail / its own VDPWR branch
STAR_Y = (319400, 320360)        # M2 bar joining the VDPWR stripes at the top of the tile


def parse_def(path):
    t = Path(path).read_text()
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", t).group(1))
    die = [int(v) for v in re.search(r"DIEAREA \( (\S+) (\S+) \) \( (\S+) (\S+) \)", t).groups()]
    conv = (lambda v: v * 1000 // dbu)
    pins = {}
    for m in re.finditer(r"- (\S+) \+ NET \S+ \+ DIRECTION (\w+) \+ USE (\w+)\s+\+ PORT\s+\+ LAYER (\w+) "
                         r"\( (\S+) (\S+) \) \( (\S+) (\S+) \)\s+\+ PLACED \( (\S+) (\S+) \) (\w+)", t):
        name, d, use, layer, a, b, c, e, x, y, o = m.groups()
        a, b, c, e, x, y = (int(v) for v in (a, b, c, e, x, y))
        pins[name] = dict(dir=d, use=use, layer=layer,
                          rect=(conv(x + a), conv(y + b), conv(x + c), conv(y + e)))
    assert len(pins) == int(re.search(r"PINS (\d+) ;", t).group(1)), "DEF pin parse"
    return dict(w=conv(die[2]), h=conv(die[3]), pins=pins)


def build(defpath, gds_out, lef_out):
    import klayout.db as db
    import os
    T = parse_def(defpath)
    W, H, PINS = T["w"], T["h"], T["pins"]
    assert (W, H) == (711200, 325360), (W, H)
    pdk = Path(os.environ.get("PDK_ROOT", "/foss/pdks")) / "gf180mcuD"
    scgds = pdk / "libs.ref/gf180mcu_fd_sc_mcu7t5v0/gds/gf180mcu_fd_sc_mcu7t5v0.gds"

    ly = db.Layout()
    ly.dbu = 0.001
    ly.read(str(REPO / "layout/vco_top.gds"))
    assert ly.cell("vco_top") is not None
    ly.read(str(REPO / "layout/tx_drv.gds"))
    assert ly.cell("tx_drv") is not None
    # the fine-tuning blocks; the macro brings its own copies of the standard cells, which the wrapper then reuses
    # (a second copy would come in renamed "...$1")
    for f, c in ((REPO / "layout/mdac.gds", "mdac"), (REPO / "layout/vctrl_pd.gds", "vctrl_pd"), (MAC_GDS, "tx_fine")):
        ly.read(str(f))
        assert ly.cell(c) is not None, c
    sc = db.Layout()
    sc.read(str(scgds))
    cells = {}
    for n in ("inv_1", "tiel", "tieh", "antenna", "filltie", "fill_1", "fill_2", "fill_4"):
        if ly.cell(SC + n) is not None:                             # already in the layout (from the macro)
            cells[n] = ly.cell(SC + n)
            continue
        src = sc.cell(SC + n)
        dst = ly.create_cell(SC + n)
        dst.copy_tree(src)
        # drop the library's non-mask annotations (63/63 vendor text): not needed in the wrapper
        for li in ly.layer_indexes():
            if (ly.get_info(li).layer, ly.get_info(li).datatype) == (63, 63):
                dst.shapes(li).clear()
        cells[n] = dst
    top = ly.create_cell(TOP)
    L = {k: ly.layer(*v) for k, v in LY.items()}
    log = dict(stripes=[], pins={}, cells=[])

    def r(layer, x1, y1, x2, y2):
        x1, x2 = sorted((int(x1), int(x2)))
        y1, y2 = sorted((int(y1), int(y2)))
        assert x2 > x1 and y2 > y1, (layer, x1, y1, x2, y2)
        assert x1 % 5 == 0 and x2 % 5 == 0 and y1 % 5 == 0 and y2 % 5 == 0, (layer, x1, y1, x2, y2)
        top.shapes(L[layer]).insert(db.Box(x1, y1, x2, y2))

    def cut(layer, x, y):
        r(layer, x - CUT // 2, y - CUT // 2, x + CUT // 2, y + CUT // 2)

    def pad(layer, x, y):
        r(layer, x - PAD // 2, y - PAD // 2, x + PAD // 2, y + PAD // 2)

    def via(n, x, y):
        """via n (1: M1-M2, 2: M2-M3, 3: M3-M4) with 0.38 pads on both metals."""
        lo, hi = {1: ("m1", "m2"), 2: ("m2", "m3"), 3: ("m3", "m4")}[n]
        pad(lo, x, y)
        pad(hi, x, y)
        cut(f"v{n}", x, y)

    def via_array(n, xa, xb, ya, yb, margin=200):
        """via n cuts on PITCH inside [xa, xb] x [ya, yb] (both metals drawn by the caller), centred."""
        nx = max(1, (xb - xa - 2 * margin - CUT) // PITCH + 1)
        ny = max(1, (yb - ya - 2 * margin - CUT) // PITCH + 1)
        x0 = (xa + xb) // 2 - (nx - 1) * PITCH // 2
        y0 = (ya + yb) // 2 - (ny - 1) * PITCH // 2
        x0 -= x0 % 5
        y0 -= y0 % 5
        for i in range(nx):
            for j in range(ny):
                cut(f"v{n}", x0 + i * PITCH, y0 + j * PITCH)
        return nx * ny

    def place(n, x, y, flip=False):
        """standard cell at (x, y) (its lower-left corner); flip: FS orientation (VDD rail at the bottom)."""
        tr = db.Trans(db.Trans.M0, db.Vector(int(x), int(y) + ROW_H)) if flip else db.Trans(db.Vector(int(x), int(y)))
        top.insert(db.CellInstArray(cells[n].cell_index(), tr))
        log["cells"].append((n, x / 1000, y / 1000))

    def label(text, rect):
        """pin: label box on Metal4_label (the LEF rectangle) and the text at its centre."""
        r("m4t", *rect)
        top.shapes(L["m4t"]).insert(db.Text(text, db.Trans(db.Vector((rect[0] + rect[2]) // 2,
                                                                     (rect[1] + rect[3]) // 2))))

    # ---- boundary + vco_top ----
    r("bnd", 0, 0, W, H)
    top.insert(db.CellInstArray(ly.cell("vco_top").cell_index(), db.Trans(db.Trans.M90, db.Vector(X0, Y0))))
    mac = (mx(VT["xr"]), Y0 + VT["yb"], mx(VT["xl"]), Y0 + VT["yt"])
    ytop = Y0 + VT["yt"]

    # ---- template pins: Metal4 drawing + label, exactly the DEF rectangles ----
    for name, p in PINS.items():
        assert p["layer"] == "Metal4"
        r("m4", *p["rect"])
        label(name, p["rect"])
        log["pins"][name] = [v / 1000 for v in p["rect"]]

    def pin_x(name):
        a = PINS[name]["rect"]
        return (a[0] + a[2]) // 2

    def top_pin_drop(name, ybot):
        """digital pin (top edge) -> Metal4 strip down to a via3 at ybot + 190 (M3 pad there)."""
        x = pin_x(name)
        r("m4", x - PAD // 2, ybot, x + PAD // 2, PINS[name]["rect"][3])
        via(3, x, ybot + PAD // 2)
        return x, ybot + PAD // 2

    # ---- analog: ua[0] <- vctrl, ua[1] <- vbn ----
    # vctrl: macro M2 at its (mirrored) left edge, y Y0 + 12.745 ... 13.125
    vy = Y0 + (VCTRL_M2[2] + VCTRL_M2[3]) // 2
    vx = 295800
    r("m2", vx - PAD // 2, Y0 + VCTRL_M2[2], mx(VCTRL_M2[1]) + 100, Y0 + VCTRL_M2[3])
    via(2, vx, vy)
    r("m3", vx - PAD // 2, 5000, vx + PAD // 2, vy)                 # M3 down
    ua0 = PINS["ua[0]"]["rect"]
    r("m3", vx - PAD // 2, 5000, ua0[2], 6000)                      # M3 under the macro to the pad
    r("m4", ua0[0], ua0[1], ua0[2], 6000)                           # Metal4 pad drop
    via_array(3, ua0[0], ua0[2], 5000, 6000, margin=120)
    # vbn: macro M2 pad, y Y0 + 44.19 ... 47.085
    by0, by1 = Y0 + 45000, Y0 + 46400
    bx = (292400, 294400)
    r("m2", bx[0], by0, mx(VBN_M2[1]) + 100, by1)
    r("m3", bx[0], 3000, bx[1], by1)
    via_array(2, bx[0], bx[1], by0, by1)
    ua1 = PINS["ua[1]"]["rect"]
    r("m3", ua1[0], 3000, bx[1], 5000)
    r("m4", ua1[0], ua1[1], ua1[2], 5000)
    via_array(3, ua1[0], ua1[2], 3000, 5000, margin=120)

    # ---- power stripes ----
    for net, x0, w in STRIPES:
        yb, yt = STRIPE_Y
        if net == "VDPWR" and x0 == 56520:
            yt = 321940                                             # reaches the tiel row's VDD rail
        r("m4", x0, yb, x0 + w, yt)
        label(net, (x0, yb, x0 + w, yt))
        log["stripes"].append((net, x0 / 1000, w / 1000, yb / 1000, yt / 1000))
    # landings on the macro's M3 straps
    sx = {(n, x): (x, x + w) for n, x, w in STRIPES}
    nv = {}
    for (n, x0), (a, b) in sx.items():
        if 297000 < a and b < 546000 and n == "VDPWR":              # VDD strap: tile x 297.0 ... 546.44
            nv[(n, x0)] = via_array(3, a, b, Y0 + VDD_STRAP[2], Y0 + VDD_STRAP[3], margin=150)
        if n == "VGND" and a > 297000:                              # VSS strap, y Y0 - 2.4 ... Y0
            assert any(mx(s1) < a and b < mx(s0) for s0, s1 in VSS_STRAP), (a, b)
            nv[(n, x0)] = via_array(3, a, b, Y0 - 2400, Y0, margin=150)
    # VDD_LS: its own VDPWR stripe on the M3 pad
    lsx0, lsx1 = mx(VDDLS[1]), mx(VDDLS[0])
    nv[("VDPWR", 649140)] = via_array(3, lsx0, lsx1, Y0 + VDDLS[2], Y0 + VDDLS[3], margin=150)
    # VDPWR bar at the top of the tile: M2 (under the VGND stripes and the M3 signal risers) from the tiel row's
    # stripe to the VDD_LS stripe, via2 + via3 at every VDPWR stripe; a star point at the pin edge
    r("m2", 136520, STAR_Y[0], 665650, STAR_Y[1])                # from the x 136.52 stripe: the 56.52 one joins
                                                                    # it through the macro's rails; the bar would
                                                                    # hit uio_oe[3]'s tieh output via at x 61.88
    for n, x0, w in STRIPES:
        if n == "VDPWR" and x0 >= 136520:
            r("m3", x0, STAR_Y[0], x0 + w, STAR_Y[1])
            via_array(2, x0, x0 + w, *STAR_Y, margin=150)
            via_array(3, x0, x0 + w, *STAR_Y, margin=150)
    log["via3"] = {f"{n}@{x / 1000:.2f}": v for (n, x), v in nv.items()}

    # ---- inverter row: bitb_i = not ui_in[i] ----
    yr = INV_ROW_Y
    bitc = {k: mx((a + b) // 2) for k, (a, b) in BITS.items()}       # riser centres in tile x
    rise = {k: (mx(b), mx(a)) for k, (a, b) in BITS.items()}         # riser x ranges in tile x
    x = 555160 - 1120
    place("filltie", x, yr)
    row0 = x
    x += 1120
    yI, yZ = yr + 1700, yr + 2950
    inv_x = {}
    for i in (4, 3, 2, 1, 0):
        place("inv_1", x, yr)
        inv_x[i] = x
        xI, xZ = x + 870, x + 1430
        # I: via1 on the pin (no M1 pad: the pin is 0.325 wide), M2 to the bit riser, via2
        cut("v1", xI, yI); pad("m2", xI, yI)
        xb = bitc[f"bit{i}"]
        r("m2", min(xb, xI) - PAD // 2, yI - PAD // 2, max(xb, xI) + PAD // 2, yI + PAD // 2)
        via(2, xb, yI)
        # ZN: via1 high on the pin, M2 to the bitb riser, via2
        cut("v1", xZ, yZ); pad("m2", xZ, yZ)
        xbb = bitc[f"bitb{i}"]
        r("m2", min(xbb, xZ) - PAD // 2, yZ - PAD // 2, max(xbb, xZ) + PAD // 2, yZ + PAD // 2)
        via(2, xbb, yZ)
        # bitb riser up from the macro to the stub
        a, b = rise[f"bitb{i}"]
        r("m3", a, ytop - 400, b, yZ + PAD // 2)
        x += 2240
        if i:
            place("filltie", x, yr); x += 1120
            place("fill_1", x, yr); x += 560
    place("filltie", x, yr)
    row1 = x + 1120
    # rails -> stripes: VDD (top) left to the x 540 VDPWR stripe, VSS (bottom) right to the x 590 VGND stripe
    r("m1", 540000, yr + ROW_H - 300, row0 + 10, yr + ROW_H + 300)
    via(1, 541000, yr + ROW_H); via(2, 541000, yr + ROW_H); via(3, 541000, yr + ROW_H)
    r("m1", row1 - 10, yr - 300, 592000, yr + 300)
    via(1, 591000, yr); via(2, 591000, yr); via(3, 591000, yr)
    # antenna diodes on the five bit nets (KLayout ANT.16 / ANT.4: ~280 um of 0.38 um M3 on a few um2 of gate),
    # one row up (FS, sharing the VDD rail): antenna cell I pin -> via1, M2 stub at yA, via2 on the bit riser
    ya_row = yr + ROW_H
    yA = ya_row + 2100                                              # antenna I pin (FS): y 1.21 ... 3.11
    x = row0
    place("filltie", x, ya_row, flip=True); x += 1120
    for i in (4, 3, 2, 1, 0):
        place("antenna", x, ya_row, flip=True)
        xa = x + 305
        cut("v1", xa, yA); pad("m2", xa, yA)
        xb = bitc[f"bit{i}"]
        r("m2", min(xb, xa) - PAD // 2, yA - PAD // 2, max(xb, xa) + PAD // 2, yA + PAD // 2)
        via(2, xb, yA)
        x += 1120
        fills = (("filltie", 1120), ("fill_2", 1120), ("fill_1", 560)) if i else (("filltie", 1120), ("fill_2", 1120))
        for f, wf in fills:
            place(f, x, ya_row, flip=True); x += wf
    assert x == row1, (x, row1)
    r("m1", row1 - 10, ya_row + ROW_H - 300, 592000, ya_row + ROW_H + 300)   # its VSS rail (top) -> VGND
    via(1, 591000, ya_row + ROW_H); via(2, 591000, ya_row + ROW_H); via(3, 591000, ya_row + ROW_H)

    # ---- bit lines: macro riser -> M2 track -> M3 up to ui_in[i] ----
    TRK = {i: 100000 + 2000 * i for i in range(5)}
    for i in range(5):
        a, b = rise[f"bit{i}"]
        yt_ = TRK[i]
        r("m3", a, ytop - 400, b, yt_ + PAD // 2)
        via(2, bitc[f"bit{i}"], yt_)
        name = f"ui_in[{i}]"
        xp, yv = top_pin_drop(name, 322500)
        r("m2", xp - PAD // 2, yt_ - PAD // 2, bitc[f"bit{i}"] + PAD // 2, yt_ + PAD // 2)
        via(2, xp, yt_)
        r("m3", xp - PAD // 2, yt_ - PAD // 2, xp + PAD // 2, yv + PAD // 2)

    yck = 112000
    ckx = mx((CK[0] + CK[1]) // 2)
    r("m3", mx(CK[1]), ytop - 400, mx(CK[0]), yck + PAD // 2)
    via(2, ckx, yck)

    # ---- tx_drv: the dipole driver, mirrored in y above lsdiv; tile (x, y) = (TX_X + x, TX_Y - y) ----
    top.insert(db.CellInstArray(ly.cell("tx_drv").cell_index(), db.Trans(db.Trans.M0, db.Vector(TX_X, TX_Y))))
    tx = lambda x: TX_X + x
    ty = lambda y: TX_Y - y
    # ls: vco_top's ls M3 riser (macro top edge) on up into tx_drv's ls pin (its bottom edge here)
    lsx = mx((LS_PIN[0] + LS_PIN[1]) // 2)
    assert lsx == tx(TXD["ls"]), (lsx, tx(TXD["ls"]))
    r("m3", lsx - PAD // 2, ytop - 400, lsx + PAD // 2, TX_PIN_Y + 400)
    # outputs: the out bars (M2 + M3, tx_drv's channel) out of both edges, up beside the block, left over its top
    # and down to the pads, out_n -> ua[2], out_p -> ua[3]; about the same length each (~ 750 um), away from the
    # ring and the reference. Horizontals on M2 (they cross the ui_in / ck M3 risers), verticals on M3 (they cross
    # the ck M2 track); M2 + M3 together where nothing crosses (beside tx_drv), via2 arrays at every layer change.
    yo0, yo1 = sorted((ty(TXD["out_b"]), ty(TXD["out_t"])))
    w = OUT_W

    def m23(xa, xb, ya, yb):
        r("m2", xa, ya, xb, yb)
        r("m3", xa, ya, xb, yb)
    ua2, ua3 = PINS["ua[2]"]["rect"], PINS["ua[3]"]["rect"]
    # Each overlap of two segments gets exactly one via2 array (two arrays on one area put cuts on top of each
    # other: V2.1 / V2.2a), and the bar extensions stop their arrays short of tx_drv's own via2s (from 0.4 um in).
    # out_n: left edge -> x 578...586 -> up to y 232...240 -> left (M2) to x 236...244 -> down (M3) to ua[2]
    xn = (578000, 586000)
    yn = (232000, 240000)
    xc = (ua2[0] + ua2[2]) // 2
    xnd = (xc - w // 2 - (xc - w // 2) % 5, xc + w // 2 - (xc + w // 2) % 5)
    m23(xn[0], tx(0) + 400, yo0, yo1)                               # bar extension, overlaps the block's bar
    via_array(2, xn[1], tx(0) - 300, yo0, yo1)
    m23(xn[0], xn[1], yo0, yn[1])                                   # up (M2 + M3)
    via_array(2, xn[0], xn[1], yo0, yn[1])
    r("m2", xnd[0], yn[0], xn[1], yn[1])                            # left (M2)
    r("m3", xnd[0], 2000, xnd[1], yn[1])                            # down (M3)
    via_array(2, xnd[0], xnd[1], yn[0], yn[1])
    r("m4", ua2[0], ua2[1], ua2[2], 4500)                           # Metal4 pad drop
    via_array(3, ua2[0], ua2[2], 2000, 4500, margin=120)
    # out_p: right edge -> x 674...682 -> up to y 244...252 -> left (M2) to x 181...189 -> down (M3) -> ua[3]
    xp_ = (tx(TXD["w"]) + 4000, tx(TXD["w"]) + 4000 + w)
    yp = (244000, 252000)
    xpd = (181000, 189000)
    m23(tx(TXD["w"]) - 400, xp_[1], yo0, yo1)
    via_array(2, tx(TXD["w"]) + 300, xp_[0], yo0, yo1)
    m23(xp_[0], xp_[1], yo0, yp[1])
    via_array(2, xp_[0], xp_[1], yo0, yp[1])
    r("m2", xpd[0], yp[0], xp_[1], yp[1])
    r("m3", xpd[0], 1500, xpd[1], yp[1])
    via_array(2, xpd[0], xpd[1], yp[0], yp[1])
    r("m3", xpd[0], 1500, ua3[2], 4500)                             # right to the pad, below the ck riser's end
    r("m4", ua3[0], ua3[1], ua3[2], 4500)
    via_array(3, ua3[0], ua3[2], 1500, 4500, margin=120)
    # enables: ui_in[5] -> en_p, ui_in[6] -> en_n: Metal4 drop, M3 down to an M2 line under tx_drv, M3 up into
    # the pin; each line runs on to its antenna diode (KLayout ANT.4 / ANT.16, as the bit lines)
    xr0 = 652000                                                    # antenna row: filltie, antenna x 2, filltie
    yR = ANT_ROW_Y
    place("filltie", xr0, yR)
    for k in range(2):
        place("antenna", xr0 + 1120 * (k + 1), yR)
    place("filltie", xr0 + 3360, yR)
    for k, (net, pin) in enumerate((("en_n", "ui_in[6]"), ("en_p", "ui_in[5]"))):
        yl = yR + 1300 + 1000 * k                                   # the antenna I pin (N): y 0.81 ... 2.71
        xa = xr0 + 1120 * (k + 1) + 305
        xp, yv = top_pin_drop(pin, 322500)
        r("m3", xp - PAD // 2, yl - PAD // 2, xp + PAD // 2, yv + PAD // 2)
        via(2, xp, yl)
        r("m2", xp - PAD // 2, yl - PAD // 2, xa + PAD // 2, yl + PAD // 2)
        xe = tx(TXD[net])
        via(2, xe, yl)
        r("m3", xe - PAD // 2, yl - PAD // 2, xe + PAD // 2, TX_PIN_Y + 400)
        cut("v1", xa, yl); pad("m2", xa, yl)
    # antenna row rails: VDD (top) up into tx_drv's VDD rail (M1), VSS (bottom) right to the tx_drv VGND stripe
    r("m1", xr0 + 400, yR + ROW_H - 300, xr0 + 1000, TX_PIN_Y + 300)
    r("m1", xr0 + 4480 - 10, yR - 300, 661200, yR + 300)
    via(1, 660650, yR); via(2, 660650, yR); via(3, 660650, yR)
    # supplies: the driver's VDPWR stripe on its VDD rail, VGND on its VSS rail (both carry M3 there)
    for net, (y0, y1) in (("VDPWR", TXD["vdd"]), ("VGND", TXD["vss"])):
        x0 = {"VDPWR": 663650, "VGND": 659650}[net]
        a_, b_ = sorted((ty(y0), ty(y1)))
        nv[(net + "_tx", x0)] = via_array(3, x0, x0 + 2000, a_, b_, margin=150)
    log["via3"] = {f"{n}@{x / 1000:.2f}": v for (n, x), v in nv.items()}
    log["tx_drv"] = dict(origin=(TX_X / 1000, TX_Y / 1000), mirror="y -> -y",
                         bbox=[tx(0) / 1000, ty(TXD["yt"]) / 1000, tx(TXD["w"]) / 1000, ty(TXD["yb"]) / 1000],
                         out_n="ua[2]", out_p="ua[3]", en_p="ui_in[5]", en_n="ui_in[6]")

    # ---- tie-low row ----
    tied = [f"uo_out[{i}]" for i in range(1, 8)] + [f"uio_out[{i}]" for i in range(8)] + \
           [f"uio_oe[{i}]" for i in range(8)]
    tied.sort(key=pin_x)
    driven = set(TOPPINS.values())                                  # these slots get a fill_4 instead of a tie cell
    xs = [pin_x(n) for n in tied]
    assert all(b - a == 7280 for a, b in zip(xs, xs[1:])), xs
    yr = TIE_ROW_Y
    x = xs[0] - 1410
    for n in tied:
        xp = pin_x(n)
        assert x == xp - 1410
        if n in driven:
            place("fill_4", x, yr)
        else:
            high = n == "uio_oe[3]"                                 # MISO: uio[3] is an output
            place("tieh" if high else "tiel", x, yr)
            yz = yr + (2850 if high else 1090)                      # tieh Z M1: y 2.305 ... 3.39; tiel ZN: 0.53 ... 1.65
            cut("v1", xp, yz); pad("m2", xp, yz)
            cut("v2", xp, yz); pad("m3", xp, yz)
            cut("v3", xp, yz)
            r("m4", xp - PAD // 2, yz - PAD // 2, xp + PAD // 2, PINS[n]["rect"][3])
        x += 2240
        for f, wf in (("filltie", 1120), ("fill_4", 2240), ("fill_2", 1120), ("fill_1", 560)):
            place(f, x, yr); x += wf
    # tiel row rails -> the 1.6 um stripe pair at x 85 / 87.6 (inside the uio_oe[0] slot)
    via(1, 59920, yr); via(2, 59920, yr); via(3, 59920, yr)
    via(1, 57320, yr + ROW_H); via(2, 57320, yr + ROW_H); via(3, 57320, yr + ROW_H)

    log["tx_fine"] = add_tx_fine(ly, top, L, r, cut, pad, via, via_array, pin_x, top_pin_drop, PINS, ytop, yck)

    # ---- checks on what was drawn ----
    dup = [c.name for c in ly.each_cell() if "$" in c.name]
    assert not dup, f"duplicate cell names: {dup}"
    for li in ly.layer_indexes():
        i = ly.get_info(li)
        if (i.layer, i.datatype) in ((81, 0), (82, 0), (81, 10)):
            assert db.Region(top.begin_shapes_rec(li)).is_empty(), "Metal5 / via4 in the wrapper"
    bb = top.bbox()
    assert (bb.left, bb.bottom, bb.right, bb.top) == (0, 0, W, H), bb
    ly.write(str(gds_out))

    write_lef(lef_out, W, H, PINS, top, L, db)
    log.update(macro=[v / 1000 for v in mac], mirror="x -> -x", origin=(X0 / 1000, Y0 / 1000),
               inv_x={i: v / 1000 for i, v in inv_x.items()}, tracks={f"bit{i}": TRK[i] / 1000 for i in TRK},
               ck_track=yck / 1000)
    return log


def macro_pins(lef):
    """{pin: (layer, (x0, y0, x1, y1) nm)} and {VDD/VSS: [rects]} from the macro LEF."""
    t = Path(lef).read_text()
    pins, power = {}, {}
    for m in re.finditer(r"PIN (\S+)(.*?)END \1", t, re.S):
        name, body = m.groups()
        rects = [(l, tuple(int(round(float(v) * 1000)) for v in r)) for l, *r in
                 re.findall(r"LAYER (\S+) ;\s*RECT (\S+) (\S+) (\S+) (\S+)", body)]
        if name in ("VDD", "VSS"):
            power[name] = [rc for l, rc in rects if l == "Metal4"]
        else:
            pins[name] = rects[0]
    return pins, power


def add_tx_fine(ly, top, L, r, cut, pad, via, via_array, pin_x, top_pin_drop, PINS, ytop, yck):
    """The fine-tuning blocks (docs/tx_fine_tune.md): the digital macro tx_fine, the medium DAC mdac, the vctrl
    pull-down vctrl_pd, and their wiring. Returns a log dict."""
    import klayout.db as db
    log = {}
    # ---- instances ----
    for c, (x, y) in (("tx_fine", MAC), ("mdac", MDAC), ("vctrl_pd", VPD)):
        top.insert(db.CellInstArray(ly.cell(c).cell_index(), db.Trans(db.Vector(x, y))))
    mp, mpow = macro_pins(MAC_LEF)
    dp = json.loads(MDAC_PINS.read_text())
    M = lambda x, y: (MAC[0] + x, MAC[1] + y)
    D = lambda x, y: (MDAC[0] + x, MDAC[1] + y)
    # ---- macro power: the strap pairs under the tile stripes must line up exactly ----
    for net, tnet in (("VDD", "VDPWR"), ("VSS", "VGND")):
        xs = sorted(MAC[0] + rc[0] for rc in mpow[net])
        tile = sorted(x0 for n, x0, w in STRIPES if n == tnet and x0 < 200000)
        assert all(t in xs for t in tile), (net, xs, tile)
    log["macro_straps_used"] = [x0 / 1000 for n, x0, w in STRIPES if x0 < 200000]
    # ---- medium DAC: supplies on the x 420 (VDPWR) / 426 (VGND) stripes ----
    for net, x0 in (("VDD", 420000), ("VSS", 426000)):
        _, xl, yl = dp["pins"][net]
        yc = MDAC[1] + yl
        via_array(3, x0, x0 + 2000, yc - 1000, yc + 1000, margin=150)
    # vg: DAC M2 pin (right edge) -> M2 right to vco_top's vg riser, M3 down onto it
    _, xg, yg = dp["pins"]["vg"]
    gx, gy = D(xg, yg)
    vgx = mx((VG_TOP[0] + VG_TOP[1]) // 2)
    r("m2", gx - PAD // 2, gy - PAD // 2, vgx + PAD // 2, gy + PAD // 2)
    via(2, vgx, gy)
    r("m3", vgx - PAD // 2, ytop - 400, vgx + PAD // 2, gy + PAD // 2)
    # vbnf: DAC M3 pin -> M3 right and down onto vco_top's vbnf riser
    _, xb, yb = dp["pins"]["vbnf"]
    bx_, by_ = D(xb, yb)
    vbx = mx((VBNF_TOP[0] + VBNF_TOP[1]) // 2)
    r("m3", bx_ - PAD // 2, by_ - PAD // 2, vbx + PAD // 2, by_ + PAD // 2)
    r("m3", vbx - PAD // 2, ytop - 400, vbx + PAD // 2, by_ + PAD // 2)
    log["mdac"] = dict(origin=[v / 1000 for v in MDAC], vg=[gx / 1000, gy / 1000], vbnf=[bx_ / 1000, by_ / 1000])
    # ---- vctrl pull-down: a -> vctrl (the ua[0] M3 at x 295.8), b -> VSS (cgm_ref's bottom M2 rail) ----
    pa = (VPD[0] + 31910, VPD[1] + 11300)
    pb_ = (VPD[0] + 580, VPD[1] + 1100)
    vx = 295800
    r("m2", pa[0] - PAD // 2, pa[1] - PAD // 2, vx + PAD // 2, pa[1] + PAD // 2)
    via(2, vx, pa[1])
    r("m2", pb_[0] - PAD // 2, Y0 - 190 - 100, mx(VT["xr"]) + 600, Y0 + 190 - 100)
    r("m2", pb_[0] - PAD // 2, Y0 - 290, pb_[0] + PAD // 2, pb_[1] + PAD // 2)
    log["vctrl_pd"] = dict(origin=[v / 1000 for v in VPD])
    # ---- DAC control lines: macro east pins (M3) -> M2 -> M3 jog -> M2 -> DAC pins n<g> (M2, left edge) ----
    names = [(f"dac_tn[{i}]", f"ns{i + 1}") for i in range(31)] + [(f"dac_bn[{b}]", f"nb{b}") for b in range(5)] + \
            [("dac_sdn", "nsd")]
    jog = {}
    ends = {}
    for mpin, dpin in names:
        _, (x0, y0, x1, y1) = mp[mpin]
        sx, sy = M(x1, (y0 + y1) // 2)
        sy -= sy % 5
        _, dx, dy = dp["pins"][dpin]
        ends[mpin] = (sx, sy, D(dx, dy))
    # the out_p M2 bar (y 244 ... 252) crosses the macro-side band: a pin there steps down on M3 to y 242.9 first
    BAND = (243700, 252300)
    step = {m: 242900 for m, (sx, sy, _) in ends.items() if BAND[0] <= sy <= BAND[1]}
    assert len(step) <= 1, step
    ends = {m: (sx, step.get(m, sy), d) for m, (sx, sy, d) in ends.items()}
    pin_y = {m: M(0, (mp[m][1][1] + mp[m][1][3]) // 2)[1] // 5 * 5 for m in ends}
    # jog order: line i's macro-side M2 [macro, x_i] at y m_i and line j's DAC-side M2 [x_j, DAC] at y d_j overlap
    # if |m_i - d_j| < 700 and x_j < x_i, so such pairs need x_i < x_j: a topological order (ties by m)
    after = {a: {b for b in ends if b != a and abs(ends[a][1] - ends[b][2][1]) < 700} for a in ends}
    order, done = [], set()
    while len(order) < len(ends):
        free = [a for a in ends if a not in done and not any(a in after[b] for b in ends if b not in done and b != a)]
        assert free, "jog order: cycle"
        nxt = min(free, key=lambda a: ends[a][1])
        order.append(nxt); done.add(nxt)
    for k, mpin in enumerate(order):
        dpin = dict(names)[mpin]
        sx, sy, (tx_, ty_) = ends[mpin]
        xj = JOG_X[0] + 680 * k
        assert xj + PAD // 2 < JOG_X[1], k
        xo = sx + 800                                               # via2 just outside the macro's east edge
        py = pin_y[mpin]
        r("m3", sx - 560, py - 280, xo + PAD // 2, py + 280)        # the pin (M3) out of the macro
        if py != sy:                                                # the out_p band: M3 down to y 242.9
            r("m3", xo - PAD // 2, sy - PAD // 2, xo + PAD // 2, py + PAD // 2)
        via(2, xo, sy)
        r("m2", xo - PAD // 2, sy - PAD // 2, xj + PAD // 2, sy + PAD // 2)
        if abs(sy - ty_) < 700:                                     # too close for two via2s: an M2 dogleg
            r("m2", xj - PAD // 2, min(sy, ty_) - PAD // 2, xj + PAD // 2, max(sy, ty_) + PAD // 2)
        else:
            via(2, xj, sy)
            r("m3", xj - PAD // 2, min(sy, ty_) - PAD // 2, xj + PAD // 2, max(sy, ty_) + PAD // 2)
            via(2, xj, ty_)
        # antenna: an M3 hop just before the DAC, so the long M2 run is not on the switch gate when M2 is etched
        h1, h2 = HOP_X
        r("m2", xj - PAD // 2, ty_ - PAD // 2, h1 + PAD // 2, ty_ + PAD // 2)
        via(2, h1, ty_)
        r("m3", h1 - PAD // 2, ty_ - PAD // 2, h2 + PAD // 2, ty_ + PAD // 2)
        via(2, h2, ty_)
        r("m2", h2 - PAD // 2, ty_ - PAD // 2, tx_ + PAD // 2, ty_ + PAD // 2)
        jog[mpin] = dict(dac=dpin, jog_x=xj / 1000, y_macro=sy / 1000, y_dac=ty_ / 1000)
    log["dac_lines"] = jog
    # ---- ck: vco_top's ck (M2 track y 112) -> x 178 -> M3 down to y 40 -> M2 under the macro to its ck pin ----
    _, (x0, y0, x1, y1) = mp["ck"]
    cx, cy = M((x0 + x1) // 2, y0)
    cx -= cx % 5
    xc3, yc2 = 178000, 40000
    ckx = mx((CK[0] + CK[1]) // 2)
    r("m2", xc3 - PAD // 2, yck - PAD // 2, ckx + PAD // 2, yck + PAD // 2)
    via(2, xc3, yck)
    r("m3", xc3 - PAD // 2, yc2 - PAD // 2, xc3 + PAD // 2, yck + PAD // 2)
    via(2, xc3, yc2)
    r("m2", cx - PAD // 2, yc2 - PAD // 2, xc3 + PAD // 2, yc2 + PAD // 2)
    r("m2", cx - PAD // 2, yc2 - PAD // 2, cx + PAD // 2, cy + 560)
    # ---- top-edge pins: macro north pins (M2) -> M3 up -> M2 track (y 306 ...) -> M3 up to a via3 -> Metal4 drop ----
    ytrk = {}
    for k, (mpin, tpin) in enumerate(sorted(TOPPINS.items(), key=lambda t: mp[t[0]][1][0])):
        _, (x0, y0, x1, y1) = mp[mpin]
        sx = MAC[0] + (x0 + x1) // 2
        sx -= sx % 5
        ys = MAC[1] + y1 + 600                                      # just above the macro's top edge
        yt = 306400 + 800 * k                                       # clear of the pin stubs (top 305.79)
        r("m2", sx - 280, MAC[1] + y0, sx + 280, ys + PAD // 2)    # pin stub up out of the macro
        via(2, sx, ys)
        r("m3", sx - PAD // 2, ys - PAD // 2, sx + PAD // 2, yt + PAD // 2)
        via(2, sx, yt)
        xp, yv = top_pin_drop(tpin, 322500)
        r("m2", min(sx, xp) - PAD // 2, yt - PAD // 2, max(sx, xp) + PAD // 2, yt + PAD // 2)
        via(2, xp, yt)
        r("m3", xp - PAD // 2, yt - PAD // 2, xp + PAD // 2, yv + PAD // 2)
        ytrk[mpin] = dict(pin=tpin, track_y=yt / 1000)
    log["top_pins"] = ytrk
    return log


def write_lef(path, W, H, PINS, top, L, db):
    f = lambda v: f"{v / 1000:.3f}"
    out = ["VERSION 5.7 ;", "  NOWIREEXTENSIONATPIN ON ;", '  DIVIDERCHAR "/" ;', '  BUSBITCHARS "[]" ;',
           f"MACRO {TOP}", "  CLASS BLOCK ;", f"  FOREIGN {TOP} ;", "  ORIGIN 0.000 0.000 ;",
           f"  SIZE {f(W)} BY {f(H)} ;"]
    for name in sorted(PINS):
        p = PINS[name]
        out += [f"  PIN {name}", f"    DIRECTION {p['dir']} ;", "    USE SIGNAL ;", "    PORT",
                "      LAYER Metal4 ;", "        RECT " + " ".join(f(v) for v in p["rect"]) + " ;",
                "    END", f"  END {name}"]
    for net, use in (("VDPWR", "POWER"), ("VGND", "GROUND")):
        out += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER Metal4 ;"]
        for n, x0, w in STRIPES:
            if n == net:
                yt = 321940 if (n, x0) == ("VDPWR", 56520) else STRIPE_Y[1]
                out.append(f"        RECT {f(x0)} {f(STRIPE_Y[0])} {f(x0 + w)} {f(yt)} ;")
        out += ["    END", f"  END {net}"]
    # obstructions: Metal1-3 over the whole tile; Metal4: every drawn Metal4 shape that is not a pin or a stripe
    # (the pin drops and the analog pad drops), as bounding boxes
    out += ["  OBS"] + sum([[f"    LAYER Metal{k} ;", f"      RECT 0.000 0.000 {f(W)} {f(H)} ;"] for k in (1, 2, 3)], [])
    m4 = db.Region(top.shapes(L["m4"])).merged()
    pins = db.Region()
    for p in PINS.values():
        pins.insert(db.Box(*p["rect"]))
    for n, x0, w in STRIPES:
        yt = 321940 if (n, x0) == ("VDPWR", 56520) else STRIPE_Y[1]
        pins.insert(db.Box(x0, STRIPE_Y[0], x0 + w, yt))
    rest = (m4 - pins.sized(300)).merged()
    if not rest.is_empty():
        out.append("    LAYER Metal4 ;")
        for poly in rest.each():
            b = poly.bbox()
            out.append(f"      RECT {f(b.left)} {f(b.bottom)} {f(b.right)} {f(b.top)} ;")
    out += ["  END", f"END {TOP}", "END LIBRARY", ""]
    Path(path).write_text("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--def", dest="defp", default=None)
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()
    out = REPO / "build" / "tt"
    out.mkdir(parents=True, exist_ok=True)
    defp = Path(a.defp) if a.defp else out / "tt_analog_2x2.def"
    if not defp.exists():
        urllib.request.urlretrieve(DEF_URL, defp)
    (REPO / "gds").mkdir(exist_ok=True)
    (REPO / "lef").mkdir(exist_ok=True)
    gds = REPO / "gds" / f"{TOP}.gds"
    lef = REPO / "lef" / f"{TOP}.lef"
    log = build(defp, gds, lef)
    (out / "meta.json").write_text(json.dumps(log, indent=1))
    print(f"wrote {gds} ({gds.stat().st_size / 1e6:.2f} MB), {lef}")
    print("macro (tile um):", log["macro"], " via3 counts:", log["via3"])
    if not a.no_png:
        png = REPO / "docs" / "img" / "tt_wrapper.png"
        subprocess.run(["klayout", "-zz", "-rd", f"gds={gds}", "-rd", f"png={png}", "-rd", "w=2400",
                        "-rd", "hide=0/0", "-r", str(HERE / "render_gds.py")], check=False)


if __name__ == "__main__":
    main()
