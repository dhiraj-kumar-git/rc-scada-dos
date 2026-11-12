"""E3: zero-loss sweep of load mode with a hold FIFO and a simulated swap.

Usage:
    python3 python/zero_loss.py config.json

Builds a 65,536-record slice of the ping flood test capture (from 1 s before the
attack; longer than the 16,384-entry hold FIFO, so overflow is possible), its
golden windows, then runs tb/tb_zero_loss.v (cycle-accurate simulation) at a
sweep of offered rates. Swap length S = round(partial bytes / 128e6 x 100e6)
clocks, from the Network Diagnoser partial bitstream (E2); if that file is
missing, XAPP1159's 1,060 us (S = 106,000) is used and labelled.

Done when: drops are 0 below the predicted limit H x 100e6 / S and above 0
beyond it, and every run with 0 drops has windows identical to the golden model.
Writes results/zero_loss.md and results/zero_loss.csv.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (TICK_US, TS_BITS, format_window, load_rules, pack, run_detector,  # noqa: E402
                    window_counts)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
R = os.path.join(ROOT, "results")
N = 65536
H = 16384
CLK = 100e6
PCAP = 128e6
PARTIAL = os.path.join(B, "dfx_diag", "config_net_diag_pblock_rm_partial.bit")


def make_slice(cfg_path):
    cfg = json.load(open(cfg_path))
    cap = next(d["capture"] for d in cfg["demo"] if d["capture"].startswith("ping"))
    rec = np.load(os.path.join(B, "records", cap + ".npz"))
    ts, kind, src, att = rec["ts_us"], rec["kind"], rec["src"], rec["is_attack"]
    t0 = max(0, int(ts[att][0]) - 1000000)
    sel = np.where(ts >= t0)[0][:N]
    ticks = (ts[sel] - t0) // TICK_US
    assert ticks[-1] < (1 << TS_BITS)
    with open(os.path.join(B, "e3_records.mem"), "w") as f:
        f.write("".join("%016x\n" % pack(int(t), int(k), int(s)) for t, k, s in zip(ticks, kind[sel], src[sel])))
    with open(os.path.join(B, "e3_n.vh"), "w") as f:
        f.write("localparam integer E3_N = %d;\n" % len(sel))
    rules = load_rules(os.path.join(B, "rules.json"))
    exp = [format_window(o) for o in run_detector(rules, window_counts(ticks, kind[sel]))]
    return cap, len(sel), exp


def run(rate, swap):
    q = min(1 << 24, int(round(rate / CLK * (1 << 24))))
    out = subprocess.run(["vvp", "-n", os.path.join(B, "tb_zero_loss.vvp"), "+rate_q24=%d" % q,
                          "+depth=%d" % H, "+swap=%d" % swap], cwd=ROOT, capture_output=True, text=True).stdout
    m = re.search(r"RESULT .*offered=(\d+) drops=(\d+) max_level=(\d+) swap_start=(-?\d+) cycles=(\d+)", out)
    if not m:
        raise SystemExit("simulation failed:\n" + out)
    offered, drops, max_level, swap_start, cycles = map(int, m.groups())
    act = [ln.strip() for ln in open(os.path.join(B, "e3_windows.txt")) if ln.strip()]
    return dict(rate=q / (1 << 24) * CLK, drops=drops, max_level=max_level, swap_start=swap_start,
                cycles=cycles, offered=offered, act=act)


def main(cfg_path):
    cap, n, exp = make_slice(cfg_path)
    subprocess.run(["iverilog", "-g2005", "-I", "rtl", "-I", "build", "-o", os.path.join(B, "tb_zero_loss.vvp"),
                    "tb/tb_zero_loss.v", "rtl/detector.v"], cwd=ROOT, check=True)
    if os.path.exists(PARTIAL):
        pbytes = os.path.getsize(PARTIAL)
        s_src = "Network Diagnoser partial bitstream, %d bytes (E2), at 128 MB/s (PCAP, ZyCAP)" % pbytes
        swap = int(round(pbytes / PCAP * CLK))
    else:
        swap = 106000
        s_src = "XAPP1159 measured swap time 1,060 us (E2 partial size not available)"
    limit = H * CLK / swap
    rates = sorted({1.488e6, 14.88e6, 100e6} | {round(f * limit) for f in (0.5, 0.9, 0.97, 0.99, 1.01, 1.03, 1.1, 2.0)})
    rows, ok = [], True
    base = run(100e6, 0)
    base_ok = base["drops"] == 0 and base["act"] == exp
    ok &= base_ok
    for rate in rates:
        r = run(rate, swap)
        same = r["act"] == exp
        below = r["rate"] < limit
        expect_drops = not below
        good = (r["drops"] == 0) if below else (r["drops"] > 0)
        if r["drops"] == 0 and not same:
            good = False          # zero loss must give identical windows: anything else is a bug
        ok &= good
        rows.append((r, same, below, good))
    md = ["# Zero-loss sweep: load mode with hold FIFO and simulated swap", "",
          "Cycle-accurate simulation (tb/tb_zero_loss.v, Detector RTL); not yet measured on the board.", "",
          "- Traffic: %d records of the %s test capture, from 1 s before the attack." % (n, cap),
          "- Hold FIFO depth H = %d records. Swap starts at the first alarm; consumer stopped for S = %d clocks (%.3f ms)."
          % (H, swap, swap / CLK * 1e3),
          "- S from: %s; predicted from partial bitstream size." % s_src,
          "- Predicted limit H x 100e6 / S = %.3f million records/s." % (limit / 1e6),
          "- Reference: 1 GbE worst case 1.488, 10 GbE worst case 14.88 million packets/s.", "",
          "Baseline (100 million records/s offered, no swap): drops %d, windows identical to golden: %s."
          % (base["drops"], "yes" if base_ok else "NO"), "",
          "| offered, million records/s | relative to limit | dropped records | max FIFO level | windows identical to golden | check |",
          "| --- | --- | --- | --- | --- | --- |"]
    csv = ["offered_mrps,dropped,max_level,identical,limit_mrps"]
    for r, same, below, good in rows:
        md.append("| %.3f | %.2f | %d | %d | %s | %s |" % (r["rate"] / 1e6, r["rate"] / limit, r["drops"], r["max_level"],
                                                       "yes" if same else ("no (records dropped)" if r["drops"] else "NO"),
                                                       "PASS" if good else "FAIL"))
        csv.append("%.6f,%d,%d,%d,%.6f" % (r["rate"] / 1e6, r["drops"], r["max_level"], int(same), limit / 1e6))
    md += ["", "RESULT: %s" % ("PASS" if ok else "FAIL")]
    open(os.path.join(R, "zero_loss.md"), "w").write("\n".join(md) + "\n")
    open(os.path.join(R, "zero_loss.csv"), "w").write("\n".join(csv) + "\n")
    print("\n".join(md))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
