/* ARM baseline: the same Detector as rtl/detector.v, in plain C.
 * Same windows, same learned rules (rules.h), same 3-window persistence. */
#ifndef DETECTOR_H
#define DETECTOR_H
#include <stdint.h>

#define WINDOW_TICKS 1000u
#define PERSIST 3

typedef struct {
    uint32_t idx, icmp, syn, modbus, other;
    int cls, alarm, branch;
} window_out_t;

typedef struct {
    uint32_t windows, alarm_windows;
    int32_t first_alarm, first_class;
} summary_t;

/* Runs one region. emit may be NULL (used for timing). */
void detect_region(const uint64_t *rec, uint32_t n,
                   void (*emit)(const window_out_t *w, void *ctx), void *ctx,
                   summary_t *sum);
#endif
