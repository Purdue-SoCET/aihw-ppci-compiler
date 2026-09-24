/*
 * hazard_test.c - rs1_rd1 read/write hazard repro
 *
 * scpad_ld's rs1_rd1 operand is both read (source address) and
 * written (auto-incremented by hardware). The compiler only marks
 * it as read, so the register allocator doesn't know the value
 * changed. Under register pressure it could reuse the stale value.
 *
 * See COMPILER_ISSUES.md section 4 for details.
 */

int main() {
    int src_gmem = 0x1000;
    int dst_sp   = 0x100;
    int dst_sp2  = 0x200;
    int sdma_ctl = 0b00101010101010;

    /* first DMA: hw auto-increments dst_sp after transfer */
    asm("scpad_ld %0, %1, %2" : : "r"(dst_sp), "r"(src_gmem), "r"(sdma_ctl));

    /* compiler doesn't know dst_sp changed, may reuse stale value */
    int next_addr = dst_sp + 128;

    /* second DMA with computed address */
    asm("scpad_ld %0, %1, %2" : : "r"(next_addr), "r"(src_gmem), "r"(sdma_ctl));

    asm("halt");
    return 0;
}
