int give_5(){
    return 5;
}

int main(){
    vec vr;
    vec v3;
    vec v4;
    vec v5;

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

    float a = 5.6;
    float b = 10.1;

    float c = a / b;

    v3 = v1 + c;
    v4 = v2 - c;

    vr = v3 * c;
    v5 = v4;

    vr += v5;

    vr *= give_5();

    int store_addr = 0xAAAA;

    asm("vreg_st %0, %1, 0, 0, 0, 0, 0"
    : 
    : "v"(vr), "r"(store_addr));

}