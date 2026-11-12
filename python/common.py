"""Shared definitions for the RC SCADA DoS project.

Everything that Python, Verilog and C must agree on lives here, so there is
one source of truth. If you change a constant here, regenerate the Verilog
and C files with make_demo.py and train_rules.py.
"""

import json
import math

# ---------------------------------------------------------------- records
# One record = 64 bits:
#   [63:40] timestamp, 24 bits, in ticks of TICK_US microseconds, relative
#           to the start of the demo slice
#   [39:32] kind code (see below)
#   [31:0]  IPv4 source address
TICK_US = 100            # 1 tick = 100 us
WINDOW_TICKS = 1000      # 1 window = 1000 ticks = 100 ms
TS_BITS = 24             # max slice length = 2^24 ticks = about 1677 s

KIND_OTHER = 0
KIND_ICMP_ECHO = 1       # ICMP type 8 (echo request)
KIND_TCP_SYN = 2         # TCP with SYN set and ACK clear
KIND_MODBUS_REQ = 3      # TCP to port 502 carrying payload (a Modbus request)
KIND_NAMES = ["other", "icmp_echo", "tcp_syn", "modbus_req"]

# ---------------------------------------------------------------- classes
CLASSES = ["normal", "ping_flood", "syn_flood", "modbus_flood"]
CLASS_ID = {name: i for i, name in enumerate(CLASSES)}

# attack tree branches
BRANCH_NONE, BRANCH_NETWORK, BRANCH_APPLICATION = 0, 1, 2


def branch_of(cls):
    if cls == 0:
        return BRANCH_NONE
    if cls == CLASS_ID["modbus_flood"]:
        return BRANCH_APPLICATION
    return BRANCH_NETWORK


PERSIST = 3              # alarm needs this many attack windows in a row
CNT_MAX = 0xFFFF         # 16-bit saturating counters in hardware

# feature order used by the rules (Python, Verilog and C)
FEATURES = ["icmp", "syn", "modbus", "other"]


def pack(ts_tick, kind, src):
    assert 0 <= ts_tick < (1 << TS_BITS), "timestamp out of range"
    return (ts_tick << 40) | ((kind & 0xFF) << 32) | (src & 0xFFFFFFFF)


def unpack(word):
    return (word >> 40) & 0xFFFFFF, (word >> 32) & 0xFF, word & 0xFFFFFFFF


def window_counts(ts_ticks, kinds):
    """Per-window counts, exactly as the hardware produces them.

    Windows run from 0 to last_ts // WINDOW_TICKS, including empty ones.
    Returns a list of [icmp, syn, modbus, other] (saturated at CNT_MAX).
    """
    if len(ts_ticks) == 0:
        return []
    n_win = int(ts_ticks[-1]) // WINDOW_TICKS + 1
    counts = [[0, 0, 0, 0] for _ in range(n_win)]
    col = {KIND_ICMP_ECHO: 0, KIND_TCP_SYN: 1, KIND_MODBUS_REQ: 2}
    for t, k in zip(ts_ticks, kinds):
        w = int(t) // WINDOW_TICKS
        c = col.get(int(k), 3)
        if counts[w][c] < CNT_MAX:
            counts[w][c] += 1
    return counts


# ---------------------------------------------------------------- rules
def load_rules(path):
    with open(path) as f:
        return json.load(f)


def classify(rules, feats):
    """Walk the exported tree. feats = [icmp, syn, modbus, other] (ints)."""
    node = rules["nodes"][0]
    while "leaf" not in node:
        x = feats[node["feature"]]
        node = rules["nodes"][node["left"] if x <= node["threshold"] else node["right"]]
    return node["leaf"]


def run_detector(rules, counts):
    """Golden model of the hardware Detector.

    Returns one tuple per window:
    (idx, icmp, syn, modbus, other, cls, alarm, branch)
    """
    out = []
    run = 0
    for idx, f in enumerate(counts):
        cls = classify(rules, f)
        run = 0 if cls == 0 else min(run + 1, 3)
        alarm = 1 if run >= PERSIST else 0
        out.append((idx, f[0], f[1], f[2], f[3], cls, alarm, branch_of(cls)))
    return out


def summary_line(region, outputs):
    """One human-readable line that Python, C and Verilog all print."""
    alarm_windows = [o for o in outputs if o[6] == 1]
    first = alarm_windows[0] if alarm_windows else None
    return ("region=%d windows=%d alarm_windows=%d first_alarm=%d first_class=%d"
            % (region, len(outputs), len(alarm_windows),
               first[0] if first else -1, first[5] if first else -1))


def format_window(o):
    return " ".join(str(int(v)) for v in o)


def floor_threshold(t):
    """sklearn splits integer features at x.5; x <= 7.5 is x <= 7 for ints."""
    return int(math.floor(t))


# ---------------------------------------------------------------- sketch (E1)
# Count-min sketch and distinct-source counter, per 100 ms window.
# Python, Verilog (rtl/sketch.v) and C (c/sketch_bench.c) must match bit for bit.
SK_K = [2654435761, 2246822519, 3266489917, 668265263,
        374761393, 2869860233, 1597334677, 3812015801]   # one odd multiplier per row
SK_W = 1024              # cells per row (10-bit hash)
SK_DEPTHS = (1, 2, 4, 8)
SK_CNT_MAX = 0xFFFF      # 16-bit saturating cells
DISTINCT_XOR = 0x9E3779B9
DISTINCT_BITS = 1024


def sk_hash(src, r):
    """Row r hash: top 10 bits of (src * K[r]) mod 2^32."""
    return ((src * SK_K[r]) & 0xFFFFFFFF) >> 22


def distinct_bit(src):
    return (((src * SK_K[0]) & 0xFFFFFFFF) ^ DISTINCT_XOR) >> 22


def run_sketch(ts_ticks, srcs, d):
    """Golden model of the sketch. Returns one tuple per window that holds at
    least one record, in window order: (win, top_src, top_est, set_bits).

    Cells and the distinct table are logically zero at the start of every
    window. Only records with src != 0 update them. Per record: every row
    increments cell[r][h_r] (saturating); est = min of the incremented values;
    if est > top_est (strictly) then top_est = est and top_src = src.
    """
    assert d in SK_DEPTHS
    out = []
    cur = None
    cells = bits = None
    top_src = top_est = set_bits = 0
    for t, s in zip(ts_ticks, srcs):
        w = int(t) // WINDOW_TICKS
        s = int(s)
        if w != cur:
            if cur is not None:
                out.append((cur, top_src, top_est, set_bits))
            cur = w
            cells = [dict() for _ in range(d)]
            bits = set()
            top_src = top_est = set_bits = 0
        if s == 0:
            continue
        est = SK_CNT_MAX
        for r in range(d):
            h = sk_hash(s, r)
            v = min(cells[r].get(h, 0) + 1, SK_CNT_MAX)
            cells[r][h] = v
            est = min(est, v)
        if est > top_est:
            top_est, top_src = est, s
        b = distinct_bit(s)
        if b not in bits:
            bits.add(b)
            set_bits += 1
    if cur is not None:
        out.append((cur, top_src, top_est, set_bits))
    return out


def distinct_estimate(set_bits):
    """Linear-counting estimate of distinct sources from set bits (Python only).
    Returns None when the table is saturated (all bits set)."""
    if set_bits >= DISTINCT_BITS:
        return None
    return -DISTINCT_BITS * math.log((DISTINCT_BITS - set_bits) / DISTINCT_BITS)


def ddos_setbits_threshold(t):
    """Smallest set_bits whose distinct estimate is >= t (what hardware compares)."""
    for sb in range(DISTINCT_BITS + 1):
        n = distinct_estimate(sb)
        if n is None or n >= t:
            return sb
    return DISTINCT_BITS


def format_sketch(o):
    return " ".join(str(int(v)) for v in o)


# ---------------------------------------------------------------- DFX modules (E2)
# One reconfigurable partition (rm_slot) with a common interface. Every module
# emits 64-bit words on out_word:
#   decision word (one per window, every window):
#     [63:62] 0, [61:56] module id, [55:32] window, [31:30] class, [29] alarm,
#     [28:27] branch, [26:0] 0
#   diagnosis word (one per window holding records; Diagnoser modules only):
#     [63:62] 1, [61:47] window[14:0], [46:36] set_bits, [35] DDoS (set_bits >= DDOS_SETBITS),
#     [34:32] module id, [31:0] top source
RM_DETECTOR, RM_NET_DIAG, RM_MODBUS_DIAG = 1, 2, 3
RM_NAMES = {RM_DETECTOR: "rm_detector", RM_NET_DIAG: "rm_net_diag", RM_MODBUS_DIAG: "rm_modbus_diag"}
RM_SKETCH_D = {RM_DETECTOR: 0, RM_NET_DIAG: 4, RM_MODBUS_DIAG: 2}


def rm_words(module, rules, ticks, kinds, srcs):
    """Golden output of a DFX module: (decision words, diagnosis words), each in order."""
    dec = []
    for o in run_detector(rules, window_counts(ticks, kinds)):
        idx, cls, alarm, branch = o[0], o[5], o[6], o[7]
        dec.append((0 << 62) | (module << 56) | (idx << 32) | (cls << 30) | (alarm << 29) | (branch << 27))
    diag = []
    d = RM_SKETCH_D[module]
    if d:
        thr = rules.get("ddos_setbits", DISTINCT_BITS + 1)
        for w, top_src, _est, set_bits in run_sketch(ticks, srcs, d):
            ddos = 1 if set_bits >= thr else 0
            diag.append((1 << 62) | ((w & 0x7FFF) << 47) | (set_bits << 36) | (ddos << 35)
                        | (module << 32) | top_src)
    return dec, diag


def format_word(w):
    return "%016x" % w
