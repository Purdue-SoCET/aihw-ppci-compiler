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

    asm("lw_s %0, 0(%1)"  : "=r"(a_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 4(%1)"  : "=r"(a_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 8(%1)"  : "=r"(w_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 12(%1)" : "=r"(w_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 16(%1)" : "=r"(c_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 20(%1)" : "=r"(c_sp)   : "r"(cfg_ptr));

    int sdma_ctl_a;
    int sdma_ctl_w;
    int sdma_ctl_c;
    asm("li_s %0, 127926298" : "=r"(sdma_ctl_a));
    asm("li_s %0, 1949302787" : "=r"(sdma_ctl_w));
    asm("li_s %0, 1177550851" : "=r"(sdma_ctl_c));

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

    asm("halt");
    return 0;
}
