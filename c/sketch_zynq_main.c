/* Bare-metal ARM run of the per-packet work benchmark (Vitis Hello World
 * template, Release build). Add sketch_bench.c and sketch_bench.h; use this
 * file instead of helloworld.c. Prints records per second for d = 0,1,2,4,8. */
#include <stdint.h>
#include "xil_printf.h"
#include "xtime_l.h"
#include "sketch_bench.h"
#define N (1u << 16)
#define REPS 20
static uint64_t rec[N];
int main(void)
{
    const int ds[] = {0, 1, 2, 4, 8};
    int k, r;
    sketch_make_records(rec, N, 12345u);
    xil_printf("\r\nARM per-packet work benchmark, COUNTS_PER_SECOND=%u\r\n", (unsigned)COUNTS_PER_SECOND);
    for (k = 0; k < 5; k++) {
        XTime t0, t1;
        uint64_t s = 0, ticks, recs, per_s, ns_x10;
        XTime_GetTime(&t0);
        for (r = 0; r < REPS; r++) s += sketch_run(rec, N, ds[k]);
        XTime_GetTime(&t1);
        ticks = (uint64_t)(t1 - t0);
        recs = (uint64_t)N * REPS;
        per_s = ticks ? recs * (uint64_t)COUNTS_PER_SECOND / ticks : 0;
        ns_x10 = recs ? ticks * 10000000000ULL / ((uint64_t)COUNTS_PER_SECOND * recs) : 0;
        xil_printf("arm d=%d records_per_s=%u ns_per_record=%u.%u check=%u\r\n", ds[k],
                   (unsigned)per_s, (unsigned)(ns_x10 / 10), (unsigned)(ns_x10 % 10), (unsigned)(s & 0xFFFF));
    }
    xil_printf("done\r\n");
    return 0;
}
