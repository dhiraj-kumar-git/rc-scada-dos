# FPGA attack tree evaluation of DoS attacks on SCADA (ZedBoard)

Vivado builds can run from scripts: `scripts/build_replay.tcl` (replay
bitstream), `scripts/dfx_smoke.tcl` (DFX full and partial bitstreams),
`scripts/program_board.tcl` (lab only). `make arm-check` runs the C code built
for the Cortex-A9 under QEMU.

Reconfigurable Computing project, BITS Pilani WILP. Team: Parth Dutta,
Riteshbabu Allam, Dhiraj Kumar, Saunak Chakraborty.

Current scope: real Modbus/TCP benchmark traffic (Coimbra ICS_PCAPS)
replayed from block RAM through a Verilog Detector that uses rules learned in
Python. Python, the Verilog simulation, the C baseline and the board must all
give the same answer, window by window.

## Rule for every claim

Nothing goes on a slide unless a script in this repo produced it and a check
below passed. If a check fails, the slide says "not done yet".

## Layout

| Path | What it is |
| --- | --- |
| `python/common.py` | One source of truth: record format, windows, persistence, golden model |
| `python/extract.py` | pcap → records + `build/source_report.md` (who sends what) |
| `python/train_rules.py` | Learns the depth-3 tree, writes `rtl/rules.vh`, `c/rules.h`, `results/detection_metrics.md`, plots |
| `python/make_demo.py` | Builds `rtl/records.mem`, `rtl/regions.vh`, `c/records.h`, golden outputs |
| `python/compare.py` | Checks sim / C / board output against the golden model |
| `rtl/detector.v`, `rtl/replay_top.v` | Detector and replay board top |
| `tb/tb_replay.v` | Testbench over every region |
| `c/detector.c`, `c/zynq_main.c` | ARM baseline (bare-metal) and its PC twin `c/host_main.c` |
| `constraints/zedboard_replay.xdc` | Pins for clock, BTNC, SW0..1, LD0..7 |
| `dfx_smoke/` | Two reconfigurable modules for the first DFX test |
| `tests/make_fixture.py` | Synthetic pcaps that test the toolchain only, never results |

Generated files (`rtl/rules.vh`, `rtl/regions.vh`, `rtl/records.mem`,
`c/rules.h`, `c/records.h`) are committed by the data owner after the real run,
so the Verilog and C owners never need to retrain.

## Setup (everyone, once)

```
git clone <your private repo url> rc-scada-dos
```

```
cd rc-scada-dos
```

```
pip install -r requirements.txt
```

Linux or WSL: install Icarus Verilog for simulation.

```
sudo apt-get install -y iverilog
```

Check the toolchain on synthetic data (runs in a separate `selftest/` copy, so
it never touches the real generated files):

```
make test
```

Done when the output ends with `RESULT: PASS` twice (simulation and C).

## Data owner: real data

1. Download `captures1.zip` from the Coimbra release
   (https://github.com/tjcruz-dei/ICS_PCAPS/releases/tag/MODBUSTCP%231) and
   unzip into `data/`.
2. List the files and fill every `REPLACE` name in `config.json`.

```
ls data/
```

3. Extract and read the source report before anything else.

```
make data
```

```
cat build/source_report.md
```

Done when: each attack capture shows a sensible attack interval and a count of
distinct unknown sources. Write down that count for each flood: it decides
whether the Diagnoser later reports "DoS, top source" or "DDoS, about N
sources".

4. Learn the rules and measure them on the test captures.

```
make rules
```

Done when `results/detection_metrics.md` exists. Its tables are the detection results
for the slides, together with `results/learned_rules.txt` and `results/window_counts_*.png`.

5. Build the demo memory.

```
make demo
```

Done when there is no `WARNING` line. If a flood region warns that too few
attack windows fit, set that region's `lead_s` to 0.3 and `max_records` to
16384, and if the total no longer fits, set `bram_depth` to 65536. Rerun.

6. Commit the generated files and tag them, so everyone builds from the same
   data.

```
git add rtl/rules.vh rtl/regions.vh rtl/records.mem c/rules.h c/records.h results/ config.json
```

```
git commit -m "Add Coimbra capture config, learned rules, demo memory and test metrics"
```

```
git tag real-data-v1 && git push && git push --tags
```

## Verilog owner: simulation

```
make sim
```

Done when every region prints `PASS` and the last line is `RESULT: PASS`. Note
the `cycles` and `records_per_cycle` values for each region: they are the
FPGA timing results (at 100 MHz, time = cycles × 10 ns).

## Board owner: Vivado, replay bitstream

1. New RTL project, part `xc7z020clg484-1` (or the ZedBoard board file).
2. Add sources: `rtl/detector.v`, `rtl/replay_top.v`, `rtl/rules.vh`,
   `rtl/regions.vh`, `rtl/records.mem`. Set `replay_top` as top.
3. Add constraints: `constraints/zedboard_replay.xdc`. Check J18 (VADJ) as the
   file explains.
4. If synthesis says it cannot open an include file, add `rtl/` under
   Settings > General > Verilog options > Include directories.
5. Run synthesis, implementation, generate bitstream.

Done when: timing is met (WNS ≥ 0 ns at 10 ns) and the utilization report
shows block RAM in use (about 64 RAMB36 for depth 32768: 32,768 words × 64 bits). Zero block RAM
means `records.mem` was not found: set the `MEMFILE` parameter of
`replay_top` to the file's absolute path and rebuild.

6. Program the board. Set SW1..SW0 to a region, press BTNC.

Done when the LEDs match the `expected LEDs` line that `make demo` printed for
that region (LD1 done, LD2 alarm, LD3 network, LD4 application, LD5 ping,
LD6 SYN, LD7 Modbus).

Optional: after synthesis, Set Up Debug on the `cycles` net (already marked
for debug), rebuild, and read it in the Hardware Manager after a run. It must
equal the simulation's `cycles` for that region.

## ARM owner: baseline on the Cortex-A9

1. Vivado block design with only the Zynq PS (Run Block Automation, apply the
   ZedBoard preset), generate the wrapper, export hardware (XSA).
2. Vitis: platform from the XSA, new application from the Hello World
   template, bare-metal (standalone).
3. Replace `helloworld.c` with `c/zynq_main.c`; add `c/detector.c`,
   `c/detector.h`, `c/rules.h`, `c/records.h`. Build in Release (-O2).
4. Run on the board with a serial terminal at 115200 baud on the USB-UART port.
5. Copy every `region=` line into `build/board_summary.txt`, then check it.

```
python3 python/compare.py board
```

Done when it prints `summary: PASS`. The `arm region=` lines give the ARM
records per second, the CPU number for the speed comparison.

Before the board: the same C code runs on a PC and must match.

```
make host
```

## DFX smoke test

Goal: show a partial bitstream changing one module while the rest keeps
running. Uses `dfx_smoke/top_dfx.v` with two variants of `rm_pattern`
(`rm_count.v`, `rm_walk.v`).

1. New project with `top_dfx.v` and `rm_count.v`; LD0..LD7 and the clock pins
   from `constraints/zedboard_replay.xdc` (drop the btnc and sw lines).
2. Tools > Enable Dynamic Function eXchange. Right-click `u_rm` > Create
   Partition Definition. Add `rm_walk.v` as a second reconfigurable module.
3. Run the Dynamic Function eXchange Wizard (Vivado 2020.1 or later; older versions call it the Partial Reconfiguration Wizard) to create two configurations, then
   draw a small Pblock for `u_rm` and run implementation.
4. Generate bitstreams. Program the full bitstream, then program the other
   module's partial bitstream from the Hardware Manager.

Done when the LED pattern changes from counting to a walking LED without
reprogramming the whole device. Reference: UG909 (Vivado Dynamic Function
eXchange user guide) and XAPP1231.

## Results that go on slides

- `build/source_report.md`: sources per capture (spoofed or single attacker)
- `results/detection_metrics.md`: precision, recall, F1 per class on test captures,
  alarm delay, false alarms, learned rules vs the teammates' hand rule
- `results/window_counts_*.png`: traffic per window with attack windows shaded
- `make sim` output: PASS and cycles per region
- Board: LEDs per region matching the expected line
- ARM: `arm region=` records per second, and `compare.py board` PASS

Dataset citation: I. Frazão, P. H. Abreu, T. Cruz, H. Araújo, P. Simões,
"Denial of Service Attacks: Detecting the frailties of machine learning
algorithms in the Classification Process", CRITIS 2018,
DOI 10.1007/978-3-030-05849-4_19.

## Per-packet work benchmark (why FPGA)

Measures how a CPU's cost per record grows as work is added per packet:
plain counting (d = 0), then a count-min sketch with d = 1, 2, 4, 8 rows plus
a distinct-source bitmap. The FPGA does all rows in the same clock; this
benchmark measures the CPU side.

On a PC:

```
make bench
```

On the ARM: new Vitis Hello World app on the same platform, replace
`helloworld.c` with `c/sketch_zynq_main.c`, add `c/sketch_bench.c` and
`c/sketch_bench.h`, build in Release, run with the serial terminal open.

Done when the UART prints five `arm d=` lines and `done`. Copy them into the
results table. These are the ARM numbers; the FPGA side of the comparison is
shown when the sketch RTL exists (simulation cycles and Vivado timing).
