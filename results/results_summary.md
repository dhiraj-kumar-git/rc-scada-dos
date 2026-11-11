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
| WNS at 10 ns clock | | build/vivado_timing.txt |
| Block RAM cells | | build/vivado_utilization.txt |
| LUTs / FFs | | build/vivado_utilization.txt |

## Per-packet work benchmark (why FPGA)

| Work per packet | PC, million records/s (measured, 2.1 GHz Xeon) | ARM on the board (lab session) | FPGA |
| --- | --- | --- | --- |
| Plain counting (d = 0) | 627 to 818 | | not built yet |
| Sketch, 1 row | 239 to 249 | | not built yet |
| Sketch, 2 rows | 106 to 175 | | not built yet |
| Sketch, 4 rows | 89 to 114 | | not built yet |
| Sketch, 8 rows | 62 to 70 | | not built yet |

## DFX bitstreams (today) and live swap (lab session)

| Result | Value | Comes from |
| --- | --- | --- |
| Full bitstreams built (names, sizes) | | `DFX_RESULT` lines |
| Partial bitstreams built (names, sizes) | | `DFX_RESULT` lines |
| pr_verify passed (yes or no) | | build/dfx/pr_verify.txt |
| Predicted swap time at 128 MB/s (partial size / 128 MB/s) | | computed from the row above |
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
