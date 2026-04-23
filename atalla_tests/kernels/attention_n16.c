#define CFG_BASE  0x00080000
#define N         16
#define N_M1      15

#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

/*
 * Attention kernel matched to build_attention.py --n 16 --seed 0 contract:
 *   cfg[0]=Q, cfg[1]=K, cfg[2]=V, cfg[3]=O
 *   cfg[4]=SP0 base, cfg[5]=SP1 base
 */
int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int Q_GMEM = cfg[0];
    int K_GMEM = cfg[1];
    int V_GMEM = cfg[2];
    int O_GMEM = cfg[3];
    int q_sp = cfg[4];
    int k_sp = cfg[5];

    int all_mask = -1;
    int row_bytes = N * 2;

    volatile int sdma_ctl_q_row = SDMA_RS3(0, 1, N, N);
    volatile int sdma_ctl_k_tile = SDMA_RS3(1, N, N, N);
    volatile int sdma_ctl_v_tile = SDMA_RS3(0, N, N, N);
    volatile int sdma_ctl_o_row = SDMA_RS3(0, 1, N, N);

    scpad_load(k_sp, K_GMEM, sdma_ctl_k_tile);

    int qi = 0;
    while (qi < N) {
        int q_addr = Q_GMEM + qi * row_bytes;
        int o_addr = O_GMEM + qi * row_bytes;
        int col = 0;

        while (col < N) {
            vec k_row = vector_load(k_sp, col, N_M1, 1);
            load_weights(k_row);
            col = col + 1;
        }

        scpad_load(q_sp, q_addr, sdma_ctl_q_row);
        vec q_row = vector_load(q_sp, 0, N_M1, 0);
        vec zero = vector_load(q_sp, 0, N_M1, 0);
        zero = vec_op_masked("*", zero, 0.0, all_mask);
        vec score = gemm(q_row, zero, all_mask);

        vec vmax = vec_op_masked("RMAX", score, 0.0, all_mask);
        vec shifted = vec_op_masked("-", score, vmax, all_mask);
        vec exp_v = vec_op_masked("EXP", shifted, 0.0, all_mask);
        vec sum_v = vec_op_masked("RSUM", exp_v, 0.0, all_mask);
        float inv_sum = 1.0 / sum_v[0];
        vec probs = vec_op_masked("*", exp_v, inv_sum, all_mask);

        scpad_load(q_sp, V_GMEM, sdma_ctl_v_tile);
        col = 0;
        while (col < N) {
            vec v_row = vector_load(q_sp, col, N_M1, 0);
            load_weights(v_row);
            col = col + 1;
        }

        vec zero_out = vector_load(q_sp, 0, N_M1, 0);
        zero_out = vec_op_masked("*", zero_out, 0.0, all_mask);
        vec out = gemm(probs, zero_out, all_mask);
        vector_store(out, q_sp, 0, N_M1, 0);
        scpad_store(q_sp, o_addr, sdma_ctl_o_row);

        qi = qi + 1;
    }

    asm("halt");
    return 0;
}
