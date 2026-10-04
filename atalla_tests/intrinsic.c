int main(){
    vec v1 = vector_load(0xABCD, 1, 31, 1);
    vec v2 = vector_load(0xDEAD, 1, 31, 1);

    vec v3 = v1 + v2;

    vector_store(v3, 0xABCD, 1, 31, 1);

    return (int)v3[5];
}
