// #include <stdio.h>

void printf(char*, int);


int main() {
    // unsigned int input1 = 10; // Value for x1
    // unsigned int input2 = 20; // Value for x2
    // unsigned int result;      // Will hold the value from x4

    // // The inline assembly block
    // // Format: asm volatile ("assembly code" : outputs : inputs : clobbers)
    // asm(
    //     "theta x10, x11, x12"  // %0 will be replaced by the first constraint, %1 by the second, etc.
    //     : "=r" (result)     // Output operand: Write-only ('=') register ('r'), stored in 'result'
    //     : "r" (input1), "r" (input2) // Input operands: in registers, from 'input1' and 'input2'
    //     :
    // );

    // printf("Result of theta: %u\n", result);
    int a = sizeof(char); // Use %u for unsigned int
    return 0;
}
