#define CFG_BASE  0x00080000u  /* functional_sim/gemm_dram_layout.GEMM_CFG_BASE */
/*
 * TA tiled GEMM — software-pipelined K loop with optional A/W scratchpad residency split.
 *
 * Scratchpad has 32 rows per bank (functional_sim). When TILE<=16, activations (A) use
 * rows [0, TILE) and weights (W) use [TILE, 2*TILE) so the A DMA does not overwrite W
 * before load_weights streams W into the systolic array. When TILE>32 would be needed
 * for split, TILE>16 instead: fall back to sequential overlay at row 0 (same as legacy).
 *
 * Deeper "weight-stationary" reuse (multiple N-tiles per resident A with m>1) needs
 * more rows than 32 for TILE=16+16+16 or a smaller TILE — not enabled here; this kernel
 * keeps the correct (mi, ni, ki) accumulation order while improving locality where split fits.
 *
 * Shapes from cfg at CFG_BASE (see ta_gemm_emit.py).
 */
#define TILE      32
#define TILE_M1   31

#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

/* Rows on sid-0 scratchpad: A low, W high when 2*TILE <= 32; else both use 0 (staged). */
#define SP_ROW_A 0
#define SP_ROW_W ((TILE) <= 16 ? (TILE) : 0)
#define SP_BYTE_A (SP_ROW_A * 32 * 2)
#define SP_BYTE_W (SP_ROW_W * 32 * 2)

int main(void) {
    /* PPCI does not cover volatile cfg-table pointer loads yet; keep lw_s from cfg base. */
    int cfg = (int)CFG_BASE;
    int A_GMEM;
    int W_GMEM;
    int C_GMEM;
    int gM;
    int gN;
    int gK;
    int M_tiles;
    int N_tiles;
    int K_tiles;
    int tile_sz;

    asm("lw_s %0, 0(%1)" : "=r"(A_GMEM) : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(W_GMEM) : "r"(cfg));
    asm("lw_s %0, 8(%1)" : "=r"(C_GMEM) : "r"(cfg));
    asm("lw_s %0, 12(%1)" : "=r"(gM) : "r"(cfg));
    asm("lw_s %0, 16(%1)" : "=r"(gN) : "r"(cfg));
    asm("lw_s %0, 20(%1)" : "=r"(gK) : "r"(cfg));
    asm("lw_s %0, 24(%1)" : "=r"(M_tiles) : "r"(cfg));
    asm("lw_s %0, 28(%1)" : "=r"(N_tiles) : "r"(cfg));
    asm("lw_s %0, 32(%1)" : "=r"(K_tiles) : "r"(cfg));
    asm("lw_s %0, 36(%1)" : "=r"(tile_sz) : "r"(cfg));

    if (tile_sz != TILE) {
        asm("halt");
        return 0;
    }

    int all_mask = -1;
    int sp_c = 0;
    volatile int sdma_ctl_w = SDMA_RS3(0, TILE, TILE, gN);
    volatile int sdma_ctl_a = SDMA_RS3(0, TILE, TILE, gK);
    volatile int sdma_ctl_c = SDMA_RS3(1, TILE, TILE, gN);

    int mi = 0;
    while (mi < M_tiles) {
        int ni = 0;
        while (ni < N_tiles) {
            int c_off = mi * tile_sz * gN + ni * tile_sz;
            int c_addr = C_GMEM + c_off * 2;

            scpad_load(sp_c, c_addr, sdma_ctl_c);

            int w_off_first = ni * tile_sz;
            scpad_load(SP_BYTE_W, W_GMEM + w_off_first * 2, sdma_ctl_w);

            int ki = 0;
            while (ki < K_tiles) {
                int a_addr = A_GMEM + (mi * tile_sz * gK + ki * tile_sz) * 2;

                int wi = 0;
                while (wi < TILE) {
                    vec wvec = vector_load(0, SP_ROW_W + wi, TILE_M1, 0);
                    load_weights(wvec);
                    wi = wi + 1;
                }

                scpad_load(SP_BYTE_A, a_addr, sdma_ctl_a);

                int ri = 0;
                while (ri < TILE) {
                    vec a_row = vector_load(0, SP_ROW_A + ri, TILE_M1, 0);
                    vec c_row = vector_load(0, ri, TILE_M1, 1);
                    vec result = gemm(a_row, c_row, all_mask);
                    vector_store(result, 0, ri, TILE_M1, 1);
                    ri = ri + 1;
                }

                ki = ki + 1;
                if (ki < K_tiles) {
                    int w_off_n = ki * tile_sz * gN + ni * tile_sz;
                    scpad_load(SP_BYTE_W, W_GMEM + w_off_n * 2, sdma_ctl_w);
                }
            }

            scpad_store(sp_c, c_addr, sdma_ctl_c);
            ni = ni + 1;
        }
        mi = mi + 1;
    }

    asm("halt");
    return 0;
}
