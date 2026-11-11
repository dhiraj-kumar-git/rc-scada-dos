"""Make SMALL SYNTHETIC pcaps to test the toolchain end to end.

These are NOT results and must never be shown as results. They only prove
that extract -> train -> demo memory -> Verilog sim -> C baseline all agree.
Real numbers come from the Coimbra captures (config.json).

Usage (from repo root):
    python3 tests/make_fixture.py
Writes data_fixture/*.pcap and config_fixture.json.
"""

import json
import os
import random
import socket

import dpkt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data_fixture")
PLC, HMI, NTP, ATTACKER = "10.0.0.10", "10.0.0.20", "10.0.0.30", "10.0.0.66"


def eth(ip):
    return dpkt.ethernet.Ethernet(src=b"\x02\x00\x00\x00\x00\x01", dst=b"\x02\x00\x00\x00\x00\x02",
                                  type=dpkt.ethernet.ETH_TYPE_IP, data=ip)


def ipv4(src, dst, p, data):
    return dpkt.ip.IP(src=socket.inet_aton(src), dst=socket.inet_aton(dst), p=p, ttl=64, data=data)


def modbus_req(tid):
    return tid.to_bytes(2, "big") + b"\x00\x00\x00\x06\x01\x03\x00\x00\x00\x0a"


def normal_traffic(rng, dur):
    pk = []
    t, tid = 0.0, 0
    while t < dur:                       # HMI polls the PLC about 10 times per second
        tid = (tid + 1) & 0xFFFF
        req = dpkt.tcp.TCP(sport=40000, dport=502, flags=dpkt.tcp.TH_ACK | dpkt.tcp.TH_PUSH,
                           data=modbus_req(tid))
        pk.append((t, eth(ipv4(HMI, PLC, dpkt.ip.IP_PROTO_TCP, req))))
        rsp = dpkt.tcp.TCP(sport=502, dport=40000, flags=dpkt.tcp.TH_ACK | dpkt.tcp.TH_PUSH,
                           data=b"\x00" * 29)
        pk.append((t + 0.002, eth(ipv4(PLC, HMI, dpkt.ip.IP_PROTO_TCP, rsp))))
        t += 0.1 + rng.uniform(-0.01, 0.01)
    t = 0.0
    while t < dur:                       # background UDP
        pk.append((t, eth(ipv4(NTP, HMI, dpkt.ip.IP_PROTO_UDP, dpkt.udp.UDP(sport=123, dport=123, data=b"x" * 48)))))
        t += 0.5
    t = 1.0
    while t < dur:                       # occasional legitimate ping
        pk.append((t, eth(ipv4(HMI, PLC, dpkt.ip.IP_PROTO_ICMP,
                                dpkt.icmp.ICMP(type=8, data=dpkt.icmp.ICMP.Echo(id=1, seq=1, data=b"p" * 32))))))
        t += 5.0
    return pk


def rand_ip(rng):
    return "%d.%d.%d.%d" % (rng.randint(1, 223), rng.randint(0, 255), rng.randint(0, 255), rng.randint(1, 254))


def attack(rng, kind, t0, t1, rate):
    pk = []
    t = t0
    while t < t1:
        if kind == "ping_flood":
            pk.append((t, eth(ipv4(rand_ip(rng), PLC, dpkt.ip.IP_PROTO_ICMP,
                                   dpkt.icmp.ICMP(type=8, data=dpkt.icmp.ICMP.Echo(id=2, seq=1, data=b""))))))
        elif kind == "syn_flood":
            pk.append((t, eth(ipv4(rand_ip(rng), PLC, dpkt.ip.IP_PROTO_TCP,
                                   dpkt.tcp.TCP(sport=rng.randint(1024, 65535), dport=502, flags=dpkt.tcp.TH_SYN)))))
        else:
            req = dpkt.tcp.TCP(sport=41000, dport=502, flags=dpkt.tcp.TH_ACK | dpkt.tcp.TH_PUSH,
                               data=modbus_req(rng.randint(0, 65535)))
            pk.append((t, eth(ipv4(ATTACKER, PLC, dpkt.ip.IP_PROTO_TCP, req))))
        t += rng.expovariate(rate)
    return pk


def write(path, pk):
    pk.sort(key=lambda x: x[0])
    with open(path, "wb") as f:
        w = dpkt.pcap.Writer(f)
        for t, p in pk:
            w.writepkt(bytes(p), ts=1_600_000_000 + t)


def main():
    os.makedirs(OUT, exist_ok=True)
    caps = []
    for split, seed in (("train", 1), ("test", 2)):
        rng = random.Random(seed)
        name = "fixture-normal-%s" % split
        write(os.path.join(OUT, name + ".pcap"), normal_traffic(rng, 60))
        caps.append({"file": "data_fixture/%s.pcap" % name, "scenario": "normal", "split": split})
        for kind, rate in (("ping_flood", 2000), ("syn_flood", 2000), ("modbus_flood", 300)):
            name = "fixture-%s-%s" % (kind, split)
            write(os.path.join(OUT, name + ".pcap"), normal_traffic(rng, 60) + attack(rng, kind, 30, 40, rate))
            caps.append({"file": "data_fixture/%s.pcap" % name, "scenario": kind, "split": split})
    cfg = {"_note": "SYNTHETIC FIXTURE. Tests the toolchain only. Not results.",
           "captures": caps,
           "bram_depth": 32768,
           "demo": [{"capture": "fixture-normal-test", "start_s": 0, "max_records": 8192},
                    {"capture": "fixture-ping_flood-test", "lead_s": 3, "max_records": 8192},
                    {"capture": "fixture-syn_flood-test", "lead_s": 3, "max_records": 8192},
                    {"capture": "fixture-modbus_flood-test", "lead_s": 3, "max_records": 8192}]}
    with open(os.path.join(ROOT, "config_fixture.json"), "w") as f:
        json.dump(cfg, f, indent=1)
    print("wrote", OUT, "and config_fixture.json")


if __name__ == "__main__":
    main()
