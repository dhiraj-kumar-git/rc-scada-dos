// Count-min sketch (D rows x 1024 cells) and distinct-source counter, per
// 100 ms window. Golden model: run_sketch() in python/common.py.
//
// Takes the same record stream as the Detector, one record per clock, and
// never stalls it (no ready signal). For each window that holds at least one
// record it emits (win, top_src, top_est, set_bits) a few clocks after the
// window's last record.
//
// Per record with src != 0: every row r increments cell[r][h_r], where
// h_r = top 10 bits of (src * K[r]) mod 2^32; est = min of the incremented
// values; if est > top_est then top_est = est, top_src = src. The distinct
// table sets bit b = top 10 bits of ((src * K[0]) mod 2^32 ^ 0x9E3779B9) and
// counts newly set bits.
//
// Cells are logically zero at the start of every window: each cell stores a
// 16-bit tag (window index + 1) next to its 16-bit count, so a cell whose tag
// is not the current window's reads as 0. Window indices are below 2^15 for
// 24-bit timestamps, so tags never wrap within a run. After each run the
// tables are cleared in the background (busy = 1 for 1024 clocks), so the
// next run starts from zero.
//
// Pipeline: S1 input, S2 multiply, S3 multiply register + read address,
// S4 read data + update + write (one-deep forwarding covers a write in the
// same clock as the read), S5 and S5b min over rows (balanced tree, two
// clocks), S6 top / set_bits / emit.
module sketch #(
    parameter integer D = 4
) (
    input  wire        clk,
    input  wire        clr,          // start of a run: resets the window state
    input  wire        in_fire,      // a record is accepted by the Detector this clock
    input  wire [63:0] in_rec,
    input  wire [23:0] in_win,       // window index of that record
    input  wire        flush,        // rising edge: end of the run
    output reg         out_valid,
    output reg  [23:0] out_win,
    output reg  [31:0] out_top_src,
    output reg  [15:0] out_top_est,
    output reg  [10:0] out_set_bits,
    output wire        busy
);
    localparam [31:0] DXOR = 32'h9E3779B9;

    function [31:0] kmul;
        input integer r;
        case (r)
            0: kmul = 32'd2654435761;
            1: kmul = 32'd2246822519;
            2: kmul = 32'd3266489917;
            3: kmul = 32'd668265263;
            4: kmul = 32'd374761393;
            5: kmul = 32'd2869860233;
            6: kmul = 32'd1597334677;
            default: kmul = 32'd3812015801;
        endcase
    endfunction

    // ------------------------------------------------ S1: input register
    reg        flush_d = 1'b0;
    reg        s1_v = 0, s1_upd = 0, s1_fl = 0;
    reg [31:0] s1_src = 0;
    reg [23:0] s1_win = 0;
    always @(posedge clk) begin
        flush_d <= flush;
        s1_v    <= in_fire && !clr;
        s1_upd  <= in_fire && !clr && (in_rec[31:0] != 32'd0);
        s1_fl   <= flush && !flush_d;
        s1_src  <= in_rec[31:0];
        s1_win  <= in_win;
    end

    // ------------------------------------------------ S2, S3: multiply (2 registers)
    reg        s2_v = 0, s2_upd = 0, s2_fl = 0, s3_v = 0, s3_upd = 0, s3_fl = 0;
    reg [31:0] s2_src = 0, s3_src = 0;
    reg [23:0] s2_win = 0, s3_win = 0;
    reg [32*D-1:0] s2_prod = 0, s3_prod = 0;
    integer r;
    always @(posedge clk) begin
        s2_v <= s1_v; s2_upd <= s1_upd; s2_fl <= s1_fl; s2_src <= s1_src; s2_win <= s1_win;
        for (r = 0; r < D; r = r + 1)
            s2_prod[32*r +: 32] <= s1_src * kmul(r);
        s3_v <= s2_v; s3_upd <= s2_upd; s3_fl <= s2_fl; s3_src <= s2_src; s3_win <= s2_win;
        s3_prod <= s2_prod;
    end

    // read addresses (from S3 registers)
    wire [10*D-1:0] ra;
    genvar g;
    generate
        for (g = 0; g < D; g = g + 1) begin : addr
            assign ra[10*g +: 10] = s3_prod[32*g + 22 +: 10];
        end
    endgenerate
    wire [31:0] dx = s3_prod[31:0] ^ DXOR;
    wire [9:0]  dra = dx[31:22];

    // ------------------------------------------------ S4: read data, update, write
    reg        s4_v = 0, s4_upd = 0, s4_fl = 0;
    reg [31:0] s4_src = 0;
    reg [23:0] s4_win = 0;
    reg [10*D-1:0] s4_addr = 0;
    reg [9:0]  s4_daddr = 0;
    always @(posedge clk) begin
        s4_v <= s3_v; s4_upd <= s3_upd; s4_fl <= s3_fl; s4_src <= s3_src; s4_win <= s3_win;
        s4_addr <= ra; s4_daddr <= dra;
    end
    wire [15:0] s4_tag = s4_win[15:0] + 16'd1;

    // background clear after a run
    reg        clearing = 1'b0;
    reg [9:0]  clr_addr = 10'd0;
    assign busy = clearing;

    // last clock's writes, for forwarding
    reg            w_v = 1'b0;
    reg [10*D-1:0] w_addr = 0;
    reg [32*D-1:0] w_val = 0;
    reg [9:0]      w_daddr = 0;
    reg [15:0]     w_dtag = 0;

    wire [32*D-1:0] rd;          // block RAM read data, one word per row
    wire [32*D-1:0] new_val;     // {tag, count} written back
    wire [16*D-1:0] new_cnt;
    wire [15:0]     drd;         // distinct table read data (tag)

    generate
        for (g = 0; g < D; g = g + 1) begin : row
            reg [31:0] mem [0:1023];
            reg [31:0] q = 32'd0;
            integer i;
            initial for (i = 0; i < 1024; i = i + 1) mem[i] = 32'd0;
            wire [9:0]  a   = s4_addr[10*g +: 10];
            wire [31:0] cur = (w_v && (w_addr[10*g +: 10] == a)) ? w_val[32*g +: 32] : q;
            wire        hit = (cur[31:16] == s4_tag);
            wire [15:0] c   = hit ? ((cur[15:0] == 16'hFFFF) ? 16'hFFFF : cur[15:0] + 16'd1) : 16'd1;
            assign new_cnt[16*g +: 16] = c;
            assign new_val[32*g +: 32] = {s4_tag, c};
            assign rd[32*g +: 32] = q;
            always @(posedge clk) begin
                if (clearing)
                    mem[clr_addr] <= 32'd0;
                else if (s4_v && s4_upd)
                    mem[a] <= {s4_tag, c};
                q <= mem[ra[10*g +: 10]];
            end
        end
    endgenerate

    reg [15:0] dmem [0:1023];
    reg [15:0] dq = 16'd0;
    integer j;
    initial for (j = 0; j < 1024; j = j + 1) dmem[j] = 16'd0;
    wire [15:0] dcur  = (w_v && (w_daddr == s4_daddr)) ? w_dtag : dq;
    wire        d_new = (dcur != s4_tag);
    always @(posedge clk) begin
        if (clearing)
            dmem[clr_addr] <= 16'd0;
        else if (s4_v && s4_upd)
            dmem[s4_daddr] <= s4_tag;
        dq <= dmem[dra];
    end
    assign drd = dq;

    always @(posedge clk) begin
        w_v     <= s4_v && s4_upd;
        w_addr  <= s4_addr;
        w_val   <= new_val;
        w_daddr <= s4_daddr;
        w_dtag  <= s4_tag;
    end

    // ------------------------------------------------ S5: min over rows
    reg        s5_v = 0, s5_upd = 0, s5_fl = 0, s5_new = 0;
    reg [31:0] s5_src = 0;
    reg [23:0] s5_win = 0;
    reg [16*D-1:0] s5_cnt = 0;
    always @(posedge clk) begin
        s5_v <= s4_v; s5_upd <= s4_upd; s5_fl <= s4_fl; s5_src <= s4_src; s5_win <= s4_win;
        s5_cnt <= new_cnt;
        s5_new <= s4_upd && d_new;
    end
    // min over rows as a balanced tree in two clocks: S5 -> S5b (two group minima) -> S6
    function [15:0] min2;
        input [15:0] a, b;
        min2 = (a < b) ? a : b;
    endfunction
    wire [16*8-1:0] cpad;
    generate
        if (D < 8) begin : pad
            assign cpad = {{(16*(8-D)){1'b1}}, s5_cnt};
        end else begin : nopad
            assign cpad = s5_cnt;
        end
    endgenerate
    wire [15:0] grp0 = min2(min2(cpad[0 +: 16], cpad[16 +: 16]), min2(cpad[32 +: 16], cpad[48 +: 16]));
    wire [15:0] grp1 = min2(min2(cpad[64 +: 16], cpad[80 +: 16]), min2(cpad[96 +: 16], cpad[112 +: 16]));

    reg        s5b_v = 0, s5b_upd = 0, s5b_fl = 0, s5b_new = 0;
    reg [31:0] s5b_src = 0;
    reg [23:0] s5b_win = 0;
    reg [15:0] s5b_g0 = 0, s5b_g1 = 0;
    always @(posedge clk) begin
        s5b_v <= s5_v; s5b_upd <= s5_upd; s5b_fl <= s5_fl; s5b_new <= s5_new;
        s5b_src <= s5_src; s5b_win <= s5_win; s5b_g0 <= grp0; s5b_g1 <= grp1;
    end

    reg        s6_v = 0, s6_upd = 0, s6_fl = 0, s6_new = 0;
    reg [31:0] s6_src = 0;
    reg [23:0] s6_win = 0;
    reg [15:0] s6_est = 0;
    always @(posedge clk) begin
        s6_v <= s5b_v; s6_upd <= s5b_upd; s6_fl <= s5b_fl; s6_new <= s5b_new;
        s6_src <= s5b_src; s6_win <= s5b_win; s6_est <= min2(s5b_g0, s5b_g1);
    end

    // ------------------------------------------------ S6: per-window top source and distinct count
    reg        have = 1'b0;
    reg [23:0] cur_win = 0;
    reg [31:0] top_src = 0;
    reg [15:0] top_est = 0;
    reg [10:0] set_bits = 0;

    initial begin
        out_valid = 0; out_win = 0; out_top_src = 0; out_top_est = 0; out_set_bits = 0;
    end

    always @(posedge clk) begin
        out_valid <= 1'b0;
        if (clr) begin
            have <= 1'b0; top_src <= 0; top_est <= 0; set_bits <= 0;
        end else if (s6_v) begin
            if (!have || (s6_win != cur_win)) begin
                if (have) begin
                    out_valid <= 1'b1; out_win <= cur_win; out_top_src <= top_src;
                    out_top_est <= top_est; out_set_bits <= set_bits;
                end
                have     <= 1'b1;
                cur_win  <= s6_win;
                top_est  <= s6_upd ? s6_est : 16'd0;
                top_src  <= s6_upd ? s6_src : 32'd0;
                set_bits <= s6_new ? 11'd1 : 11'd0;
            end else begin
                if (s6_upd && (s6_est > top_est)) begin
                    top_est <= s6_est;
                    top_src <= s6_src;
                end
                if (s6_new) set_bits <= set_bits + 11'd1;
            end
        end else if (s6_fl) begin
            if (have) begin
                out_valid <= 1'b1; out_win <= cur_win; out_top_src <= top_src;
                out_top_est <= top_est; out_set_bits <= set_bits;
            end
            have <= 1'b0;
        end
    end

    // background clear: starts when the end-of-run token leaves S6
    always @(posedge clk) begin
        if (s6_fl && !clearing) begin
            clearing <= 1'b1;
            clr_addr <= 10'd0;
        end else if (clearing) begin
            clr_addr <= clr_addr + 10'd1;
            if (clr_addr == 10'd1023) clearing <= 1'b0;
        end
    end
endmodule
