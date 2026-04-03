#define CFG_BASE  0x3C
#define WIDTH_M1  31
#define ROWS      1
#define ROWS_M1   0
#define MASK_VAL  0xFFFFFFFF

int main() {
    int cfg = CFG_BASE;
    int IN_GMEM;
    int dummy;
    asm("lw_s %0, 0(%1)" : "=r"(IN_GMEM) : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(dummy)   : "r"(cfg));

    int sp = 0;
    int mask_val = MASK_VAL;
    int ncols = 1;
    int sdma_ctl;
    asm("li_s %0, 32505887" : "=r"(sdma_ctl));

    scpad_load(sp, IN_GMEM, sdma_ctl);

    int row = 0;
    while (row < ROWS) {
        vec v = vector_load(row, ncols, 31, 0);

        vec vmax = vec_op_masked("RMAX", v, 0.0, mask_val);
        vec shifted = vec_op_masked("-", v, vmax, mask_val);

        vec exp_v = vec_op_masked("EXP", shifted, 0.0, mask_val);

        vec sum_v = vec_op_masked("RSUM", exp_v, 0.0, mask_val);

        float sum_f = sum_v[0];
        float inv_sum = 1.0 / sum_f;

        vec result = vec_op_masked("*", exp_v, inv_sum, mask_val);

        vector_store(result, row, ncols, 31, 0);
        row = row + 1;
    }

    scpad_store(sp, IN_GMEM, sdma_ctl);

    asm("halt");
    return 0;
}
