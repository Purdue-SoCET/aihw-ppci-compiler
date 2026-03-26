/* vector_test.c - exercises VV, VS, VI, masked, and memory vector instructions */

int main() {
    /* --- Load two vectors from memory --- */
    vec v1;
    int addr1 = 0xABCD;
    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
        : "=v"(v1)
        : "r"(addr1));

    vec v2;
    int addr2 = 0xDEAD;
    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
        : "=v"(v2)
        : "r"(addr2));

    /* --- VV: vector-vector arithmetic --- */
    vec v3 = v1 + v2;   /* add_vv  */
    vec v4 = v3 - v2;   /* sub_vv  */
    vec v5 = v4 * v1;   /* mul_vv  */
    vec v6 = v5 / v1;   /* div_vv  */

    /* --- VV: vector-vector bitwise --- */
    vec v7 = v6 & v5;   /* and_vv  */
    vec v8 = v7 | v1;   /* or_vv   */
    vec v9 = v8 ^ v2;   /* xor_vv  */

    /* --- VS: vector-scalar arithmetic --- */
    float s = 3.5;
    vec v10 = v9 + s;   /* add_vs  */
    vec v11 = v10 - s;  /* sub_vs  */
    vec v12 = v11 * s;  /* mul_vs  */
    vec v13 = v12 / s;  /* div_vs  */

    /* --- VI: vector-immediate arithmetic --- */
    vec v14 = v13 + 4.0;  /* addi_vi */
    vec v15 = v14 - 2.0;  /* subi_vi */
    vec v16 = v15 * 3.0;  /* muli_vi */
    vec v17 = v16 / 2.0;  /* divi_vi */

    /* --- VI: bitwise NOT --- */
    vec v18 = ~v17;        /* not_vi  */

    /* --- Masked operations (vec_op_masked) --- */
    int mask = 0b111;
    vec v19 = vec_op_masked("+", v18, v1, mask);      /* add_vv masked  */
    vec v20 = vec_op_masked("*", v19, v2, mask);      /* mul_vv masked  */
    vec v21 = vec_op_masked("GEMM", v19, v20, mask);  /* gemm_vv masked */
    vec v22 = vec_op_masked("SQRT", v21, 0.0, mask);  /* sqrti_vi       */
    vec v23 = vec_op_masked("RSUM", v22, 0.0, mask);  /* rsum_vi        */
    vec v24 = vec_op_masked("RMIN", v23, 0.0, mask);  /* rmin_vi        */
    vec v25 = vec_op_masked("RMAX", v24, 0.0, mask);  /* rmax_vi        */

    /* --- Store result --- */
    int store_addr = 0xAAAA;
    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
        :
        : "v"(v25), "r"(store_addr));

    return 0;
}
