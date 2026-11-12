"""Check simulator or C output against the Python golden model.

Usage:
    python3 python/compare.py sim     # after the Verilog testbench
    python3 python/compare.py host    # after the C baseline on the PC
    python3 python/compare.py board   # after pasting the ARM UART summary into build/board_summary.txt
    python3 python/compare.py sketch        # sketch in simulation, D = 1, 2, 4, 8, every region
    python3 python/compare.py sketch-host   # C sketch on the PC, D = 1, 2, 4, 8, every region
    python3 python/compare.py sketch-vec    # sketch test vectors (back-to-back updates), D = 1, 2, 4, 8
    python3 python/compare.py modules       # DFX modules in the static top: decision and diagnosis words, LEDs

Compares build/<prefix>_r<i>.txt with build/expected_r<i>.txt line by line
(every window: counts, class, alarm, branch) and build/<prefix>_summary.txt
with build/expected_summary.txt. Exit code 0 only if everything matches.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")


def read(path):
    with open(path) as f:
        return [ln.strip() for ln in f if ln.strip()]


def main(prefix):
    ok = True
    for exp in sorted(glob.glob(os.path.join(B, "expected_r*.txt"))):
        i = re.search(r"expected_r(\d+)\.txt", exp).group(1)
        act = os.path.join(B, "%s_r%s.txt" % (prefix, i))
        if not os.path.exists(act):
            if prefix != "board":
                print("region %s: MISSING %s" % (i, act))
                ok = False
            continue
        e, a = read(exp), read(act)
        bad = [(n, x, y) for n, (x, y) in enumerate(zip(e, a)) if x != y]
        if len(e) != len(a) or bad:
            ok = False
            print("region %s: FAIL (%d expected windows, %d actual)" % (i, len(e), len(a)))
            for n, x, y in bad[:5]:
                print("  window %d expected '%s' got '%s'" % (n, x, y))
        else:
            print("region %s: PASS, %d windows identical" % (i, len(e)))
    es = read(os.path.join(B, "expected_summary.txt"))
    sp = os.path.join(B, "%s_summary.txt" % prefix)
    if os.path.exists(sp):
        acts = [ln for ln in read(sp) if ln.startswith("region=")]
        if acts == es:
            print("summary: PASS")
        else:
            ok = False
            print("summary: FAIL")
            for x, y in zip(es, acts):
                if x != y:
                    print("  expected '%s'\n  got      '%s'" % (x, y))
    else:
        ok = False
        print("summary: MISSING", sp)
    el = os.path.join(B, "expected_leds.txt")
    al = os.path.join(B, "%s_leds.txt" % prefix)
    if prefix == "sim" and os.path.exists(el):
        if os.path.exists(al) and read(al) == read(el):
            print("LEDs: PASS (LD7..LD0 after each run match the expected values)")
        else:
            ok = False
            print("LEDs: FAIL")
            if os.path.exists(al):
                for x, y in zip(read(el), read(al)):
                    if x != y:
                        print("  expected '%s'\n  got      '%s'" % (x, y))
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def main_sketch(mode):
    """Sketch outputs (win top_src top_est set_bits per window) against the golden model.
    Every depth D = 1, 2, 4, 8 must be present and identical."""
    prefix = {"sketch": "sim", "sketch-host": "host", "sketch-vec": "sim"}[mode]
    ok = True
    for d in (1, 2, 4, 8):
        if mode == "sketch-vec":
            pairs = [("vectors", os.path.join(B, "expected_sketch_vec_d%d.txt" % d),
                      os.path.join(B, "sim_sketch_vec_d%d.txt" % d))]
        else:
            exps = sorted(glob.glob(os.path.join(B, "expected_sketch_d%d_r*.txt" % d)))
            pairs = [("region " + re.search(r"_r(\d+)\.txt", e).group(1), e,
                      e.replace("expected_sketch", "%s_sketch" % prefix)) for e in exps]
            if not pairs:
                ok = False
                print("D=%d: MISSING expected files (run make demo)" % d)
        for name, exp, act in pairs:
            if not os.path.exists(act):
                ok = False
                print("D=%d %s: MISSING %s" % (d, name, os.path.relpath(act, ROOT)))
                continue
            e, a = read(exp), read(act)
            bad = [(n, x, y) for n, (x, y) in enumerate(zip(e, a)) if x != y]
            if len(e) != len(a) or bad:
                ok = False
                print("D=%d %s: FAIL (%d expected windows, %d actual)" % (d, name, len(e), len(a)))
                for n, x, y in bad[:5]:
                    print("  line %d expected '%s' got '%s'" % (n, x, y))
            else:
                print("D=%d %s: PASS, %d windows identical" % (d, name, len(e)))
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def main_modules():
    """DFX modules (E2): decision and diagnosis words per region, and LEDs, for every module."""
    ok = True
    for m, name in ((1, "rm_detector"), (2, "rm_net_diag"), (3, "rm_modbus_diag")):
        for exp in sorted(glob.glob(os.path.join(B, "expected_mod%d_r*_*.txt" % m))):
            i, tag = re.search(r"_r(\d+)_(dec|diag)\.txt", exp).groups()
            act = os.path.join(B, "sim_rm%d_r%s_%s.txt" % (m, i, tag))
            if not os.path.exists(act):
                ok = False
                print("%s region %s %s: MISSING" % (name, i, tag))
                continue
            e, a = read(exp), read(act)
            if e != a:
                ok = False
                bad = [(n, x, y) for n, (x, y) in enumerate(zip(e, a)) if x != y]
                print("%s region %s %s: FAIL (%d expected words, %d actual)" % (name, i, tag, len(e), len(a)))
                for n, x, y in bad[:3]:
                    print("  word %d expected %s got %s" % (n, x, y))
            else:
                print("%s region %s %s: PASS, %d words identical" % (name, i, tag, len(e)))
        el, al = os.path.join(B, "expected_leds.txt"), os.path.join(B, "sim_rm%d_leds.txt" % m)
        if os.path.exists(al) and read(al) == read(el):
            print("%s LEDs: PASS" % name)
        else:
            ok = False
            print("%s LEDs: FAIL or MISSING" % name)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].startswith("sketch"):
        main_sketch(sys.argv[1])
    if len(sys.argv) == 2 and sys.argv[1] == "modules":
        main_modules()
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
