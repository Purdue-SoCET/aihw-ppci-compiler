#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_FLAT_M1  (K_FLAT - 1)
#define K_OUT_M1   (K_OUT - 1)
#define ALL_MASK   0xFFFFF

/* Conv-as-GEMM: software-pipelined row schedule (M fixed at 4).
 * Uses explicit interleaving like conv_pipelined_unrolled.c instead of a rolled
 * double-buffer loop — PPCI -O2 has miscompiled that pattern on some platforms
 * (wrong results + different packet counts vs Linux).
 * Weight load stays rolled to differ from conv_pipelined_unrolled.c. */
int main() {
    int cfg_ptr = CFG_BASE;

    int a_gmem; int a_sp; int w_gmem; int w_sp; int c_gmem; int c_sp;

    asm("lw_s %0, 0(%1)"  : "=r"(a_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 4(%1)"  : "=r"(a_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 8(%1)"  : "=r"(w_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 12(%1)" : "=r"(w_sp)   : "r"(cfg_ptr));
    asm("lw_s %0, 16(%1)" : "=r"(c_gmem) : "r"(cfg_ptr));
    asm("lw_s %0, 20(%1)" : "=r"(c_sp)   : "r"(cfg_ptr));

    int sdma_ctl_a;
    int sdma_ctl_w;
    int sdma_ctl_c;
    asm("li_s %0, 127926298" : "=r"(sdma_ctl_a));
    asm("li_s %0, 1949302787" : "=r"(sdma_ctl_w));
    asm("li_s %0, 1177550851" : "=r"(sdma_ctl_c));

    scpad_load(a_sp, a_gmem, sdma_ctl_a);
    scpad_load(w_sp, w_gmem, sdma_ctl_w);

    int wi = 0;
    while (wi < K_OUT) {
        vec wvec = vector_load(w_sp, wi, K_FLAT_M1, 1);
        load_weights(wvec);
        wi = wi + 1;
    }

    scpad_load(c_sp, c_gmem, sdma_ctl_c);

    int all_mask = ALL_MASK;

    vec a0 = vector_load(a_sp, 0, K_FLAT_M1, 0);
    vec c0 = vector_load(c_sp, 0, K_OUT_M1, 1);
    vec a1 = vector_load(a_sp, 1, K_FLAT_M1, 0);
    vec c1 = vector_load(c_sp, 1, K_OUT_M1, 1);

    vec r0 = gemm(a0, c0, all_mask);
    vector_store(r0, c_sp, 0, K_OUT_M1, 1);

    vec a2 = vector_load(a_sp, 2, K_FLAT_M1, 0);
    vec c2 = vector_load(c_sp, 2, K_OUT_M1, 1);

    vec r1 = gemm(a1, c1, all_mask);
    vector_store(r1, c_sp, 1, K_OUT_M1, 1);

    vec a3 = vector_load(a_sp, 3, K_FLAT_M1, 0);
    vec c3 = vector_load(c_sp, 3, K_OUT_M1, 1);

    vec r2 = gemm(a2, c2, all_mask);
    vector_store(r2, c_sp, 2, K_OUT_M1, 1);

    vec r3 = gemm(a3, c3, all_mask);
    vector_store(r3, c_sp, 3, K_OUT_M1, 1);

    scpad_store(c_sp, c_gmem, sdma_ctl_c);

    asm("halt");
    return 0;
}
