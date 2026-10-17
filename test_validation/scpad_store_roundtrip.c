/*
Validation target:
- INPUT_GMEM_BASE: 0x1000
- INPUT_LANE0: 2.0
- INPUT_OTHER_LANES: 0.0
- EXPECT_X10: 2
- This test checks `scpad_store` by DMA-loading a 1x32 BF16 row into SP0,
  DMA-storing it back to a new GMEM address, then reloading it.
*/

int main() {
    int input_addr = 0x1000;
    int output_addr = 0x1040;
    int scpad_addr = 0x0000;
    int metadata = 0x01F0001F; /* sid=0, rows=1, cols=32, full_cols=32 */

    scpad_load(scpad_addr, input_addr, metadata);
    scpad_store(scpad_addr, output_addr, metadata);

    vec roundtrip = vector_load(output_addr, 1, 31, 1);
    return (int)roundtrip[0];
}
