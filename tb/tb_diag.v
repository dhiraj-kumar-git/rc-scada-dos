// Testbench for the DFX static top with one module in u_rm (compile with
// -DRM_ID=<1|2|3> and that module's file). Writes per region:
//   build/sim_rm<id>_r<i>_dec.txt   decision words (hex), in order
//   build/sim_rm<id>_r<i>_diag.txt  diagnosis words (hex), in order
//   build/sim_rm<id>_summary.txt    cycles per region, build/sim_rm<id>_leds.txt
// python/compare.py rm checks them against the golden model.
`timescale 1ns/1ps
module tb_diag;
`include "regions.vh"
`ifndef RM_ID
`define RM_ID 1
`endif
    reg clk = 0;
    always #5 clk = ~clk;
    reg btnc = 0;
    reg [1:0] sw = 0;
    wire [7:0] led;
    diag_top #(.DEBOUNCE_BITS(2), .MEMFILE("rtl/records.mem")) dut (.clk(clk), .btnc(btnc), .sw(sw), .led(led));

    integer fdec = 0, fdia = 0, fs, fl, r;
    reg [8*64:1] fname;
    reg [31:0] len;
    always @(posedge clk) begin
        if (dut.rm_valid && dut.rm_word[63:62] == 2'b00 && fdec != 0) $fwrite(fdec, "%016x\n", dut.rm_word);
        if (dut.rm_valid && dut.rm_word[63:62] == 2'b01 && fdia != 0) $fwrite(fdia, "%016x\n", dut.rm_word);
    end
    initial begin
        $sformat(fname, "build/sim_rm%0d_summary.txt", `RM_ID); fs = $fopen(fname, "w");
        $sformat(fname, "build/sim_rm%0d_leds.txt", `RM_ID);    fl = $fopen(fname, "w");
        repeat (20) @(posedge clk);
        for (r = 0; r < 4; r = r + 1) begin
            len = (r == 0) ? R0_LEN : (r == 1) ? R1_LEN : (r == 2) ? R2_LEN : R3_LEN;
            if (len != 0) begin
                $sformat(fname, "build/sim_rm%0d_r%0d_dec.txt", `RM_ID, r);  fdec = $fopen(fname, "w");
                $sformat(fname, "build/sim_rm%0d_r%0d_diag.txt", `RM_ID, r); fdia = $fopen(fname, "w");
                sw = r[1:0];
                repeat (4) @(posedge clk);
                btnc = 1; repeat (20) @(posedge clk); btnc = 0;
                wait (dut.state == 2'd1);
                wait (dut.state == 2'd3);
                repeat (1200) @(posedge clk);      // drain diagnosis words and the background clear
                $fclose(fdec); $fclose(fdia); fdec = 0; fdia = 0;
                $fwrite(fl, "region=%0d leds=%b\n", r, led);
                $fwrite(fs, "rm=%0d region=%0d records=%0d cycles=%0d records_per_cycle=%0.3f\n",
                        `RM_ID, r, len, dut.cycles, len * 1.0 / dut.cycles);
                $display("rm=%0d region=%0d records=%0d cycles=%0d records_per_cycle=%0.3f | LEDs=%b",
                         `RM_ID, r, len, dut.cycles, len * 1.0 / dut.cycles, led);
            end
        end
        $fclose(fs); $fclose(fl);
        $finish;
    end
endmodule
