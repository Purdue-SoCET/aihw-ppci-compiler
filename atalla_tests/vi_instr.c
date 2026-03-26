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

    vec v3 = v1 + c;

    vr = v3 - 5.0;

    // vr = v1 - c;

    vr = c * vr;

    // vr = vr / 6.0;

    // exp, sqrt, rsum, rmin, rmax probably all need intrinsics

    vec v5 = 3.2 + vr;

    v5 *= 10.1;

    vr = ~v5;


    

    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(v3), "r"(store_addr));

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(vr), "r"(store_addr));

    return 0;
}