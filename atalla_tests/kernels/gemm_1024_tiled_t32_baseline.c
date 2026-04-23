#define CFG_BASE  0x00080000u
#define TILE      32
#define TILE_M1   31

#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

#define SP_ROW_A 0
#define SP_ROW_W ((TILE) <= 16 ? (TILE) : 0)
#define SP_BYTE_A (SP_ROW_A * 32 * 2)
#define SP_BYTE_W (SP_ROW_W * 32 * 2)

/*
 * TILE=32 baseline GEMM with configurable weight reuse across M tiles.
 * cfg[10] = reuse_m_tiles in [1,32].
 */
int main(void) {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int A_GMEM = cfg[0];
    int W_GMEM = cfg[1];
    int C_GMEM = cfg[2];
    int gM = cfg[3];
    int gN = cfg[4];
    int gK = cfg[5];
    int M_tiles = cfg[6];
    int N_tiles = cfg[7];
    int K_tiles = cfg[8];
    int tile_sz = cfg[9];
    int reuse_m_tiles = cfg[10];

    if (reuse_m_tiles < 1) reuse_m_tiles = 1;
    if (reuse_m_tiles > 32) reuse_m_tiles = 32;
    if (reuse_m_tiles > M_tiles) reuse_m_tiles = M_tiles;

    if (tile_sz != TILE) {
        return 0;
    }

    int all_mask = -1;
    volatile int vbase = 0;
    int sp_c = 0;
    volatile int sdma_ctl_w = SDMA_RS3(0, TILE, TILE, gN);
    volatile int sdma_ctl_a = SDMA_RS3(0, TILE, TILE, gK);
    volatile int sdma_ctl_c = SDMA_RS3(1, TILE, TILE, gN);

    int elem_b = 2;
    int tile_b = tile_sz * elem_b;
    int c_m_stride_b = tile_sz * gN * elem_b;
    int a_m_stride_b = tile_sz * gK * elem_b;
    int w_k_stride_b = tile_sz * gN * elem_b;
    int a_k_stride_b = tile_sz * elem_b;

    for (int ni = 0; ni < N_tiles; ni = ni + 1) {
        int c_n_base_b = C_GMEM + ni * tile_b;
        int w_n_base_b = W_GMEM + ni * tile_b;

        for (int ki = 0; ki < K_tiles; ki = ki + 1) {
            int w_addr = w_n_base_b + ki * w_k_stride_b;
            int a_k_base_b = A_GMEM + ki * a_k_stride_b;

            for (int mi_base = 0; mi_base < M_tiles; ) {
                scpad_load(SP_BYTE_W, w_addr, sdma_ctl_w);

                for (int wi = 0; wi < TILE; wi = wi + 4) {
                    vec wvec0 = vector_load(vbase, SP_ROW_W + wi + 0, TILE_M1, 0);
                    load_weights(wvec0);
                    vec wvec1 = vector_load(vbase, SP_ROW_W + wi + 1, TILE_M1, 0);
                    load_weights(wvec1);
                    vec wvec2 = vector_load(vbase, SP_ROW_W + wi + 2, TILE_M1, 0);
                    load_weights(wvec2);
                    vec wvec3 = vector_load(vbase, SP_ROW_W + wi + 3, TILE_M1, 0);
                    load_weights(wvec3);
                }

                int mi_lim = mi_base + reuse_m_tiles;
                if (mi_lim > M_tiles) mi_lim = M_tiles;

                int c_addr = c_n_base_b + mi_base * c_m_stride_b;
                int a_addr = a_k_base_b + mi_base * a_m_stride_b;
                for (int mi = mi_base; mi < mi_lim; mi = mi + 1) {
                    scpad_load(sp_c, c_addr, sdma_ctl_c);
                    scpad_load(SP_BYTE_A, a_addr, sdma_ctl_a);

                    for (int ri = 0; ri < TILE; ri = ri + 4) {
                        int rr = ri;
                        vec a_row0 = vector_load(vbase, SP_ROW_A + rr, TILE_M1, 0);
                        vec c_row0 = vector_load(vbase, rr, TILE_M1, 1);
                        vec r0 = gemm(a_row0, c_row0, all_mask);
                        vector_store(r0, vbase, rr, TILE_M1, 1);

                        rr = ri + 1;
                        vec a_row1 = vector_load(vbase, SP_ROW_A + rr, TILE_M1, 0);
                        vec c_row1 = vector_load(vbase, rr, TILE_M1, 1);
                        vec r1 = gemm(a_row1, c_row1, all_mask);
                        vector_store(r1, vbase, rr, TILE_M1, 1);

                        rr = ri + 2;
                        vec a_row2 = vector_load(vbase, SP_ROW_A + rr, TILE_M1, 0);
                        vec c_row2 = vector_load(vbase, rr, TILE_M1, 1);
                        vec r2 = gemm(a_row2, c_row2, all_mask);
                        vector_store(r2, vbase, rr, TILE_M1, 1);

                        rr = ri + 3;
                        vec a_row3 = vector_load(vbase, SP_ROW_A + rr, TILE_M1, 0);
                        vec c_row3 = vector_load(vbase, rr, TILE_M1, 1);
                        vec r3 = gemm(a_row3, c_row3, all_mask);
                        vector_store(r3, vbase, rr, TILE_M1, 1);
                    }

                    scpad_store(sp_c, c_addr, sdma_ctl_c);
                    c_addr = c_addr + c_m_stride_b;
                    a_addr = a_addr + a_m_stride_b;
                }

                mi_base = mi_lim;
            }
        }
    }

    asm("halt");
    return 0;
}
