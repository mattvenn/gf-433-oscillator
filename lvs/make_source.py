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
      VDD and VDD_LS -> VDPWR, VSS -> VGND; uo_out[1..7], uio_out[0..7], uio_oe[0..7]: one tiel each;
      the other inputs are open (ports with no connection).
The fillers (filltie, fill_*) hold no devices and are not listed.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOP = "tt_um_mattvenn_gf433_vco"
SC = "gf180mcu_fd_sc_mcu7t5v0__"
VCO_PORTS = "VDD VDD_LS VSS vctrl bit0 bit1 bit2 bit3 bit4 bitb0 bitb1 bitb2 bitb3 bitb4 ck a0 vbn vg ls".split()
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


def std_cells(pdk_root):
    f = Path(pdk_root) / "gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice"
    t = f.read_text()
    out = []
    for c in ("inv_1", "tiel", "antenna"):
        m = re.search(rf"^\.SUBCKT {SC}{c} .*?^\.ENDS", t, flags=re.M | re.S)
        assert m, c
        out.append(m.group(0))
    return "\n\n".join(out)


def top_cell():
    L = [f".subckt {TOP} " + " ".join(ports())]
    conn = dict(VDD="VDPWR", VDD_LS="VDPWR", VSS="VGND", vctrl="ua[0]", ck="uo_out[0]", vbn="ua[1]", a0="a0",
                vg="vg", ls="ls")
    for i in range(5):
        conn[f"bit{i}"] = f"ui_in[{i}]"
        conn[f"bitb{i}"] = f"bitb{i}"
    L.append("xvco " + " ".join(conn[p] for p in VCO_PORTS) + " vco_top")
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
    tied = [f"uo_out[{i}]" for i in range(1, 8)] + [f"uio_out[{i}]" for i in range(8)] + \
           [f"uio_oe[{i}]" for i in range(8)]
    for n in tied:       # tiel: ZN VDD VNW VPW VSS
        tag = re.sub(r"\W", "", n.replace("[", "_"))
        L.append(f"xtie_{tag} {n} VDPWR VDPWR VGND VGND {SC}tiel")
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
    hdr = (f"* LVS source for {TOP} (Tiny Tapeout gf180mcuD analog 2x2), generated by lvs/make_source.py\n"
           "* from xschem/vco_top.sch (edits: lsdiv Cc removed, XRBW L snapped 5.023 -> 5.025 um), xschem/tx_drv.sch\n"
           "* and the PDK's\n"
           "* gf180mcu_fd_sc_mcu7t5v0 spice (inv_1, tiel, antenna). Do not edit by hand.\n")
    body = hdr + "\n" + top_cell() + "\n\n" + t.strip() + "\n\n" + tx.strip() + "\n\n" + std_cells(pdk) + "\n\n.end\n"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(body)
    print(f"wrote {a.out}: {sum(1 for l in body.splitlines() if l[:1] in 'XxMmCcRr')} element lines")


if __name__ == "__main__":
    main()
