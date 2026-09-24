/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 0xFFFFFFFF
- This test checks the vector-vector `make_mask` overload by comparing a vector
  with itself under a full input mask.
*/

int main() {
    int addr = 0x1000;

    vec input = vector_load(addr, 1, 31, 1);
    int mask = make_mask("==", input, input, -1);

    return mask;
}
