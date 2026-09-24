/*
Validation target:
- EXPECT_X10: 3
- This test checks the scalar `sqrt` intrinsic on an exact BF16 value.
*/

int main() {
    float x = 3.0;
    float square = x * x;
    float y = sqrt(square);

    return (int)y;
}
