int main(){
    vec a;
    int a_addr = 0xABCD;
    a = vector_load(a_addr, 1, 31, 1);

    for(int i = 0; i < 10; i++){
        a += i;
    }

    int store_addr = 0xAAAA;
    vector_store(a, store_addr, 1, 31, 1);

    return 0;
}
