int main(){
    vec v1;
    int vec_addr1 = 0xABCD;

    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v1)
    : "r"(vec_addr1));

    vec v2;
    int vec_addr2 = 0xDEAD;

    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v2)
    : "r"(vec_addr2));

    vec v3 = v1 + v2;
    vec v4 = v3 - v2;
    vec v5 = v4 * v2;
    vec v6 = v5;

    int mask = 0b101;


    vec v10 = gemm(v5, v6, mask);

    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v10), "r"(store_addr));

    return 0;
}