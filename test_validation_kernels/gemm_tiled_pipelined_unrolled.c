#define CFG_BASE  0x3C
#define TILE      4
#define TILE_M1   3

/* Tiled GEMM: K-tile W prefetch + manual unroll of TILE weight loads and row GEMMs. */
int main() {
    int cfg = CFG_BASE;
    int A_GMEM; int W_GMEM; int C_GMEM;
    int gM; int gN; int gK;
    int M_tiles; int N_tiles; int K_tiles; int tile_sz;

    A_GMEM = atalla_load_u32(cfg + 0);
    W_GMEM = atalla_load_u32(cfg + 4);
    C_GMEM = atalla_load_u32(cfg + 8);
    gM = atalla_load_u32(cfg + 12);
    gN = atalla_load_u32(cfg + 16);
    gK = atalla_load_u32(cfg + 20);
    M_tiles = atalla_load_u32(cfg + 24);
    N_tiles = atalla_load_u32(cfg + 28);
    K_tiles = atalla_load_u32(cfg + 32);
    tile_sz = atalla_load_u32(cfg + 36);

    int all_mask = -1;
    int sp_base = 0;
    /* SDMA ctl: [31:30] sid, [29:25] rows-1, [24:20] cols-1, [19:0] DRAM row stride-1.
       4x4 tile out of 8-wide A/W/C matrices => stride field 7 (sid 0 / sid 1). */
    int sdma_ctl_sp0;
    sdma_ctl_sp0 = atalla_const_u32(103809031u);
    int sdma_ctl_sp1;
    sdma_ctl_sp1 = atalla_const_u32(1177550855u);

    int mi = 0;
    while (mi < M_tiles) {
        int ni = 0;
        while (ni < N_tiles) {
            int c_off = mi * tile_sz * gN + ni * tile_sz;
            int c_addr = C_GMEM + c_off * 2;

            scpad_load(sp_base, c_addr, sdma_ctl_sp1);

            int w_off_first = 0 * tile_sz * gN + ni * tile_sz;
            scpad_load(sp_base, W_GMEM + w_off_first * 2, sdma_ctl_sp0);

            int ki = 0;
            while (ki < K_tiles) {
                int a_addr = A_GMEM + (mi * tile_sz * gK + ki * tile_sz) * 2;

                {
                    vec w0 = vector_load(0, 0, TILE_M1, 0);
                    load_weights(w0);
                    vec w1 = vector_load(0, 1, TILE_M1, 0);
                    load_weights(w1);
                    vec w2 = vector_load(0, 2, TILE_M1, 0);
                    load_weights(w2);
                    vec w3 = vector_load(0, 3, TILE_M1, 0);
                    load_weights(w3);
                }

                scpad_load(sp_base, a_addr, sdma_ctl_sp0);

                {
                    vec a0 = vector_load(0, 0, TILE_M1, 0);
                    vec c0 = vector_load(0, 0, TILE_M1, 1);
                    vec r0 = gemm(a0, c0, all_mask);
                    vector_store(r0, 0, 0, TILE_M1, 1);

                    vec a1 = vector_load(0, 1, TILE_M1, 0);
                    vec c1 = vector_load(0, 1, TILE_M1, 1);
                    vec r1 = gemm(a1, c1, all_mask);
                    vector_store(r1, 0, 1, TILE_M1, 1);

                    vec a2 = vector_load(0, 2, TILE_M1, 0);
                    vec c2 = vector_load(0, 2, TILE_M1, 1);
                    vec r2 = gemm(a2, c2, all_mask);
                    vector_store(r2, 0, 2, TILE_M1, 1);

                    vec a3 = vector_load(0, 3, TILE_M1, 0);
                    vec c3 = vector_load(0, 3, TILE_M1, 1);
                    vec r3 = gemm(a3, c3, all_mask);
                    vector_store(r3, 0, 3, TILE_M1, 1);
                }

                ki = ki + 1;
                if (ki < K_tiles) {
                    int w_off_next = ki * tile_sz * gN + ni * tile_sz;
                    scpad_load(sp_base, W_GMEM + w_off_next * 2, sdma_ctl_sp0);
                }
            }

            scpad_store(sp_base, c_addr, sdma_ctl_sp1);
            ni = ni + 1;
        }
        mi = mi + 1;
    }

    atalla_halt();
    return 0;
}
