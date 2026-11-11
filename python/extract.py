"""Step 1: turn each pcap in the config into a records file and a source report.

Usage:
    python3 python/extract.py config.json

For every capture it writes build/records/<name>.npz with:
    ts_us      int64   microseconds since the first packet of that capture
    kind       uint8   kind code from common.py
    src        uint32  IPv4 source (0 for non-IPv4 frames)
    is_attack  bool    labelling rule, see below

Labelling rule (deterministic, printed in the report so a person can check it):
    "known hosts" = every IPv4 source seen in the captures whose scenario is
    "normal". In an attack capture, a packet is an attack packet if its source
    is not a known host. If the config gives "attacker_ip" for a capture, the
    rule becomes: attack packet = source equals that IP.

It also writes build/source_report.md: per capture, the number of packets of
each kind, the number of distinct sources, the number of distinct unknown
sources, and the top 10 sources. Read it before training: it tells you whether
the floods come from one machine or from many (spoofed) addresses.
"""

import collections
import json
import os
import socket
import struct
import sys

import dpkt
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (KIND_ICMP_ECHO, KIND_MODBUS_REQ, KIND_NAMES, KIND_OTHER,  # noqa: E402
                    KIND_TCP_SYN)


def ip_to_int(b):
    return struct.unpack("!I", b)[0]


def int_to_ip(i):
    return socket.inet_ntoa(struct.pack("!I", int(i)))


def open_reader(f):
    try:
        return dpkt.pcap.Reader(f)
    except ValueError:
        f.seek(0)
        return dpkt.pcapng.Reader(f)


def classify_packet(buf, linktype):
    """Return (kind, src) for one frame."""
    try:
        if linktype == dpkt.pcap.DLT_LINUX_SLL:
            l2 = dpkt.sll.SLL(buf)
        else:
            l2 = dpkt.ethernet.Ethernet(buf)
    except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
        return KIND_OTHER, 0
    ip = l2.data
    if not isinstance(ip, dpkt.ip.IP):
        return KIND_OTHER, 0
    src = ip_to_int(ip.src)
    l4 = ip.data
    if isinstance(l4, dpkt.icmp.ICMP):
        return (KIND_ICMP_ECHO if l4.type == 8 else KIND_OTHER), src
    if isinstance(l4, dpkt.tcp.TCP):
        syn = bool(l4.flags & dpkt.tcp.TH_SYN)
        ack = bool(l4.flags & dpkt.tcp.TH_ACK)
        if syn and not ack:
            return KIND_TCP_SYN, src
        if l4.dport == 502 and len(l4.data) > 0:
            return KIND_MODBUS_REQ, src
    return KIND_OTHER, src


def read_capture(path):
    ts, kinds, srcs = [], [], []
    with open(path, "rb") as f:
        reader = open_reader(f)
        linktype = reader.datalink() if hasattr(reader, "datalink") else dpkt.pcap.DLT_EN10MB
        for t, buf in reader:
            k, s = classify_packet(buf, linktype)
            ts.append(t)
            kinds.append(k)
            srcs.append(s)
    if not ts:
        raise SystemExit("no packets in %s" % path)
    t0 = ts[0]
    ts_us = np.array([int(round((t - t0) * 1e6)) for t in ts], dtype=np.int64)
    order = np.argsort(ts_us, kind="stable")   # captures are normally in order
    return ts_us[order], np.array(kinds, np.uint8)[order], np.array(srcs, np.uint32)[order]


def capture_name(entry):
    return entry.get("name") or os.path.splitext(os.path.basename(entry["file"]))[0]


def main(cfg_path):
    with open(cfg_path) as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(cfg_path))
    out_dir = os.path.join(base, "build", "records")
    os.makedirs(out_dir, exist_ok=True)

    loaded = {}
    for e in cfg["captures"]:
        path = os.path.join(base, e["file"])
        print("reading", path)
        loaded[capture_name(e)] = read_capture(path)

    known = set()
    for e in cfg["captures"]:
        if e["scenario"] == "normal":
            known.update(int(s) for s in np.unique(loaded[capture_name(e)][2]) if s != 0)

    lines = ["# Source report", "",
             "Known hosts (from normal captures): " + ", ".join(sorted(int_to_ip(k) for k in known)), ""]
    for e in cfg["captures"]:
        name = capture_name(e)
        ts_us, kinds, srcs = loaded[name]
        if e["scenario"] == "normal":
            is_attack = np.zeros(len(ts_us), bool)
            rule = "normal capture: no attack packets"
        elif e.get("attacker_ip"):
            a = ip_to_int(socket.inet_aton(e["attacker_ip"]))
            is_attack = srcs == a
            rule = "attack packet = source is %s (set in config)" % e["attacker_ip"]
        else:
            is_attack = np.array([int(s) != 0 and int(s) not in known for s in srcs], bool)
            rule = "attack packet = source not a known host"
        np.savez(os.path.join(out_dir, name + ".npz"), ts_us=ts_us, kind=kinds, src=srcs,
                 is_attack=is_attack)

        kc = collections.Counter(int(k) for k in kinds)
        sc = collections.Counter(int(s) for s in srcs if s != 0)
        unknown = [s for s in sc if s not in known]
        att_ts = ts_us[is_attack]
        lines += ["## %s (scenario: %s, split: %s)" % (name, e["scenario"], e.get("split", "-")), "",
                  "- packets: %d, duration: %.1f s" % (len(ts_us), ts_us[-1] / 1e6),
                  "- kinds: " + ", ".join("%s %d" % (KIND_NAMES[k], kc.get(k, 0)) for k in range(4)),
                  "- distinct sources: %d, of which not known hosts: %d" % (len(sc), len(unknown)),
                  "- labelling rule: " + rule,
                  "- attack packets: %d" % int(is_attack.sum())]
        if len(att_ts):
            lines.append("- attack interval: %.3f s to %.3f s" % (att_ts[0] / 1e6, att_ts[-1] / 1e6))
        lines += ["", "| source | packets | known host |", "| --- | --- | --- |"]
        for s, n in sc.most_common(10):
            lines.append("| %s | %d | %s |" % (int_to_ip(s), n, "yes" if s in known else "no"))
        lines.append("")
        print("  %s: %d packets, %d distinct sources (%d unknown), %d attack packets"
              % (name, len(ts_us), len(sc), len(unknown), int(is_attack.sum())))

    report = os.path.join(base, "build", "source_report.md")
    with open(report, "w") as f:
        f.write("\n".join(lines))
    print("wrote", report)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
