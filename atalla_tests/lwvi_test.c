/*
 * lwvi_test.c - lw_vi weight preload via inline asm
 *
 * GEMM requires preloading weight rows into the systolic array
 * buffer with lw_vi before calling gemm_vv. No C intrinsic
 * exists for lw_vi yet, so this uses inline asm as a workaround.
 * Note the spill issue also affects the vec operand here.
 */

int main() {
    int w_sp = 0x400;
    int a_sp = 0x100;
    int c_sp = 0x200;
    int msk = 0xFFFFFFFF;
    int ncols = 1;
    int sdma_ctl = 0b00101010101010;

    /* load weight tile from GMEM to scratchpad */
    asm("scpad_ld %0, %1, %2" : : "r"(w_sp), "r"(0x1000), "r"(sdma_ctl));

    /* preload 4 weight rows into systolic array buffer */
    vec dummy;
    asm("lw_vi %0, %0, 0, m0" : "=v"(dummy) : "v"(dummy));
    asm("lw_vi %0, %0, 1, m0" : "=v"(dummy) : "v"(dummy));
    asm("lw_vi %0, %0, 2, m0" : "=v"(dummy) : "v"(dummy));
    asm("lw_vi %0, %0, 3, m0" : "=v"(dummy) : "v"(dummy));

    /* GEMM after weight preload */
    vec a_vec;
    asm("vreg_ld %0, %1, %2, 31, 0" : "=v"(a_vec) : "r"(a_sp), "r"(ncols));

    vec c_vec;
    asm("vreg_ld %0, %1, %2, 31, 0" : "=v"(c_vec) : "r"(c_sp), "r"(ncols));

    vec result = gemm(a_vec, c_vec, msk);

    asm("vreg_st %0, %1, %2, 31, 0" : : "v"(result), "r"(c_sp), "r"(ncols));

    asm("halt");
    return 0;
}
