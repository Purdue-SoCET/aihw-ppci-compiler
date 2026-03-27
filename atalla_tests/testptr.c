// void str_vec(vec smth, int addr){
//     asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
//     : 
//     : "v"(smth), "r"(addr));
// }

void load_vec(vec* v, int addr){
    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(*v)
    : "r"(addr));
}

int main(){
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

    load_vec(&v1, vec_addr1);

    vec v2;
    int vec_addr2 = 0xDEAD;
    asm("vreg_ld %0, %1, 0, 0, 0, 0, 0"
    : "=v"(v2)
    : "r"(vec_addr2));

    int m = make_mask("<", v1, v2, 0);
    // int m = 0xFAF;

    vec v3 = v1 + v2;
    vec v4 = v1 * 3.6;
    v4 -= 5.9;
    v4 = vec_op_masked("EXP", v4, 0.0, 0xFFFA0000);
    v4 = gemm(v3, v4, 10);

    float elem = v4[5];

    // str_vec(v4, 0xABCD);

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v4), "r"(vec_addr1));

    return (int)elem;

    // gemm(v3, v2, v1);
}