// Testbench: runs every region of rtl/records.mem through replay_top and
// writes every window the Detector emits to build/sim_r<i>.txt, plus one
// summary line per region to build/sim_summary.txt. python/compare.py then
// checks these files against the Python golden model, line by line.
`timescale 1ns/1ps
module tb_replay;
`include "regions.vh"

    reg clk = 0;
    always #5 clk = ~clk;          // 100 MHz

    reg btnc = 0;
    reg [1:0] sw = 0;
    wire [7:0] led;

    replay_top #(.DEBOUNCE_BITS(2), .MEMFILE("rtl/records.mem")) dut (
        .clk(clk), .btnc(btnc), .sw(sw), .led(led));

    integer fd = 0, fs = 0, fl = 0, r, n_win, n_alarm, first_alarm, first_class;
    reg [8*64:1] fname;
    reg [31:0] len;

    always @(posedge clk) begin
        if (dut.u_det.win_valid && fd != 0) begin
            $fwrite(fd, "%0d %0d %0d %0d %0d %0d %0d %0d\n",
                    dut.u_det.win_idx, dut.u_det.win_icmp, dut.u_det.win_syn,
                    dut.u_det.win_modbus, dut.u_det.win_other, dut.u_det.win_cls,
                    dut.u_det.win_alarm, dut.u_det.win_branch);
            n_win = n_win + 1;
            if (dut.u_det.win_alarm) begin
                if (n_alarm == 0) begin
                    first_alarm = dut.u_det.win_idx;
                    first_class = dut.u_det.win_cls;
                end
                n_alarm = n_alarm + 1;
            end
        end
    end

    initial begin
        fs = $fopen("build/sim_summary.txt", "w");
        fl = $fopen("build/sim_leds.txt", "w");
        repeat (20) @(posedge clk);
        for (r = 0; r < 4; r = r + 1) begin
            len = (r == 0) ? R0_LEN : (r == 1) ? R1_LEN : (r == 2) ? R2_LEN : R3_LEN;
            if (len != 0) begin
                $sformat(fname, "build/sim_r%0d.txt", r);
                fd = $fopen(fname, "w");
                n_win = 0; n_alarm = 0; first_alarm = -1; first_class = -1;
                sw = r[1:0];
                repeat (4) @(posedge clk);
                btnc = 1; repeat (20) @(posedge clk); btnc = 0;
                wait (dut.state == 2'd1);          // RUN
                wait (dut.state == 2'd3);          // DONE
                repeat (4) @(posedge clk);
                $fclose(fd); fd = 0;
                $fwrite(fs, "region=%0d windows=%0d alarm_windows=%0d first_alarm=%0d first_class=%0d\n",
                        r, n_win, n_alarm, first_alarm, first_class);
                $fwrite(fl, "region=%0d leds=%b\n", r, led);
                $display("region=%0d windows=%0d alarm_windows=%0d first_alarm=%0d first_class=%0d | records=%0d cycles=%0d records_per_cycle=%0.3f | LEDs=%b",
                         r, n_win, n_alarm, first_alarm, first_class, len, dut.cycles,
                         len * 1.0 / dut.cycles, led);
            end
        end
        $fclose(fs);
        $fclose(fl);
        $finish;
    end
endmodule
