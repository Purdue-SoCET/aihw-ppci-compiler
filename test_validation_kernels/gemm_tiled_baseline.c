#define CFG_BASE  0x3C
#define TILE      4
#define TILE_M1   3

/* Tiled GEMM: baseline — rolled loops, no K-tile W prefetch. */
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

            int ki = 0;
            while (ki < K_tiles) {
                int a_off = mi * tile_sz * gK + ki * tile_sz;
                int a_addr = A_GMEM + a_off * 2;

                int w_off = ki * tile_sz * gN + ni * tile_sz;
                int w_addr = W_GMEM + w_off * 2;

                scpad_load(sp_base, w_addr, sdma_ctl_sp0);

                int wi = 0;
                while (wi < TILE) {
                    vec wvec = vector_load(0, wi, TILE_M1, 0);
                    load_weights(wvec);
                    wi = wi + 1;
                }

                scpad_load(sp_base, a_addr, sdma_ctl_sp0);

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

            scpad_store(sp_base, c_addr, sdma_ctl_sp1);
            ni = ni + 1;
        }
        mi = mi + 1;
    }

    atalla_halt();
    return 0;
}
