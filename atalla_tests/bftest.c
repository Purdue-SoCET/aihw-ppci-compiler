void inc_float(float* x){
    *x = *x + 1.0;
}

int main(){
    float a = 5.0;

    float b = 6.7;

    float c = a / b;

    float d = sqrt(c);

    inc_float(&d);

    return d;
}