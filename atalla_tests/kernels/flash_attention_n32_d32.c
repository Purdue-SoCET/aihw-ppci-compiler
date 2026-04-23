#define N 32
#define N_M1 31

#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

/*
 * Flash-attention matched contract (N=32, D=32, non-causal):
 *   Q @ K^T -> row softmax -> (softmax probs) @ V
 * DRAM layout matches functional_sim/kernels/build_flash_attention.py:
 *   scale @ 0x20 (f32), Q @ 0x1000, K @ 0x3000, V @ 0x5000, O @ 0x7000
 * Scratchpad:
 *   sid0 row 0 used for single-row DMA / vector loads.
 */
int main() {
    const int SCALE_ADDR = 0x0C00;
    const int Q_GMEM = 0x1000;
    const int K_GMEM = 0x3000;
    const int V_GMEM = 0x5000;
    const int O_GMEM = 0x7000;
    const int sp = 0;
    const int row_bytes = N * 2;

    int all_mask = -1;
    float scale = *(volatile float*)SCALE_ADDR;

    volatile int sdma_ctl_row = SDMA_RS3(0, 1, N, N);
    volatile int sdma_ctl_tile = SDMA_RS3(0, N, N, N);

    /* Match flash generator: warm weight FIFO before first real block load. */
    scpad_load(sp, Q_GMEM, sdma_ctl_row);
    vec warm = vector_load(sp, 0, N_M1, 0);
    int w = 0;
    while (w < N) {
        load_weights(warm);
        w = w + 1;
    }

    int qi = 0;
    while (qi < N) {
        int q_addr = Q_GMEM + qi * row_bytes;
        int o_addr = O_GMEM + qi * row_bytes;

        scpad_load(sp, K_GMEM, sdma_ctl_tile);
        int col = 0;
        while (col < N) {
            int idx = (N - 1) - col;
            vec k_row = vector_load(sp, idx, N_M1, 1);
            load_weights(k_row);
            col = col + 1;
        }

        scpad_load(sp, q_addr, sdma_ctl_row);
        vec q_row = vector_load(sp, 0, N_M1, 0);
        vec zero = vector_load(sp, 0, N_M1, 0);
        zero = vec_op_masked("*", zero, 0.0, all_mask);
        vec score = gemm(q_row, zero, all_mask);
        score = vec_op_masked("*", score, scale, all_mask);

        vec vmax = vec_op_masked("RMAX", score, 0.0, all_mask);
        vec shifted = vec_op_masked("-", score, vmax, all_mask);
        vec exp_v = vec_op_masked("EXP", shifted, 0.0, all_mask);
        vec sum_v = vec_op_masked("RSUM", exp_v, 0.0, all_mask);
        float inv_sum = 1.0 / sum_v[0];
        vec probs = vec_op_masked("*", exp_v, inv_sum, all_mask);

        scpad_load(sp, V_GMEM, sdma_ctl_tile);
        col = 0;
        while (col < N) {
            int idx = (N - 1) - col;
            vec v_row = vector_load(sp, idx, N_M1, 0);
            load_weights(v_row);
            col = col + 1;
        }

        vec zero_out = vector_load(sp, 0, N_M1, 0);
        zero_out = vec_op_masked("*", zero_out, 0.0, all_mask);
        vec out = gemm(probs, zero_out, all_mask);
        vector_store(out, sp, 0, N_M1, 0);
        scpad_store(sp, o_addr, sdma_ctl_row);

        qi = qi + 1;
    }

    /* Explicit simulator termination (outside hot loops). */
    asm("halt");
    return 0;
}
