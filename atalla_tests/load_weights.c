int main(){

    vec v1;
    int vec_addr1 = 0xABCD;

    asm("vreg_ld %0, %1, %2, 31, 1"
    : "=v"(v1)
    : "r"(vec_addr1), "r"(1));

    load_weights(v1);

    return v1[0];
}