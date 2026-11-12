# Comparison with published work

Our numbers are labelled with how they were obtained. Published numbers are quoted from the source named in each row. Different rows measure different things; the last column says how they relate.

| Work | Platform | What is measured | Number | How it relates to ours |
| --- | --- | --- | --- | --- |
| This project, detection | ZedBoard XC7Z020 PL, 100 MHz | Detector (learned depth-3 tree, 4 window counts) on Coimbra test captures | F1 ping 1.000, SYN 0.999, Modbus 0.955; alarm after 200 to 300 ms; 0 false alarms on the 1 h clean capture | results/detection_metrics.md; per 100 ms window |
| This project, throughput | ZedBoard XC7Z020 PL, 100 MHz | Records per second with sketch D = 1 to 8 | 94.6 to 98.5 million records/s at every D (cycle-accurate simulation; timing met in Vivado implementation at 100 MHz; not yet measured on the board) | results/why_fpga.md |
| This project, PC baseline | Intel i7-13620H | Same sketch in C | 266 to 66 million records/s for D = 1 to 8 | results/benchmark_pc.txt |
| This project, swap | ZedBoard, PCAP | Partial bitstream for one Diagnoser | 1,154,452 bytes, about 9.02 ms (predicted from partial bitstream size) | build/dfx_diag/ |
| This project, smoke test swap | ZedBoard, PCAP | Partial bitstream, 20-column region | 383,555 bytes, about 3.00 ms (predicted from partial bitstream size) | build/dfx/ |
| This project, zero loss | Simulation | Hold FIFO 16,384, swap at first alarm | 0 drops up to 1.82 million records/s (cycle-accurate simulation) | results/zero_loss.md |
| Frazao et al., CRITIS 2018, and Frazao dissertation (Univ. of Coimbra) | MATLAB, offline | kNN, DT, RF, SVM, NB, NN on the same Coimbra captures, accuracy and F1 per capture | Decision Tree best; kNN on the ping flood 63.33 % accuracy, 73.58 % F1 (k = 1, euclidean, dissertation Table 5.1); Modbus query flood 'unusually good' for all classifiers, traced to 'a field with little variance during the attack' | Same dataset and attacks; offline, per-trace features; we classify 100 ms windows in hardware with 4 counts. Not a like-for-like score |
| Xilinx XAPP1159 | Zynq-7000 | Partial reconfiguration through PCAP | 134,392 bytes in 1,060 us (about 127 MB/s) | Measured on hardware; our swap estimate uses the same order of throughput |
| ZyCAP (Vipin and Fahmy) | Zynq-7000 | PCAP reconfiguration throughput | 128 MB/s | Rate used for our swap predictions |
| Thinh et al. 2016 | Zynq | Partial reconfiguration time | about 82 ms for 822 KB | Slower controller; shows the spread of swap times |
| Le Jeune et al., ACNS 2021 workshops (LNCS 12726) | Pynq-Z2, XC7Z020-1CLG400C (same chip family), 100 MHz | Quantized CNN intrusion detection (FINN), CICIDS2017 | about 2,400 frames/s, 22.44 Mbps supported; 24,635 LUT (46.31 %), 27,450 FF, 37.5 BRAM; 2-bit accuracy 99.41 % | Different task and dataset; deep model uses about half the LUTs of the same chip, while our detector and sketch fit in a few percent |
| Line rates | Ethernet | Worst case, 64-byte frames | 1 GbE 1.488, 10 GbE 14.88 million packets/s | Reference lines in why_fpga.png and zero_loss.png |

Sources: Frazao dissertation, estudogeral.uc.pt handle 10316/86748 (Chapter 5); Le Jeune, Goedeme, Mentens, DOI 10.1007/978-3-030-81645-2_9 (open copy on KU Leuven Lirias), Table 2, Table 3 and Sect. 5; XAPP1159, ZyCAP and Thinh et al. figures as given in the project plan.
