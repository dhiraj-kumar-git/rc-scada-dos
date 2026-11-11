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
