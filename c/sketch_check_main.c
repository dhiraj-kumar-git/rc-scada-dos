/* Host check of the C sketch against the golden model: writes
 * build/host_sketch_d<D>_r<i>.txt for D = 1, 2, 4, 8 and every demo region.
 * Compare with: python3 python/compare.py sketch-host */
#include <stdio.h>
#include "records.h"
#include "sketch_bench.h"

static sk_out_t out[32768];

int main(void)
{
    const int ds[4] = {1, 2, 4, 8};
    for (int k = 0; k < 4; k++) {
        for (int r = 0; r < N_REGIONS; r++) {
            char name[64];
            uint32_t nw = sketch_windows(&RECORDS[REGION_START[r]], REGION_LEN[r], ds[k], out, 32768u);
            snprintf(name, sizeof name, "build/host_sketch_d%d_r%d.txt", ds[k], r);
            FILE *f = fopen(name, "w");
            if (!f) { perror(name); return 1; }
            for (uint32_t i = 0; i < nw && i < 32768u; i++)
                fprintf(f, "%u %u %u %u\n", out[i].win, out[i].top_src, out[i].top_est, out[i].set_bits);
            fclose(f);
        }
        printf("sketch_check d=%d: %d regions written\n", ds[k], N_REGIONS);
    }
    return 0;
}
