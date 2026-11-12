// Detector: counts packets by kind in 100 ms windows, classifies each window
// with the learned rules (rules.vh), applies 3-window persistence and maps the
// class to an attack tree branch.
//
// Stream interface: one 64-bit record per clock when in_valid && in_ready.
//   record[63:40] timestamp in 100 us ticks, record[39:32] kind,
//   record[31:0] source IPv4 (unused by the Detector, used later by the sketch)
// When a record's timestamp falls past the current window, in_ready drops for
// one clock, the window is emitted on win_* and the window advances. Empty
// windows are emitted the same way, so the output matches python/common.py
// exactly. Pulse flush for one clock after the last record to emit the final
// window.
module detector #(
    parameter integer WINDOW_TICKS = 1000,
    parameter integer PERSIST      = 3
) (
    input  wire        clk,
    input  wire        clr,          // synchronous clear, starts a new run
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [63:0] in_rec,
    input  wire        flush,
    output reg         win_valid,
    output reg  [23:0] win_idx,
    output reg  [15:0] win_icmp,
    output reg  [15:0] win_syn,
    output reg  [15:0] win_modbus,
    output reg  [15:0] win_other,
    output reg  [1:0]  win_cls,      // 0 normal, 1 ping, 2 syn, 3 modbus
    output reg         win_alarm,
    output reg  [1:0]  win_branch,   // 0 none, 1 network layer, 2 application layer
    output wire [23:0] cur_win       // window of the record accepted this clock (for the sketch)
);

`include "rules.vh"

    localparam [7:0] K_ICMP = 8'd1, K_SYN = 8'd2, K_MODBUS = 8'd3;

    wire [23:0] ts   = in_rec[63:40];
    wire [7:0]  kind = in_rec[39:32];

    reg [24:0] cur_end = WINDOW_TICKS;
    reg [23:0] idx = 0;
    reg [15:0] c_icmp = 0, c_syn = 0, c_modbus = 0, c_other = 0;
    reg [1:0]  run = 0;

    wire boundary = in_valid && ({1'b0, ts} >= cur_end);
    assign in_ready = !boundary;
    assign cur_win  = idx;
    wire emit = boundary || flush;

    wire [1:0] cls   = classify(c_icmp, c_syn, c_modbus, c_other);
    wire [1:0] run_n = (cls == 2'd0) ? 2'd0 : ((run == 2'd3) ? 2'd3 : run + 2'd1);

    function [15:0] inc_sat;
        input [15:0] x;
        inc_sat = (x == 16'hFFFF) ? x : x + 16'd1;
    endfunction

    initial begin
        win_valid = 0; win_idx = 0; win_icmp = 0; win_syn = 0; win_modbus = 0;
        win_other = 0; win_cls = 0; win_alarm = 0; win_branch = 0;
    end

    always @(posedge clk) begin
        win_valid <= 1'b0;
        if (clr) begin
            cur_end  <= WINDOW_TICKS;
            idx      <= 24'd0;
            c_icmp   <= 16'd0; c_syn <= 16'd0; c_modbus <= 16'd0; c_other <= 16'd0;
            run      <= 2'd0;
        end else if (emit) begin
            win_valid  <= 1'b1;
            win_idx    <= idx;
            win_icmp   <= c_icmp;
            win_syn    <= c_syn;
            win_modbus <= c_modbus;
            win_other  <= c_other;
            win_cls    <= cls;
            win_alarm  <= (run_n >= PERSIST);
            win_branch <= (cls == 2'd0) ? 2'd0 : ((cls == 2'd3) ? 2'd2 : 2'd1);
            run        <= run_n;
            idx        <= idx + 24'd1;
            cur_end    <= cur_end + WINDOW_TICKS;
            c_icmp <= 16'd0; c_syn <= 16'd0; c_modbus <= 16'd0; c_other <= 16'd0;
        end else if (in_valid) begin
            case (kind)
                K_ICMP:   c_icmp   <= inc_sat(c_icmp);
                K_SYN:    c_syn    <= inc_sat(c_syn);
                K_MODBUS: c_modbus <= inc_sat(c_modbus);
                default:  c_other  <= inc_sat(c_other);
            endcase
        end
    end
endmodule
