// Testbench for rtl/sketch.v alone, on the synthetic vectors from
// tests/make_sketch_vectors.py (back-to-back updates, saturation, idle clocks).
// Compile with -DSKETCH_D=<d>; writes build/sim_sketch_vec_d<d>.txt.
`timescale 1ns/1ps
module tb_sketch;
`include "sketch_vec_n.vh"
`ifndef SKETCH_D
`define SKETCH_D 4
`endif
    reg clk = 0;
    always #5 clk = ~clk;

    reg [71:0] vec [0:NVEC-1];
    initial $readmemh("build/sketch_vec.mem", vec);

    reg         clr = 0, fire = 0, flush = 0;
    reg  [63:0] rec = 0;
    reg  [23:0] win = 0;
    wire        ov, busy;
    wire [23:0] ow;
    wire [31:0] osrc;
    wire [15:0] oest;
    wire [10:0] obits;

    sketch #(.D(`SKETCH_D)) dut (
        .clk(clk), .clr(clr), .in_fire(fire), .in_rec(rec), .in_win(win), .flush(flush),
        .out_valid(ov), .out_win(ow), .out_top_src(osrc), .out_top_est(oest), .out_set_bits(obits),
        .busy(busy));

    integer fo, n, g;
    reg [8*64:1] fname;
    always @(posedge clk)
        if (ov) $fwrite(fo, "%0d %0d %0d %0d\n", ow, osrc, oest, obits);

    initial begin
        $sformat(fname, "build/sim_sketch_vec_d%0d.txt", `SKETCH_D);
        fo = $fopen(fname, "w");
        @(posedge clk); clr <= 1; @(posedge clk); clr <= 0;
        for (n = 0; n < NVEC; n = n + 1) begin
            for (g = 0; g < vec[n][71:64]; g = g + 1) begin
                fire <= 0; @(posedge clk);
            end
            fire <= 1;
            rec  <= vec[n][63:0];
            win  <= vec[n][63:40] / 1000;
            @(posedge clk);
        end
        fire <= 0;
        @(posedge clk); flush <= 1; @(posedge clk); flush <= 0;
        repeat (20) @(posedge clk);
        if (!busy) $display("ERROR: background clear did not start");
        wait (!busy);
        $fclose(fo);
        $display("tb_sketch D=%0d: %0d records", `SKETCH_D, NVEC);
        $finish;
    end
endmodule
