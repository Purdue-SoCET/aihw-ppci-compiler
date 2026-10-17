/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 7.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 7
- This test checks the standalone `gemm` intrinsic path. With no prior
  `load_weights` calls, the simulator's weight buffer is zeroed, so the addend
  vector should pass through unchanged.
*/

int main() {
    int addr = 0x1000;

    vec input = vector_load(addr, 1, 31, 1);
    vec result = gemm(input, input, -1);

    return (int)result[0];
}
