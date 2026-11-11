`timescale 1ns/1ps
module tb_dfx;
    reg clk = 0; reg tick = 0; wire [7:0] led;
    always #5 clk = ~clk;
    rm_pattern u (.clk(clk), .tick(tick), .led(led));
    integer i;
    initial begin
        for (i = 0; i < 4; i = i + 1) begin
            @(negedge clk) tick = 1; @(negedge clk) tick = 0; $display("tick %0d led=%b", i, led);
        end
        $finish;
    end
endmodule
