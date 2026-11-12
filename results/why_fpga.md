# Why FPGA: records per second versus sketch depth D

PC: `make bench` (results/benchmark_pc.txt), median and min to max of 3 runs, synthetic records.
FPGA: 100 MHz x records per cycle from cycle-accurate simulation of the demo regions (build/sketch_sim_d<D>.txt), shown only where Vivado implementation at 100 MHz meets timing (results/sketch_sweep.txt). Not yet measured on the board. ARM: lab session.

| D (sketch rows) | PC, million records/s | FPGA flood regions, million records/s | FPGA clean region, million records/s | Vivado WNS at 10 ns | ARM |
| --- | --- | --- | --- | --- | --- |
| 0 (plain counting) | 856 (756 to 886) | 94.6 to 98.5 (Detector only, M1 simulation) | 66.7 | +2.890 ns (full M1 design) | lab session |
| 1 | 266 (259 to 267) | 94.6 to 98.5 | 66.7 | +1.208 ns (met) | lab session |
| 2 | 184 (179 to 185) | 94.6 to 98.5 | 66.7 | +1.281 ns (met) | lab session |
| 4 | 113 (94 to 114) | 94.6 to 98.5 | 66.7 | +1.702 ns (met) | lab session |
| 8 | 66 (65 to 69) | 94.6 to 98.5 | 66.7 | +1.490 ns (met) | lab session |

Reference: 1 GbE worst case 1.488 and 10 GbE worst case 14.88 million packets/s (64-byte frames plus preamble and gap).

## Sketch resources (Vivado implementation at 100 MHz, sketch alone, out of context)

| D | WNS | LUTs | FFs | RAMB36 | RAMB18 | DSP48 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | +1.208 ns (met) | 295 | 367 | 2 | 1 | 3 |
| 2 | +1.281 ns (met) | 470 | 442 | 4 | 1 | 6 |
| 4 | +1.702 ns (met) | 821 | 577 | 8 | 1 | 12 |
| 8 | +1.490 ns (met) | 1488 | 861 | 16 | 1 | 24 |
