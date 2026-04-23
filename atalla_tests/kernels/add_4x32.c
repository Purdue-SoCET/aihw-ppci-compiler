#define CFG_BASE  0x3C
#define ROWS      4
#define COLS      32
#define ALL_MASK  0xFFFFFFFF
#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int A_GMEM = cfg[0];
    int B_GMEM = cfg[1];
    int C_GMEM = cfg[2];

    int sp = 0;
    int all_mask = ALL_MASK;

    volatile int sdma_ctl_sp0 = SDMA_RS3(0, ROWS, COLS, COLS);
    volatile int sdma_ctl_sp1 = SDMA_RS3(1, ROWS, COLS, COLS);

    scpad_load(sp, A_GMEM, sdma_ctl_sp0);
    scpad_load(sp, B_GMEM, sdma_ctl_sp1);

    int row = 0;
    while (row < ROWS) {
        vec a = vector_load(0, row, 31, 0);
        vec b = vector_load(0, row, 31, 1);
        vec c = vec_op_masked("+", a, b, all_mask);
        vector_store(c, 0, row, 31, 0);
        row = row + 1;
    }

    scpad_store(sp, C_GMEM, sdma_ctl_sp0);

    return 0;
}
