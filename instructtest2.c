extern int helper(int);

int instruct_tests(int a, int b) {
    int r = a + b;

    int h = helper(r); //hopefully generates a jal relocation, it does

    return h + 3;
}
