"""E1 result table: records per second versus sketch depth D, PC and FPGA.

Reads only files written by the checks:
    results/benchmark_pc.txt     make bench (PC)
    build/sketch_sim_d<D>.txt    make sketch (cycle-accurate simulation, records per cycle)
    results/sketch_sweep.txt     scripts/sketch_sweep.tcl (Vivado implementation at 100 MHz)
Writes results/why_fpga.md. FPGA records/s = 100e6 x records per cycle, only
where timing is met. Reference lines: 1 GbE and 10 GbE worst case (minimum
size frames), 1.488 and 14.88 million packets per second.
"""
import os
import re
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")
B = os.path.join(ROOT, "build")
GBE1, GBE10 = 1.488, 14.88


def pc_rates():
    runs = {}
    for ln in open(os.path.join(R, "benchmark_pc.txt")):
        m = re.match(r"pc d=(\d+) records_per_s=(\d+)", ln)
        if m:
            runs.setdefault(int(m.group(1)), []).append(int(m.group(2)) / 1e6)
    return runs


def fpga_rpc(d):
    path = os.path.join(B, "sketch_sim_d%d.txt" % d)
    if not os.path.exists(path):
        return None
    vals = {}
    for ln in open(path):
        m = re.match(r"region=(\d+) .*records_per_cycle=([0-9.]+)", ln)
        if m:
            vals[int(m.group(1))] = float(m.group(2))
    return vals


def sweep():
    out = {}
    p = os.path.join(R, "sketch_sweep.txt")
    if os.path.exists(p):
        for ln in open(p):
            if ln.startswith("#") or not ln.strip():
                continue
            d, wns, luts, ffs, b36, b18, dsp, ok = ln.split()
            out[int(d)] = dict(wns=float(wns), luts=int(luts), ffs=int(ffs), b36=int(b36),
                               b18=int(b18), dsp=int(dsp), ok=ok)
    return out


def main():
    pc, sw = pc_rates(), sweep()
    md = ["# Why FPGA: records per second versus sketch depth D", "",
          "PC: `make bench` (results/benchmark_pc.txt), median and min to max of 3 runs, synthetic records.",
          "FPGA: 100 MHz x records per cycle from cycle-accurate simulation of the demo regions "
          "(build/sketch_sim_d<D>.txt), shown only where Vivado implementation at 100 MHz meets timing "
          "(results/sketch_sweep.txt). Not yet measured on the board. ARM: lab session.", "",
          "| D (sketch rows) | PC, million records/s | FPGA flood regions, million records/s | FPGA clean region, million records/s | Vivado WNS at 10 ns | ARM |",
          "| --- | --- | --- | --- | --- | --- |"]
    for d in (0, 1, 2, 4, 8):
        v = pc.get(d)
        pcs = "%.0f (%.0f to %.0f)" % (statistics.median(v), min(v), max(v)) if v else "-"
        if d == 0:
            md.append("| 0 (plain counting) | %s | 94.6 to 98.5 (Detector only, M1 simulation) | 66.7 | +2.890 ns (full M1 design) | lab session |" % pcs)
            continue
        rpc, s = fpga_rpc(d), sw.get(d)
        if rpc is None or s is None:
            fl = fc = "not run"
            wns = "-"
        else:
            wns = "%+.3f ns (%s)" % (s["wns"], s["ok"])
            if s["ok"] == "met":
                flood = [rpc[i] * 100 for i in (1, 2, 3) if i in rpc]
                fl = "%.1f to %.1f" % (min(flood), max(flood))
                fc = "%.1f" % (rpc[0] * 100) if 0 in rpc else "-"
            else:
                fl = fc = "timing not met"
        md.append("| %d | %s | %s | %s | %s | lab session |" % (d, pcs, fl, fc, wns))
    md += ["", "Reference: 1 GbE worst case %.3f and 10 GbE worst case %.2f million packets/s "
           "(64-byte frames plus preamble and gap)." % (GBE1, GBE10), "",
           "## Sketch resources (Vivado implementation at 100 MHz, sketch alone, out of context)", "",
           "| D | WNS | LUTs | FFs | RAMB36 | RAMB18 | DSP48 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in (1, 2, 4, 8):
        s = sw.get(d)
        if s:
            md.append("| %d | %+.3f ns (%s) | %d | %d | %d | %d | %d |" % (d, s["wns"], s["ok"], s["luts"], s["ffs"],
                                                                    s["b36"], s["b18"], s["dsp"]))
    open(os.path.join(R, "why_fpga.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
