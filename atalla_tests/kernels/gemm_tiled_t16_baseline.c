#define CFG_BASE  0x3C
/* TILE=16 baseline GEMM (no K-prefetch). Pairs with gemm_tiled_ta_pipelined.c for
 * matched_suite TILE=16 shapes; SP0 row budget requires TILE<=16 for full A+B slabs. */
#define TILE      16
#define TILE_M1   15

#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

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
    if (tile_sz != TILE) {
        asm("halt");
        return 0;
    }

    int all_mask = -1;
    int sp_base = 0;
    volatile int sdma_ctl_w = SDMA_RS3(0, TILE, TILE, gN);
    volatile int sdma_ctl_a = SDMA_RS3(0, TILE, TILE, gK);
    volatile int sdma_ctl_c = SDMA_RS3(1, TILE, TILE, gN);

    int mi = 0;
    while (mi < M_tiles) {
        int ni = 0;
        while (ni < N_tiles) {
            int c_off = mi * tile_sz * gN + ni * tile_sz;
            int c_addr = C_GMEM + c_off * 2;

            scpad_load(sp_base, c_addr, sdma_ctl_c);

            int ki = 0;
            while (ki < K_tiles) {
                int a_off = mi * tile_sz * gK + ki * tile_sz;
                int a_addr = A_GMEM + a_off * 2;

                int w_off = ki * tile_sz * gN + ni * tile_sz;
                int w_addr = W_GMEM + w_off * 2;

                scpad_load(sp_base, w_addr, sdma_ctl_w);

                int wi = 0;
                while (wi < TILE) {
                    vec wvec = vector_load(0, wi, TILE_M1, 0);
                    load_weights(wvec);
                    wi = wi + 1;
                }

                scpad_load(sp_base, a_addr, sdma_ctl_a);

                int ri = 0;
                while (ri < TILE) {
                    vec a_row = vector_load(0, ri, TILE_M1, 0);
                    vec c_row = vector_load(0, ri, TILE_M1, 1);
                    vec result = gemm(a_row, c_row, all_mask);
                    vector_store(result, 0, ri, TILE_M1, 1);
                    ri = ri + 1;
                }

                ki = ki + 1;
            }

            scpad_store(sp_base, c_addr, sdma_ctl_c);
            ni = ni + 1;
        }
        mi = mi + 1;
    }

    asm("halt");
    return 0;
}
