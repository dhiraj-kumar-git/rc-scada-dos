"""E4: charts and literature comparison for the slides (results/).

Reads only files written by the checks:
    results/benchmark_pc.txt, build/sketch_sim_d<D>.txt, results/sketch_sweep.txt   (E1)
    build/dfx_diag/*.bit                                                            (E2)
    results/zero_loss.csv                                                           (E3)
    build/expected_r<i>.txt (golden windows, identical to simulation), config.json  (timelines)
Writes:
    results/why_fpga.png, results/zero_loss.png, results/timeline_<scenario>.png,
    results/comparison.md
Palette: reference categorical slots (blue, orange, aqua, yellow), recessive grid,
legend plus direct labels, no dual axes.
"""
import glob
import json
import os
import re
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from common import BRANCH_APPLICATION, BRANCH_NETWORK, CLASSES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")
B = os.path.join(ROOT, "build")
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e4e0", "#fcfcfb"
GBE1, GBE10 = 1.488, 14.88
LABEL_SIM = "cycle-accurate simulation"
LABEL_VIV = "Vivado implementation at 100 MHz"
LABEL_SWAP = "predicted from partial bitstream size"
LABEL_BOARD = "not yet measured on the board"


def style(ax):
    ax.set_facecolor(SURF)
    ax.grid(color=GRID, linewidth=0.8, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b9b8b3")
    ax.tick_params(colors=MUTED, labelsize=9)


def caption(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8, color=MUTED, ha="left", va="bottom", wrap=True)


def why_fpga():
    runs = {}
    for ln in open(os.path.join(R, "benchmark_pc.txt")):
        m = re.match(r"pc d=(\d+) records_per_s=(\d+)", ln)
        if m:
            runs.setdefault(int(m.group(1)), []).append(int(m.group(2)) / 1e6)
    sweep = {}
    for ln in open(os.path.join(R, "sketch_sweep.txt")):
        if ln.strip() and not ln.startswith("#"):
            f = ln.split()
            sweep[int(f[0])] = f[-1]
    ds = [1, 2, 4, 8]
    pc = [statistics.median(runs[d]) for d in ds]
    fl_lo, fl_hi = [], []
    for d in ds:
        vals = {}
        for ln in open(os.path.join(B, "sketch_sim_d%d.txt" % d)):
            m = re.match(r"region=(\d+) .*records_per_cycle=([0-9.]+)", ln)
            if m:
                vals[int(m.group(1))] = float(m.group(2)) * 100
        assert sweep[d] == "met", "timing not met for D=%d" % d
        flood = [vals[i] for i in (1, 2, 3)]
        fl_lo.append(min(flood))
        fl_hi.append(max(flood))
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=200)
    fig.patch.set_facecolor(SURF)
    style(ax)
    ax.set_yscale("log")
    ax.plot(ds, pc, color=BLUE, linewidth=2, marker="o", markersize=7, zorder=3, label="PC (i7-13620H, make bench)")
    ax.errorbar(ds, pc, yerr=[[p - min(runs[d]) for p, d in zip(pc, ds)], [max(runs[d]) - p for p, d in zip(pc, ds)]],
                fmt="none", ecolor=BLUE, elinewidth=1, capsize=3, zorder=3)
    mid = [(a + b) / 2 for a, b in zip(fl_lo, fl_hi)]
    ax.fill_between(ds, fl_lo, fl_hi, color=ORANGE, alpha=0.25, linewidth=0, zorder=2)
    ax.plot(ds, mid, color=ORANGE, linewidth=2, marker="s", markersize=7, zorder=3, label="FPGA sketch at 100 MHz")
    for y, t in ((GBE10, "10 GbE worst case, 14.88 Mpps"), (GBE1, "1 GbE worst case, 1.488 Mpps")):
        ax.axhline(y, color=MUTED, linestyle=(0, (5, 4)), linewidth=1.2, zorder=1)
        ax.text(8.15, y * 1.08, t, fontsize=8.5, color=MUTED, ha="right", va="bottom")
    ax.text(8.2, pc[-1], "PC %.0f M/s" % pc[-1], fontsize=9, color=INK, va="center")
    ax.text(8.2, mid[-1] * 1.15, "FPGA %.0f to %.0f M/s" % (fl_lo[-1], fl_hi[-1]), fontsize=9, color=INK, va="bottom")
    ax.text(1.1, pc[0], "PC %.0f M/s" % pc[0], fontsize=9, color=INK, va="bottom")
    ax.set_xticks(ds)
    ax.set_xticklabels(["1 row", "2 rows", "4 rows", "8 rows"])
    ax.set_xlim(0.7, 10.2)
    ax.set_ylim(1, 1500)
    ax.set_xlabel("Count-min sketch depth D (rows updated per packet)", fontsize=9.5, color=INK)
    ax.set_ylabel("Million records per second (log scale)", fontsize=9.5, color=INK)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    caption(fig, "FPGA: 100 MHz x records per cycle in the flood regions (%s; timing met in %s for every D; %s). "
            "PC: median of 3 runs, whiskers min to max, synthetic records. ARM: lab session." % (LABEL_SIM, LABEL_VIV, LABEL_BOARD))
    fig.savefig(os.path.join(R, "why_fpga.png"), facecolor=SURF)
    plt.close(fig)
    return pc, fl_lo, fl_hi


def zero_loss():
    rows = [ln.strip().split(",") for ln in open(os.path.join(R, "zero_loss.csv"))][1:]
    rate = [float(r[0]) for r in rows]
    drop = [int(r[1]) for r in rows]
    limit = float(rows[0][4])
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=200)
    fig.patch.set_facecolor(SURF)
    style(ax)
    ax.set_xscale("log")
    ax.plot(rate, drop, color=BLUE, linewidth=2, marker="o", markersize=7, zorder=3)
    ax.axvline(limit, color=ORANGE, linewidth=1.8, zorder=2)
    ax.text(limit * 1.06, max(drop) * 0.55, "predicted limit\nH x 100e6 / S\n= %.2f M records/s" % limit,
            fontsize=8.5, color=INK, va="center")
    for x, t, side in ((GBE1, "1 GbE\nworst case", "right"), (GBE10, "10 GbE\nworst case", "left")):
        ax.axvline(x, color=MUTED, linestyle=(0, (5, 4)), linewidth=1.2, zorder=1)
        if side == "right":
            ax.text(x * 0.94, max(drop) * 0.92, t, fontsize=8.5, color=MUTED, ha="right", va="top")
        else:
            ax.text(x * 1.07, max(drop) * 0.45, t, fontsize=8.5, color=MUTED, ha="left", va="top")
    ax.set_xlabel("Offered rate, million records per second (log scale)", fontsize=9.5, color=INK)
    ax.set_ylabel("Dropped records (of 65,536)", fontsize=9.5, color=INK)
    ax.set_ylim(-1500, max(drop) * 1.08)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    caption(fig, "Hold FIFO 16,384 records; swap of 9.02 ms at the first alarm (%s); %s; %s." % (LABEL_SWAP, LABEL_SIM, LABEL_BOARD))
    fig.savefig(os.path.join(R, "zero_loss.png"), facecolor=SURF)
    plt.close(fig)
    return limit


def timelines():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    names = []
    for i, d in enumerate(cfg["demo"]):
        rows = [list(map(int, ln.split())) for ln in open(os.path.join(B, "expected_r%d.txt" % i)) if ln.strip()]
        t = [r[0] * 0.1 for r in rows]
        alarm = [r[6] for r in rows]
        first = next((r for r in rows if r[6] == 1), None)
        if first is None:
            title = "%s: no alarm (normal traffic)" % d["capture"]
        else:
            br = {BRANCH_NETWORK: "network-layer branch", BRANCH_APPLICATION: "application-layer branch"}[first[7]]
            title = "%s: alarm at %.1f s, %s, %s" % (d["capture"], first[0] * 0.1, CLASSES[first[5]].replace("_", " "), br)
        fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=200)
        fig.patch.set_facecolor(SURF)
        style(ax)
        k = 0
        while k < len(alarm):
            if alarm[k]:
                j = k
                while j < len(alarm) and alarm[j]:
                    j += 1
                ax.axvspan(t[k], t[j - 1] + 0.1, color="#e34948", alpha=0.12, linewidth=0, zorder=1)
                k = j
            else:
                k += 1
        series = [("ICMP echo", 1, BLUE), ("TCP SYN", 2, ORANGE), ("Modbus request", 3, AQUA), ("other", 4, YELLOW)]
        for lab, col, c in series:
            y = [r[col] for r in rows]
            ax.plot(t, y, color=c, linewidth=1.5, label=lab, zorder=3)
        ax.set_xlabel("time since start of demo region (s)", fontsize=9.5, color=INK)
        ax.set_ylabel("packets per 100 ms window", fontsize=9.5, color=INK)
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.06), fontsize=8.5, frameon=False, ncol=4)
        ax.text(0.01, 0.97, "shaded: alarm windows", transform=ax.transAxes, fontsize=8, color=MUTED, va="top")
        fig.tight_layout(rect=(0, 0.13, 1, 1))
        caption(fig, "Detector windows: golden model, identical to %s of the RTL (make sim PASS); %s." % (LABEL_SIM, LABEL_BOARD))
        name = "timeline_%s.png" % CLASSES[first[5]] if first else "timeline_normal.png"
        fig.savefig(os.path.join(R, name), facecolor=SURF)
        plt.close(fig)
        names.append(name)
    return names


def comparison(pc, fl_lo, fl_hi, limit):
    part = sorted(glob.glob(os.path.join(B, "dfx_diag", "*_partial.bit")))
    psize = os.path.getsize(part[0]) if part else None
    smoke = os.path.join(B, "dfx", "config_count_pblock_rm_partial.bit")
    ssize = os.path.getsize(smoke) if os.path.exists(smoke) else None
    md = ["# Comparison with published work", "",
          "Our numbers are labelled with how they were obtained. Published numbers are quoted from the "
          "source named in each row. Different rows measure different things; the last column says how they relate.", "",
          "| Work | Platform | What is measured | Number | How it relates to ours |", "| --- | --- | --- | --- | --- |",
          "| This project, detection | ZedBoard XC7Z020 PL, 100 MHz | Detector (learned depth-3 tree, 4 window counts) on Coimbra test captures | "
          "F1 ping 1.000, SYN 0.999, Modbus 0.955; alarm after 200 to 300 ms; 0 false alarms on the 1 h clean capture | "
          "results/detection_metrics.md; per 100 ms window |",
          "| This project, throughput | ZedBoard XC7Z020 PL, 100 MHz | Records per second with sketch D = 1 to 8 | "
          "%.1f to %.1f million records/s at every D (%s; timing met in %s; %s) | results/why_fpga.md |" % (min(fl_lo), max(fl_hi), LABEL_SIM, LABEL_VIV, LABEL_BOARD),
          "| This project, PC baseline | Intel i7-13620H | Same sketch in C | %.0f to %.0f million records/s for D = 1 to 8 | results/benchmark_pc.txt |" % (pc[0], pc[-1]),
          "| This project, swap | ZedBoard, PCAP | Partial bitstream for one Diagnoser | %s bytes, about %.2f ms (%s) | build/dfx_diag/ |"
          % ("{:,}".format(psize) if psize else "-", psize / 128e6 * 1e3 if psize else 0, LABEL_SWAP),
          "| This project, smoke test swap | ZedBoard, PCAP | Partial bitstream, 20-column region | %s bytes, about %.2f ms (%s) | build/dfx/ |"
          % ("{:,}".format(ssize) if ssize else "-", ssize / 128e6 * 1e3 if ssize else 0, LABEL_SWAP),
          "| This project, zero loss | Simulation | Hold FIFO 16,384, swap at first alarm | 0 drops up to %.2f million records/s (%s) | results/zero_loss.md |" % (limit, LABEL_SIM),
          "| Frazao et al., CRITIS 2018, and Frazao dissertation (Univ. of Coimbra) | MATLAB, offline | kNN, DT, RF, SVM, NB, NN on the same Coimbra captures, accuracy and F1 per capture | "
          "Decision Tree best; kNN on the ping flood 63.33 % accuracy, 73.58 % F1 (k = 1, euclidean, dissertation Table 5.1); Modbus query flood 'unusually good' for all classifiers, traced to 'a field with little variance during the attack' | "
          "Same dataset and attacks; offline, per-trace features; we classify 100 ms windows in hardware with 4 counts. Not a like-for-like score |",
          "| Xilinx XAPP1159 | Zynq-7000 | Partial reconfiguration through PCAP | 134,392 bytes in 1,060 us (about 127 MB/s) | Measured on hardware; our swap estimate uses the same order of throughput |",
          "| ZyCAP (Vipin and Fahmy) | Zynq-7000 | PCAP reconfiguration throughput | 128 MB/s | Rate used for our swap predictions |",
          "| Thinh et al. 2016 | Zynq | Partial reconfiguration time | about 82 ms for 822 KB | Slower controller; shows the spread of swap times |",
          "| Le Jeune et al., ACNS 2021 workshops (LNCS 12726) | Pynq-Z2, XC7Z020-1CLG400C (same chip family), 100 MHz | Quantized CNN intrusion detection (FINN), CICIDS2017 | "
          "about 2,400 frames/s, 22.44 Mbps supported; 24,635 LUT (46.31 %), 27,450 FF, 37.5 BRAM; 2-bit accuracy 99.41 % | "
          "Different task and dataset; deep model uses about half the LUTs of the same chip, while our detector and sketch fit in a few percent |",
          "| Line rates | Ethernet | Worst case, 64-byte frames | 1 GbE 1.488, 10 GbE 14.88 million packets/s | Reference lines in why_fpga.png and zero_loss.png |",
          "", "Sources: Frazao dissertation, estudogeral.uc.pt handle 10316/86748 (Chapter 5); Le Jeune, Goedeme, Mentens, "
          "DOI 10.1007/978-3-030-81645-2_9 (open copy on KU Leuven Lirias), Table 2, Table 3 and Sect. 5; "
          "XAPP1159, ZyCAP and Thinh et al. figures as given in the project plan."]
    open(os.path.join(R, "comparison.md"), "w").write("\n".join(md) + "\n")


if __name__ == "__main__":
    pc, lo, hi = why_fpga()
    lim = zero_loss()
    names = timelines()
    comparison(pc, lo, hi, lim)
    print("wrote results/why_fpga.png results/zero_loss.png", " ".join("results/" + n for n in names), "results/comparison.md")
