
// int vec_addr1 = 0xABCD;

int main(){
    // int a = 5;

    // int b = 3;

    // int c;

    // asm("mul_s %0, %1, %2"
    // : "=r"(c)
    // : "r"(a), "r"(b));

    vec v1;
    int vec_addr1 = 0xABCD;

    int a = 0xAAAA;
    int b = 0xBBBB;

    asm("scpad_ld %0, %1, 0, 0, 0"
    : 
    : "r"(a), "r"(b));

    asm("scpad_st %0, %1, 0, 0, 0"
    : 
    : "r"(a), "r"(b));

    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v1)
    : "r"(vec_addr1));

    vec v2;
    int vec_addr2 = 0xDEAD;

    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v2)
    : "r"(vec_addr2));

    vec v3 = v1 + v2;

    vec v4 = v1 * v2;

    v4 = gemm(v3, v4, 10);

    // gemm(v3, v1, v2);

    

    return 0;

    // gemm(v3, v2, v1);
}