#include "sketch_bench.h"

static uint32_t cnt[SK_MAX_D][SK_W];
static uint8_t  win[SK_MAX_D][SK_W];
static uint32_t bitmap[SK_W / 32];
/* one odd multiplier per row: hash = top 10 bits of (src * K[r]) */
static const uint32_t K[SK_MAX_D] = {2654435761u, 2246822519u, 3266489917u, 668265263u,
                                     374761393u, 2869860233u, 1597334677u, 3812015801u};

uint64_t sketch_run(const uint64_t *rec, uint32_t n, int d)
{
    uint32_t c[4] = {0, 0, 0, 0}, cur_end = 1000, w = 0, top = 0, top_est = 0;
    uint64_t sink = 0;
    uint32_t i;
    int r;
    for (i = 0; i < n; i++) {
        uint32_t ts = (uint32_t)(rec[i] >> 40) & 0xFFFFFFu;
        uint32_t kind = (uint32_t)(rec[i] >> 32) & 0xFFu;
        uint32_t src = (uint32_t)rec[i];
        while (ts >= cur_end) {
            sink += c[0] + c[1] + c[2] + c[3] + top;
            c[0] = c[1] = c[2] = c[3] = 0;
            top_est = 0; w++; cur_end += 1000;
        }
        c[kind & 3]++;
        if (d > 0) {
            uint32_t est = 0xFFFFFFFFu, b;
            for (r = 0; r < d; r++) {
                uint32_t h = (src * K[r]) >> 22;
                uint32_t v;
                if (win[r][h] != (uint8_t)w) { win[r][h] = (uint8_t)w; cnt[r][h] = 0; }
                v = ++cnt[r][h];
                if (v < est) est = v;
            }
            if (est > top_est) { top_est = est; top = src; }
            b = ((src * K[0]) ^ 0x9e3779b9u) >> 22;
            bitmap[b >> 5] |= 1u << (b & 31);
        }
    }
    return sink + bitmap[0] + bitmap[SK_W / 32 - 1];
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
