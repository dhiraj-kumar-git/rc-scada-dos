# Zero-loss sweep: load mode with hold FIFO and simulated swap

Cycle-accurate simulation (tb/tb_zero_loss.v, Detector RTL); not yet measured on the board.

- Traffic: 65536 records of the ping_5m_0p5h test capture, from 1 s before the attack.
- Hold FIFO depth H = 16384 records. Swap starts at the first alarm; consumer stopped for S = 901916 clocks (9.019 ms).
- S from: Network Diagnoser partial bitstream, 1154452 bytes (E2), at 128 MB/s (PCAP, ZyCAP); predicted from partial bitstream size.
- Predicted limit H x 100e6 / S = 1.817 million records/s.
- Reference: 1 GbE worst case 1.488, 10 GbE worst case 14.88 million packets/s.

Baseline (100 million records/s offered, no swap): drops 0, windows identical to golden: yes.

| offered, million records/s | relative to limit | dropped records | max FIFO level | windows identical to golden | check |
| --- | --- | --- | --- | --- | --- |
| 0.908 | 0.50 | 0 | 8192 | yes | PASS |
| 1.488 | 0.82 | 0 | 13420 | yes | PASS |
| 1.635 | 0.90 | 0 | 14745 | yes | PASS |
| 1.762 | 0.97 | 0 | 15892 | yes | PASS |
| 1.798 | 0.99 | 0 | 16220 | yes | PASS |
| 1.835 | 1.01 | 163 | 16384 | no (records dropped) | PASS |
| 1.871 | 1.03 | 491 | 16384 | no (records dropped) | PASS |
| 1.998 | 1.10 | 1638 | 16384 | no (records dropped) | PASS |
| 3.633 | 2.00 | 16384 | 16384 | no (records dropped) | PASS |
| 14.880 | 8.19 | 49143 | 16384 | no (records dropped) | PASS |
| 100.000 | 55.05 | 49143 | 16384 | no (records dropped) | PASS |

RESULT: PASS
