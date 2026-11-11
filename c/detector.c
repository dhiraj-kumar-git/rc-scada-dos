#include "detector.h"
#include "rules.h"

static inline uint32_t inc_sat(uint32_t x) { return x == 0xFFFFu ? x : x + 1u; }

void detect_region(const uint64_t *rec, uint32_t n,
                   void (*emit)(const window_out_t *w, void *ctx), void *ctx,
                   summary_t *sum)
{
    uint32_t cur_end = WINDOW_TICKS, idx = 0;
    uint32_t c_icmp = 0, c_syn = 0, c_modbus = 0, c_other = 0;
    int run = 0;
    uint32_t i;
    window_out_t w;

    sum->windows = 0; sum->alarm_windows = 0; sum->first_alarm = -1; sum->first_class = -1;

#define EMIT_WINDOW() do {                                                   \
        int cls_ = classify(c_icmp, c_syn, c_modbus, c_other);              \
        run = (cls_ == 0) ? 0 : (run == 3 ? 3 : run + 1);                   \
        w.idx = idx; w.icmp = c_icmp; w.syn = c_syn; w.modbus = c_modbus;   \
        w.other = c_other; w.cls = cls_; w.alarm = (run >= PERSIST);        \
        w.branch = (cls_ == 0) ? 0 : (cls_ == 3 ? 2 : 1);                   \
        sum->windows++;                                                     \
        if (w.alarm) {                                                      \
            if (sum->alarm_windows == 0) {                                  \
                sum->first_alarm = (int32_t)idx; sum->first_class = cls_;   \
            }                                                               \
            sum->alarm_windows++;                                           \
        }                                                                   \
        if (emit) emit(&w, ctx);                                            \
        idx++; c_icmp = c_syn = c_modbus = c_other = 0;                     \
    } while (0)

    for (i = 0; i < n; i++) {
        uint32_t ts = (uint32_t)(rec[i] >> 40) & 0xFFFFFFu;
        uint32_t kind = (uint32_t)(rec[i] >> 32) & 0xFFu;
        while (ts >= cur_end) {
            EMIT_WINDOW();
            cur_end += WINDOW_TICKS;
        }
        switch (kind) {
        case 1: c_icmp = inc_sat(c_icmp); break;
        case 2: c_syn = inc_sat(c_syn); break;
        case 3: c_modbus = inc_sat(c_modbus); break;
        default: c_other = inc_sat(c_other); break;
        }
    }
    if (n > 0) EMIT_WINDOW();
#undef EMIT_WINDOW
}
