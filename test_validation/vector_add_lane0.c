/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- The runner seeds GMEM at INPUT_GMEM_BASE with 32 BF16 lanes.
- This test performs one simple vector instruction: `doubled = input + input`.
- EXPECT_X10: 4
- After running through functional_sim, check:
  test_validation/out/vector_add_lane0/output_sregs.out
- The expected value should be in scalar register x10, which carries the
  return value from main on this Atalla flow.
*/

int main() {
    int addr = 0x1000;

    vec input = vector_load(addr, 1, 31, 1);
    vec doubled = input + input;

    return (int)doubled[0];
}

