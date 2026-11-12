"""Synthetic test vectors for the sketch (toolchain check only, not results).

Exercises the cases a pipelined hardware sketch can get wrong: the same source
back to back, alternating sources, near back-to-back repeats, two sources that
share a cell, src = 0 records, 16-bit saturation, empty windows, and idle
clocks between records.

Writes:
    build/sketch_vec.mem              one 72-bit word per record: [71:64] idle clocks before it, [63:0] record
    build/sketch_vec_n.vh             number of records
    build/expected_sketch_vec_d<D>.txt  golden output for D = 1, 2, 4, 8
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from common import SK_DEPTHS, format_sketch, pack, run_sketch, sk_hash  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
os.makedirs(B, exist_ok=True)
rng = random.Random(2026)

A, Bs, C = 0x0A000001, 0xC0A80105, 0xAC1BE032
# two different sources that land in the same row-0 cell
base_h = sk_hash(A, 0)
COLL = next(s for s in range(0x0B000000, 0x0C000000) if s != A and sk_hash(s, 0) == base_h)

recs = []   # (tick, src, gap)


def add(win, srcs, gap=0, spread=True):
    n = len(srcs)
    for k, s in enumerate(srcs):
        t = win * 1000 + ((k * 999) // max(n, 1) if spread else 0)
        recs.append((t, s, gap() if callable(gap) else gap))


add(0, [A] * 3000)                                   # same source, back to back
add(1, [A, Bs] * 1500)                               # alternating
add(2, [A, A, Bs, Bs] * 500 + [A, Bs, C] * 500)      # near back-to-back repeats
add(3, [A, COLL] * 800 + [COLL] * 50)                # different sources, same row-0 cell
add(4, [A, 0, Bs, 0, 0, A] * 300)                    # src = 0 must not update
add(6, [rng.getrandbits(32) | 1 for _ in range(3000)])   # many sources: distinct count, collisions (window 5 empty)
add(7, [A, Bs, A] * 600, gap=lambda: rng.choice([0, 0, 1, 2, 3]))   # idle clocks between records
add(9, [C] * 70000, spread=False)                    # saturates 16-bit cells at 65535
add(10, [Bs] * 5 + [C] * 3)                          # after saturation: fresh window starts at 1
add(12, [0, 0, 0])                                   # window with only src = 0

with open(os.path.join(B, "sketch_vec.mem"), "w") as f:
    for t, s, gap in recs:
        f.write("%02x%016x\n" % (gap, pack(t, 0, s)))
with open(os.path.join(B, "sketch_vec_n.vh"), "w") as f:
    f.write("localparam integer NVEC = %d;\n" % len(recs))
ticks = [t for t, _, _ in recs]
srcs = [s for _, s, _ in recs]
for d in SK_DEPTHS:
    with open(os.path.join(B, "expected_sketch_vec_d%d.txt" % d), "w") as f:
        f.write("\n".join(format_sketch(o) for o in run_sketch(ticks, srcs, d)) + "\n")
print("sketch vectors: %d records, collision source 0x%08x shares row-0 cell %d with 0x%08x"
      % (len(recs), COLL, base_h, A))
