/*
 * mask_test.c - mv_stm with hardcoded mask register
 *
 * Tests writing to a specific mask register (m1) via inline asm.
 * Hardcoded m1 in the template string works, but there's no
 * constraint letter to let the compiler allocate mask regs.
 *
 * See COMPILER_ISSUES.md section 3 for details.
 */
int main() {
    int mask_val = 0x0000FFFF;
    asm("mv_stm m1, %0" : : "r"(mask_val));
    asm("halt");
    return 0;
}
