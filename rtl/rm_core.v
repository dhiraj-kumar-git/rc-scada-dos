// Shared body of the DFX modules (rm_detector, rm_net_diag, rm_modbus_diag).
// Golden model: rm_words() in python/common.py.
//
// Common interface: clk, clr, in_valid, in_ready, in_rec[63:0], flush,
// out_valid, out_word[63:0]. The Detector emits a decision word for every
// window; with SKETCH_D > 0 the sketch adds a diagnosis word for every window
// that holds records (top source, set_bits, DDoS flag). Decision words have
// priority on out_word; diagnosis words wait in a 16-entry FIFO (they are rare:
// at most one per window, and at least one record clock apart).
// While the sketch clears its tables after a run, in_ready stays low.
module rm_core #(
    parameter integer MODULE_ID = 1,
    parameter integer SKETCH_D  = 0
) (
    input  wire        clk,
    input  wire        clr,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [63:0] in_rec,
    input  wire        flush,
    output reg         out_valid,
    output reg  [63:0] out_word
);
`include "rules.vh"

    wire        det_ready, sk_busy;
    wire        win_valid, win_alarm;
    wire [23:0] win_idx, cur_win;
    wire [15:0] win_icmp, win_syn, win_modbus, win_other;
    wire [1:0]  win_cls, win_branch;
    wire        dv = in_valid && !sk_busy;
    assign in_ready = det_ready && !sk_busy;
    wire        fire = dv && det_ready;

    detector u_det (
        .clk(clk), .clr(clr), .in_valid(dv), .in_ready(det_ready), .in_rec(in_rec), .flush(flush),
        .win_valid(win_valid), .win_idx(win_idx), .win_icmp(win_icmp), .win_syn(win_syn),
        .win_modbus(win_modbus), .win_other(win_other), .win_cls(win_cls), .win_alarm(win_alarm),
        .win_branch(win_branch), .cur_win(cur_win));

    wire        sk_valid;
    wire [23:0] sk_win;
    wire [31:0] sk_src;
    wire [15:0] sk_est;
    wire [10:0] sk_bits;
    generate
        if (SKETCH_D > 0) begin : g_sk
            sketch #(.D(SKETCH_D)) u_sk (
                .clk(clk), .clr(clr), .in_fire(fire), .in_rec(in_rec), .in_win(cur_win), .flush(flush),
                .out_valid(sk_valid), .out_win(sk_win), .out_top_src(sk_src), .out_top_est(sk_est),
                .out_set_bits(sk_bits), .busy(sk_busy));
        end else begin : g_nosk
            assign sk_valid = 1'b0; assign sk_win = 24'd0; assign sk_src = 32'd0;
            assign sk_est = 16'd0; assign sk_bits = 11'd0; assign sk_busy = 1'b0;
        end
    endgenerate

    wire [63:0] dec_word  = {2'b00, MODULE_ID[5:0], win_idx, win_cls, win_alarm, win_branch, 27'd0};
    wire [63:0] diag_word = {2'b01, sk_win[14:0], sk_bits, (sk_bits >= DDOS_SETBITS), MODULE_ID[2:0], sk_src};

    // diagnosis FIFO
    reg [63:0] fq [0:15];
    reg [3:0]  wp = 4'd0, rp = 4'd0;
    reg [4:0]  cnt = 5'd0;
    wire       pop = !win_valid && (cnt != 5'd0);
    always @(posedge clk) begin
        if (sk_valid) fq[wp] <= diag_word;
        if (clr) begin
            wp <= 4'd0; rp <= 4'd0; cnt <= 5'd0;
        end else begin
            if (sk_valid) wp <= wp + 4'd1;
            if (pop) rp <= rp + 4'd1;
            cnt <= cnt + {4'd0, sk_valid} - {4'd0, pop};
        end
    end

    initial begin out_valid = 1'b0; out_word = 64'd0; end
    always @(posedge clk) begin
        out_valid <= win_valid || pop;
        out_word  <= win_valid ? dec_word : fq[rp];
    end
endmodule
