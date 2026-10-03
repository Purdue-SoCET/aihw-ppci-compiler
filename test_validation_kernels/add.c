#define CFG_BASE  0x3C
#define ROWS      4
#define ALL_MASK  0xFFFFFFFF

int main() {
    int cfg = CFG_BASE;
    int A_GMEM;
    int B_GMEM;
    int C_GMEM;
    A_GMEM = *(volatile int *)(cfg + 0);
    B_GMEM = *(volatile int *)(cfg + 4);
    C_GMEM = *(volatile int *)(cfg + 8);

    int sp = 0;
    int all_mask = ALL_MASK;

    int sdma_ctl_sp0;
    sdma_ctl_sp0 = 133169183u;
    int sdma_ctl_sp1;
    sdma_ctl_sp1 = 1206911007u;

    scpad_load(sp, A_GMEM, sdma_ctl_sp0);
    scpad_load(sp, B_GMEM, sdma_ctl_sp1);

    int row = 0;
    while (row < ROWS) {
        vec a = vector_load(0, row, 31, 0);
        vec b = vector_load(0, row, 31, 1);
        vec c = vec_op_masked("+", a, b, all_mask);
        vector_store(c, 0, row, 31, 0);
        row = row + 1;
    }

    scpad_store(sp, C_GMEM, sdma_ctl_sp0);

    atalla_halt();
    return 0;
}
