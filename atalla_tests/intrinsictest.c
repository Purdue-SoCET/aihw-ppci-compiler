inline int mult_int(int a, int b){
    return a * b;
}

int main(){
    vec vr;

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

    float c = 3.6;

    int mask = mult_int(3, 6);

    vec v3 = vec_op_masked("+", v2, c, 5);

    vec v4 = vec_op_masked("*", v3, v2, mask);

    v4 = vec_op_masked("GEMM", v3, v4, mask);


    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v4), "r"(store_addr));

    // asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    // : 
    // : "v"(vr), "r"(store_addr));

    return 0;
}