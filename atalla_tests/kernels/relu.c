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
    int ncols = 1;
    int sdma_ctl;
    asm("li_s %0, 133169183" : "=r"(sdma_ctl));

    scpad_load(sp, IN_GMEM, sdma_ctl);

    vec zero_vec = vector_load(0, ncols, 31, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, all_mask);

    int row = 0;
    while (row < ROWS) {
        vec v = vector_load(row, ncols, 31, 0);

        int m_neg = make_mask("<", v, zero_vec, all_mask);
        vec result = vec_op_masked("*", v, 0.0, m_neg);

        vector_store(result, row, ncols, 31, 0);
        row = row + 1;
    }

    scpad_store(sp, OUT_GMEM, sdma_ctl);

    asm("halt");
    return 0;
}
