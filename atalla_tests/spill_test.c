/*
 * spill_test.c - vector register spill repro
 *
 * Basic ReLU: needs 4 vec variables live at once (v_data, v_zero,
 * comparison result, v_result). Compiler spills with num_cols=0
 * so only 1/32 elements survive the round-trip through scratchpad.
 *
 * See COMPILER_ISSUES.md section 1 for details.
 */

int main() {
    int addr = 0x100;
    int out_addr = 0x200;
    int full_mask = 0xFFFFFFFF;
    int ncols = 1;

    /* load input vector from scratchpad */
    vec v_data;
    asm("vreg_ld %0, %1, %2, 31, 0" : "=v"(v_data) : "r"(addr), "r"(ncols));

    /* create zero vector: 0.0 added to data*0 */
    vec v_zero = vec_op_masked("+", v_data, 0.0, full_mask);
    v_zero = vec_op_masked("*", v_zero, 0.0, full_mask);

    /* compare: mask = (data > 0) */
    int pos_mask = make_mask(">", v_data, v_zero, full_mask);

    /* masked add: result = data * 1.0 where positive, else 0 */
    vec v_result = vec_op_masked("*", v_data, 1.0, pos_mask);

    /* store result */
    asm("vreg_st %0, %1, %2, 31, 0" : : "v"(v_result), "r"(out_addr), "r"(ncols));

    asm("halt");
    return 0;
}
