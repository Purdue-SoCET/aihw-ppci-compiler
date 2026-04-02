int main(){
    vec v1;
    int vec_addr1 = 0xABCD;

    v1 = vector_load(vec_addr1, 1, 31, 1);

    vec v2;
    int vec_addr2 = 0xDEAD;

    v2 = vector_load(vec_addr2, 1, 31, 1);

    vec v3 = v1 + v2;
    vec v4 = v3 - v2;
    vec v5 = v4 * v2;
    vec v6 = v5;

    int mask = 0b101;


    vec v10 = gemm(v5, v6, mask);

    int store_addr = 0xAAAA;

    vector_store(v10, store_addr, 1, 31, 1);

    return 0;
}