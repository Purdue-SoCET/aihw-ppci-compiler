#define CFG_BASE  0x3C
#define ROWS      4
#define ALL_MASK  0xFFFFFFFF

int main() {
    int cfg = CFG_BASE;
    int A_GMEM;
    int B_GMEM;
    int C_GMEM;
    asm("lw_s %0, 0(%1)" : "=r"(A_GMEM)  : "r"(cfg));
    asm("lw_s %0, 4(%1)" : "=r"(B_GMEM)  : "r"(cfg));
    asm("lw_s %0, 8(%1)" : "=r"(C_GMEM) : "r"(cfg));

    int sp = 0;
    int all_mask = ALL_MASK;
    int ncols = 1;

    int sdma_ctl_sp0;
    asm("li_s %0, 133169183" : "=r"(sdma_ctl_sp0));
    int sdma_ctl_sp1;
    asm("li_s %0, 1206911007" : "=r"(sdma_ctl_sp1));

    scpad_load(sp, A_GMEM, sdma_ctl_sp0);
    scpad_load(sp, B_GMEM, sdma_ctl_sp1);

    int row = 0;
    while (row < ROWS) {
        vec a = vector_load(row, ncols, 31, 0);
        vec b = vector_load(row, ncols, 31, 1);
        vec c = vec_op_masked("+", a, b, all_mask);
        vector_store(c, row, ncols, 31, 0);
        row = row + 1;
    }

    scpad_store(sp, C_GMEM, sdma_ctl_sp0);

    asm("halt");
    return 0;
}
