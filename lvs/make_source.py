#!/usr/bin/env python3
"""LVS source netlist for the Tiny Tapeout wrapper: lvs/tt_um_mattvenn_gf433_vco.spice.

    python3 lvs/make_source.py [--netlist <vco_top.spice>] [--out lvs/tt_um_mattvenn_gf433_vco.spice]

Without --netlist it netlists xschem/vco_top.sch first (xschem/gen/netlist.sh, needs xschem: run it in the image).
The output is self-contained, so CI needs neither xschem nor the PDK's standard-cell netlist:
  - the vco_top hierarchy from xschem, with the LVS edits of layout/gen/check_top.sh:
      lsdiv's "Cc a0 net1 2e-15" removed (drawn as M2/M3 fingers: parasitic C, not a device),
      XRBW r_length snapped to the 5 nm grid (5.023 -> 5.025 um);
  - the standard cells used (gf180mcu_fd_sc_mcu7t5v0__inv_1, __tiel, __antenna), copied from the PDK's spice;
  - the top cell tt_um_mattvenn_gf433_vco with the template's ports (bus pins expanded, ui_in[0] ...), wired as
    layout/gen/tt_wrapper.py draws it:
      ui_in[0..4] -> bit0..4, five inv_1 make bitb0..4, one antenna-diode cell on each; ck -> uo_out[0]; ua[0] -> vctrl; ua[1] -> vbn;
      tx_drv (xschem/tx_drv.sch: tx_split, tx_arm): ls from vco_top, en_p <- ui_in[5], en_n <- ui_in[6] (one antenna
      cell each), out_p -> ua[3], out_n -> ua[2], VDD -> VDPWR;
      VDD and VDD_LS -> VDPWR, VSS -> VGND;
      the fine-tuning blocks (docs/tx_fine_tune.md): the digital macro tx_fine (macro/tx_fine/nl/tx_fine.pnl.v
      through lvs/verilog2spice.py: clk, rst_n, uio_in[0..2] = SCLK / MOSI / CS_n, uio_out[3] = MISO, ui_in[7] = FSK,
      ck from vco_top, uo_out[0..3] = ck_o / div16 / div64 / div1024), the medium DAC mdac (layout/gen/mdac.py
      lvs_source(): vg and vbnf from vco_top, its 37 control lines from the macro) and the vctrl pull-down
      vctrl_pd (ua[0] -> VGND);
      uo_out[4..7], uio_out[0..2, 4..7], uio_oe[0..2, 4..7]: one tiel each; uio_oe[3]: one tieh;
      the other inputs are open (ports with no connection).
The fillers (filltie, fill_*) hold no devices and are not listed.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOP = "tt_um_mattvenn_gf433_vco"
SC = "gf180mcu_fd_sc_mcu7t5v0__"
VCO_PORTS = None    # read from the xschem netlist's .subckt vco_top line (main)
TX_PORTS = "VDD VSS ls en_p en_n out_p out_n".split()


def ports():
    p = ["VGND", "VDPWR"]
    for bus in ("ui_in", "uo_out", "uio_in", "uio_out", "uio_oe", "ua"):
        p += [f"{bus}[{i}]" for i in range(8)]
    return p + ["ena", "clk", "rst_n"]


def lvs_edits(t):
    t, ncc = re.subn(r"^Cc a0 net1 2e-15\n", "", t, flags=re.M)

    def snap(m):
        v = float(m.group(2)) * 1e-6
        return f"{m.group(1)}{round(v * 1e9 / 5) * 5 / 1000:.3f}e-6"
    t, nrbw = re.subn(r"^(XRBW .* r_length=)([\d.]+)(e-6)", snap, t, flags=re.M)
    assert ncc == 1 and nrbw == 1, ("LVS edits did not apply", ncc, nrbw)
    return t


def std_cells(pdk_root, names):
    f = Path(pdk_root) / "gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice"
    t = f.read_text()
    out = []
    for c in names:
        m = re.search(rf"^\.SUBCKT {SC}{c} .*?^\.ENDS", t, flags=re.M | re.S)
        assert m, c
        out.append(m.group(0))
    return "\n\n".join(out)


MAC_MAP = {"clk": "clk", "rst_n": "rst_n", "sclk": "uio_in[0]", "mosi": "uio_in[1]", "cs_n": "uio_in[2]",
           "miso": "uio_out[3]", "fsk": "ui_in[7]", "ck": "ck", "ck_o": "uo_out[0]", "div16": "uo_out[1]",
           "div64": "uo_out[2]", "div1024": "uo_out[3]", "VDD": "VDPWR", "VSS": "VGND"}


def dac_net(pin):
    """mdac control pin -> the macro output net (dac_tn[i] drives segment s(i+1), dac_bn[b] bit b, dac_sdn the SD cell)."""
    if pin == "nsd":
        return "dac_sdn"
    if pin.startswith("nb"):
        return f"dac_bn[{int(pin[2:])}]"
    assert pin.startswith("ns"), pin
    return f"dac_tn[{int(pin[2:]) - 1}]"


def top_cell(vco_ports, mac_ports, dac_ports):
    L = [f".subckt {TOP} " + " ".join(ports())]
    conn = dict(VDD="VDPWR", VDD_LS="VDPWR", VSS="VGND", vctrl="ua[0]", ck="ck", vbn="ua[1]", a0="a0",
                vg="vg", ls="ls", vbnf="vbnf")
    for i in range(5):
        conn[f"bit{i}"] = f"ui_in[{i}]"
        conn[f"bitb{i}"] = f"bitb{i}"
    L.append("xvco " + " ".join(conn[p] for p in vco_ports) + " vco_top")
    for i in range(5):   # inv_1: I ZN VDD VNW VPW VSS
        L.append(f"xinv{i} ui_in[{i}] bitb{i} VDPWR VDPWR VGND VGND {SC}inv_1")
    for i in range(5):   # antenna (two diodes): I VDD VNW VPW VSS
        L.append(f"xant{i} ui_in[{i}] VDPWR VDPWR VGND VGND {SC}antenna")
    # the dipole TX driver: VDD on VDPWR (its own stripe), en_p / en_n from ui_in[5] / [6] (an antenna diode each),
    # out_p -> ua[3], out_n -> ua[2]
    tc = dict(VDD="VDPWR", VSS="VGND", ls="ls", en_p="ui_in[5]", en_n="ui_in[6]", out_p="ua[3]", out_n="ua[2]")
    L.append("xtx " + " ".join(tc[p] for p in TX_PORTS) + " tx_drv")
    for i in (5, 6):
        L.append(f"xant{i} ui_in[{i}] VDPWR VDPWR VGND VGND {SC}antenna")
    # fine tuning: the digital macro, the medium DAC, the vctrl pull-down
    L.append("xmac " + " ".join(MAC_MAP.get(p, p) for p in mac_ports) + " tx_fine")
    dc = dict(VDD="VDPWR", VSS="VGND", vg="vg", vbnf="vbnf")
    L.append("xmdac " + " ".join(dc.get(p) or dac_net(p) for p in dac_ports) + " mdac")
    L.append("xvpd ua[0] VGND vctrl_pd")
    driven = set(MAC_MAP.values())
    tied = [f"uo_out[{i}]" for i in range(1, 8)] + [f"uio_out[{i}]" for i in range(8)] + \
           [f"uio_oe[{i}]" for i in range(8)]
    for n in tied:       # tiel: ZN VDD VNW VPW VSS; tieh: Z VDD VNW VPW VSS
        if n in driven:
            continue
        tag = re.sub(r"\W", "", n.replace("[", "_"))
        cell = "tieh" if n == "uio_oe[3]" else "tiel"
        L.append(f"xtie_{tag} {n} VDPWR VDPWR VGND VGND {SC}{cell}")
    L.append(".ends")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", default=None, help="xschem vco_top netlist (default: netlist it now)")
    ap.add_argument("--tx-netlist", default=None, help="xschem tx_drv netlist (default: next to the vco_top one)")
    ap.add_argument("--out", default=str(REPO / "lvs" / f"{TOP}.spice"))
    a = ap.parse_args()
    if a.netlist:
        nl = Path(a.netlist)
    else:
        d = REPO / "build" / "tt" / "xsch"
        d.mkdir(parents=True, exist_ok=True)
        # xschem needs the image's PDK for its symbols (XSCHEM_PDK_ROOT, default /foss/pdks), whatever PDK_ROOT is
        env = dict(os.environ, PDK_ROOT=os.environ.get("XSCHEM_PDK_ROOT", "/foss/pdks"))
        subprocess.run(["bash", "xschem/gen/netlist.sh", "xschem", str(d), "vco_top", "tx_drv"], cwd=REPO, check=True,
                       env=env)
        nl = d / "vco_top.spice"
    t = nl.read_text()
    tx = re.sub(r"^\.end\s*$", "", (Path(a.tx_netlist) if a.tx_netlist else nl.parent / "tx_drv.spice").read_text(),
                flags=re.M)
    tx = re.sub(r"^\*\* (sch|sym)_path:.*\n", "", tx, flags=re.M)
    t = re.sub(r"^\*\* (sch|sym)_path:.*\n", "", t, flags=re.M)    # no local paths in the committed netlist
    t = re.sub(r"^\.end\s*$", "", t, flags=re.M)
    t = lvs_edits(t)
    pdk = os.environ.get("PDK_ROOT", "/foss/pdks")
    vco_ports = re.search(r"^\.subckt vco_top (.*)$", t, re.M).group(1).split()
    # the digital macro: its powered netlist as SPICE (the standard cells it uses come with it)
    sys.path.insert(0, str(REPO / "lvs"))
    import verilog2spice as v2s
    lib = Path(pdk) / "gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice"
    mac_ports, insts, assigns = v2s.parse(REPO / "macro/tx_fine/nl/tx_fine.pnl.v", "tx_fine")
    cells = v2s.lib_cells(lib)
    par = {}
    for x, y in assigns:
        par[y if x in mac_ports else x] = x if x in mac_ports else y
    fnd = lambda n: fnd(par[n]) if n in par and par[n] != n else n
    mac = [".subckt tx_fine " + " ".join(mac_ports)]
    used = []
    for cell, name, pins in insts:
        pins = dict(pins)
        pins.setdefault("VNW", pins.get("VDD")); pins.setdefault("VPW", pins.get("VSS"))   # endcap / filltie list only VDD VSS
        nm = re.sub(r'[^\w]', '_', name)
        mac.append(f"X{nm} " + " ".join(fnd(pins[p]) if p in pins else f"nc_{nm}_{p}" for p in cells[cell][0])
                   + f" {cell}")                                    # an unconnected output: its own dangling net
        used.append(cell)
    mac.append(".ends tx_fine")
    # the medium DAC and the vctrl pull-down: from their layout generators' source netlists (no tools needed)
    sys.path.insert(0, str(REPO / "layout/gen"))
    import mdac as mdac_lay
    dsp = REPO / "build" / "tt" / "mdac_src.spice"
    dsp.parent.mkdir(parents=True, exist_ok=True)
    dac_ports = mdac_lay.lvs_source(dsp)
    import vctrl_pd as vpd_lay
    vpd = (".subckt vctrl_pd a b\n"
           f"XRV a b b ppolyf_u_1k r_width=1e-6 r_length={vpd_lay.rtot() / 1000:.3f}e-6\n.ends vctrl_pd")
    sc_used = ["inv_1", "tiel", "tieh", "antenna"] + [c[len(SC):] for c in dict.fromkeys(used) if c.startswith(SC)]
    sc_used = list(dict.fromkeys(sc_used))
    hdr = (f"* LVS source for {TOP} (Tiny Tapeout gf180mcuD analog 2x2), generated by lvs/make_source.py\n"
           "* from xschem/vco_top.sch (edits: lsdiv Cc removed, XRBW L snapped 5.023 -> 5.025 um), xschem/tx_drv.sch\n"
           "* and the PDK's\n"
           "* gf180mcu_fd_sc_mcu7t5v0 spice (the cells used); macro/tx_fine/nl/tx_fine.pnl.v (lvs/verilog2spice.py);\n"
           "* layout/gen/mdac.py lvs_source(); layout/gen/vctrl_pd.py. Do not edit by hand.\n")
    body = (hdr + "\n" + top_cell(vco_ports, mac_ports, dac_ports) + "\n\n" + t.strip() + "\n\n" + tx.strip() + "\n\n"
            + "\n".join(mac) + "\n\n" + dsp.read_text() + "\n" + vpd + "\n\n" + std_cells(pdk, sc_used) + "\n\n.end\n")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(body)
    print(f"wrote {a.out}: {sum(1 for l in body.splitlines() if l[:1] in 'XxMmCcRr')} element lines")


if __name__ == "__main__":
    main()
