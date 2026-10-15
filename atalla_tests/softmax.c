/*
 * Softmax kernel: softmax(x) = exp(x - max(x)) / sum(exp(x - max(x)))
 *
 * Config at ADDR_TABLE (0x3C):
 *   [0] IN_GMEM    [4] unused
 *
 * Fixed: 1 row x 32 elements. Result written back in-place.
 * Uses rmax, exp, rsum reductions, then scalar reciprocal + broadcast multiply.
 */

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
    int sdma_ctl = 0b00101010101010;

    /* load input from DRAM */
    asm("scpad_ld %0, %1, %2" : : "r"(sp), "r"(IN_GMEM), "r"(sdma_ctl));

    int row = 0;
    while (row < ROWS) {
        vec v;
        asm("vreg_ld %0, %1, %2, 31, 0" : "=v"(v) : "r"(row), "r"(ncols));

        /* subtract max for numerical stability */
        vec vmax = vec_op_masked("RMAX", v, 0.0, mask_val);
        vec shifted = vec_op_masked("-", v, vmax, mask_val);

        /* exponentiate */
        vec exp_v = vec_op_masked("EXP", shifted, 0.0, mask_val);

        /* sum reduction */
        vec sum_v = vec_op_masked("RSUM", exp_v, 0.0, mask_val);

        /* extract scalar sum, compute reciprocal, multiply */
        float sum_f = sum_v[0];
        int sum_bits;
        int inv_bits;
        asm("stbf_s %0, %1, %2" : "=r"(sum_bits) : "r"(sum_f), "r"(0));
        asm("rcp_bf %0, %1, %2" : "=r"(inv_bits) : "r"(sum_bits), "r"(0));
        float inv_sum;
        asm("bfts_s %0, %1, %2" : "=r"(inv_sum) : "r"(inv_bits), "r"(0));

        vec result = vec_op_masked("*", exp_v, inv_sum, mask_val);

        asm("vreg_st %0, %1, %2, 31, 0" : : "v"(result), "r"(row), "r"(ncols));
        row = row + 1;
    }

    /* store result back in-place */
    asm("scpad_st %0, %1, %2" : : "r"(sp), "r"(IN_GMEM), "r"(sdma_ctl));

    asm("halt");
    return 0;
}
