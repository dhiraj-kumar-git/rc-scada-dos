// Black-box declaration of the reconfigurable partition, used only when the
// static design (diag_top) is synthesised. Modules: rm_detector.v,
// rm_net_diag.v, rm_modbus_diag.v.
(* black_box *)
module rm_slot (
    input  wire        clk,
    input  wire        clr,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [63:0] in_rec,
    input  wire        flush,
    output wire        out_valid,
    output wire [63:0] out_word
);
endmodule
