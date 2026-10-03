#define CFG_BASE   0x3C
#define M          4
#define K_FLAT     27
#define K_OUT      4
#define K_FLAT_M1  (K_FLAT - 1)
#define K_OUT_M1   (K_OUT - 1)
#define ALL_MASK   0xFFFFF

/* Conv-as-GEMM: pipelined + fully unrolled K_OUT weights and M output rows. */
int main() {
    int cfg_ptr = CFG_BASE;

    int a_gmem; int a_sp; int w_gmem; int w_sp; int c_gmem; int c_sp;

    a_gmem = *(volatile int *)(cfg_ptr + 0);
    a_sp = *(volatile int *)(cfg_ptr + 4);
    w_gmem = *(volatile int *)(cfg_ptr + 8);
    w_sp = *(volatile int *)(cfg_ptr + 12);
    c_gmem = *(volatile int *)(cfg_ptr + 16);
    c_sp = *(volatile int *)(cfg_ptr + 20);

    int sdma_ctl_a;
    int sdma_ctl_w;
    int sdma_ctl_c;
    sdma_ctl_a = 127926298u;
    sdma_ctl_w = 1949302787u;
    sdma_ctl_c = 1177550851u;

    scpad_load(a_sp, a_gmem, sdma_ctl_a);
    scpad_load(w_sp, w_gmem, sdma_ctl_w);

    {
        vec wv0 = vector_load(w_sp, 0, K_FLAT_M1, 1);
        load_weights(wv0);
        vec wv1 = vector_load(w_sp, 1, K_FLAT_M1, 1);
        load_weights(wv1);
        vec wv2 = vector_load(w_sp, 2, K_FLAT_M1, 1);
        load_weights(wv2);
        vec wv3 = vector_load(w_sp, 3, K_FLAT_M1, 1);
        load_weights(wv3);
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

    atalla_halt();
    return 0;
}
