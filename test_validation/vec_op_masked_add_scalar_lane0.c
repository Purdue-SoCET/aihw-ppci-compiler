/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 5
- This test checks the vector-scalar `vec_op_masked` overload with full-lane
  addition.
*/

int main() {
    int addr = 0x1000;
    float a = 1.0;
    float b = 2.0;
    float scalar = a + b;

    vec input = vector_load(addr, 1, 31, 1);
    vec result = vec_op_masked("+", input, scalar, -1);

    return (int)result[0];
}
