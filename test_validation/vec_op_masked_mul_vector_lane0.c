/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 3.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 9
- This test checks the vector-vector `vec_op_masked` overload with full-lane
  multiplication.
*/

int main() {
    int addr = 0x1000;

    vec input = vector_load(addr, 1, 31, 1);
    vec result = vec_op_masked("*", input, input, -1);

    return (int)result[0];
}
