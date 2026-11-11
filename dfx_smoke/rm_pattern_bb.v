// Black-box declaration of the reconfigurable module, used only when the
// static design is synthesised. The real modules are rm_count.v and rm_walk.v.
(* black_box *)
module rm_pattern (
    input  wire       clk,
    input  wire       tick,
    output wire [7:0] led
);
endmodule
