/*
Eight independent vector adds. Each iteration loads two 32-lane vectors,
adds them, and stores the result. Trip count is even and constant.

Addresses step by 64 bytes, one 32-lane bf16 vector.
*/

int main() {
    int a = 0x1000;
    int b = 0x2000;
    int c = 0x3000;

    for (int i = 0; i < 8; i++) {
        vec x = vector_load(a, 1, 31, 1);
        vec y = vector_load(b, 1, 31, 1);
        vec z = x + y;
        vector_store(z, c, 1, 31, 1);
        a += 64;
        b += 64;
        c += 64;
    }

    return 0;
}
