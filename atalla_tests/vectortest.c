#include <stdint.h>

// Keep the signature intentionally similar in spirit to your scalar test.
// Arrays are required because vectors load/store multiple elements.
int vector_instruct_tests(const int *A, const int *B, int *C, int stride_bytes, int k_scalar) {
    // We'll compute a scalar checksum after vector work, to mirror your return style.
    int checksum = 0;

    // ===== VI: set mask/lanes =====
    // Enable the lowest 4 lanes via immediate mask 0xF (binary 1111).
    // This "documents" VI usage even if your current backend treats it as a no-op.
    asm volatile("mset.vi x9, x9, 0xF");

    // ===== VM: load vectors from memory =====
    // vreg.ld vd, base(rs1), aux/stride(rs2), imm
    // Here: load A into x10, B into x12, using the same stride and imm=0.
    asm volatile("vreg.ld x10, %0, %1, 0" :: "r"(A), "r"(stride_bytes));
    asm volatile("vreg.ld x12, %0, %1, 0" :: "r"(B), "r"(stride_bytes));

    // ===== VV: elementwise add =====
    // x10 = x10 + x12  (C = A + B)
    asm volatile("add.vv x10, x10, x12");

    // ===== VS: add a scalar k to every lane =====
    // x10 = x10 + k_scalar
    asm volatile("add.vs x10, x10, %0" :: "r"(k_scalar));

    // ===== VM: store result vector to memory =====
    asm volatile("vreg.st x10, %0, %1, 0" :: "r"(C), "r"(stride_bytes));

    // ===== Scalar checksum (like your r_acc + mem_val) =====
    // XOR all four elements, then add the last one (mimics your pattern of mixing ops).
    for (int i = 0; i < 4; ++i) checksum ^= C[i];
    checksum += C[3];

    return checksum;
}
