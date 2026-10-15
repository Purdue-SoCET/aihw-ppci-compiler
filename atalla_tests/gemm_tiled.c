/*
 * Tiled GEMM kernel: C += A * W using systolic array.
 *
 * Config at ADDR_TABLE (0x3C):
 *   [0]  A_GMEM    [4]  W_GMEM    [8]  C_GMEM
 *   [12] M         [16] N         [20] K
 *   [24] M_tiles   [28] N_tiles   [32] K_tiles   [36] tile_sz
 *
 * Each tile is TILE x TILE (4x4 for this test).
 * Loads A, W tiles from DRAM into scratchpad, preloads W into systolic array,
 * runs GEMM row by row, stores C tile back.
 */

#define CFG_BASE  0x3C
#define TILE      4
#define TILE_M1   3

int main() {
    int cfg = CFG_BASE;
    int A_GMEM; int W_GMEM; int C_GMEM;
    int gM; int gN; int gK;
    int M_tiles; int N_tiles; int K_tiles; int tile_sz;

    asm("lw_s %0, 0(%1)"  : "=r"(A_GMEM)  : "r"(cfg));
    asm("lw_s %0, 4(%1)"  : "=r"(W_GMEM)  : "r"(cfg));
    asm("lw_s %0, 8(%1)"  : "=r"(C_GMEM)  : "r"(cfg));
    asm("lw_s %0, 12(%1)" : "=r"(gM)      : "r"(cfg));
    asm("lw_s %0, 16(%1)" : "=r"(gN)      : "r"(cfg));
    asm("lw_s %0, 20(%1)" : "=r"(gK)      : "r"(cfg));
    asm("lw_s %0, 24(%1)" : "=r"(M_tiles) : "r"(cfg));
    asm("lw_s %0, 28(%1)" : "=r"(N_tiles) : "r"(cfg));
    asm("lw_s %0, 32(%1)" : "=r"(K_tiles) : "r"(cfg));
    asm("lw_s %0, 36(%1)" : "=r"(tile_sz) : "r"(cfg));

    int all_mask = -1;
    int sp_a = 0;
    int sp_w = 512;
    int sp_c = 0;
    int ncols = 1;
    int sdma_ctl_a = 0b00101010101010;
    int sdma_ctl_c = 0b00101010101010;

    int mi = 0;
    while (mi < M_tiles) {
        int ni = 0;
        while (ni < N_tiles) {
            int c_off = mi * tile_sz * gN + ni * tile_sz;
            int c_byte = c_off * 2;
            int c_addr = C_GMEM + c_byte;

            /* load C tile accumulator */
            asm("scpad_ld %0, %1, %2" : : "r"(sp_c), "r"(c_addr), "r"(sdma_ctl_c));

            int ki = 0;
            while (ki < K_tiles) {
                int a_off = mi * tile_sz * gK + ki * tile_sz;
                int a_byte = a_off * 2;
                int a_addr = A_GMEM + a_byte;

                int w_off = ki * tile_sz * gN + ni * tile_sz;
                int w_byte = w_off * 2;
                int w_addr = W_GMEM + w_byte;

                /* load A and W tiles */
                asm("scpad_ld %0, %1, %2" : : "r"(sp_a), "r"(a_addr), "r"(sdma_ctl_a));
                asm("scpad_ld %0, %1, %2" : : "r"(sp_w), "r"(w_addr), "r"(sdma_ctl_a));

                /* preload W rows into systolic array */
                int wi = 0;
                while (wi < TILE) {
                    vec wvec;
                    asm("vreg_ld %0, %1, %2, 3, 0"
                        : "=v"(wvec) : "r"(wi), "r"(ncols));
                    wi = wi + 1;
                }

                /* GEMM: each row of A against preloaded W */
                int ri = 0;
                while (ri < TILE) {
                    vec a_row;
                    vec c_row;
                    asm("vreg_ld %0, %1, %2, 3, 0"
                        : "=v"(a_row) : "r"(ri), "r"(ncols));
                    asm("vreg_ld %0, %1, %2, 3, 1"
                        : "=v"(c_row) : "r"(ri), "r"(ncols));

                    vec result = gemm(a_row, c_row, all_mask);

                    asm("vreg_st %0, %1, %2, 3, 1"
                        : : "v"(result), "r"(ri), "r"(ncols));
                    ri = ri + 1;
                }

                ki = ki + 1;
            }

            /* store C tile back to DRAM */
            asm("scpad_st %0, %1, %2" : : "r"(sp_c), "r"(c_addr), "r"(sdma_ctl_c));
            ni = ni + 1;
        }
        mi = mi + 1;
    }

    asm("halt");
    return 0;
}
