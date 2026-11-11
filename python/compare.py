"""Check simulator or C output against the Python golden model.

Usage:
    python3 python/compare.py sim     # after the Verilog testbench
    python3 python/compare.py host    # after the C baseline on the PC
    python3 python/compare.py board   # after pasting the ARM UART summary into build/board_summary.txt

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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
