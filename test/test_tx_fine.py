"""cocotb tests of src/tx_fine.v: SPI write / readback, reset values, the FSK offset and saturation, the
thermometer decode, the divider ratios and the ck gate, and the SD bitstream against sim/tune/sd_model.py (bit for
bit). Run: cd test && make  (GL=1 for the hardened netlist)."""
import sys
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Timer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim/tune"))
import sd_model  # noqa: E402

CLK_NS = 40      # 25 MHz project clock
CK_NS = 9.2      # ~108 MHz VCO / 4
SCK_NS = 400     # SPI clock period (clk / 10)


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.ck, CK_NS, unit="ns").start())
    dut.sclk.value = 0; dut.mosi.value = 0; dut.cs_n.value = 1; dut.fsk.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def xfer(dut, word):
    """One 16-bit frame; returns the 16 MISO bits sampled on the rising edges."""
    dut.cs_n.value = 0
    await Timer(SCK_NS, unit="ns")
    got = 0
    for i in range(15, -1, -1):
        dut.mosi.value = (word >> i) & 1
        await Timer(SCK_NS / 2, unit="ns")
        dut.sclk.value = 1
        got = (got << 1) | int(dut.miso.value)
        await Timer(SCK_NS / 2, unit="ns")
        dut.sclk.value = 0
    await Timer(SCK_NS, unit="ns")
    dut.cs_n.value = 1
    await Timer(SCK_NS, unit="ns")
    return got


async def wr(dut, addr, data):
    await xfer(dut, (addr << 12) | (data & 0xfff))


async def rd(dut, addr):
    return (await xfer(dut, 0x8000 | (addr << 12))) & 0xfff


def dac_word(dut):
    t = ~int(dut.dac_tn.value) & 0x7fffffff; b = ~int(dut.dac_bn.value) & 0x1f
    hi = bin(t).count("1")
    assert t == (1 << hi) - 1, f"thermometer not contiguous: {t:031b}"
    return (hi << 5) | b


@cocotb.test()
async def reset_values(dut):
    await start(dut)
    assert await rd(dut, 7) == 0x433
    assert await rd(dut, 0) == 512
    assert await rd(dut, 1) == 0
    assert await rd(dut, 2) == 0
    assert await rd(dut, 3) == 0
    assert dac_word(dut) == 512 and (1 - int(dut.dac_sdn.value)) == 0
    for _ in range(50):          # ck gated off, SD off
        await RisingEdge(dut.ck)
        assert int(dut.ck_o.value) == 0
        assert (1 - int(dut.dac_sdn.value)) == 0


@cocotb.test()
async def write_readback(dut):
    await start(dut)
    for a, v in ((0, 0x2a5), (1, 0x5c), (2, 0x9f3), (3, 0x5)):
        await wr(dut, a, v)
    assert await rd(dut, 0) == 0x2a5
    assert await rd(dut, 1) == 0x5c
    assert await rd(dut, 2) == 0x9f3
    assert await rd(dut, 3) == 0x5
    await wr(dut, 0, 0x3ff); await wr(dut, 3, 0)
    assert await rd(dut, 0) == 0x3ff
    await ClockCycles(dut.clk, 6)
    assert dac_word(dut) == 1023
    for w in (0, 1, 31, 32, 33, 511, 992, 1000):
        await wr(dut, 0, w)
        await ClockCycles(dut.clk, 6)
        assert dac_word(dut) == w, (w, dac_word(dut))


@cocotb.test()
async def sd_matches_model(dut):
    """The SD bitstream equals sd_model.sd1 bit for bit, and its mean equals the fraction."""
    await start(dut)
    for frac in (1, 77, 128, 200, 255):
        await wr(dut, 3, 0)          # SD off: acc cleared
        await wr(dut, 1, frac)
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        dut._log.info(f"frac {frac}")
        cocotb.start_soon(wr(dut, 3, 1))       # SD_EN; collect from the first clk after it takes effect
        while True:
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            if int(dut.ctrl.value) & 1:
                break
        n = 512
        got = []
        for _ in range(n):
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            got.append(1 - int(dut.dac_sdn.value))
        ref = list(sd_model.sd1(frac, 8, n))
        assert got == ref, f"frac {frac}: first mismatch at {next(i for i in range(n) if got[i] != ref[i])}"
        assert sum(got) == frac * n // 256


@cocotb.test()
async def fsk_offset(dut):
    await start(dut)
    await wr(dut, 0, 500); await wr(dut, 1, 0x40); await wr(dut, 2, 0x2c0)   # dev 2.75 LSB
    await wr(dut, 3, 0b100)                                                     # FSK_EN
    for f, exp in ((1, (500 << 8) + 0x40 + 0x2c0), (0, (500 << 8) + 0x40 - 0x2c0)):
        dut.fsk.value = f
        await ClockCycles(dut.clk, 8)
        assert dac_word(dut) == exp >> 8
        assert await rd(dut, 4) == exp >> 8
    await wr(dut, 3, 0b1100)                                                    # FSK_INV
    dut.fsk.value = 0
    await ClockCycles(dut.clk, 8)
    assert dac_word(dut) == ((500 << 8) + 0x40 + 0x2c0) >> 8
    # saturation at both ends
    await wr(dut, 3, 0b100); await wr(dut, 0, 1022); await wr(dut, 2, 0xfff); dut.fsk.value = 1
    await ClockCycles(dut.clk, 8)
    assert dac_word(dut) == 1023
    await wr(dut, 0, 3); dut.fsk.value = 0
    await ClockCycles(dut.clk, 8)
    assert dac_word(dut) == 0


@cocotb.test()
async def divider_and_ck_gate(dut):
    await start(dut)
    from cocotb.utils import get_sim_time
    for sig, n in ((dut.div16, 16), (dut.div64, 64), (dut.div1024, 1024)):
        await RisingEdge(sig)
        t0 = get_sim_time("ps")
        await RisingEdge(sig)
        per = (get_sim_time("ps") - t0) / (CK_NS * 1000)
        assert abs(per - n) < 0.01, f"div{n}: {per} ck periods"
    await wr(dut, 3, 0b10)                                                      # CK_EN
    await ClockCycles(dut.ck, 10)
    hi = 0
    for _ in range(40):
        await Timer(CK_NS / 4, unit="ns")
        hi += int(dut.ck_o.value) == int(dut.ck.value)
    assert hi == 40
    await wr(dut, 3, 0)
    await ClockCycles(dut.ck, 10)
    for _ in range(40):
        await Timer(CK_NS / 4, unit="ns")
        assert int(dut.ck_o.value) == 0
