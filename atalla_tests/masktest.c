int main(){
    vec v1;
    int vec_addr1 = 0xABCD;

    int a = 0xAAAA;
    int b = 0xBBBB;

    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v1)
    : "r"(vec_addr1));

    vec v2;
    int vec_addr2 = 0xDEAD;
    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v2)
    : "r"(vec_addr2));

    int full_mask;

    asm("mv_mts %0, m0"
    : "=r"(full_mask));


    int m = make_mask("<", v1, 5.0, full_mask);
    int m1 = make_mask("==", v1, v2, full_mask);

    vec v3 = vec_op_masked("*", v1, v2, m);
    vec v4 = gemm(v3, v2, m1);

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v3), "r"(vec_addr1));

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v4), "r"(vec_addr1));

    return m;
}