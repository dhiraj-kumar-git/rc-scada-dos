# Results summary

Fill every cell from the file or output named in its row. Leave a cell empty
rather than estimate it. A value is final only when its check passed.

## Detection on the real Coimbra captures (test split)

| Result | Normal | Ping flood | SYN flood | Modbus flood | Comes from |
| --- | --- | --- | --- | --- | --- |
| Distinct unknown sources in the test capture | 0 | 59958 | 59939 | 1 (172.27.224.50) | build/source_report.md |
| Precision / recall / F1 (test windows) | 1.000 / 0.999 / 0.999 | 1.000 / 1.000 / 1.000 | 0.999 / 1.000 / 0.999 | 0.933 / 0.978 / 0.955 | results/detection_metrics.md |
| Alarm delay (ms) | - (no alarm) | 200 | 300 | 200 | results/detection_metrics.md |
| False alarm windows | 0 | 0 | 0 | 33 (all inside the attack interval, see note 3) | results/detection_metrics.md |
| Hand rule: alarm delay / false alarms | - / 0 | not applicable (Modbus-only rule) | not applicable (Modbus-only rule) | 400 / 2 | results/detection_metrics.md |

Learned rules (results/learned_rules.txt): ICMP echo > 0 per window gives ping_flood;
otherwise more than 8 "other" packets gives modbus_flood; otherwise more than 1
SYN gives syn_flood; otherwise normal. Test windows: 89952, exported rules agree
with sklearn on 1.0000 of them. Distinct unknown sources: build/source_report.md
(build/ is not committed; rerun `make data` to regenerate it).

## Hardware and software agreement and timing (demo regions)

| Result | Region 0 normal | Region 1 ping | Region 2 SYN | Region 3 Modbus | Comes from |
| --- | --- | --- | --- | --- | --- |
| Records / windows | 8192 / 4087 | 8192 / 443 | 8192 / 461 | 8192 / 121 | `make demo` output |
| FPGA simulation: cycles / records per cycle | 12282 / 0.667 | 8638 / 0.948 | 8656 / 0.946 | 8316 / 0.985 | `make sim` output |
| FPGA time at 100 MHz (cycles x 10 ns) | 122.82 us | 86.38 us | 86.56 us | 83.16 us | computed from the row above |
| Simulation LEDs match expected (yes or no) | yes (00000010) | yes (00101110) | yes (01001110) | yes (10010110) | `make sim` LEDs line |
| C on PC / ARM build under QEMU PASS (yes or no) | yes / yes | yes / yes | yes / yes | yes / yes | `make host`, `make arm-check` |
| Board LEDs match expected (lab session) | | | | | LED check plus photos |
| ARM on the board: records per second (lab session) | | | | | UART `arm region=` lines |

## Vivado build

| Result | Value | Comes from |
| --- | --- | --- |
| WNS at 10 ns clock | +2.890 ns (all timing constraints met; WHS +0.086 ns) | build/vivado_timing.txt |
| Block RAM cells | 25 RAMB36 of 140 (17.86 %), see note 7 | build/vivado_utilization.txt |
| LUTs / FFs | 149 of 53200 (0.28 %) / 330 of 106400 (0.31 %) | build/vivado_utilization.txt |

## Per-packet work benchmark (why FPGA)

Measured with `make bench` on an Intel i7-13620H laptop (WSL2, gcc -O2), synthetic records
(c/sketch_bench.c: 40 per 100 ms window, random sources). FPGA column: not built yet.

| Work per packet | PC, million records/s, median (min to max) of 3 runs, results/benchmark_pc.txt | ARM on the board (lab session) | FPGA |
| --- | --- | --- | --- |
| Plain counting (d = 0) | 952 (947 to 983) | | not built yet |
| Sketch, 1 row | 222 (221 to 223) | | not built yet |
| Sketch, 2 rows | 173 (164 to 173) | | not built yet |
| Sketch, 4 rows | 110 (105 to 114) | | not built yet |
| Sketch, 8 rows | 62 (54 to 63) | | not built yet |

## DFX bitstreams and live swap (lab session)

| Result | Value | Comes from |
| --- | --- | --- |
| Full bitstreams built (names, sizes) | config_count.bit 4,045,762 bytes; config_walk.bit 4,045,762 bytes | `DFX_RESULT` lines |
| Partial bitstreams built (names, sizes) | config_count_pblock_rm_partial.bit 383,555 bytes; config_walk_pblock_rm_partial.bit 383,555 bytes | `DFX_RESULT` lines |
| pr_verify passed (yes or no) | yes: the two routed configurations are compatible (1224 static tiles, 634 static routed nodes compared) | build/dfx/pr_verify.txt |
| Predicted swap time at 128 MB/s (partial size / 128 MB/s) | about 3.0 ms (383,555 bytes / 128 x 10^6 bytes/s = 2.997 ms); a prediction, not a measurement | computed from the row above |
| Live swap changed the LEDs without full reprogram (lab session) | | observed |

## Notes on the data (from build/source_report.md and results/detection_metrics.md)

1. Captures used (release MODBUSTCP#1, asset captures1_v2.zip). Train / test:
   clean 0.5 h / clean 1 h (only one 0.5 h clean capture exists);
   pingFloodDDoS 15m-0,5h / 5m-0,5h; tcpSYNFloodDDoS 15m-0,5h / 5m-0,5h;
   modbusQueryFlooding 15m-0,5h / 5m-0,5h. Each test capture is a different
   run from its train capture. The "5m" and "15m" in the names match the attack
   length: the attack intervals in the report start at about 298 s and last
   about 5 and 15 minutes.
2. Spoofing confirmed on the files: the ping and SYN floods use about one new
   source address per attack packet (59958 and 59939 unknown sources in the
   test captures). The Modbus query flood comes from one host, 172.27.224.50,
   not spoofed. Known hosts: 172.27.224.250, 172.27.224.251, 172.27.224.70.
3. The 33 Modbus false alarm windows all lie between the first and last attack
   window (2987 to 5986) of the Modbus test capture. The flood is bursty: only
   1693 of those windows hold an attacker packet. In the gaps the reply traffic
   stays high and the alarm stays on, while the labelling rule calls those gap
   windows normal. Outside attack intervals the learned rules raise 0 false
   alarms (clean 1 h capture: 0). The metric is reported as computed.
4. Training label caveat: in the Modbus train capture the attacker host sent 5
   non-Modbus packets at 51 s and a few after the flood, so a handful of train
   windows outside the flood are labelled modbus_flood. Test metrics do not use
   train data. Data and labelling rule left unchanged.
5. Records per cycle: each window boundary costs one clock, so cycles are about
   records + windows. Region 0 (normal) has 4087 mostly sparse windows, hence
   0.667; flood regions are 0.946 to 0.985.
6. The `make arm-check` timing is emulator (QEMU) speed and is not quoted.
7. Block RAM: a 32768 x 64-bit memory would need 64 RAMB36. Vivado kept 25.
   The Detector does not read the 32 source-address bits (kept for the sketch;
   synthesis warnings Synth 8-7129 and 8-13373), and in this data only 24 of
   the remaining 32 bit columns are ever non-zero (timestamp bits 0 to 21,
   kind bits 0 and 1), so the rest were removed as constants. The synthesis
   log confirms records.mem was read (Synth 8-3876). Bitstream:
   build/replay_top.bit, built with Vivado 2026.1, part xc7z020clg484-1,
   100 MHz clock; implementation had 0 warnings, 0 critical warnings.
8. DFX (Vivado 2026.1, 60-day evaluation license that includes DFX; the
   free BASIC license does not). Reconfigurable region pblock_rm:
   SLICE_X26Y100:SLICE_X45Y149 plus the DSP48, RAMB18 and RAMB36 columns
   inside it (clock region X0Y2, one clock region high). Final run: 0 errors,
   0 critical warnings; timing met at 100 MHz in both configurations
   (WNS +6.278 ns counter, +5.679 ns walking LED). Whole counter configuration: 13 LUTs,
   35 FFs. Both modules also pass simulation (dfx_smoke/tb_dfx.v, Icarus):
   rm_count counts 1, 2, 3, 4; rm_walk walks 2, 4, 8, 16. The live swap on the
   board is still a lab session item.

## E1: count-min sketch and distinct-source counter (cycle-accurate simulation; Vivado implementation at 100 MHz; not yet measured on the board)

Golden model `run_sketch()` in python/common.py; RTL rtl/sketch.v; C c/sketch_bench.c.

| Check | Result | Source |
| --- | --- | --- |
| RTL sketch vs golden model, 4 demo regions x D = 1, 2, 4, 8 | PASS, every window identical (2940, 434, 452, 78 windows per depth) | `make sketch` (python/compare.py sketch) |
| Stress vectors (same source back to back, alternating, shared cell, src = 0, saturation at 65535, idle clocks) | PASS for D = 1, 2, 4, 8 (87,761 records); a copy without forwarding fails | `make sketch-vec` |
| C sketch vs golden model | PASS, every window, D = 1, 2, 4, 8 | `make sketch-host` |
| Records per cycle with the sketch attached | identical to no sketch at every D: 0.667, 0.948, 0.946, 0.985 | build/sketch_sim_d<D>.txt |
| Timing at 100 MHz, sketch alone | met for D = 1, 2, 4, 8 (WNS +1.208, +1.281, +1.702, +1.490 ns) | results/sketch_sweep.txt |

Records per second versus D (PC: make bench; FPGA: 100 MHz x simulated records per cycle,
flood regions): see results/why_fpga.md. PC 856, 266, 184, 113, 66 million records/s for
D = 0, 1, 2, 4, 8; FPGA 94.6 to 98.5 million records/s at every D. The PC is faster up to
D = 4; the FPGA rate does not depend on D. Both exceed the 10 GbE worst case (14.88 Mpps).

Notes:
9. Window tag: 16 bits (window index + 1) per cell instead of 8. An 8-bit tag repeats
   every 256 windows, which would break "cells are zero at the start of every window";
   window indices stay below 2^15, so 16 bits never repeat within a run. Each row still
   uses block RAM only (1024 x 32 bits; Vivado used 2 RAMB36 per row).
10. The first sweep failed timing at D = 8 (WNS -1.556 ns, 17 logic levels in the row
    minimum). Fixed by a balanced two-clock minimum; one extra clock of sketch latency,
    no change in records per cycle.
11. DoS or DDoS (results/detection_metrics.md): T = max(16, 4 x 3.00) = 16 distinct sources
    (set_bits >= 16). Test captures: ping flood 2948 of 3091 attack windows flagged DDoS,
    SYN flood 2942 of 3091, Modbus flood (one attacker host) 0 of 1693, normal windows 0.

## E2: real DFX modules, detection then diagnosis (cycle-accurate simulation; Vivado implementation at 100 MHz; not yet measured on the board)

One partition u_rm (rm_slot), static top rtl/diag_top.v. Modules: rm_detector (Detector),
rm_net_diag (Detector + sketch D = 4 + distinct counter), rm_modbus_diag (Detector + sketch D = 2).
Golden model `rm_words()` in python/common.py.

| Check | Result | Source |
| --- | --- | --- |
| Each module through the static top, 4 demo regions | PASS: decision words (4087, 443, 461, 121 per module) and diagnosis words (2940, 434, 452, 78) identical; LEDs match | `make modules-sim` (python/compare.py modules) |
| Full and partial bitstreams, 3 configurations | built; timing met at 100 MHz in all three (WNS +0.844 ns) | build/dfx_diag/, DFX_DIAG_RESULT lines |
| pr_verify | configuration 1 compatible with 2 and with 3 (3570 static tiles, 50,247 routed nodes, 77 partition pins) | build/dfx_diag/pr_verify.txt |

| Module | Partial bitstream | Predicted swap time (predicted from partial bitstream size, 128 MB/s) | Pblock use: LUTs / FFs / RAMB36 / DSP |
| --- | --- | --- | --- |
| rm_detector | 1,154,452 bytes | 9.02 ms | 94 / 156 / 0 / 0 |
| rm_net_diag | 1,154,452 bytes | 9.02 ms | 853 / 729 / 8.5 / 12 |
| rm_modbus_diag | 1,154,452 bytes | 9.02 ms | 559 / 597 / 4.5 / 6 |

Full bitstreams 4,045,763 bytes each. References: XAPP1159 134,392 bytes in 1,060 us; Thinh et al.
2016 about 82 ms for 822 KB.

Notes:
12. The Pblock is the whole clock region X1Y2 (2600 slices, 30 RAMB36, 40 DSP48), so all three
    partial bitstreams have the same size; a narrower Pblock that still holds 8.5 RAMB36 and 12 DSP
    would shrink the swap (next step). A first run with the region written as CLOCKREGION_X1Y2
    left the Pblock empty (DRC HDPR-74); explicit site ranges fixed it.
13. 8 CRITICAL WARNING [Common 17-55] in the DFX run: the bank-wide IOSTANDARD lines of
    constraints/zedboard_replay.xdc find no ports when the locked static checkpoint is reopened
    for configurations 2 and 3. Checked in all three routed checkpoints: every pin has the same
    location and I/O standard as in configuration 1 (clk and LEDs LVCMOS33, BTNC and switches
    LVCMOS18), so the warnings have no effect on the bitstreams.

## E3: load mode, hold FIFO and zero-loss swap (cycle-accurate simulation; swap time predicted from partial bitstream size; not yet measured on the board)

tb/tb_zero_loss.v (Detector RTL), python/zero_loss.py; full table results/zero_loss.md.
Traffic: 65,536 records of the ping flood test capture. H = 16,384. Swap at the first alarm,
S = 901,916 clocks (9.02 ms, Network Diagnoser partial bitstream at 128 MB/s).
Predicted limit H x 100e6 / S = 1.817 million records/s.

| Offered, million records/s | 0.908 | 1.488 (1 GbE) | 1.762 | 1.798 | 1.835 | 1.871 | 1.998 | 3.633 | 14.88 (10 GbE) | 100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dropped records | 0 | 0 | 0 | 0 | 163 | 491 | 1638 | 16384 | 49143 | 49143 |

Check PASS: 0 drops below the limit, drops beyond it (163, 491, 1638 against the predicted
0.01, 0.03, 0.10 x H = 164, 492, 1638), and every zero-drop run gives windows identical to the
golden model. Zero loss holds above the 1 GbE worst case but not at the 10 GbE worst case with
this swap time; 10 GbE would need H of about 134,000 records or a shorter swap.

## E4: charts and comparison (results/)

| File | What it shows | Source data |
| --- | --- | --- |
| results/why_fpga.png | Records/s versus sketch depth D, PC and FPGA, 1 GbE and 10 GbE worst-case lines | results/benchmark_pc.txt, build/sketch_sim_d<D>.txt, results/sketch_sweep.txt |
| results/zero_loss.png | Dropped records versus offered rate, predicted limit marked | results/zero_loss.csv |
| results/timeline_normal.png, timeline_ping_flood.png, timeline_syn_flood.png, timeline_modbus_flood.png | Per-window counts per demo region, alarm windows shaded, attack tree branch named | build/expected_r<i>.txt (identical to simulation) |
| results/comparison.md | Our numbers next to Frazao et al. 2018 (same dataset), XAPP1159, ZyCAP, Thinh et al. 2016, Le Jeune et al. 2021, 1 GbE and 10 GbE | the files above; sources listed in the file |

Every chart caption carries the required labels: cycle-accurate simulation, Vivado implementation
at 100 MHz, predicted from partial bitstream size, not yet measured on the board.
Generated by `python3 python/e4_charts.py`.
