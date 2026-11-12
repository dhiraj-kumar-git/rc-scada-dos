/* Per-packet work benchmark: plain counting vs count-min sketch with d rows
 * plus a distinct-source table (same rules as the golden model). Used to show how a CPU's cost per record
 * grows with the work done per packet. Same record format as the project. */
#ifndef SKETCH_BENCH_H
#define SKETCH_BENCH_H
#include <stdint.h>
#define SK_W 1024            /* cells per row */
#define SK_MAX_D 8           /* max rows */
/* Runs over n records with d rows (0 = plain counting only).
 * Returns a value that depends on every update, so the compiler cannot skip work. */
uint64_t sketch_run(const uint64_t *rec, uint32_t n, int d);
/* Per-window outputs, same as run_sketch() in python/common.py: one entry per
 * window that holds at least one record. Returns the number of windows. */
typedef struct { uint32_t win, top_src, top_est, set_bits; } sk_out_t;
uint32_t sketch_windows(const uint64_t *rec, uint32_t n, int d, sk_out_t *out, uint32_t max_out);
/* Fills rec with n synthetic records: 40 per 100 ms window, random sources. */
void sketch_make_records(uint64_t *rec, uint32_t n, uint32_t seed);
#endif
