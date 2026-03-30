inline int mult_int(int a, int b){
    return a * b;
}

int main(){
    vec vr;

    vec v1;
    int vec_addr1 = 0xABCD;

    asm("vreg_ld %0, %1, %2, 31, 1"
    : "=v"(v1)
    : "r"(vec_addr1), "r"(1));

    vec v2;
    int vec_addr2 = 0xDEAD;

    asm("vreg_ld %0, %1, %2, 31, 1"
    : "=v"(v2)
    : "r"(vec_addr2), "r"(1));

    float c = 3.6;

    int mask = mult_int(3, 6);

    vec v3 = vec_op_masked("+", v2, c, 5);

    vec v4 = vec_op_masked("*", v3, v2, mask);

    v4 = vec_op_masked("GEMM", v3, v4, mask);

    // vec v5 = vec_op_masked("SQRT", v1, 0.0, 10);

    vec v5 = vec_op_masked("RMIN", v4, 0.0, 10);


    // These correctly error when uncommented.
    // v5 = vec_op_masked("RSUM", v5, v4, 10);

    // v5 = vec_op_masked("BS", v5, v4, 5);


    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, %2, 31, 1"
    : 
    : "v"(v5), "r"(store_addr), "r"(1));

    // asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    // : 
    // : "v"(vr), "r"(store_addr));

    return 0;
}