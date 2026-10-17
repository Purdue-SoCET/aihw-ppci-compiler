/*
Validation target:
- Expected C result: 50 decimal, 0x00000032 hex.
- EXPECT_X10: 50
- After running through functional_sim, check:
  test_validation/out/scalar_sum_loop/output_sregs.out
- The expected value should be in scalar register x10, which carries the
  return value from main on this Atalla flow.
- There is no test-specific data-memory or scratchpad output to validate here.
*/

int main() {
    int total = 5;

    for (int i = 0; i < 10; i++) {
        total += i;
    }

    return total;
}

