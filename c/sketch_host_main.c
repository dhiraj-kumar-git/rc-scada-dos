/* PC run of the per-packet work benchmark:
 *   make bench
 * The number that matters for the project is the ARM one (sketch_zynq_main.c). */
#include <stdio.h>
#include <time.h>
#include "sketch_bench.h"
#define N (1u << 18)
static uint64_t rec[N];
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void)
{
    const int ds[] = {0, 1, 2, 4, 8};
    sketch_make_records(rec, N, 12345u);
    for (int k = 0; k < 5; k++) {
        const int reps = 40;
        uint64_t s = 0;
        double t0 = now();
        for (int r = 0; r < reps; r++) s += sketch_run(rec, N, ds[k]);
        double dt = now() - t0;
        printf("pc d=%d records_per_s=%.0f ns_per_record=%.2f check=%llu\n", ds[k],
               N * (double)reps / dt, dt * 1e9 / (N * (double)reps), (unsigned long long)(s & 0xFFFF));
    }
    return 0;
}
