// Reconfigurable module variant A: LEDs show a binary count.
module rm_pattern (
    input  wire       clk,
    input  wire       tick,
    output reg  [7:0] led = 8'd0
);
    always @(posedge clk) if (tick) led <= led + 8'd1;
endmodule
