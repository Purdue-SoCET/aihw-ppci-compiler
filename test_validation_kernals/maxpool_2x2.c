/* 2x2 maxpool, stride 2, on an 8x8 BF16 tile (one channel).
 *
 * Vertical pass: same masked add idiom as maxpool.c (two rows -> one).
 * Horizontal pass: four masked RMAX ops (masks 0x3, 0xC, 0x30, 0xC0) take
 * max over lane pairs (0,1),(2,3),(4,5),(6,7) without vmov.vts or scalar
 * compares — AtallaC bf16 branches / float ? : are currently miscompiled for
 * phi merge (see compiler IR for simple if (a>b)).
 *
 * Output layout: 4 scratchpad rows x 4 active BF16 columns (num_cols_m1 = 3).
 */
#define CFG_BASE      0x3C
#define WIDTH_M1      7
#define OUT_WIDTH_M1  3
#define H_IN          8
#define H_MID         4
#define CHANNELS      1
#define STRIDE        2
#define IN_CH_BYTES   (8 * 8 * 2)
#define OUT_CH_BYTES  (4 * 4 * 2)
#define LANE_MASK     255

#define M01  0x3
#define M23  0xC
#define M45  0x30
#define M67  0xC0

int main() {
    int cfg = CFG_BASE;
    int IN_BASE;
    int OUT_BASE;
    asm("lw_s %0, 0(%1)" : "=r"(IN_BASE)  : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(OUT_BASE) : "r"(cfg));

    int sp = 0;
    int lane_mask = LANE_MASK;

    int sdma_in;
    asm("li_s %0, 242221063" : "=r"(sdma_in));

    int sdma_out;
    /* NR=NC=3 (4x4 tile), full DRAM stride = 4 cols => raw_fc = 3 */
    asm("li_s %0, 103809027" : "=r"(sdma_out));

    vec zero_vec = vector_load(0, 0, WIDTH_M1, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, lane_mask);

    int ch = 0;
    while (ch < CHANNELS) {
        int in_ptr = IN_BASE + ch * IN_CH_BYTES;
        int out_ptr = OUT_BASE + ch * OUT_CH_BYTES;

        scpad_load(sp, in_ptr, sdma_in);

        int oh = 0;
        while (oh < H_MID) {
            int in_row = oh * STRIDE;

            vec best = vector_load(0, in_row, WIDTH_M1, 0);
            int r1 = in_row + 1;
            vec v1 = vector_load(0, r1, WIDTH_M1, 0);
            int gt1 = make_mask(">", v1, best, lane_mask);
            best = vec_op_masked("+", zero_vec, v1, gt1);

            vector_store(best, 0, oh, WIDTH_M1, 0);
            oh = oh + 1;
        }

        int row = 0;
        while (row < H_MID) {
            vec r = vector_load(0, row, WIDTH_M1, 0);

            vec p01 = vec_op_masked("RMAX", r, 0.0, M01);
            vec acc = vec_op_masked("+", zero_vec, p01, 0x1);

            vec p23 = vec_op_masked("RMAX", r, 0.0, M23);
            acc = vec_op_masked("+", zero_vec, p23, 0x2);

            vec p45 = vec_op_masked("RMAX", r, 0.0, M45);
            acc = vec_op_masked("+", zero_vec, p45, 0x4);

            vec p67 = vec_op_masked("RMAX", r, 0.0, M67);
            acc = vec_op_masked("+", zero_vec, p67, 0x8);

            vector_store(acc, 0, row, OUT_WIDTH_M1, 0);
            row = row + 1;
        }

        scpad_store(sp, out_ptr, sdma_out);
        ch = ch + 1;
    }

    asm("halt");
    return 0;
}
