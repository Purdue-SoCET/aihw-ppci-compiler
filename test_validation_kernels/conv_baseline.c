#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_FLAT_M1  (K_FLAT - 1)
#define K_OUT_M1   (K_OUT - 1)
#define ALL_MASK   0xFFFFF

/* Conv-as-GEMM: baseline — rolled weight and output row loops, no prefetch. */
int main() {
    int cfg_ptr = CFG_BASE;

    int a_gmem; int a_sp; int w_gmem; int w_sp; int c_gmem; int c_sp;

    a_gmem = atalla_load_u32(cfg_ptr + 0);
    a_sp = atalla_load_u32(cfg_ptr + 4);
    w_gmem = atalla_load_u32(cfg_ptr + 8);
    w_sp = atalla_load_u32(cfg_ptr + 12);
    c_gmem = atalla_load_u32(cfg_ptr + 16);
    c_sp = atalla_load_u32(cfg_ptr + 20);

    int sdma_ctl_a;
    int sdma_ctl_w;
    int sdma_ctl_c;
    sdma_ctl_a = atalla_const_u32(127926298u);
    sdma_ctl_w = atalla_const_u32(1949302787u);
    sdma_ctl_c = atalla_const_u32(1177550851u);

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

    atalla_halt();
    return 0;
}
