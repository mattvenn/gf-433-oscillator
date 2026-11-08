#!/usr/bin/env python3
"""VCO top level: ring_core_v3 + cgm_ref + lsdiv + the VDD_LS decap, abutted, in one cell vco_top.

    python3 layout/gen/vco_top.py [--gds layout/vco_top.gds] [--out build/top] [--no-png]

The three block GDS files are placed as instances (not flattened, not changed). The decap cell decap_ls is drawn
here with the ring_core helpers (the style of cgm_ref's CF: nfet_03v3 gate-cap fingers, S/D columns into a p+
tapped VSS rail, gate strap on top) and written by magic; the assembly and the top-level metal are done with KLayout
on the GDS layers, so the block cells are copied byte for byte (cgm_ref keeps its RES_MK over the n-well resistor).

Floorplan (x left to right, all blocks on the same y origin = the bottom VSS rail, y -2.4 ... 0):
  decap_ls | channel (ck M3, VDD_LS M2) | lsdiv (raised +31.455 um, a0 abutting) | ring_core | cgm_ref
  - lsdiv's a0 M2 spine (right edge) touches the core's a0 M2 tap (left edge, y 36.17): no a0 wire.
  - cgm_ref abuts the core's right edge (x 67.19): vbnf meets the DAC gate pin vbn, vctrl feeds through.
Top-level metal (M1-M3 only, no Metal4/5):
  VSS   : bottom rail M1 + M2 + p+ tap (in decap_ls) from the decap under lsdiv to the core, two p+ tap columns
          under lsdiv (DCF.1a); M2 + M1 bridges core -> cgm_ref; an M3 strap over the
          whole bottom rail (gap at the core's vg M3 pin) with via2s, for the tile's Metal4 VGND via3 landing;
          lsdiv's left M3 VSS strap extended down (4 um wide under lsdiv) into it: lsdiv's return current goes
          straight to the bottom rail, not through the core's tap ring.
  VDD   : the core's VDD rail (y 43.155...45.555) -> an M2 drop (x 58...62) -> an M3 strap along the top edge
          (y 62.88 ... top) over cgm_ref's column A to cgm_ref's VDD rail (y 62.88...65.28, via2s between its via1s).
  VDD_LS: lsdiv's VDD rail (M2, y 41.17...43.57 here) <- an M2 strap from the decap's gate strap; M2 spine and an
          M3 pad up to the top edge. Separate from VDD everywhere inside the macro.
Pins (labels in vco_top): bit0-4 / bitb0-4 and ck on M3 at the top edge, VDD and VDD_LS on M3 at the top edge,
  vg on M3 at the bottom edge (the core's pin), vctrl and vbn on M2 at the right edge (cgm_ref's pins), VSS on M2/M3
  at the bottom, a0 on M2 at the lsdiv / core junction (not routed to an edge: ~1 % of f per fF on a0).
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ring_core import Cell, fet_row  # noqa: E402

REPO = HERE.parents[1]
COX = 4.07e-3                      # nfet_03v3 gate C per area incl. overlap (F/m2), as ring_core_v3.py
DCLS = dict(nf=5, w=49.14, l=10.0)  # VDD_LS decap fingers: the CF finger of cgm_ref, 5 of them
DCLS["c_pf"] = DCLS["nf"] * DCLS["w"] * DCLS["l"] * 1e-12 * COX * 1e12

# placements (nm): block origins in vco_top
CORE = (0, 0)
REF = (67190, 0)                   # the core's right edge
LS = (-42390, 31455)               # lsdiv's right edge (40.49) on the core's left edge (-1.9); a0 4.715 -> 36.17
YTOP = 66795                       # macro top = cgm_ref's top
YBOT = -4000                       # macro bottom = the core's vg pin
VSS_B, VSS_T = -2400, 0
CK_X = (-44390, -44010)            # ck M3 riser in the channel left of lsdiv
DC_R = -45600                      # decap_ls right edge
VDD_DROP = (58000, 62000)          # VDD M2 drop above the core (right of the bit risers)
VDD_M3 = (56500, 62880)            # VDD M3 strap: x start, y bottom (to YTOP)
LS_VDD = (41170, 43570)
RAIL_END = -1000                   # decap_ls's VSS rail runs on under lsdiv onto the core's M1 tap ring (x -1.605)
TAP_X = (-31600, -16600)           # p+ tap columns under lsdiv (vco_top x)
TAP_TOP = 28000            # lsdiv VDD rail in vco_top (9.715...12.115 + 31.455)
CORE_BITS_X = [(30450, 30830), (33090, 33470), (34150, 34530), (36790, 37170), (37850, 38230), (40490, 40870),
               (41550, 41930), (44190, 44570), (45250, 45630), (47890, 48270)]   # core bit/bitb M3 at its top edge
CORE_TOP = 47875
VG_X = (29000, 29380)


def um(v):
    return int(round(v * 1000 / 5.0)) * 5


def decap_cell(rail_to=None, taps=()):
    """decap_ls: nf fingers W x L (nfet_03v3), gate = VDD_LS strap (M1 + M2) on top, S/D/B VSS, rail at the bottom.
    rail_to: extend the VSS rail (M1 + M2 + p+ tap) to this local x (under lsdiv, to the core's left edge);
    taps: local x of p+ tap columns (M1 + contacts) standing on the rail up to TAP_TOP, which break up the empty
    area under lsdiv (KLayout DCF.1a: no gap of >= 20 um between COMP shapes without dummy COMP)."""
    c = Cell("decap_ls")
    x0, yb = 1000, 600
    W, L, n = um(DCLS["w"]), um(DCLS["l"]), DCLS["nf"]
    cf = fet_row(c, x0, yb, W, [(L, "VDD_LS")] * n, "n")
    yt = yb + W
    s_b = yt + 255
    s_t = s_b + 800
    pcy = s_b + 190
    for (ga, gb) in cf["gx"]:
        c.r("poly", ga, yt, gb, pcy + 185)
        gcx = (ga + gb) // 2
        for o in range(-3600, 3601, 1200):
            c.r("pc", gcx + o - 115, pcy - 115, gcx + o + 115, pcy + 115)
    for cx in cf["rx"]:                      # S/D columns down into the VSS rail
        c.r("m1", cx - 190, VSS_T - 300, cx + 190, cf["cb"])
    x1 = cf["x1"]
    xr = x1 + 1000
    xe = rail_to if rail_to is not None else xr
    c.r("m1", 600, s_b, x1, s_t)             # gate strap M1 + M2 (VDD_LS)
    c.r("m2", 600, s_b, x1, s_t)
    x = 1000
    while x + 400 < x1:
        c.r("v1", x - 130, s_b + 270, x + 130, s_t - 270)
        x += 2000
    # VSS rail (M1 + M2, p+ tap), as cgm_ref's rail()
    c.r("m1", 0, VSS_B, xe, VSS_T)
    c.r("m2", 0, VSS_B, xe, VSS_T)
    x = 400
    while x + 400 < xe:
        c.r("v1", x - 130, VSS_B + 300, x + 130, VSS_T - 300)
        x += 2000
    te = xe - 300 if rail_to is None else xe - 1300   # tap strip stops 0.7 um short of the core's p+ ring
    c.r("psd", 300, VSS_B + 1010, te, VSS_B + 1390)
    c.r("psc", 375, VSS_B + 1085, te - 75, VSS_B + 1315)
    for tx in taps:                          # p+ tap columns on the rail
        c.r("psd", tx - 190, VSS_B + 1010, tx + 190, TAP_TOP)
        c.r("psc", tx - 115, VSS_B + 1085, tx + 115, TAP_TOP - 75)
        c.r("m1", tx - 190, VSS_B, tx + 190, TAP_TOP)
    c.label("VSS", "m2", 1000, (VSS_B + VSS_T) // 2, port=True)
    c.label("VDD_LS", "m2", 1000, (s_b + s_t) // 2, port=True)
    return c, dict(xr=xr, xe=xe, x1=x1, strap=(600, s_b, x1, s_t), top=s_t, gate_area_um2=n * DCLS["w"] * DCLS["l"])


def build_decap_gds(out):
    c0, i0 = decap_cell()
    dx = DC_R - i0["xr"]                     # decap_ls origin in vco_top
    c, info = decap_cell(rail_to=RAIL_END - dx, taps=[x - dx for x in TAP_X])
    gds = out / "decap_ls.gds"
    tcl = "drc off\nsnap internal\n" + c.tcl() + f"load decap_ls\nselect top cell\nexpand\ngds write {gds}\nquit -noprompt\n"
    (out / "decap_ls.tcl").write_text(tcl)
    rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
    for old in out.glob("*.mag"):
        old.unlink()
    r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "decap_ls.tcl"], cwd=out,
                       capture_output=True, text=True)
    (out / "magic_decap.log").write_text(r.stdout + r.stderr)
    assert gds.exists(), "magic did not write decap_ls.gds"
    return gds, info


def assemble(decap_gds, info, dst):
    import klayout.db as db
    ly = db.Layout()
    ly.dbu = 0.001
    opt = db.LoadLayoutOptions()
    for f in (REPO / "layout/ring_core_v3.gds", REPO / "layout/lsdiv.gds", REPO / "layout/cgm_ref.gds", decap_gds):
        ly.read(str(f), opt)
    names = {c.name for c in ly.each_cell()}
    assert {"ring_core", "lsdiv", "cgm_ref", "decap_ls"} <= names, names
    top = ly.create_cell("vco_top")
    DC = (DC_R - info["xr"], 0)
    for name, (x, y) in (("ring_core", CORE), ("cgm_ref", REF), ("lsdiv", LS), ("decap_ls", DC)):
        top.insert(db.CellInstArray(ly.cell(name).cell_index(), db.Trans(db.Vector(x, y))))
    L = {k: ly.layer(*v) for k, v in dict(m1=(34, 0), v1=(35, 0), m2=(36, 0), v2=(38, 0), m3=(42, 0),
                                          m1t=(34, 10), m2t=(36, 10), m3t=(42, 10)).items()}
    shapes = []

    def r(layer, x1, y1, x2, y2):
        x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
        top.shapes(L[layer]).insert(db.Box(x1, y1, x2, y2))
        shapes.append((layer, x1, y1, x2, y2))

    def via2s(xa, xb, ya, yb, pitch=660, xs=None):
        """via2 cuts (0.26, V2.1) on a pitch inside [xa, xb] x [ya, yb] (M2 / M3 already drawn there)."""
        xs = xs if xs is not None else list(range(xa + 300, xb - 299, pitch))
        y = ya + 300
        while y <= yb - 300:
            for x in xs:
                r("v2", x - 130, y - 130, x + 130, y + 130)
            y += pitch

    def lab(text, layer, x, y):
        top.shapes(L[layer + "t"]).insert(db.Text(text, db.Trans(db.Vector(x, y))))

    xl = DC[0]                                 # macro left edge
    xr = REF[0] + 238750                       # macro right edge (cgm_ref's)
    # ---- VSS ----
    r("m2", RAIL_END - 500, VSS_B, -500, VSS_T)  # decap_ls's M2 rail -> the core's M2 VSS rail (starts at -0.92)
    r("m1", 66600, VSS_B, 67600, VSS_T)        # core M1 rail end (66.895) -> cgm_ref M1 rail (67.19)
    r("m2", 65800, VSS_B, 67600, VSS_T)        # core M2 rail end (66.21) -> cgm_ref M2 rail
    vg_gap = (VG_X[0] - 600, VG_X[1] + 600)
    for (a, b) in ((xl, vg_gap[0]), (vg_gap[1], xr)):
        r("m3", a, VSS_B, b, VSS_T)
        via2s(a, b, -1500, -900, pitch=2000)        # one row at y -1.2
    lsx = LS[0] + 300                          # lsdiv's left M3 VSS strap: lsdiv x 0.3 ... 1.3
    r("m3", lsx, VSS_B, lsx + 1000, LS[1] + 500)
    r("m3", lsx, VSS_B, lsx + 4000, LS[1] - 500)
    lab("VSS", "m2", -20000, (VSS_B + VSS_T) // 2)
    lab("VSS", "m3", -30000, (VSS_B + VSS_T) // 2)
    # ---- VDD (ring + reference) ----
    r("m2", VDD_DROP[0], 43300, VDD_DROP[1], YTOP)
    r("m3", VDD_M3[0], VDD_M3[1], xr, YTOP)
    via2s(VDD_DROP[0], VDD_DROP[1], VDD_M3[1], YTOP)
    rail0 = REF[0] + 115240                    # cgm_ref VDD rail M2 x start; its via1s at rail0 + 400 + 2000 k
    xs = list(range(rail0 + 1400, xr - 600, 2000))
    via2s(rail0, xr, 62880, 65280, pitch=600, xs=xs)
    lab("VDD", "m3", (VDD_M3[0] + VDD_DROP[0]) // 2 + 30000, (VDD_M3[1] + YTOP) // 2)
    # ---- VDD_LS (lsdiv + decap) ----
    sx0, sb, sx1, st = info["strap"]
    spine = (DC[0] + sx1 - 1200, DC[0] + sx1)
    r("m2", spine[0], LS_VDD[0], spine[1], YTOP)               # spine: gate strap -> top edge, down to lsdiv's rail
    r("m2", spine[0], LS_VDD[0], LS[0] + 800, LS_VDD[1])       # -> lsdiv VDD rail (M2 from lsdiv x 0.3)
    r("m3", spine[0], YTOP - 2400, spine[1], YTOP)
    via2s(spine[0], spine[1], YTOP - 2400, YTOP)
    lab("VDD_LS", "m3", (spine[0] + spine[1]) // 2, YTOP - 1200)
    # ---- ck: lsdiv's left-edge M2 -> M3 riser to the top edge ----
    cky = (LS[1] + 2750, LS[1] + 3130)
    r("m2", CK_X[0], cky[0], LS[0] + 500, cky[1])
    r("m2", CK_X[0], cky[0] - 0, CK_X[1], cky[0] + 380)
    r("v2", (CK_X[0] + CK_X[1]) // 2 - 130, (cky[0] + cky[1]) // 2 - 130, (CK_X[0] + CK_X[1]) // 2 + 130,
      (cky[0] + cky[1]) // 2 + 130)
    r("m3", CK_X[0], cky[0], CK_X[1], YTOP)
    lab("ck", "m3", (CK_X[0] + CK_X[1]) // 2, YTOP - 200)
    # ---- bits: the core's M3 pins up to the top edge ----
    names = ["bitb0", "bit0", "bitb1", "bit1", "bitb2", "bit2", "bitb3", "bit3", "bitb4", "bit4"]
    for (a, b), nm in zip(CORE_BITS_X, names):
        r("m3", a, CORE_TOP - 400, b, YTOP)
        lab(nm, "m3", (a + b) // 2, YTOP - 200)
    # ---- a0: the abutment (a patch inside the union of the two shapes, no extra area) ----
    r("m2", -2000, 35980, -1800, 36360)
    lab("a0", "m2", -1900, 36170)
    # ---- block pins that are already on the macro edge ----
    lab("vg", "m3", (VG_X[0] + VG_X[1]) // 2, YBOT + 300)
    lab("vctrl", "m2", xr - 100, 12935)
    lab("vbn", "m2", xr - 100, 46205)
    # no Metal4 / Metal5 anywhere
    for li in ly.layer_indexes():
        info_l = ly.get_info(li)
        if info_l.layer in (46, 81, 41, 82) and not db.Region(top.begin_shapes_rec(li)).is_empty():
            raise SystemExit(f"Metal4/5 or via3/4 found on {info_l}")
    ly.write(str(dst))
    bb = top.dbbox()
    pins = {}
    for li in (L["m2t"], L["m3t"]):
        for s in top.shapes(li).each():
            pins.setdefault(s.text_string, []).append((s.text_pos.x / 1000, s.text_pos.y / 1000))
    return dict(bbox=[bb.left, bb.bottom, bb.right, bb.top], cells=sorted(c.name for c in ly.each_cell()),
                place=dict(ring_core=CORE, cgm_ref=REF, lsdiv=LS, decap_ls=DC), pins=pins,
                decap=dict(DCLS, xr=info["xr"], gate_area_um2=info["gate_area_um2"]),
                blocks={n: [v / 1000 for v in (lambda c: [c.bbox().left, c.bbox().bottom, c.bbox().right,
                                                              c.bbox().top])(ly.cell(n))] for n in
                        ("ring_core", "cgm_ref", "lsdiv", "decap_ls")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gds", default=str(REPO / "layout" / "vco_top.gds"))
    ap.add_argument("--out", default=str(REPO / "build" / "top"))
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dgds, info = build_decap_gds(out)
    meta = assemble(dgds, info, Path(a.gds))
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    bb = meta["bbox"]
    print(f"vco_top bbox x {bb[0]:.3f} ... {bb[2]:.3f}, y {bb[1]:.3f} ... {bb[3]:.3f} um: "
          f"{bb[2] - bb[0]:.2f} x {bb[3] - bb[1]:.2f} um = {(bb[2] - bb[0]) * (bb[3] - bb[1]):.0f} um2")
    print(f"decap_ls: {DCLS['nf']} x {DCLS['w']}/{DCLS['l']} um = {info['gate_area_um2']:.0f} um2 gate, "
          f"~{DCLS['c_pf']:.2f} pF; cell width {info['xr'] / 1000:.2f} um")
    print("cells", meta["cells"])
    if not a.no_png:
        png = REPO / "docs" / "img" / "vco_top.png"
        subprocess.run(["klayout", "-zz", "-rd", f"gds={a.gds}", "-rd", f"png={png}", "-rd", "w=2400",
                        "-r", str(HERE / "render_gds.py")], check=False)


if __name__ == "__main__":
    main()
