/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 2
- This test checks the `vector_store` intrinsic by storing one GMEM-loaded
  vector to a new GMEM address and loading it back.
*/

int main() {
    int input_addr = 0x1000;
    int output_addr = 0x1040;

    vec input = vector_load(input_addr, 1, 31, 1);
    vector_store(input, output_addr, 1, 31, 1);

    vec roundtrip = vector_load(output_addr, 1, 31, 1);
    return (int)roundtrip[0];
}
