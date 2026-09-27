/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 4
- This test checks `load_weights` by loading one sparse vector into the GEMM
  weight buffer, then using `gemm` to observe the resulting lane-0 dot product.
*/

int main() {
    int addr = 0x1000;

    vec weights = vector_load(addr, 1, 31, 1);
    load_weights(weights);

    vec activations = vector_load(addr, 1, 31, 1);
    vec zeros = activations - activations;
    vec result = gemm(activations, zeros, -1);

    return (int)result[0];
}
