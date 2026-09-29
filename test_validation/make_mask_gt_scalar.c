/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 0x00000001
- This test checks the vector-scalar `make_mask` overload. Only lane 0 is
  greater than 1.0 in the seeded input vector.
*/

int main() {
    int addr = 0x1000;

    vec input = vector_load(addr, 1, 31, 1);
    int mask = make_mask(">", input, 1.0, -1);

    return mask;
}
