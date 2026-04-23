#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_FLAT_M1  (K_FLAT - 1)
#define K_OUT_M1   (K_OUT - 1)
#define ALL_MASK   0xFFFFF
#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    (((unsigned)((sid) & 3u) << 30) | ((unsigned)(((tile_rows) - 1) & 0x1Fu) << 25) | ((unsigned)(((tile_cols) - 1) & 0x1Fu) << 20) | (unsigned)(((full_cols) - 1) & 0xFFFFFu))

/* Conv-as-GEMM: baseline — rolled weight and output row loops, no prefetch. */
int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int a_gmem = cfg[0];
    int a_sp = cfg[1];
    int w_gmem = cfg[2];
    int w_sp = cfg[3];
    int c_gmem = cfg[4];
    int c_sp = cfg[5];

    volatile int sdma_ctl_a = SDMA_RS3(0, M, K_FLAT, K_FLAT);
    volatile int sdma_ctl_w = SDMA_RS3(1, K_FLAT, K_OUT, K_OUT);
    volatile int sdma_ctl_c = SDMA_RS3(1, M, K_OUT, K_OUT);

    scpad_load(a_sp, a_gmem, sdma_ctl_a);
    scpad_load(w_sp, w_gmem, sdma_ctl_w);

    int wi = 0;
    while (wi < K_OUT) {
        vec wvec = vector_load(w_sp, wi, K_FLAT_M1, 1);
        load_weights(wvec);
        wi = wi + 1;
    }

    scpad_load(c_sp, c_gmem, sdma_ctl_c);

    int all_mask = ALL_MASK;
    int row = 0;
    while (row < M) {
        vec a_row = vector_load(a_sp, row, K_FLAT_M1, 0);
        vec c_row = vector_load(c_sp, row, K_OUT_M1, 1);
        vec result = gemm(a_row, c_row, all_mask);
        vector_store(result, c_sp, row, K_OUT_M1, 1);
        row = row + 1;
    }

    scpad_store(c_sp, c_gmem, sdma_ctl_c);

    return 0;
}
