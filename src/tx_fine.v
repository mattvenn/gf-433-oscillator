/*
 * Copyright (c) 2026 Matt Venn
 * SPDX-License-Identifier: Apache-2.0
 *
 * tx_fine: the digital macro for on-chip fine tuning and FSK (docs/tx_fine_tune.md).
 *
 *   clk domain (the TT project clock, 10-50 MHz): SPI register, FSK offset, first-order sigma-delta (SD),
 *     the medium DAC's control lines (31 thermometer segments, 5 binary bits, one SD cell), registered.
 *   ck domain (the VCO's f/4, about 108 MHz): ripple divider /16, /64, /1024, and ck itself gated by CTRL.CK_EN.
 *
 * SPI: mode 0 (SCLK idles low, MOSI sampled on the rising edge, MISO changes on the falling edge), MSB first,
 * 16-bit frames while CS_n is low: [15] 1 = read / 0 = write, [14:12] address, [11:0] data. A write takes effect
 * at the 16th rising edge. In a read, MISO carries the register's 12 bits on rising edges 5..16. SCLK, MOSI and
 * CS_n are synchronised to clk (two flops), so SCLK must stay below clk / 8.
 *
 * Registers (reset value):
 *   0 MED_INT  [9:0]  medium DAC integer word (512)
 *   1 MED_FRAC [7:0]  fractional word, through the SD (0)
 *   2 FSK_DEV  [11:0] FSK deviation, 4.8 fixed point in DAC LSBs (0)
 *   3 CTRL     [0] SD_EN (0)  [1] CK_EN: ck on uo[0] (0)  [2] FSK_EN (0)  [3] FSK_INV (0)
 *   4 EFF_INT  [9:0]  read only: the integer word the DAC sees now (after FSK and saturation)
 *   7 ID       [11:0] read only: 12'h433
 * Effective word = {MED_INT, MED_FRAC} + DEV when FSK_EN and the synchronised fsk input (ui[7]) is 1 (0 with
 * FSK_INV), - DEV when it is 0, saturated to 0 ... 1023 + 255/256. The integer part drives the array; the
 * fraction drives the SD: {carry, acc} <= acc + frac each clk, sd = carry (sim/tune/sd_model.py sd1).
 * Pipeline: the effective word is registered (eff_q), then decoded into the array lines, so the FSK adder and the
 * thermometer decode are in separate clk cycles. The array lines are active low: the medium DAC's steering switch
 * conducts with its gate at 0 V (sim/tune/mdac.py).
 */

`default_nettype none

module tx_fine (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        sclk,
    input  wire        mosi,
    input  wire        cs_n,
    output reg         miso,
    input  wire        fsk,
    input  wire        ck,
    output wire        ck_o,
    output wire        div16,
    output wire        div64,
    output wire        div1024,
    output reg  [30:0] dac_tn,     // thermometer, active low: segment i+1 on (0) when word[9:5] > i
    output reg  [4:0]  dac_bn,     // binary word[4:0], active low
    output reg         dac_sdn     // the SD cell (1 LSB), active low
);
    // ---------------- clk domain ----------------
    reg [2:0] s_sclk, s_cs;
    reg [1:0] s_mosi, s_fsk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s_sclk <= 3'b000; s_cs <= 3'b111; s_mosi <= 2'b00; s_fsk <= 2'b00;
        end else begin
            s_sclk <= {s_sclk[1:0], sclk};
            s_cs   <= {s_cs[1:0], cs_n};
            s_mosi <= {s_mosi[0], mosi};
            s_fsk  <= {s_fsk[0], fsk};
        end
    wire sck_rise = s_sclk[1] & ~s_sclk[2];
    wire sck_fall = ~s_sclk[1] & s_sclk[2];
    wire sel = ~s_cs[1];

    reg [9:0]  med_int;
    reg [7:0]  med_frac;
    reg [11:0] fsk_dev;
    reg [3:0]  ctrl;
    reg [9:0]  eff_int;
    wire sd_en = ctrl[0], ck_en = ctrl[1], fsk_en = ctrl[2], fsk_inv = ctrl[3];

    reg [4:0]  bitcnt;
    reg [15:0] sr;
    reg [11:0] rd;
    reg        rnw;
    reg [2:0]  addr;

    function [11:0] rdmux(input [2:0] a);
        case (a)
            3'd0: rdmux = {2'b00, med_int};
            3'd1: rdmux = {4'h0, med_frac};
            3'd2: rdmux = fsk_dev;
            3'd3: rdmux = {8'h00, ctrl};
            3'd4: rdmux = {2'b00, eff_int};
            3'd7: rdmux = 12'h433;
            default: rdmux = 12'h000;
        endcase
    endfunction

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            bitcnt <= 0; sr <= 0; rd <= 0; rnw <= 0; addr <= 0; miso <= 0;
            med_int <= 10'd512; med_frac <= 8'd0; fsk_dev <= 12'd0; ctrl <= 4'd0;
        end else if (!sel) begin
            bitcnt <= 0; miso <= 0;
        end else begin
            if (sck_rise) begin
                sr <= {sr[14:0], s_mosi[1]};
                bitcnt <= bitcnt + 1'b1;
                if (bitcnt == 5'd3) begin           // 4th bit: R/W and the address are in
                    rnw  <= sr[2];
                    addr <= {sr[1:0], s_mosi[1]};
                    rd   <= rdmux({sr[1:0], s_mosi[1]});
                end
                if (bitcnt == 5'd15 && !sr[14]) begin   // 16th bit of a write frame
                    case (sr[13:11])
                        3'd0: med_int  <= {sr[8:0], s_mosi[1]};
                        3'd1: med_frac <= {sr[6:0], s_mosi[1]};
                        3'd2: fsk_dev  <= {sr[10:0], s_mosi[1]};
                        3'd3: ctrl     <= {sr[2:0], s_mosi[1]};
                        default: ;
                    endcase
                end
            end
            if (sck_fall && bitcnt >= 5'd4 && bitcnt <= 5'd15 && rnw) begin
                miso <= rd[11];
                rd   <= {rd[10:0], 1'b0};
            end
        end

    // effective word (10.8), FSK and saturation
    wire [17:0] base = {med_int, med_frac};
    wire [18:0] devx = {7'd0, fsk_dev};
    wire        up   = s_fsk[1] ^ fsk_inv;
    wire [18:0] sum  = up ? ({1'b0, base} + devx) : ({1'b0, base} - devx);
    wire [17:0] eff  = !fsk_en ? base : (up ? (sum[18] ? 18'h3ffff : sum[17:0])
                                            : (sum[18] ? 18'h00000 : sum[17:0]));

    reg  [17:0] eff_q;
    reg  [7:0] acc;
    wire [8:0] acc_n = {1'b0, acc} + {1'b0, eff_q[7:0]};
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            eff_q <= {10'd512, 8'd0};
            acc <= 0; dac_sdn <= 1'b1; dac_tn <= 31'h7fff_0000; dac_bn <= 5'h1f; eff_int <= 10'd512;
        end else begin
            eff_q <= eff;
            if (sd_en) begin
                acc <= acc_n[7:0];
                dac_sdn <= ~acc_n[8];
            end else begin
                acc <= 0;
                dac_sdn <= 1'b1;
            end
            eff_int <= eff_q[17:8];
            for (i = 0; i < 31; i = i + 1)
                dac_tn[i] <= ~(eff_q[17:13] > i);
            dac_bn <= ~eff_q[12:8];
        end

    // ---------------- ck domain ----------------
    reg [1:0] r_ck;      // reset synchroniser
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r_ck <= 2'b00; else r_ck <= {r_ck[0], 1'b1};
    wire rst_ck_n = r_ck[1];

    // ripple counter: stage 0 toggles on ck, stage i on the falling edge of stage i-1, so only stage 0 runs at
    // the ck rate (about 108 MHz); the outputs are frequency outputs, so the ripple skew doesn't matter
    wire [10:0] tck;
    assign tck[0] = ck;
    genvar gi;
    generate
        for (gi = 0; gi < 10; gi = gi + 1) begin : rip
            reg q;
            if (gi == 0) begin : s0
                always @(posedge ck or negedge rst_ck_n)
                    if (!rst_ck_n) q <= 1'b0; else q <= ~q;
            end else begin : sn
                always @(negedge tck[gi] or negedge rst_ck_n)
                    if (!rst_ck_n) q <= 1'b0; else q <= ~q;
            end
            assign tck[gi + 1] = q;
        end
    endgenerate
    assign div16   = tck[4];
    assign div64   = tck[6];
    assign div1024 = tck[10];

    reg [1:0] s_cken;    // CK_EN into the ck domain
    always @(posedge ck or negedge rst_ck_n)
        if (!rst_ck_n) s_cken <= 2'b00; else s_cken <= {s_cken[0], ck_en};
    reg g_en;            // changes only while ck is low: a glitch-free AND gate
    always @(negedge ck or negedge rst_ck_n)
        if (!rst_ck_n) g_en <= 1'b0; else g_en <= s_cken[1];
    assign ck_o = ck & g_en;
endmodule
