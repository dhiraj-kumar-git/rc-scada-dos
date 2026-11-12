// E3: load mode with a hold FIFO and a simulated swap (cycle-accurate simulation).
//
// A testbench-level traffic generator offers the records of build/e3_records.mem
// at a fixed rate (plusarg +rate_q24 = offered records per clock x 2^24) into a
// hold FIFO of depth H (plusarg +depth, at most 16384); the Detector consumes
// from the FIFO. A record that arrives while the FIFO is full is dropped and
// counted. When the Detector raises its first alarm, the consumer stops for S
// clocks (plusarg +swap), modelling a partial reconfiguration of u_rm.
// Windows follow record timestamps, so with zero drops every window must equal
// the golden model whatever the rate.
// Writes build/e3_windows.txt and one RESULT line.
`timescale 1ns/1ps
module tb_zero_loss;
`include "e3_n.vh"
    reg clk = 0;
    always #5 clk = ~clk;

    reg [63:0] src [0:E3_N-1];
    initial $readmemh("build/e3_records.mem", src);

    integer rate_q24, depth, swap_s;
    reg [63:0] fifo [0:16383];
    integer wr = 0, rd = 0, level = 0, max_level = 0, offered = 0, drops = 0;
    integer swap_left = 0, swap_start = -1, cyc = 0, acc = 0;
    reg     alarm_seen = 0, swap_done = 0, flush = 0, clr = 0;

    wire        f_valid = (level > 0) && (swap_left == 0);
    wire [63:0] f_data  = fifo[rd % 16384];
    wire        in_ready;
    wire        win_valid, win_alarm;
    wire [23:0] win_idx, cur_win;
    wire [15:0] w_icmp, w_syn, w_modbus, w_other;
    wire [1:0]  w_cls, w_branch;

    detector u_det (.clk(clk), .clr(clr), .in_valid(f_valid), .in_ready(in_ready), .in_rec(f_data),
        .flush(flush), .win_valid(win_valid), .win_idx(win_idx), .win_icmp(w_icmp), .win_syn(w_syn),
        .win_modbus(w_modbus), .win_other(w_other), .win_cls(w_cls), .win_alarm(win_alarm),
        .win_branch(w_branch), .cur_win(cur_win));

    integer fw;
    wire pop = f_valid && in_ready;
    reg  offer;

    always @(posedge clk) begin
        cyc <= cyc + 1;
        // generator: fractional rate accumulator, at most one record per clock
        offer = 0;
        if (offered < E3_N) begin
            if (acc + rate_q24 >= (1 << 24)) begin
                offer = 1;
                acc <= acc + rate_q24 - (1 << 24);
            end else begin
                acc <= acc + rate_q24;
            end
        end
        if (offer) begin
            offered <= offered + 1;
            if (level - (pop ? 1 : 0) >= depth) begin
                drops <= drops + 1;
            end else begin
                fifo[wr % 16384] <= src[offered];
                wr <= wr + 1;
            end
        end
        if (pop) rd <= rd + 1;
        level <= level + ((offer && !(level - (pop ? 1 : 0) >= depth)) ? 1 : 0) - (pop ? 1 : 0);
        if (level > max_level) max_level <= level;
        // simulated swap at the first alarm
        if (swap_left > 0) swap_left <= swap_left - 1;
        if (win_valid) begin
            $fwrite(fw, "%0d %0d %0d %0d %0d %0d %0d %0d\n", win_idx, w_icmp, w_syn, w_modbus,
                    w_other, w_cls, win_alarm, w_branch);
            if (win_alarm && !alarm_seen) begin
                alarm_seen <= 1;
                if (swap_s > 0) begin
                    swap_left  <= swap_s;
                    swap_start <= cyc;
                end
            end
        end
    end

    initial begin
        if (!$value$plusargs("rate_q24=%d", rate_q24)) rate_q24 = 1 << 24;
        if (!$value$plusargs("depth=%d", depth)) depth = 16384;
        if (!$value$plusargs("swap=%d", swap_s)) swap_s = 0;
        fw = $fopen("build/e3_windows.txt", "w");
        @(posedge clk); clr <= 1; @(posedge clk); clr <= 0;
        wait (offered == E3_N);
        wait (level == 0 && swap_left == 0);
        @(posedge clk); flush <= 1; @(posedge clk); flush <= 0;
        repeat (4) @(posedge clk);
        $fclose(fw);
        $display("RESULT rate_q24=%0d depth=%0d swap=%0d offered=%0d drops=%0d max_level=%0d swap_start=%0d cycles=%0d",
                 rate_q24, depth, swap_s, offered, drops, max_level, swap_start, cyc);
        $finish;
    end
endmodule
