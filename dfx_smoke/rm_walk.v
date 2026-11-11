// Reconfigurable module variant B: one lit LED walks left.
// If the register starts at zero after a partial reconfiguration, it reloads
// a single lit LED, so the pattern can never get stuck dark.
module rm_pattern (
    input  wire       clk,
    input  wire       tick,
    output reg  [7:0] led = 8'd1
);
    always @(posedge clk)
        if (tick) led <= (led == 8'd0) ? 8'd1 : {led[6:0], led[7]};
endmodule
