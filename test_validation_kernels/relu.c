#define CFG_BASE  0x3C
#define WIDTH_M1  31
#define ROWS      4
#define ROWS_M1   3
#define ALL_MASK  0xFFFFFFFF

int main() {
    int cfg = CFG_BASE;
    int IN_GMEM;
    int OUT_GMEM;
    IN_GMEM = *(volatile int *)(cfg + 0);
    OUT_GMEM = *(volatile int *)(cfg + 4);

    int sp = 0;
    int all_mask = ALL_MASK;
    int sdma_ctl;
    sdma_ctl = 133169183u;

    scpad_load(sp, IN_GMEM, sdma_ctl);

    /* vector_load(scpad_base, row, num_cols_m1, sid) */
    vec zero_vec = vector_load(0, 0, WIDTH_M1, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, all_mask);

    int row = 0;
    while (row < ROWS) {
        vec v = vector_load(0, row, WIDTH_M1, 0);

        int m_neg = make_mask("<", v, zero_vec, all_mask);
        vec result = vec_op_masked("*", v, 0.0, m_neg);

        vector_store(result, 0, row, WIDTH_M1, 0);
        row = row + 1;
    }

    scpad_store(sp, OUT_GMEM, sdma_ctl);

    atalla_halt();
    return 0;
}
