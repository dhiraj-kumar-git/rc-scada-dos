"""Step 3: build the on-chip replay memory and the golden expected outputs.

Usage:
    python3 python/make_demo.py config.json

Uses the "demo" list in the config (up to 4 regions, chosen on the board with
switches SW1..SW0). For each region it takes a slice of one capture:
  - attack capture: starts lead_s seconds before the first attack packet
  - normal capture: starts at start_s (default 0)
and keeps at most max_records records.

Writes:
    rtl/records.mem         64-bit records, one hex word per line ($readmemh)
    rtl/regions.vh          start address and length of each region
    c/records.h             the same records for the ARM baseline
    build/expected_r<i>.txt golden window outputs per region
    build/expected_summary.txt  one summary line per region
    build/expected_leds.txt     LD7..LD0 after each run, as the testbench prints them
    build/expected_sketch_d<D>_r<i>.txt  sketch golden output per window, D = 1, 2, 4, 8
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (CLASSES, PERSIST, SK_DEPTHS, TICK_US, TS_BITS, WINDOW_TICKS,  # noqa: E402
                    RM_NAMES, format_sketch, format_window, format_word, load_rules, pack,
                    rm_words, run_detector, run_sketch,
                    summary_line, window_counts)

N_REGIONS = 4


def main(cfg_path):
    with open(cfg_path) as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(cfg_path))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules = load_rules(os.path.join(base, "build", "rules.json"))
    demo = cfg["demo"]
    if not 1 <= len(demo) <= N_REGIONS:
        raise SystemExit("demo must list 1 to 4 regions")

    words, regions, summaries, led_lines = [], [], [], []
    for i, d in enumerate(demo):
        rec = np.load(os.path.join(base, "build", "records", d["capture"] + ".npz"))
        ts_us, kind, src, att = rec["ts_us"], rec["kind"], rec["src"], rec["is_attack"]
        if att.any():
            t0 = max(0, int(ts_us[att][0]) - int(d.get("lead_s", 3.0) * 1e6))
        else:
            t0 = int(d.get("start_s", 0.0) * 1e6)
        sel = np.where(ts_us >= t0)[0][: int(d.get("max_records", 8192))]
        if len(sel) == 0:
            raise SystemExit("region %d: no records after start time" % i)
        ticks = (ts_us[sel] - t0) // TICK_US
        if ticks[-1] >= (1 << TS_BITS):
            raise SystemExit("region %d: slice longer than %d ticks" % (i, 1 << TS_BITS))
        start = len(words)
        words += [pack(int(t), int(k), int(s)) for t, k, s in zip(ticks, kind[sel], src[sel])]
        regions.append((start, len(sel)))

        counts = window_counts(ticks, kind[sel])
        out = run_detector(rules, counts)
        for m in RM_NAMES:
            dec, diag = rm_words(m, rules, ticks, kind[sel], src[sel])
            for tag, wl in (("dec", dec), ("diag", diag)):
                with open(os.path.join(base, "build", "expected_mod%d_r%d_%s.txt" % (m, i, tag)), "w") as f:
                    f.write("".join(format_word(w) + "\n" for w in wl))
        for dd in SK_DEPTHS:
            sk = run_sketch(ticks, src[sel], dd)
            with open(os.path.join(base, "build", "expected_sketch_d%d_r%d.txt" % (dd, i)), "w") as f:
                f.write("\n".join(format_sketch(o) for o in sk) + "\n")
        with open(os.path.join(base, "build", "expected_r%d.txt" % i), "w") as f:
            f.write("\n".join(format_window(o) for o in out) + "\n")
        line = summary_line(i, out)
        first = next((o for o in out if o[6] == 1), None)
        leds = ("expected LEDs: LD2 alarm=%d, LD3 network=%d, LD4 application=%d, first class=%s"
                % (1 if first else 0, 1 if first and first[7] == 1 else 0,
                   1 if first and first[7] == 2 else 0, CLASSES[first[5]] if first else "none"))
        summaries.append(line)
        bits = (1 << 1)
        if first:
            bits |= (1 << 2) | ((1 << 3) if first[7] == 1 else 0) | ((1 << 4) if first[7] == 2 else 0)
            bits |= (1 << (4 + first[5])) if first[5] in (1, 2, 3) else 0
        led_lines.append("region=%d leds=%s" % (i, format(bits, "08b")))
        n_att_win = len({int(t) // WINDOW_TICKS for t in ticks[att[sel]]})
        print("%s | capture=%s records=%d windows=%d attack_windows=%d | %s"
              % (line, d["capture"], len(sel), len(out), n_att_win, leds))
        if att.any() and n_att_win < PERSIST + 2:
            print("  WARNING: only %d attack windows fit in this region; raise max_records "
                  "or lower lead_s" % n_att_win)
        if att.any() and first is None:
            print("  WARNING: attack region but the learned rules never raise an alarm here")

    depth = int(cfg.get("bram_depth", 32768))
    if len(words) > depth:
        raise SystemExit("%d records do not fit in bram_depth %d" % (len(words), depth))
    with open(os.path.join(root, "rtl", "records.mem"), "w") as f:
        f.write("\n".join("%016x" % w for w in words + [0] * (depth - len(words))) + "\n")
    with open(os.path.join(root, "rtl", "regions.vh"), "w") as f:
        f.write("// GENERATED by python/make_demo.py. Do not edit by hand.\n")
        f.write("localparam integer BRAM_DEPTH = %d;\n" % depth)
        for i in range(N_REGIONS):
            s, n = regions[i] if i < len(regions) else (0, 0)
            f.write("localparam [31:0] R%d_START = %d;\nlocalparam [31:0] R%d_LEN = %d;\n" % (i, s, i, n))
    with open(os.path.join(root, "c", "records.h"), "w") as f:
        f.write("/* GENERATED by python/make_demo.py. Do not edit by hand. */\n")
        f.write("#ifndef RECORDS_H\n#define RECORDS_H\n#include <stdint.h>\n")
        f.write("#define N_REGIONS %d\n" % len(regions))
        f.write("static const uint32_t REGION_START[N_REGIONS] = {%s};\n" % ", ".join(str(r[0]) for r in regions))
        f.write("static const uint32_t REGION_LEN[N_REGIONS] = {%s};\n" % ", ".join(str(r[1]) for r in regions))
        f.write("static const uint64_t RECORDS[%d] = {\n" % len(words))
        for j in range(0, len(words), 4):
            f.write("    " + ", ".join("0x%016xULL" % w for w in words[j:j + 4]) + ",\n")
        f.write("};\n#endif\n")
    with open(os.path.join(base, "build", "expected_summary.txt"), "w") as f:
        f.write("\n".join(summaries) + "\n")
    with open(os.path.join(base, "build", "expected_leds.txt"), "w") as f:
        f.write("\n".join(led_lines) + "\n")
    print("wrote rtl/records.mem (%d records, depth %d), rtl/regions.vh, c/records.h" % (len(words), depth))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
