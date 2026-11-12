// DFX module rm_modbus_diag: Modbus Diagnoser: Detector plus sketch D = 2 (Modbus flood, top source).
// Every module defines rm_slot with the same ports, so any one can be loaded
// into the reconfigurable partition u_rm.
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
    rm_core #(.MODULE_ID(3), .SKETCH_D(2)) u_core (
        .clk(clk), .clr(clr), .in_valid(in_valid), .in_ready(in_ready), .in_rec(in_rec),
        .flush(flush), .out_valid(out_valid), .out_word(out_word));
endmodule
