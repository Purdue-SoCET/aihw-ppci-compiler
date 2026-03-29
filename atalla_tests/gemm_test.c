/*
 * gemm_test.c - check gemm_vv operand count
 *
 * Verifies the compiler emits all 5 operands for gemm_vv
 * (vd, vs1, vs2, mask, sac). The functional sim rejects
 * the instruction if sac is missing.
 *
 * See COMPILER_ISSUES.md section 2 for details.
 */

int main() {
    int a_addr = 0x100;
    int c_addr = 0x200;
    int msk = 0xFFFFFFFF;

    vec a_vec;
    asm("vreg_ld %0, %1, 31, 0, 0, 0, 0" : "=v"(a_vec) : "r"(a_addr));

    vec c_vec;
    asm("vreg_ld %0, %1, 31, 0, 0, 0, 0" : "=v"(c_vec) : "r"(c_addr));

    vec result = gemm(a_vec, c_vec, msk);

    asm("vreg_st %0, %1, 31, 0, 0, 0, 0" : : "v"(result), "r"(c_addr));

    asm("halt");
    return 0;
}
