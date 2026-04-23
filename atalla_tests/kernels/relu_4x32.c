#define CFG_BASE  0x3C
#define WIDTH_M1  31
#define ROWS      4
#define COLS      32
#define ALL_MASK  0xFFFFFFFF
#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int IN_GMEM = cfg[0];
    int OUT_GMEM = cfg[1];

    int sp = 0;
    int all_mask = ALL_MASK;
    volatile int sdma_ctl = SDMA_RS3(0, ROWS, COLS, COLS);

    scpad_load(sp, IN_GMEM, sdma_ctl);

    vec zero_vec = vector_load(0, 0, WIDTH_M1, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, all_mask);

    int row = 0;
    while (row < ROWS) {
        vec v = vector_load(0, row, WIDTH_M1, 0);
        vec result = zero_vec;
        result = vec_op_masked(
            "+",
            zero_vec,
            v,
            make_mask("<", zero_vec, v, all_mask)
        );

        vector_store(result, 0, row, WIDTH_M1, 0);
        row = row + 1;
    }

    scpad_store(sp, OUT_GMEM, sdma_ctl);

    return 0;
}
