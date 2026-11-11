/* PC build of the ARM baseline, used to prove the C code matches the golden
 * model before it goes on the board.
 *   make host       (native PC build, prefix "host")
 *   make arm-check  (ARM Cortex-A9 build run under QEMU, prefix "arm")
 * Writes build/<prefix>_r<i>.txt and build/<prefix>_summary.txt (run from repo root).
 * Timing printed here is for the machine it runs on; under QEMU it is
 * emulation speed and means nothing about the real ARM. */
#ifndef OUT_PREFIX
#define OUT_PREFIX "host"
#endif
#include <stdio.h>
#include <time.h>
#include "detector.h"
#include "records.h"

static void emit_file(const window_out_t *w, void *ctx)
{
    fprintf((FILE *)ctx, "%u %u %u %u %u %d %d %d\n", w->idx, w->icmp, w->syn,
            w->modbus, w->other, w->cls, w->alarm, w->branch);
}

int main(void)
{
    FILE *fs = fopen("build/" OUT_PREFIX "_summary.txt", "w");
    if (!fs) { perror("build/" OUT_PREFIX "_summary.txt"); return 1; }
    for (int r = 0; r < N_REGIONS; r++) {
        char name[64];
        summary_t s;
        snprintf(name, sizeof name, "build/" OUT_PREFIX "_r%d.txt", r);
        FILE *f = fopen(name, "w");
        if (!f) { perror(name); return 1; }
        detect_region(&RECORDS[REGION_START[r]], REGION_LEN[r], emit_file, f, &s);
        fclose(f);
        fprintf(fs, "region=%d windows=%u alarm_windows=%u first_alarm=%d first_class=%d\n",
                r, s.windows, s.alarm_windows, s.first_alarm, s.first_class);

        /* PC timing, for information only: the number that matters is the ARM one */
        struct timespec t0, t1;
        const int reps = 200;
        clock_gettime(CLOCK_MONOTONIC, &t0);
        for (int k = 0; k < reps; k++)
            detect_region(&RECORDS[REGION_START[r]], REGION_LEN[r], NULL, NULL, &s);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        double dt = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
        printf("region=%d windows=%u alarm_windows=%u first_alarm=%d first_class=%d | " OUT_PREFIX " timing (this machine only): %.1f million records/s\n",
               r, s.windows, s.alarm_windows, s.first_alarm, s.first_class,
               REGION_LEN[r] * (double)reps / dt / 1e6);
    }
    fclose(fs);
    return 0;
}
