int main(){
    int a = 5;

    for(int i = 0; i < 100; i++){
        a += i;
        a *= i;
        a /= i;
    }

    return a;
}