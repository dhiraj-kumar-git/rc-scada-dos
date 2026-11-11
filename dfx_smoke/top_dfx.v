// DFX smoke test: one reconfigurable module drives the
// LEDs. Two variants with the same ports: rm_count (binary counter) and
// rm_walk (one lit LED walking). Load the full bitstream, then load the
// other module's partial bitstream over JTAG: the LED pattern changes while
// the static counter keeps running.
module top_dfx (
    input  wire       clk,
    output wire [7:0] led
);
    reg [26:0] div = 0;                 // static region: free-running divider
    always @(posedge clk) div <= div + 1'b1;
    rm_pattern u_rm (.clk(clk), .tick(div[26:19] == 8'd0 && div[18:0] == 19'd0), .led(led));
endmodule
