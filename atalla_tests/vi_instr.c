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

    int a = 10;
    int b = 5;

    int c = a * b;
    // TODO: add support for floats
    // float a = 1.5;

    vec v3 = v1 + c;

    vr = v1 - c;

    vr = vr * c;

    vr = vr / c;

    // exp, sqrt, rsum, rmin, rmax probably all need intrinsics

    // vr = vr ** c;

    vr = vr >> 5;

    // vr = ~vr;


    

    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(vr), "r"(store_addr));

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v3), "r"(store_addr));

    return 0;
}