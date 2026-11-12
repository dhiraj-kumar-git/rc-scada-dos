#include <string.h>
#include "sketch_bench.h"

/* Same rules as run_sketch() in python/common.py and rtl/sketch.v:
 * cells hold a 16-bit saturating count and a 16-bit tag (window + 1), so a
 * cell is logically zero at the start of every window; only src != 0 updates;
 * est = min of the incremented cells; top source on strictly greater est;
 * distinct table: bit b = top 10 bits of ((src * K[0]) ^ 0x9E3779B9). */
static uint16_t cnt[SK_MAX_D][SK_W];
static uint16_t tag[SK_MAX_D][SK_W];
static uint16_t dtag[SK_W];
static const uint32_t K[SK_MAX_D] = {2654435761u, 2246822519u, 3266489917u, 668265263u,
                                     374761393u, 2869860233u, 1597334677u, 3812015801u};
#define DXOR 0x9E3779B9u

/* Core loop. Writes per-window outputs to out (if not NULL) and returns the
 * number of windows; *sink gets a value that depends on every update. */
static uint32_t core(const uint64_t *rec, uint32_t n, int d, sk_out_t *out, uint32_t max_out,
                     uint64_t *sink)
{
    uint32_t c[4] = {0, 0, 0, 0}, cur_end = 0, win = 0, nw = 0, i;
    uint32_t top_src = 0, top_est = 0, set_bits = 0;
    uint16_t t16 = 0;
    int have = 0, r;
    uint64_t s = 0;
    memset(tag, 0, sizeof tag);
    memset(dtag, 0, sizeof dtag);
    for (i = 0; i < n; i++) {
        uint32_t ts = (uint32_t)(rec[i] >> 40) & 0xFFFFFFu;
        uint32_t kind = (uint32_t)(rec[i] >> 32) & 0xFFu;
        uint32_t src = (uint32_t)rec[i];
        if (!have || ts >= cur_end) {
            if (have) {
                s += c[0] + c[1] + c[2] + c[3] + top_src + top_est + set_bits;
                if (out && nw < max_out) {
                    out[nw].win = win; out[nw].top_src = top_src;
                    out[nw].top_est = top_est; out[nw].set_bits = set_bits;
                }
                nw++;
            }
            win = ts / 1000u;
            cur_end = (win + 1u) * 1000u;
            t16 = (uint16_t)(win + 1u);
            c[0] = c[1] = c[2] = c[3] = 0;
            top_src = top_est = set_bits = 0;
            have = 1;
        }
        c[kind & 3]++;
        if (d > 0 && src != 0) {
            uint32_t est = 0xFFFFu, b;
            for (r = 0; r < d; r++) {
                uint32_t h = (src * K[r]) >> 22;
                uint32_t v = (tag[r][h] == t16) ? cnt[r][h] : 0u;
                v = (v == 0xFFFFu) ? v : v + 1u;
                tag[r][h] = t16;
                cnt[r][h] = (uint16_t)v;
                if (v < est) est = v;
            }
            if (est > top_est) { top_est = est; top_src = src; }
            b = ((src * K[0]) ^ DXOR) >> 22;
            if (dtag[b] != t16) { dtag[b] = t16; set_bits++; }
        }
    }
    if (have) {
        s += c[0] + c[1] + c[2] + c[3] + top_src + top_est + set_bits;
        if (out && nw < max_out) {
            out[nw].win = win; out[nw].top_src = top_src;
            out[nw].top_est = top_est; out[nw].set_bits = set_bits;
        }
        nw++;
    }
    if (sink) *sink = s;
    return nw;
}

uint64_t sketch_run(const uint64_t *rec, uint32_t n, int d)
{
    uint64_t s = 0;
    core(rec, n, d, 0, 0, &s);
    return s;
}

uint32_t sketch_windows(const uint64_t *rec, uint32_t n, int d, sk_out_t *out, uint32_t max_out)
{
    return core(rec, n, d, out, max_out, 0);
}

void sketch_make_records(uint64_t *rec, uint32_t n, uint32_t seed)
{
    uint32_t x = seed ? seed : 1u, i;
    for (i = 0; i < n; i++) {
        uint32_t ts = i / 40u;                       /* 40 records per 1000-tick window */
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;     /* xorshift32: same on PC and ARM */
        rec[i] = ((uint64_t)ts << 40) | ((uint64_t)(1u + (i % 3u)) << 32) | x;
    }
}
