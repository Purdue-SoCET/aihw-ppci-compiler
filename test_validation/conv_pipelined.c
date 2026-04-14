#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_FLAT_M1  (K_FLAT - 1)
#define K_OUT_M1   (K_OUT - 1)
#define ALL_MASK   0xFFFFF

/* Conv-as-GEMM: pipelined M loop — prefetch (a,c) for next row; rolled weight load. */
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

    int row = 0;
    int prefetch_row = 1;
    int all_mask = ALL_MASK;

    vec a_buf0 = vector_load(a_sp, row, K_FLAT_M1, 0);
    vec c_buf0 = vector_load(c_sp, row, K_OUT_M1, 1);

    while (row < M) {
        vec result0 = gemm(a_buf0, c_buf0, all_mask);
        vector_store(result0, c_sp, row, K_OUT_M1, 1);
        row = row + 1;
        if (row >= M) break;

        vec a_buf1;
        vec c_buf1;
        if (prefetch_row < M) {
            a_buf1 = vector_load(a_sp, prefetch_row, K_FLAT_M1, 0);
            c_buf1 = vector_load(c_sp, prefetch_row, K_OUT_M1, 1);
        }
        prefetch_row = prefetch_row + 1;

        vec result1 = gemm(a_buf1, c_buf1, all_mask);
        vector_store(result1, c_sp, row, K_OUT_M1, 1);
        row = row + 1;
        if (row >= M) break;

        if (prefetch_row < M) {
            a_buf0 = vector_load(a_sp, prefetch_row, K_FLAT_M1, 0);
            c_buf0 = vector_load(c_sp, prefetch_row, K_OUT_M1, 1);
        }
        prefetch_row = prefetch_row + 1;
    }

    scpad_store(c_sp, c_gmem, sdma_ctl_c);

    asm("halt");
    return 0;
}
