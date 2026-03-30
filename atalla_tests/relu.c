/*
 * ReLU kernel: max(0, x) element-wise on a tile loaded from DRAM.
 *
 * Config at ADDR_TABLE (0x3C):
 *   [0] IN_GMEM    [4] OUT_GMEM
 *
 * Fixed tile: 4 rows x 32 cols (128 bf16 elements).
 * Loads tile from DRAM into scratchpad, zeroes negatives, stores back.
 */

#define CFG_BASE  0x3C
#define WIDTH_M1  31
#define ROWS      4
#define ROWS_M1   3
#define ALL_MASK  0xFFFFFFFF

int main() {
    int cfg = CFG_BASE;
    int IN_GMEM;
    int OUT_GMEM;
    asm("lw_s %0, 0(%1)" : "=r"(IN_GMEM)  : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(OUT_GMEM) : "r"(cfg));

    int sp = 0;
    int all_mask = ALL_MASK;

    /* load input tile from DRAM to scratchpad */
    asm("scpad_ld %0, %1, 31, 3, 0" : : "r"(sp), "r"(IN_GMEM));

    /* create zero vector: load any row then multiply by 0 */
    vec zero_vec;
    asm("vreg_ld %0, %1, 31, 3, 0, 1, 0" : "=v"(zero_vec) : "r"(0));
    zero_vec = vec_op_masked("*", zero_vec, 0.0, all_mask);

    int row = 0;
    while (row < ROWS) {
        vec v;
        asm("vreg_ld %0, %1, 31, 3, 0, 1, 0" : "=v"(v) : "r"(row));

        /* build mask of negative elements, then zero them out */
        int m_neg = make_mask("<", v, zero_vec, all_mask);
        vec result = vec_op_masked("*", v, 0.0, m_neg);

        asm("vreg_st %0, %1, 31, 3, 0, 1, 0" : : "v"(result), "r"(row));
        row = row + 1;
    }

    /* store result tile back to DRAM */
    asm("scpad_st %0, %1, 31, 3, 0" : : "r"(sp), "r"(OUT_GMEM));

    asm("halt");
    return 0;
}
