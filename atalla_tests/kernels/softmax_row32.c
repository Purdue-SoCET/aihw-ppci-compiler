#define CFG_BASE  0x3C
#define WIDTH_M1  31
#define ROWS      1
#define ROWS_M1   0
#define MASK_VAL  0xFFFFFFFF
#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int IN_GMEM = cfg[0];

    int sp = 0;
    int mask_val = MASK_VAL;
    volatile int sdma_ctl = SDMA_RS3(0, 1, 32, 32);

    scpad_load(sp, IN_GMEM, sdma_ctl);

    int row = 0;
    while (row < ROWS) {
        vec v = vector_load(0, row, WIDTH_M1, 0);

        vec vmax = vec_op_masked("RMAX", v, 0.0, mask_val);
        vec shifted = vec_op_masked("-", v, vmax, mask_val);

        vec exp_v = vec_op_masked("EXP", shifted, 0.0, mask_val);

        vec sum_v = vec_op_masked("RSUM", exp_v, 0.0, mask_val);

        float sum_f = sum_v[0];
        float inv_sum = 1.0 / sum_f;

        vec result = vec_op_masked("*", exp_v, inv_sum, mask_val);

        vector_store(result, 0, row, WIDTH_M1, 0);
        row = row + 1;
    }

    scpad_store(sp, IN_GMEM, sdma_ctl);

    return 0;
}
