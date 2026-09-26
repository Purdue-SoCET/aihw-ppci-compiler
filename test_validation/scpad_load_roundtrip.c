/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 2
- This test checks `scpad_load` by DMA-loading one 1x32 BF16 row into SP0,
  then reading it back with `vector_load`.
*/

int main() {
    int input_addr = 0x1000;
    int scpad_addr = 0x0000;
    int metadata = 0x01F0001F; /* sid=0, rows=1, cols=32, full_cols=32 */

    scpad_load(scpad_addr, input_addr, metadata);

    vec from_scpad = vector_load(scpad_addr, 0, 31, 0);
    return (int)from_scpad[0];
}
