extern int helper(int);
int hi;
int instruct_tests(int a, int b) {
    int r = a + b;

    int h = helper(r); //hopefully generates a jal relocation, it does

    return h + 3;
}

int main() {
    hi = 2;
    hi--;
    int a = 2;
    int b = 3;
    int c = 0;
    c = instruct_tests(a, b);
    return 0;
}