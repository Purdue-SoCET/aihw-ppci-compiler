#define CFG_BASE  0x3C
#define WIDTH_M1  7
#define H_IN      8
#define H_OUT     4
#define CHANNELS  1
#define STRIDE    2
#define POOL      2
#define IN_CH_BYTES   (8 * 8 * 2)
#define OUT_CH_BYTES  (4 * 8 * 2)

int main() {
    int cfg = CFG_BASE;
    int IN_BASE;
    int OUT_BASE;
    asm("lw_s %0, 0(%1)" : "=r"(IN_BASE)  : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(OUT_BASE) : "r"(cfg));

    int sp = 0;
    int all_mask = -1;
    int ncols = 1;

    int sdma_in;
    asm("li_s %0, 242221063" : "=r"(sdma_in));

    int sdma_out;
    asm("li_s %0, 108003335" : "=r"(sdma_out));

    vec zero_vec = vector_load(0, ncols, 7, 0);
    zero_vec = vec_op_masked("*", zero_vec, 0.0, all_mask);

    int ch = 0;
    while (ch < CHANNELS) {
        int in_ptr = IN_BASE + ch * IN_CH_BYTES;
        int out_ptr = OUT_BASE + ch * OUT_CH_BYTES;

        scpad_load(sp, in_ptr, sdma_in);

        int oh = 0;
        while (oh < H_OUT) {
            int in_row = oh * STRIDE;

            vec best = vector_load(in_row, ncols, 7, 0);

            int r1 = in_row + 1;
            vec v1 = vector_load(r1, ncols, 7, 0);
            int gt1 = make_mask(">", v1, best, all_mask);
            best = vec_op_masked("+", v1, zero_vec, gt1);

            vector_store(best, oh, ncols, 7, 0);
            oh = oh + 1;
        }

        scpad_store(sp, out_ptr, sdma_out);
        ch = ch + 1;
    }

    asm("halt");
    return 0;
}
