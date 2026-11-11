/* Bare-metal ARM baseline for the ZedBoard (Vitis "Hello World" template).
 * Add detector.c, detector.h, rules.h and records.h to the application's src
 * folder, replace helloworld.c with this file, build in Release (-O2).
 *
 * Prints, per region, the same summary line as Python and the testbench, then
 * the measured ARM speed. Paste the "region=" lines into
 * build/board_summary.txt and run: python3 python/compare.py board */
#include <stdint.h>
#include "xil_printf.h"
#include "xtime_l.h"
#include "detector.h"
#include "records.h"

#define REPS 20

int main(void)
{
    xil_printf("\r\nARM baseline, COUNTS_PER_SECOND=%u\r\n", (unsigned)COUNTS_PER_SECOND);
    for (int r = 0; r < N_REGIONS; r++) {
        summary_t s;
        XTime t0, t1;
        detect_region(&RECORDS[REGION_START[r]], REGION_LEN[r], 0, 0, &s);
        xil_printf("region=%d windows=%u alarm_windows=%u first_alarm=%d first_class=%d\r\n",
                   r, (unsigned)s.windows, (unsigned)s.alarm_windows,
                   (int)s.first_alarm, (int)s.first_class);
        XTime_GetTime(&t0);
        for (int k = 0; k < REPS; k++)
            detect_region(&RECORDS[REGION_START[r]], REGION_LEN[r], 0, 0, &s);
        XTime_GetTime(&t1);
        uint64_t ticks = (uint64_t)(t1 - t0);
        uint64_t recs = (uint64_t)REGION_LEN[r] * REPS;
        uint64_t per_s = ticks ? recs * (uint64_t)COUNTS_PER_SECOND / ticks : 0;
        uint64_t ns_x10 = recs ? ticks * 10000000000ULL / ((uint64_t)COUNTS_PER_SECOND * recs) : 0;
        xil_printf("arm region=%d records=%u reps=%d timer_ticks=%u records_per_s=%u ns_per_record=%u.%u\r\n",
                   r, (unsigned)REGION_LEN[r], REPS, (unsigned)ticks, (unsigned)per_s,
                   (unsigned)(ns_x10 / 10), (unsigned)(ns_x10 % 10));
    }
    xil_printf("done\r\n");
    return 0;
}
