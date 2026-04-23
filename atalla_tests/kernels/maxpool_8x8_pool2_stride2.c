/* 2x2 maxpool, stride 2, on an 8x8 BF16 tile (one channel).
 * Stage 1 (vertical): max over adjacent row pairs -> 4x8.
 * Stage 2 (horizontal): max over adjacent col pairs -> 4x4.
 * Output is 4 rows x 4 active columns (num_cols_m1=3). */
#define CFG_BASE  0x3C
#define WIDTH_M1  7
#define H_IN      8
#define H_OUT     4
#define OUT_WIDTH_M1 3
#define CHANNELS  1
#define STRIDE    2
#define POOL      2
#define IN_CH_BYTES   (8 * 8 * 2)
#define OUT_CH_BYTES  (4 * 4 * 2)
/* 8 active columns: use 0xFF not -1 so lanes 8..31 stay out of compare/add. */
#define LANE_MASK  255
#define M01  0x3
#define M23  0xC
#define M45  0x30
#define M67  0xC0
#define SDMA_RS3(sid, tile_rows, tile_cols, full_cols) \
    ((((sid) & 3) << 30) | ((((tile_rows) - 1) & 0x1F) << 25) | ((((tile_cols) - 1) & 0x1F) << 20) | (((full_cols) - 1) & 0xFFFFF))

int main() {
    volatile int* cfg = (volatile int*)CFG_BASE;
    int IN_BASE = cfg[0];
    int OUT_BASE = cfg[1];

    int sp = 0;
    int lane_mask = LANE_MASK;

    volatile int sdma_in = SDMA_RS3(0, 8, 8, 8);

    /* NR=NC=3 (4x4 tile), full DRAM stride = 4 cols -> raw_fc = 3 */
    volatile int sdma_out = SDMA_RS3(0, 4, 4, 4);

    vec zero_vec = vector_load(0, 0, WIDTH_M1, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, lane_mask);

    int ch = 0;
    while (ch < CHANNELS) {
        int in_ptr = IN_BASE + ch * IN_CH_BYTES;
        int out_ptr = OUT_BASE + ch * OUT_CH_BYTES;

        scpad_load(sp, in_ptr, sdma_in);

        int oh = 0;
        while (oh < H_OUT) {
            int in_row = oh * STRIDE;

            vec r0 = vector_load(0, in_row, WIDTH_M1, 0);
            int r1 = in_row + 1;
            vec r1v = vector_load(0, r1, WIDTH_M1, 0);
            /* max(r0, r1v): merge from r0, update only lanes where r1v > r0. */
            vec diff = vec_op_masked("-", r1v, r0, lane_mask);
            vec vmax = r0;
            vmax = vec_op_masked(
                "+",
                r0,
                diff,
                make_mask(">", r1v, r0, lane_mask)
            );
            vector_store(vmax, 0, oh, WIDTH_M1, 0);
            oh = oh + 1;
        }

        /* Horizontal 2-wide max over each of the 4 intermediate rows: 4x8 -> 4x4. */
        int row = 0;
        while (row < H_OUT) {
            vec r = vector_load(0, row, WIDTH_M1, 0);
            vec acc = zero_vec;
            vec p01 = vec_op_masked("RMAX", r, 0.0, M01);
            vec p23 = vec_op_masked("RMAX", r, 0.0, M23);
            vec p45 = vec_op_masked("RMAX", r, 0.0, M45);
            vec p67 = vec_op_masked("RMAX", r, 0.0, M67);

            float m0 = p01[0];
            float m1 = p23[0];
            float m2 = p45[0];
            float m3 = p67[0];

            acc = vec_op_masked("+", acc, m0, 0x1);
            acc = vec_op_masked("+", acc, m1, 0x2);
            acc = vec_op_masked("+", acc, m2, 0x4);
            acc = vec_op_masked("+", acc, m3, 0x8);

            vector_store(acc, 0, row, OUT_WIDTH_M1, 0);
            row = row + 1;
        }

        scpad_store(sp, out_ptr, sdma_out);
        ch = ch + 1;
    }

    return 0;
}
