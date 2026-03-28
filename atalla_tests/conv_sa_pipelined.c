/*
 * Pipelined systolic-array convolution kernel for Atalla.
 *
 * Performs C = A * W  (im2col GEMM) with double-buffered prefetch.
 *
 * Config layout at CFG_BASE (6 x 32-bit words):
 *   [0] A_gmem_addr   [4] A_sp_base
 *   [8] W_gmem_addr  [12] W_sp_base
 *  [16] C_gmem_addr  [20] C_sp_base
 *
 * Template parameters (adjust per conv shape):
 *   M      = N*Ho*Wo   (rows of A / rows of C)
 *   K_FLAT = R*S*C     (cols of A / rows of W)
 *   K_OUT  = K         (cols of W / cols of C)
 */

#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_OUT_M1   (K_OUT - 1)
#define K_FLAT_M1  (K_FLAT - 1)
#define M_M1       (M - 1)
#define ALL_MASK   0xFFFFF

int main() {
    int cfg_ptr = CFG_BASE;

    /* load 6 config words (GMEM ptrs + SP bases) */
    int a_gmem;
    int a_sp;
    int w_gmem;
    int w_sp;
    int c_gmem;
    int c_sp;

    asm("lw_s %0, 0(%1)"  : "=r"(a_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 4(%1)"  : "=r"(a_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 8(%1)"  : "=r"(w_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 12(%1)" : "=r"(w_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 16(%1)" : "=r"(c_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 20(%1)" : "=r"(c_sp)   : "r"(cfg_ptr));

    /* SDMA: load A tile (SP0) and W tile (SP1) from GMEM */
    asm("scpad_ld %0, %1, 26, 3, 0" : : "r"(a_sp), "r"(a_gmem));
    asm("scpad_ld %0, %1, 3, 26, 1" : : "r"(w_sp), "r"(w_gmem));

    /* preload weight rows into vector register file */
    int wi = 0;
    vec wvec;
    while (wi < K_OUT) {
        asm("vreg_ld %0, %1, 0, 26, 1, 0, 0"
            : "=v"(wvec) : "r"(wi));
        wi = wi + 1;
    }

    /* SDMA: load C tile (SP1) from GMEM */
    asm("scpad_ld %0, %1, 3, 3, 1" : : "r"(c_sp), "r"(c_gmem));

    /* pipelined GEMM loop (double-buffered A/C vectors) */
    int row = 0;
    int prefetch_row = 1;
    int all_mask = ALL_MASK;

    /* prologue: seed first A and C vectors into buf0 */
    int a_addr0 = a_sp + row;
    int c_addr0 = c_sp + row;
    vec a_buf0;
    vec c_buf0;
    asm("vreg_ld %0, %1, 26, 4, 0, 1, 0" : "=v"(a_buf0) : "r"(a_addr0));
    asm("vreg_ld %0, %1, 3, 4, 1, 1, 0"  : "=v"(c_buf0) : "r"(c_addr0));

    while (row < M) {
        /* stage C0: compute + store using buf0 */
        int c_st_addr = c_sp + row;
        vec result0 = gemm(a_buf0, c_buf0, all_mask);
        asm("vreg_st %0, %1, 3, 4, 1, 1, 0" : : "v"(result0), "r"(c_st_addr));
        row = row + 1;
        if (row >= M) break;

        /* stage P1: prefetch next row into buf1 */
        vec a_buf1;
        vec c_buf1;
        if (prefetch_row < M) {
            int a_addr1 = a_sp + prefetch_row;
            int c_addr1 = c_sp + prefetch_row;
            asm("vreg_ld %0, %1, 26, 4, 0, 1, 0" : "=v"(a_buf1) : "r"(a_addr1));
            asm("vreg_ld %0, %1, 3, 4, 1, 1, 0"  : "=v"(c_buf1) : "r"(c_addr1));
        }
        prefetch_row = prefetch_row + 1;

        /* stage C1: compute + store using buf1 */
        c_st_addr = c_sp + row;
        vec result1 = gemm(a_buf1, c_buf1, all_mask);
        asm("vreg_st %0, %1, 3, 4, 1, 1, 0" : : "v"(result1), "r"(c_st_addr));
        row = row + 1;
        if (row >= M) break;

        /* stage P0: prefetch next row back into buf0 */
        if (prefetch_row < M) {
            a_addr0 = a_sp + prefetch_row;
            c_addr0 = c_sp + prefetch_row;
            asm("vreg_ld %0, %1, 26, 4, 0, 1, 0" : "=v"(a_buf0) : "r"(a_addr0));
            asm("vreg_ld %0, %1, 3, 4, 1, 1, 0"  : "=v"(c_buf0) : "r"(c_addr0));
        }
        prefetch_row = prefetch_row + 1;
    }

    /* drain: write C tile from SP1 back to GMEM */
    asm("scpad_st %0, %1, 3, 3, 1" : : "r"(c_sp), "r"(c_gmem));

    asm("halt");
    return 0;
}
