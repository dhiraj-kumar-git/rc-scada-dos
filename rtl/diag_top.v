// DFX static top (E2): replay real records from block RAM into the
// reconfigurable partition u_rm (rm_slot: rm_detector, rm_net_diag or
// rm_modbus_diag). Static region: replay ROM, FIFO, result latch, LEDs.
// The LED latch reads the decision words on out_word (same LEDs as replay_top).
//
//   SW1..SW0  pick the region (scenario) from rtl/regions.vh
//   BTNC      start a run
//   LD0 running   LD1 done   LD2 alarm raised
//   LD3 network-layer branch   LD4 application-layer branch
//   LD5 ping flood   LD6 SYN flood   LD7 Modbus query flood
//   (LD3..LD7 show the first alarm window of the run)
//
// cycles counts clocks from start to done; it is marked for debug so an ILA
// can read it on the board. At 100 MHz, records per second =
// records / (cycles * 10 ns).
module diag_top #(
    parameter integer DEBOUNCE_BITS = 20,          // about 10 ms at 100 MHz
    parameter         MEMFILE       = "records.mem"
) (
    input  wire       clk,
    input  wire       btnc,
    input  wire [1:0] sw,
    output wire [7:0] led
);

`include "regions.vh"

    // ------------------------------------------------ button: sync + debounce
    reg [2:0] bsync = 3'b000;
    reg [DEBOUNCE_BITS-1:0] bcnt = 0;
    reg bstable = 1'b0, bprev = 1'b0;
    always @(posedge clk) begin
        bsync <= {bsync[1:0], btnc};
        if (bsync[2] != bstable) begin
            bcnt <= bcnt + 1'b1;
            if (&bcnt) begin
                bstable <= bsync[2];
                bcnt    <= 0;
            end
        end else begin
            bcnt <= 0;
        end
        bprev <= bstable;
    end
    wire start_pulse = bstable & ~bprev;

    // ------------------------------------------------ region select
    reg [31:0] sel_start, sel_len;
    always @* begin
        case (sw)
            2'd0: begin sel_start = R0_START; sel_len = R0_LEN; end
            2'd1: begin sel_start = R1_START; sel_len = R1_LEN; end
            2'd2: begin sel_start = R2_START; sel_len = R2_LEN; end
            default: begin sel_start = R3_START; sel_len = R3_LEN; end
        endcase
    end

    // ------------------------------------------------ control
    localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_FLUSH = 2'd2, S_DONE = 2'd3;
    reg [1:0]  state = S_IDLE;
    reg [31:0] r_len = 0, rd_addr = 0, issued = 0, consumed = 0;
    (* mark_debug = "true" *) reg [31:0] cycles = 0;

    // ------------------------------------------------ block RAM (read latency 1)
    reg [63:0] mem [0:BRAM_DEPTH-1];
    initial $readmemh(MEMFILE, mem);
    reg [63:0] rd_data = 64'd0;
    reg        rd_valid = 1'b0;

    // ------------------------------------------------ 4-entry FIFO in front of the Detector
    reg [63:0] fq0 = 0, fq1 = 0, fq2 = 0, fq3 = 0;
    reg [1:0]  wp = 0, rp = 0;
    reg [2:0]  fcount = 0;
    wire       f_valid = (fcount != 3'd0);
    wire [63:0] f_data = (rp == 2'd0) ? fq0 : (rp == 2'd1) ? fq1 : (rp == 2'd2) ? fq2 : fq3;
    wire       det_ready;
    wire       pop = f_valid && det_ready;
    // issue a read only if FIFO + in-flight read leaves room: never overflows,
    // and in steady state issues one read per clock
    wire       issue = (state == S_RUN) && (issued < r_len) && ((fcount + {2'b00, rd_valid}) <= 3'd2);

    always @(posedge clk) begin
        if (issue) rd_data <= mem[rd_addr];
        rd_valid <= issue;
    end

    wire clr = start_pulse && (state == S_IDLE || state == S_DONE);

    always @(posedge clk) begin
        if (clr) begin
            wp <= 0; rp <= 0; fcount <= 0;
        end else begin
            if (rd_valid) begin
                case (wp)
                    2'd0: fq0 <= rd_data;
                    2'd1: fq1 <= rd_data;
                    2'd2: fq2 <= rd_data;
                    default: fq3 <= rd_data;
                endcase
                wp <= wp + 2'd1;
            end
            if (pop) rp <= rp + 2'd1;
            fcount <= fcount + {2'b00, rd_valid} - {2'b00, pop};
        end
    end

    // ------------------------------------------------ reconfigurable partition
    wire        rm_valid;
    wire [63:0] rm_word;
    rm_slot u_rm (
        .clk(clk), .clr(clr), .in_valid(f_valid), .in_ready(det_ready), .in_rec(f_data),
        .flush(state == S_FLUSH), .out_valid(rm_valid), .out_word(rm_word));
    wire       win_valid  = rm_valid && (rm_word[63:62] == 2'b00);
    wire       win_alarm  = rm_word[29];
    wire [1:0] win_cls    = rm_word[31:30];
    wire [1:0] win_branch = rm_word[28:27];

    // ------------------------------------------------ state machine + result latch
    reg       alarm_seen = 1'b0;
    reg [1:0] first_branch = 2'd0, first_cls = 2'd0;

    always @(posedge clk) begin
        if (clr) begin
            r_len    <= sel_len;
            rd_addr  <= sel_start;
            issued   <= 0;
            consumed <= 0;
            cycles   <= 0;
            alarm_seen <= 1'b0; first_branch <= 2'd0; first_cls <= 2'd0;
            state    <= (sel_len == 0) ? S_DONE : S_RUN;
        end else begin
            if (win_valid && win_alarm && !alarm_seen) begin
                alarm_seen   <= 1'b1;
                first_branch <= win_branch;
                first_cls    <= win_cls;
            end
            case (state)
                S_RUN: begin
                    cycles <= cycles + 1;
                    if (issue) begin
                        rd_addr <= rd_addr + 1;
                        issued  <= issued + 1;
                    end
                    if (pop) consumed <= consumed + 1;
                    if (consumed == r_len) state <= S_FLUSH;
                end
                S_FLUSH: begin
                    cycles <= cycles + 1;
                    state  <= S_DONE;
                end
                default: ;
            endcase
        end
    end

    assign led[0] = (state == S_RUN) || (state == S_FLUSH);
    assign led[1] = (state == S_DONE);
    assign led[2] = alarm_seen;
    assign led[3] = alarm_seen && (first_branch == 2'd1);
    assign led[4] = alarm_seen && (first_branch == 2'd2);
    assign led[5] = alarm_seen && (first_cls == 2'd1);
    assign led[6] = alarm_seen && (first_cls == 2'd2);
    assign led[7] = alarm_seen && (first_cls == 2'd3);
endmodule
